"""A tela Custos: quanto cada funcao paga por uso custa por mes. #1223 (dono, 31/10/2026).

So no processo das telas, com login, e so para quem esta em `custos_logins` (o resto toma 403, e a
entrada do menu nem aparece). Nenhuma rota daqui fala com a Meta: tudo e leitura do banco, mais o
lancamento de preco.

DE ONDE VEM CADA NUMERO
- Meta: a QUANTIDADE e o `pricing` de cada aviso de status (`eventos_meta`, uma vez por mensagem
  cobrada, `billable`), na CATEGORIA que a Meta cobrou -- nunca a do cadastro (em 30/10 a Meta cobrou
  como marketing um modelo cadastrado UTILITY). A FUNCAO e o `uso` do modelo que saiu
  (`enviadas_texto.modelo`, #1205); antes disso, o tipo do aviso (`avisos`) ou, por ultimo, o comeco
  do resumo do envio (`enviadas.resumo`), marcado "pelo resumo". O que sobra e "sem funcao".
- Claude e Gemini: `uso_ia`, uma linha por chamada, com os tokens que a API devolveu.
- O VALOR e quantidade x o preco vigente no dia (`precos`, o de `vale_desde` mais recente ate o dia).
  Sem preco, a linha diz quantas ficaram sem preco: NUNCA US$ 0.
- O COBRADO da Meta e o que ela mesma informa (`meta_cobrado`, a conferencia diaria). Dia sem leitura
  diz por que (`sem_acesso`, `erro`) ou fica sem conferencia.
"""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .banco import conexao

FUSO = "America/Sao_Paulo"

# As mensagens cobradas do mes, com a funcao de cada uma e o preco vigente no dia.
SQL_META = """
WITH cobradas AS (
    SELECT corpo->>'id' AS wamid,
           max(corpo->'pricing'->>'category') AS categoria,
           (min(recebido_em) AT TIME ZONE %(fuso)s)::date AS dia
      FROM atendimento.eventos_meta
     WHERE tipo = 'status' AND (corpo->'pricing'->>'billable')::boolean
     GROUP BY 1
), do_mes AS (
    SELECT * FROM cobradas WHERE dia >= %(inicio)s AND dia < %(fim)s
), atribuidas AS (
    SELECT c.*,
           CASE WHEN m.uso IS NOT NULL THEN m.uso
                WHEN a.tipo IS NOT NULL THEN 'aviso_' || a.tipo
                WHEN e.resumo LIKE 'material%%' THEN 'convite'
                WHEN e.resumo LIKE 'direta%%' THEN 'direta'
                WHEN e.resumo LIKE 'reabertura%%' THEN 'reabertura'
                ELSE 'sem_funcao' END AS funcao,
           CASE WHEN m.uso IS NOT NULL OR a.tipo IS NOT NULL THEN 'registro'
                WHEN e.resumo LIKE 'material%%' OR e.resumo LIKE 'direta%%' OR e.resumo LIKE 'reabertura%%' THEN 'resumo'
                ELSE 'nenhum' END AS fonte
      FROM do_mes c
      LEFT JOIN atendimento.enviadas_texto t ON t.wamid = c.wamid
      LEFT JOIN atendimento.modelos m ON m.nome = t.modelo
      LEFT JOIN LATERAL (SELECT tipo FROM atendimento.avisos WHERE wamid = c.wamid LIMIT 1) a ON true
      LEFT JOIN LATERAL (SELECT resumo FROM atendimento.enviadas WHERE wamid = c.wamid LIMIT 1) e ON true
)
SELECT x.*, p.por_mensagem AS preco, p.moeda
  FROM atribuidas x
  LEFT JOIN LATERAL (SELECT por_mensagem, moeda FROM atendimento.precos
                      WHERE servico = 'meta' AND item = x.categoria AND vale_desde <= x.dia
                      ORDER BY vale_desde DESC LIMIT 1) p ON true
"""

# As chamadas a modelo do mes, com o preco vigente no dia.
SQL_IA = """
SELECT u.servico, u.funcao, u.modelo, u.entrada, u.saida, u.origem,
       p.por_milhao_entrada, p.por_milhao_saida, p.moeda
  FROM atendimento.uso_ia u
  LEFT JOIN LATERAL (SELECT por_milhao_entrada, por_milhao_saida, moeda FROM atendimento.precos
                      WHERE servico = u.servico AND item = u.modelo
                        AND vale_desde <= (u.em AT TIME ZONE %(fuso)s)::date
                      ORDER BY vale_desde DESC LIMIT 1) p ON true
 WHERE (u.em AT TIME ZONE %(fuso)s)::date >= %(inicio)s AND (u.em AT TIME ZONE %(fuso)s)::date < %(fim)s
"""


