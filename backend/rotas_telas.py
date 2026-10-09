"""As rotas das tres telas do AxiaAtende: Recepcao, Envios e Destinos. #950, F1 do plano.

So no processo das telas (127.0.0.1:8009), com login. Nenhuma rota daqui fala com a Meta: o que
muda e o banco (o destino de uma opcao, o horario, religar um envio parado), e o recepcionista le
na proxima mensagem.
"""
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .banco import conexao

PRECO_CONVITE = 0.07   # US$ por mensagem paga, por cima (A2 do plano)
WHATS = re.compile(r"^55[1-9][0-9]9?[0-9]{8}$")


def mascarar(numero: str | None) -> str:
    """+55 46 9…·4421: o bastante para reconhecer, nunca o numero inteiro na tela."""
    d = re.sub(r"\D", "", numero or "")
    if len(d) < 10:
        return "sem número"
    return "+%s %s %s…·%s" % (d[:2], d[2:4], d[4], d[-4:])


class Destino(BaseModel):
    nome: str
    whatsapp: str


class Ligacao(BaseModel):
    destino_id: int


class Horario(BaseModel):
    dias: list[int]
    faixas: list[list[str]]


class Avisado(BaseModel):
    destino_id: int


def rotas(cfg, usuario) -> APIRouter:
    r = APIRouter(dependencies=[Depends(usuario)])

    # ── Recepcao ─────────────────────────────────────────────────────────────

    @r.get("/recepcao")
    def recepcao(dias: int = 7, motivo: str = "", situacao: str = ""):
        desde = datetime.now(timezone.utc) - timedelta(days=max(1, min(dias, 365)))
        with conexao(cfg) as con:
            linhas = con.execute(
                """SELECT c.*, d.nome AS destino_nome,
                          (SELECT m.chave FROM atendimento.menu m WHERE m.rotulo = c.caminho[1]
                              AND m.pai_id = (SELECT id FROM atendimento.menu WHERE chave = 'raiz') LIMIT 1) AS motivo,
                          (SELECT ed.erp_codigo || ' · ' || ed.nome FROM atendimento.envio_destinatarios ed
                            WHERE ed.whatsapp = c.wa_id ORDER BY ed.id DESC LIMIT 1) AS cliente
                     FROM atendimento.conversas c
                     LEFT JOIN atendimento.destinos d ON d.id = c.destino_id
                    WHERE c.iniciada_em >= %s ORDER BY c.iniciada_em DESC LIMIT 500""", (desde,)).fetchall()
            motivos = [dict(m) for m in con.execute(
                """SELECT chave, rotulo FROM atendimento.menu
                    WHERE pai_id = (SELECT id FROM atendimento.menu WHERE chave = 'raiz') AND ativo
                      AND acao <> 'encerrar' ORDER BY ordem""")]
        if motivo:
            linhas = [l for l in linhas if l["motivo"] == motivo]
        cartoes = {
            "chegaram": len(linhas),
            "receberam_link": sum(1 for l in linhas if l["link_em"]),
            "pararam_no_meio": sum(1 for l in linhas if l["situacao"] == "parou_no_meio"),
            "disseram_sim": sum(1 for l in linhas if l["recebeu"] is True),
            "disseram_nao": sum(1 for l in linhas if l["recebeu"] is False),
            "ia_acertou": sum(1 for l in linhas if l["ia_confirmou"] is True),
            "ia_errou": sum(1 for l in linhas if l["ia_confirmou"] is False),
        }
        saida = []
        for l in linhas:
            if l["link_em"]:
                estado = ("sim" if l["recebeu"] is True else "nao" if l["recebeu"] is False
                          else "perguntado" if l["pergunta_feita_em"] else "pergunta_marcada")
            else:
                estado = {"parou_no_meio": "parou", "encerrada": "encerrou"}.get(l["situacao"], "em_curso")
            if situacao and estado != situacao:
                continue
            saida.append({"quando": l["iniciada_em"].isoformat(), "cliente": l["cliente"],
                          "numero": mascarar(l["wa_id"]), "perfil": l["nome_perfil"],
                          "caminho": l["caminho"], "destino": l["destino_nome"], "estado": estado,
                          "pergunta_em": l["pergunta_em"].isoformat() if l["pergunta_em"] else None,
                          "aviso_nao_em": l["aviso_nao_em"].isoformat() if l["aviso_nao_em"] else None,
                          "satisfacao": l["satisfacao"], "ia": l["ia_confirmou"]})
        return {"cartoes": cartoes, "motivos": motivos, "linhas": saida}

    # ── Envios ───────────────────────────────────────────────────────────────

    @r.get("/envios")
    def envios():
        with conexao(cfg) as con:
            lista = con.execute(
                """SELECT e.id, e.tipo, e.campanha, e.peca, e.assunto, e.modelo, e.aprovado_por, e.aprovado_em,
                          e.situacao, count(d.*) FILTER (WHERE d.convite_em IS NOT NULL) AS convidados
                     FROM atendimento.envios e LEFT JOIN atendimento.envio_destinatarios d ON d.envio_id = e.id
                    GROUP BY e.id ORDER BY e.id DESC LIMIT 100""").fetchall()
            nota = con.execute("SELECT nota, lida_em FROM atendimento.nota_qualidade ORDER BY lida_em DESC LIMIT 1").fetchone()
        return {"envios": [{**dict(e), "aprovado_em": e["aprovado_em"].isoformat()} for e in lista],
                "nota": dict(nota, lida_em=nota["lida_em"].isoformat()) if nota else None}

    @r.get("/envios/{envio_id}")
    def envio(envio_id: int, responsavel: str = "", resposta: str = ""):
        with conexao(cfg) as con:
            e = con.execute("SELECT * FROM atendimento.envios WHERE id = %s", (envio_id,)).fetchone()
            if not e:
                raise HTTPException(status_code=404, detail="envio não encontrado")
            ds = con.execute("""SELECT * FROM atendimento.envio_destinatarios WHERE envio_id = %s
                                 ORDER BY posicao""", (envio_id,)).fetchall()
        conv = [d for d in ds if d["convite_em"]]
        cartoes = {"convidados": len(conv), "entregues": sum(1 for d in conv if d["entregue_em"]),
                   "lidos": sum(1 for d in conv if d["lido_em"]),
                   "quero": sum(1 for d in ds if d["resposta"] == "quero"),
                   "nao_quero": sum(1 for d in ds if d["resposta"] == "nao_quero"),
                   "nao_entregues": sum(1 for d in ds if d["situacao"] in ("falhou", "nao_e_whatsapp")),
                   "sem_responsavel": sum(1 for d in ds if d["situacao"] == "sem_responsavel"),
                   "sem_aceite": sum(1 for d in ds if d["situacao"] == "sem_aceite"),
                   "aguardando": sum(1 for d in ds if d["situacao"] == "aguardando"),
                   "custo_usd": round(len(conv) * PRECO_CONVITE, 2)}
        linhas = []
        for d in ds:
            if responsavel and d["responsavel_nome"] != responsavel:
                continue
            if resposta and (d["resposta"] or d["situacao"]) != resposta:
                continue
            linhas.append({"codigo": d["erp_codigo"], "nome": d["nome"], "cidade": d["cidade"], "uf": d["uf"],
                           "responsavel": d["responsavel_nome"], "sugestao": d["sugestao_vendedor"],
                           "situacao": d["situacao"], "lote": d["lote"],
                           "convite_em": d["convite_em"].isoformat() if d["convite_em"] else None,
                           "entregue_em": d["entregue_em"].isoformat() if d["entregue_em"] else None,
                           "lido_em": d["lido_em"].isoformat() if d["lido_em"] else None,
                           "resposta": d["resposta"], "resposta_texto": d["resposta_texto"],
                           "resposta_em": d["resposta_em"].isoformat() if d["resposta_em"] else None,
                           "imagens": "%d de %d" % (d["imagens_enviadas"], d["imagens_total"]) if d["imagens_total"] else "",
                           "aviso_recusa_em": d["aviso_recusa_em"].isoformat() if d["aviso_recusa_em"] else None,
                           "erro": d["erro"]})
        resp = sorted({d["responsavel_nome"] for d in ds if d["responsavel_nome"]})
        return {"envio": {**dict(e), "aprovado_em": e["aprovado_em"].isoformat(),
                          "recebido_em": e["recebido_em"].isoformat()},
                "cartoes": cartoes, "responsaveis": resp, "linhas": linhas}

    @r.post("/envios/{envio_id}/religar")
    def religar(envio_id: int):
        """O envio que parou pela nota amarela ou vermelha volta a andar. Decisao do dono, na tela."""
        with conexao(cfg) as con:
            n = con.execute("""UPDATE atendimento.envios SET situacao = 'ativo'
                                WHERE id = %s AND situacao = 'parado_nota'""", (envio_id,)).rowcount
        if not n:
            raise HTTPException(status_code=422, detail="este envio não está parado pela nota")
        return {"religado": envio_id}

    # ── Destinos ─────────────────────────────────────────────────────────────

    @r.get("/destinos")
    def destinos():
        with conexao(cfg) as con:
            folhas = con.execute("""
                WITH RECURSIVE c AS (
                    SELECT id, chave, rotulo, pergunta, acao, destino_id, texto_antes, ordem,
                           ARRAY[]::text[] AS caminho, ARRAY[]::text[] AS perguntas, ARRAY[ordem] AS ord
                      FROM atendimento.menu WHERE chave = 'raiz'
                    UNION ALL
                    SELECT m.id, m.chave, m.rotulo, m.pergunta, m.acao, m.destino_id, m.texto_antes, m.ordem,
                           c.caminho || m.rotulo, c.perguntas || c.pergunta, c.ord || m.ordem
                      FROM atendimento.menu m JOIN c ON m.pai_id = c.id WHERE m.ativo)
                SELECT c.id, c.chave, c.caminho, c.perguntas, c.destino_id, c.texto_antes
                  FROM c WHERE c.acao = 'destino' ORDER BY c.ord""").fetchall()
            ds = con.execute("SELECT id, nome, whatsapp, ativo FROM atendimento.destinos ORDER BY nome").fetchall()
            aj = {a["chave"]: a["valor"] for a in con.execute("SELECT chave, valor FROM atendimento.ajustes")}
        return {"opcoes": [dict(f) for f in folhas], "destinos": [dict(d) for d in ds],
                "horario": aj.get("horario"), "avisado_no_nao": aj.get("avisado_no_nao")}

    def _destino_valido(d: Destino) -> tuple[str, str]:
        numero = re.sub(r"\D", "", d.whatsapp or "")
        if numero and not numero.startswith("55"):
            numero = "55" + numero
        if not d.nome.strip() or not WHATS.match(numero):
            raise HTTPException(status_code=422, detail="nome e WhatsApp com DDD (ex.: 49 99999-0000)")
        return d.nome.strip(), numero

    @r.post("/destinos")
    def novo_destino(d: Destino, u: dict = Depends(usuario)):
        nome, numero = _destino_valido(d)
        with conexao(cfg) as con:
            return dict(con.execute("""INSERT INTO atendimento.destinos (nome, whatsapp, atualizado_por)
                                       VALUES (%s, %s, %s) RETURNING id, nome, whatsapp""",
                                    (nome, numero, u["id"])).fetchone())

    @r.put("/destinos/{destino_id}")
    def mudar_destino(destino_id: int, d: Destino, u: dict = Depends(usuario)):
        nome, numero = _destino_valido(d)
        with conexao(cfg) as con:
            n = con.execute("""UPDATE atendimento.destinos SET nome = %s, whatsapp = %s, atualizado_em = now(),
                                      atualizado_por = %s WHERE id = %s""", (nome, numero, u["id"], destino_id)).rowcount
        if not n:
            raise HTTPException(status_code=404, detail="destino não encontrado")
        return {"id": destino_id, "nome": nome, "whatsapp": numero}

    @r.put("/opcoes/{menu_id}")
    def ligar(menu_id: int, dados: Ligacao):
        """Troca para quem uma opcao do menu manda (vale para a proxima pessoa que chamar)."""
        with conexao(cfg) as con:
            if not con.execute("SELECT 1 FROM atendimento.destinos WHERE id = %s AND ativo", (dados.destino_id,)).fetchone():
                raise HTTPException(status_code=422, detail="destino não existe")
            n = con.execute("""UPDATE atendimento.menu SET destino_id = %s
                                WHERE id = %s AND acao = 'destino'""", (dados.destino_id, menu_id)).rowcount
        if not n:
            raise HTTPException(status_code=404, detail="opção não encontrada")
        return {"ok": True}

    @r.put("/ajustes/horario")
    def horario(h: Horario):
        if not set(h.dias) <= set(range(1, 8)) or not all(
                len(f) == 2 and re.match(r"^\d\d:\d\d$", f[0]) and re.match(r"^\d\d:\d\d$", f[1]) and f[0] < f[1]
                for f in h.faixas):
            raise HTTPException(status_code=422, detail="dias de 1 (segunda) a 7, e faixas HH:MM a HH:MM")
        import json
        with conexao(cfg) as con:
            con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                            WHERE chave = 'horario'""", (json.dumps(h.model_dump()),))
        return h.model_dump()

    @r.put("/ajustes/avisado")
    def avisado(a: Avisado):
        import json
        with conexao(cfg) as con:
            if not con.execute("SELECT 1 FROM atendimento.destinos WHERE id = %s", (a.destino_id,)).fetchone():
                raise HTTPException(status_code=422, detail="destino não existe")
            con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                            WHERE chave = 'avisado_no_nao'""", (json.dumps(a.destino_id),))
        return {"avisado_no_nao": a.destino_id}

    return r