class Preco(BaseModel):
    servico: str = Field(pattern="^(meta|claude|gemini)$")
    item: str = Field(min_length=1, max_length=80)
    vale_desde: date
    por_mensagem: Decimal | None = Field(default=None, ge=0)
    por_milhao_entrada: Decimal | None = Field(default=None, ge=0)
    por_milhao_saida: Decimal | None = Field(default=None, ge=0)
    moeda: str = Field(default="USD", pattern="^[A-Z]{3}$")


def _mes(texto: str | None) -> tuple[date, date]:
    hoje = date.today()
    try:
        a, m = (int(x) for x in (texto or "").split("-"))
        inicio = date(a, m, 1)
    except ValueError:
        inicio = hoje.replace(day=1)
    fim = date(inicio.year + (inicio.month == 12), inicio.month % 12 + 1, 1)
    return inicio, fim


def _soma(linhas: dict, chave: tuple, quantidade: int, valor, moeda: str | None, extra: dict) -> None:
    """Acumula uma linha da tabela. `valor` None = sem preco naquele dia: conta, mas nao soma."""
    l = linhas.setdefault(chave, dict(extra, quantidade=0, valor=0.0, sem_preco=0, moedas=set()))
    l["quantidade"] += quantidade
    if valor is None:
        l["sem_preco"] += quantidade
    else:
        l["valor"] += float(valor)
        if moeda:
            l["moedas"].add(moeda)


def montar(con, inicio: date, fim: date) -> dict:
    parametros = {"fuso": FUSO, "inicio": inicio, "fim": fim}
    linhas: dict = {}
    por_dia: dict = {}
    for r in con.execute(SQL_META, parametros):
        valor = r["preco"]
        _soma(linhas, ("meta", r["funcao"], r["categoria"], r["fonte"]), 1, valor, r["moeda"],
              {"servico": "meta", "funcao": r["funcao"], "item": r["categoria"], "fonte": r["fonte"],
               "unidade": "mensagens"})
        d = por_dia.setdefault(r["dia"], {"quantidade": 0, "calculado": 0.0, "sem_preco": 0})
        d["quantidade"] += 1
        if valor is None:
            d["sem_preco"] += 1
        else:
            d["calculado"] += float(valor)
    for r in con.execute(SQL_IA, parametros):
        if r["por_milhao_entrada"] is None:
            valor = None
        else:
            valor = (Decimal(r["entrada"]) * r["por_milhao_entrada"] + Decimal(r["saida"]) * r["por_milhao_saida"]) / 1_000_000
        _soma(linhas, (r["servico"], r["funcao"], r["modelo"], r["origem"]), 1, valor, r["moeda"],
              {"servico": r["servico"], "funcao": r["funcao"], "item": r["modelo"], "fonte": r["origem"],
               "unidade": "chamadas", "entrada": 0, "saida": 0})
        l = linhas[(r["servico"], r["funcao"], r["modelo"], r["origem"])]
        l["entrada"] += r["entrada"]
        l["saida"] += r["saida"]
    conferencia = {r["dia"]: dict(r) for r in con.execute(
        "SELECT dia, situacao, detalhe FROM atendimento.meta_conferencia WHERE dia >= %s AND dia < %s", (inicio, fim))}
    cobrado: dict = {}
    # o volume que se compara e o das mensagens COBRADAS: as de servico vem na leitura com custo zero
    for r in con.execute("""SELECT dia, sum(custo) AS custo, coalesce(sum(volume) FILTER (WHERE custo > 0), 0) AS volume,
                                   max(moeda) AS moeda
                              FROM atendimento.meta_cobrado WHERE dia >= %s AND dia < %s GROUP BY dia""", (inicio, fim)):
        cobrado[r["dia"]] = r
    dias = []
    for dia in sorted(set(por_dia) | set(conferencia) | set(cobrado)):
        c = conferencia.get(dia)
        situacao = c["situacao"] if c else "sem_conferencia"
        dias.append({"dia": dia.isoformat(), **por_dia.get(dia, {"quantidade": 0, "calculado": 0.0, "sem_preco": 0}),
                     "situacao": situacao, "detalhe": c["detalhe"] if c else "",
                     "cobrado": float(cobrado[dia]["custo"]) if situacao == "ok" and dia in cobrado else (0.0 if situacao == "ok" else None),
                     "cobrado_volume": int(cobrado[dia]["volume"]) if dia in cobrado else None,
                     "moeda": cobrado[dia]["moeda"] if dia in cobrado else ""})
    saida = []
    for l in sorted(linhas.values(), key=lambda x: (x["servico"], -x["valor"], x["funcao"])):
        saida.append(dict(l, valor=round(l["valor"], 4), moedas=sorted(l["moedas"])))
    return {"mes": inicio.strftime("%Y-%m"), "linhas": saida, "meta_dias": dias}


def rotas(cfg, usuario) -> APIRouter:
    r = APIRouter(dependencies=[Depends(usuario)])

    def dono(u: dict = Depends(usuario)) -> dict:
        if (u.get("login") or "").lower() not in cfg.custos_logins:
            raise HTTPException(status_code=403, detail="a tela Custos não está liberada para o seu usuário")
        return u

    @r.get("/custos/permitido")
    def permitido(u: dict = Depends(usuario)):
        return {"permitido": (u.get("login") or "").lower() in cfg.custos_logins}

    @r.get("/custos")
    def custos(mes: str = "", u: dict = Depends(dono)):
        inicio, fim = _mes(mes)
        with conexao(cfg) as con:
            return montar(con, inicio, fim)

    @r.get("/custos/precos")
    def precos(u: dict = Depends(dono)):
        with conexao(cfg) as con:
            linhas = [dict(p, vale_desde=p["vale_desde"].isoformat(), criado_em=p["criado_em"].isoformat(),
                           por_mensagem=float(p["por_mensagem"]) if p["por_mensagem"] is not None else None,
                           por_milhao_entrada=float(p["por_milhao_entrada"]) if p["por_milhao_entrada"] is not None else None,
                           por_milhao_saida=float(p["por_milhao_saida"]) if p["por_milhao_saida"] is not None else None)
                      for p in con.execute(
                          """SELECT p.id, p.servico, p.item, p.vale_desde, p.por_mensagem, p.por_milhao_entrada,
                                    p.por_milhao_saida, p.moeda, p.criado_em, coalesce(u.nome, '') AS criado_por
                               FROM atendimento.precos p LEFT JOIN casa.usuarios u ON u.id = p.criado_por
                              ORDER BY p.servico, p.item, p.vale_desde DESC""")]
            # o que ja apareceu e ainda pode pedir preco: as categorias que a Meta cobrou e os modelos usados
            itens = {"meta": [x["c"] for x in con.execute(
                         """SELECT DISTINCT corpo->'pricing'->>'category' AS c FROM atendimento.eventos_meta
                             WHERE tipo = 'status' AND (corpo->'pricing'->>'billable')::boolean ORDER BY 1""")],
                     "claude": [], "gemini": []}
            for x in con.execute("SELECT DISTINCT servico, modelo FROM atendimento.uso_ia ORDER BY 2"):
                itens[x["servico"]].append(x["modelo"])
        return {"precos": linhas, "itens": itens}

    @r.post("/custos/precos")
    def lancar_preco(p: Preco, u: dict = Depends(dono)):
        if p.servico == "meta" and p.por_mensagem is None:
            raise HTTPException(status_code=422, detail="na Meta, informe o valor por mensagem")
        if p.servico != "meta" and (p.por_milhao_entrada is None or p.por_milhao_saida is None):
            raise HTTPException(status_code=422, detail="informe o valor por milhão de tokens de entrada e de saída")
        with conexao(cfg) as con:
            existe = con.execute("SELECT 1 FROM atendimento.precos WHERE servico = %s AND item = %s AND vale_desde = %s",
                                 (p.servico, p.item.strip(), p.vale_desde)).fetchone()
            if existe:
                raise HTTPException(status_code=409, detail="já há preço para esse item nessa data; lance com outra data")
            novo = con.execute(
                """INSERT INTO atendimento.precos (servico, item, vale_desde, por_mensagem, por_milhao_entrada,
                                                   por_milhao_saida, moeda, criado_por)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (p.servico, p.item.strip(), p.vale_desde, p.por_mensagem if p.servico == "meta" else None,
                 p.por_milhao_entrada if p.servico != "meta" else None,
                 p.por_milhao_saida if p.servico != "meta" else None, p.moeda, u["id"])).fetchone()
        return {"id": novo["id"]}

    return r
