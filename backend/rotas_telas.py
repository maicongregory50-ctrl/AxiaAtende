"""As rotas das tres telas do AxiaAtende: Recepcao, Envios e Destinos. #950, F1 do plano.

So no processo das telas (127.0.0.1:8009), com login. Nenhuma rota daqui fala com a Meta: o que
muda e o banco (o destino de uma opcao, o horario, religar um envio parado), e o recepcionista le
na proxima mensagem.
"""
import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import agenda, leitura
from .banco import conexao

PRECO_CONVITE = 0.07   # US$ por mensagem paga, por cima (A2 do plano)
WHATS = re.compile(r"^55[1-9][0-9]9?[0-9]{8}$")


def estado_do_aviso(a) -> dict:
    """#1188: um aviso a equipe na tela Envios. O estado, e a hora em que ele aconteceu:
    `texto` e `modelo` (saiu: de graca, ou pago), `guardado` (esperando o toque em Ver da reabertura),
    `nao_visto` (7 dias sem o toque), `erro` (a Meta recusou) e `na_fila` (ainda nao saiu)."""
    if a["erro"]:
        estado, em = "erro", None
    elif a["enviado_em"]:
        estado, em = ("texto" if a["como"] == "texto" else "modelo"), a["enviado_em"]
    elif a["nao_visto_em"]:
        estado, em = "nao_visto", a["nao_visto_em"]
    elif a["guardado_em"]:
        estado, em = "guardado", a["guardado_em"]
    else:
        estado, em = "na_fila", None
    return {"id": a["id"], "tipo": a["tipo"], "para": a["para_nome"], "numero": mascarar(a["para_whatsapp"]),
            "estado": estado, "em": em.isoformat() if em else None, "criado_em": a["criado_em"].isoformat(),
            "erro": a["erro"]}


def mascarar(numero: str | None) -> str:
    """+55 46 9…·4421: o bastante para reconhecer, nunca o numero inteiro na tela."""
    d = re.sub(r"\D", "", numero or "")
    if len(d) < 10:
        return "sem número"
    return "+%s %s %s…·%s" % (d[:2], d[2:4], d[4], d[-4:])


def link_conversa(numero: str | None) -> str | None:
    """O endereco que abre a conversa no WhatsApp Web de QUEM ESTA NA TELA, ou None (#1025).

    Quem monta o endereco e aqui, nao a tela: a forma do numero e o endereco mudam num lugar so, e
    tirar o campo da resposta apaga todo link da Recepcao -- e o rollback parcial da etapa.

    O numero vai COMO A META O ENTREGOU (`wa_id`), que e o identificador da conta de WhatsApp, e nao
    pela forma `com_nove` do cadastro do ERP: 31 dos 33 wa_id medidos em 15/10/2026 vem sem o nono
    digito, e acrescenta-lo daria um numero diferente do que a conta usa.

    O limiar e o MESMO da mascara de cima: o que ela chama de "sem numero" nao vira link, para o
    texto e o endereco nunca discordarem.
    """
    d = re.sub(r"\D", "", numero or "")
    if len(d) < 10:
        return None
    return "https://web.whatsapp.com/send?phone=%s" % d


def _registrar_leitura(cfg, u: dict, conversa_id: int, itens: int) -> None:
    """#1205: a linha do registro das leituras da TELA. Um escritor por arquivo (regra do #981): o
    `leituras.jsonl` da raiz e so do script da sessao; este e so desta rota. Falhar ao registrar nao
    tira a leitura de quem pediu -- vai ao log do servico, como o script faz no stderr."""
    try:
        arquivo = cfg.logs / "telas" / "leituras.jsonl"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(json.dumps({"quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "quem": u.get("login"), "conversa": conversa_id, "itens": itens},
                               ensure_ascii=False) + "\n")
    except OSError as e:
        print("telas: registro da leitura falhou: %s" % e, flush=True)


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


class CanalDeCampo(BaseModel):
    ligado: bool


class Triagem(BaseModel):
    ligada: bool


# #1249 (dono, 04/11/2026): "cada numero que entra gera UMA linha de conversa, atualizada com a data e hora
# da ultima mensagem, recebida ou enviada; nao varias linhas; fica tudo num historico so". A Recepcao
# deixa de listar atendimentos e passa a listar CONTATOS: um por numero, ordenado pela ultima mensagem em
# qualquer sentido, com o ultimo atendimento (caminho, destino, situacao) e o que ficou pendente com a
# pessoa. Quem e da casa (foto, logo, audio, chamado, sem abrir conversa) entra pela mesma regra. So
# leitura: nenhuma conversa nasce, nenhum fio muda. O clique abre a pessoa inteira pelo numero (#1205).
def _sem_nove(numero: str | None) -> str:
    n = "".join(ch for ch in (numero or "") if ch.isdigit())
    return n[:4] + n[5:] if len(n) == 13 and n.startswith("55") and n[4] == "9" else n


def _pendencias_de(con, chave: str) -> str:
    from .envio import com_nove
    n = com_nove(chave)
    pend = []
    if con.execute("""SELECT 1 FROM atendimento.material_de_campo WHERE wa_id IN (%s, %s)
                       AND pergunta_pendente IS NOT NULL AND recebido_em > now() - interval '1 day' LIMIT 1""",
                   (chave, n)).fetchone():
        pend.append("foto sem legenda")
    if con.execute("""SELECT 1 FROM atendimento.logos_de_cliente WHERE wa_id IN (%s, %s)
                       AND pergunta_pendente IS NOT NULL LIMIT 1""", (chave, n)).fetchone():
        pend.append("logo sem cliente")
    if con.execute("SELECT 1 FROM atendimento.pendencias WHERE para_whatsapp = %s AND espera IS NOT NULL LIMIT 1",
                   (n,)).fetchone():
        pend.append("chamado esperando resposta")
    if con.execute("""SELECT 1 FROM atendimento.clientes_registros WHERE wa_id IN (%s, %s)
                       AND estado IN ('aberto', 'conferir') AND criado_em > now() - interval '1 day' LIMIT 1""",
                   (chave, n)).fetchone():
        pend.append("cliente aberto em Meus clientes")
    return " · ".join(pend)


def _estado_da_conversa(l) -> str:
    if l["link_em"]:
        # #969: uma pergunta por dia; as outras conversas do dia ficam cobertas por ela
        return ("sim" if l["recebeu"] is True else "nao" if l["recebeu"] is False
                else "pergunta_marcada" if not l["pergunta_feita_em"]
                else "perguntado" if l["pergunta_da"] == l["id"]
                else "coberta" if l["pergunta_da"] else "sem_pergunta")
    # #1098: a conversa de vaga termina com ou sem curriculo, nunca "parou no meio"
    return {"parou_no_meio": "parou", "encerrada": "encerrou", "curriculo_recebido": "curriculo",
            "sem_curriculo": "sem_curriculo",
            # #1097: a equipe tocou "Foto do campo" e a foto (ou a logo) chegou
            "imagem_recebida": "imagem", "logo_recebida": "logo"}.get(l["situacao"], "em_curso")


def _contatos(con, desde, conversas) -> list[dict]:
    """Um contato por numero: a ultima mensagem recebida, a ultima enviada, o ultimo atendimento
    (de `conversas`, ja ordenadas da mais nova para a mais velha) e as pendencias."""
    contatos: dict[str, dict] = {}

    def c(chave):
        return contatos.setdefault(chave, {"recebida": None, "enviada": None, "recebidas": 0, "enviadas": 0,
                                           "uteis": 0, "perfil": None, "wa_id": None, "conversa": None})

    for e in con.execute("""SELECT corpo->'msg'->>'from' AS de, max(recebido_em) AS em, count(*) AS n,
                                   count(*) FILTER (WHERE coalesce(corpo->'msg'->>'type', '') NOT IN ('unsupported', 'reaction')) AS uteis,
                                   max(corpo->'contacts'->0->'profile'->>'name') AS perfil
                              FROM atendimento.eventos_meta
                             WHERE tipo = 'mensagem' AND recebido_em >= %s AND corpo->'msg'->>'from' IS NOT NULL
                             GROUP BY 1""", (desde,)).fetchall():
        x = c(_sem_nove(e["de"]))
        x.update(recebida=e["em"], recebidas=e["n"], uteis=e["uteis"], perfil=e["perfil"] or x["perfil"], wa_id=e["de"])
    for s in con.execute("""SELECT para, max(enviada_em) AS em, count(*) AS n FROM atendimento.enviadas
                             WHERE enviada_em >= %s AND para ~ '^[0-9]+$' GROUP BY 1""", (desde,)).fetchall():
        x = c(_sem_nove(s["para"]))
        x.update(enviada=s["em"], enviadas=s["n"])
    for l in conversas:   # a mais nova de cada numero
        x = c(_sem_nove(l["wa_id"] or l["bsuid"]))
        if x["conversa"] is None:
            x["conversa"] = l
            x["perfil"] = x["perfil"] or l["nome_perfil"]
            x["wa_id"] = x["wa_id"] or l["wa_id"]
    linhas = []
    for chave, x in contatos.items():
        l = x["conversa"]
        # dono, 04/11/2026: "vamos remover o robo, se for a unica movimentacao". O numero de quem so mandou
        # mensagem sem tipo (ou reacao) e nao teve atendimento nao e contato: e maquina batendo na porta.
        if l is None and x["recebidas"] and x["uteis"] == 0:
            continue
        quando = max(q for q in (x["recebida"], x["enviada"], l["ultimo_toque_em"] if l else None,
                                 l["iniciada_em"] if l else None) if q is not None)
        quem = agenda.reconhecer(con, chave) or {"erp_cadastros": None}
        cadastros = quem.get("erp_cadastros")
        cadastro = ({"codigo": quem["erp_codigo"], "nome": quem["erp_nome"], "papeis": quem["erp_papeis"] or [],
                     "contato_setor": quem["erp_contato_setor"], "contato_nome": quem["erp_contato_nome"]}
                    if cadastros == 1 else None)
        interno = bool(cadastro and any(p in ("equipe", "representante") for p in cadastro["papeis"]))
        if l:
            estado, caminho, destino = _estado_da_conversa(l), l["caminho"], l["destino_nome"]
        else:
            estado, caminho, destino = ("equipe" if interno else "contato"), [], None
        wa = x["wa_id"] or chave
        linhas.append({"id": l["id"] if l else None, "pessoa": wa, "quando": quando.isoformat(),
                       "recebida_em": x["recebida"].isoformat() if x["recebida"] else None,
                       "enviada_em": x["enviada"].isoformat() if x["enviada"] else None,
                       "recebidas": x["recebidas"], "enviadas": x["enviadas"],
                       "cadastro": cadastro, "cadastros": cadastros, "interno": interno,
                       "numero": mascarar(wa), "conversar": link_conversa(wa), "perfil": x["perfil"],
                       "caminho": caminho, "destino": destino, "estado": estado,
                       "motivo": l["motivo"] if l else None,
                       "pendente": _pendencias_de(con, chave),
                       "pergunta_em": l["pergunta_em"].isoformat() if l and l["pergunta_em"] else None,
                       "aviso_nao_em": l["aviso_nao_em"].isoformat() if l and l["aviso_nao_em"] else None,
                       "satisfacao": l["satisfacao"] if l else None, "ia": l["ia_confirmou"] if l else None})
    linhas.sort(key=lambda r: r["quando"], reverse=True)
    return linhas


def rotas(cfg, usuario) -> APIRouter:
    r = APIRouter(dependencies=[Depends(usuario)])

    # ── Recepcao ─────────────────────────────────────────────────────────────

    @r.get("/recepcao")
    def recepcao(dias: int = 7, motivo: str = "", situacao: str = "", quem: str = ""):
        desde = datetime.now(timezone.utc) - timedelta(days=max(1, min(dias, 365)))
        with conexao(cfg) as con:
            conversas = con.execute(
                """SELECT c.*, d.nome AS destino_nome,
                          (SELECT m.chave FROM atendimento.menu m WHERE m.rotulo = c.caminho[1]
                              AND m.pai_id = (SELECT id FROM atendimento.menu WHERE chave = 'raiz') LIMIT 1) AS motivo
                     FROM atendimento.conversas c
                     LEFT JOIN atendimento.destinos d ON d.id = c.destino_id
                    WHERE c.iniciada_em >= %s
                      AND c.origem = 'mensagem'   -- #1204 (dono, 30/10): a que nos abrimos nao aparece aqui
                    ORDER BY c.iniciada_em DESC LIMIT 500""", (desde,)).fetchall()
            motivos = [dict(m) for m in con.execute(
                """SELECT chave, rotulo FROM atendimento.menu
                    WHERE pai_id = (SELECT id FROM atendimento.menu WHERE chave = 'raiz') AND ativo
                      AND acao <> 'encerrar' ORDER BY ordem""")]
            leitura = agenda.ultima_leitura(con)
            # #970: o que a equipe mandou pelo canal de campo no mesmo periodo (nao e conversa)
            campo = con.execute("""SELECT count(*) AS n, count(*) FILTER (WHERE catalogado_em IS NOT NULL) AS c
                                     FROM atendimento.material_de_campo WHERE recebido_em > now() - %s * interval '1 day'""",
                                (dias,)).fetchone()
            # #1249: um contato por numero (a lista); os cartoes continuam contando atendimentos
            contatos = _contatos(con, desde, conversas)
        linhas = conversas
        if motivo:
            linhas = [l for l in linhas if l["motivo"] == motivo]
            contatos = [r for r in contatos if r["motivo"] == motivo]
        # #969: so do cadastro / so fora dele (quem nao foi conferido -- agenda vazia -- fica nos dois de fora)
        if quem == "cadastro":
            linhas = [l for l in linhas if l["erp_cadastros"] == 1]
            contatos = [r for r in contatos if r["cadastros"] == 1]
        elif quem == "fora":
            linhas = [l for l in linhas if l["erp_cadastros"] != 1]
            contatos = [r for r in contatos if r["cadastros"] != 1]
        if situacao == "equipe":
            contatos = [r for r in contatos if r["interno"]]
        elif situacao:
            contatos = [r for r in contatos if r["estado"] == situacao]
        estados = [_estado_da_conversa(l) for l in linhas]
        cartoes = {
            "contatos": len(contatos), "equipe": sum(1 for r in contatos if r["interno"]),
            "campo": campo["n"], "campo_catalogadas": campo["c"],
            "chegaram": len(linhas),
            "do_cadastro": sum(1 for l in linhas if l["erp_cadastros"] == 1),
            "receberam_link": sum(1 for l in linhas if l["link_em"]),
            "pararam_no_meio": sum(1 for l in linhas if l["situacao"] == "parou_no_meio"),
            "disseram_sim": sum(1 for l in linhas if l["recebeu"] is True),
            "disseram_nao": sum(1 for l in linhas if l["recebeu"] is False),
            "ia_acertou": sum(1 for l in linhas if l["ia_confirmou"] is True),
            "ia_errou": sum(1 for l in linhas if l["ia_confirmou"] is False),
            "estados": {e: estados.count(e) for e in set(estados)},
        }
        return {"cartoes": cartoes, "motivos": motivos, "linhas": contatos, "leitura": leitura}

    @r.get("/recepcao/pessoa/{numero}")
    def ler_pessoa(numero: str, u: dict = Depends(usuario)):
        """#1249: a janela da Recepcao pelo NUMERO -- a pessoa inteira, um historico so, de dentro ou de
        fora da casa (#1205 abre pelo atendimento; esta, pelo contato). So le; registrada como a leitura
        de conversa."""
        numero = "".join(ch for ch in numero if ch.isdigit())
        if not numero:
            raise HTTPException(status_code=404, detail="número vazio")
        with conexao(cfg) as con:
            quem = agenda.reconhecer(con, numero) or {}
            perfil = con.execute("""SELECT nome_perfil FROM atendimento.conversas
                                     WHERE wa_id IN (%s, %s) AND nome_perfil <> '' ORDER BY id DESC LIMIT 1""",
                                 (numero, _sem_nove(numero))).fetchone()
            _, _, lista = leitura.itens(con, numero)
        itens = [{"quando": i["quando"].isoformat(), "lado": i["lado"], "tipo": i["tipo"], "texto": i["texto"],
                  "opcoes": i["opcoes"], "estado": i["estado"], "erro": i["erro"], "resumo": i["resumo"],
                  "destaque": False} for i in lista]
        _registrar_leitura(cfg, u, 0, len(itens))
        da_casa = quem.get("erp_cadastros") == 1
        return {"pessoa": {"nome": (quem.get("erp_nome") if da_casa else None) or (perfil["nome_perfil"] if perfil else None) or "sem nome",
                           "codigo": quem.get("erp_codigo") if da_casa else None,
                           "numero": mascarar(numero)}, "itens": itens}

    @r.get("/recepcao/conversa/{conversa_id}")
    def ler_conversa(conversa_id: int, u: dict = Depends(usuario)):
        """#1205: a janela da Recepcao. A PESSOA inteira daquela conversa (dono, 30/10: "a pessoa
        inteira"), em ordem, com o atendimento clicado em destaque. So le; cada abertura fica
        registrada, como a leitura da sessao (#981) -- num arquivo proprio das telas, um escritor."""
        with conexao(cfg) as con:
            c = con.execute("SELECT id, wa_id, bsuid, nome_perfil, erp_nome, erp_codigo, erp_cadastros "
                            "FROM atendimento.conversas WHERE id = %s", (conversa_id,)).fetchone()
            if not c:
                raise HTTPException(status_code=404, detail="conversa não encontrada")
            _, _, lista = leitura.itens(con, c["wa_id"], c["bsuid"])
        # o atendimento clicado: do marco dele ate o marco do proximo atendimento da pessoa
        inicio = fim = None
        for i in lista:
            if i["tipo"] == "atendimento":
                if inicio is not None and fim is None:
                    fim = i["quando"]
                if i["conversa_id"] == conversa_id:
                    inicio = i["quando"]
        itens = [{"quando": i["quando"].isoformat(), "lado": i["lado"], "tipo": i["tipo"], "texto": i["texto"],
                  "opcoes": i["opcoes"], "estado": i["estado"], "erro": i["erro"], "resumo": i["resumo"],
                  "destaque": inicio is not None and i["quando"] >= inicio and (fim is None or i["quando"] < fim)}
                 for i in lista]
        _registrar_leitura(cfg, u, conversa_id, len(itens))
        return {"pessoa": {"nome": (c["erp_nome"] if c["erp_cadastros"] == 1 else None) or c["nome_perfil"] or "sem nome",
                           "codigo": c["erp_codigo"] if c["erp_cadastros"] == 1 else None,
                           "numero": mascarar(c["wa_id"])},
                "itens": itens}

    # ── Envios ───────────────────────────────────────────────────────────────

    @r.get("/envios")
    def envios():
        with conexao(cfg) as con:
            lista = con.execute(
                """SELECT e.id, e.tipo, e.campanha, e.peca, e.assunto, e.modelo, e.aprovado_por, e.aprovado_em,
                          e.situacao, e.suspenso_por, e.suspenso_em,
                          count(d.*) FILTER (WHERE d.convite_em IS NOT NULL) AS convidados
                     FROM atendimento.envios e LEFT JOIN atendimento.envio_destinatarios d ON d.envio_id = e.id
                    GROUP BY e.id ORDER BY e.id DESC LIMIT 100""").fetchall()
            nota = con.execute("SELECT nota, lida_em FROM atendimento.nota_qualidade ORDER BY lida_em DESC LIMIT 1").fetchone()
            avisos = con.execute("""SELECT * FROM atendimento.avisos WHERE criado_em > now() - interval '30 days'
                                     ORDER BY id DESC LIMIT 200""").fetchall()
            # #1222: o chamado no WhatsApp -- o que saiu e o que voltou, com o estado de cada mensagem
            chamados = con.execute("""SELECT m.id, m.sentido, m.classe, m.estado, m.resultado, m.erro,
                                             left(m.texto, 140) AS texto, m.criado_em,
                                             coalesce(m.entregue_em, m.enviada_em) AS em,
                                             p.referencia, p.titulo, p.para_whatsapp, p.espera
                                        FROM atendimento.pendencias_mensagens m
                                        JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                                       WHERE m.criado_em > now() - interval '30 days'
                                       ORDER BY m.id DESC LIMIT 200""").fetchall()
            from . import segurar
            segurado = segurar.estado(con)   # #1169
        return {"segurado": segurado,
                "envios": [{**dict(e), "aprovado_em": e["aprovado_em"].isoformat(),
                            "suspenso_em": e["suspenso_em"].isoformat() if e["suspenso_em"] else None} for e in lista],
                "nota": dict(nota, lida_em=nota["lida_em"].isoformat()) if nota else None,
                "avisos": [estado_do_aviso(a) for a in avisos],
                "chamados": [{**{k: c[k] for k in ("id", "sentido", "classe", "estado", "resultado", "erro", "texto",
                                                   "referencia", "titulo", "espera")},
                              "numero": mascarar(c["para_whatsapp"]), "criado_em": c["criado_em"].isoformat(),
                              "em": c["em"].isoformat() if c["em"] else None} for c in chamados]}

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
                           "sem_convite": bool(d.get("sem_convite")),   # #1267: saiu na janela aberta
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
    def religar(envio_id: int, u: dict = Depends(usuario)):
        """O envio parado pela nota ou suspenso volta a andar, com quem e quando (#1169)."""
        from . import segurar
        with conexao(cfg) as con:
            try:
                segurar.religar(con, envio_id, u.get("login") or "?", datetime.now(timezone.utc))
            except segurar.Recusa as e:
                raise HTTPException(status_code=422, detail=str(e)) from None
        return {"religado": envio_id}

    @r.post("/envios/{envio_id}/suspender")
    def suspender(envio_id: int, u: dict = Depends(usuario)):
        """#1169: o envio para; quem ainda nao recebeu o convite fica na fila, sem perder a posicao."""
        from . import segurar
        with conexao(cfg) as con:
            try:
                segurar.suspender(con, envio_id, u.get("login") or "?", datetime.now(timezone.utc))
            except segurar.Recusa as e:
                raise HTTPException(status_code=422, detail=str(e)) from None
        return {"suspenso": envio_id}

    class Segurar(BaseModel):
        ligado: bool

    @r.put("/ajustes/segurar-envio")
    def segurar_envio(dados: Segurar, u: dict = Depends(usuario)):
        """#1169: o "segurar tudo". Ligado, nenhum convite sai e todo pedido novo nasce suspenso."""
        from . import segurar
        agora = datetime.now(timezone.utc)
        with conexao(cfg) as con:
            n = (segurar.ligar if dados.ligado else segurar.desligar)(con, u.get("login") or "?", agora)
            est = segurar.estado(con)
        return {**est, "envios": n}

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
                  FROM c WHERE c.acao IN ('destino', 'vaga') ORDER BY c.ord""").fetchall()
            vagas = con.execute("""SELECT id, titulo, aberta, triagem_ligada, fechada_em,
                                          (SELECT count(*) FROM atendimento.candidaturas k WHERE k.vaga_id = v.id) AS curriculos
                                     FROM atendimento.vagas v ORDER BY aberta DESC, id DESC LIMIT 5""").fetchall()
            ds = con.execute("SELECT id, nome, whatsapp, ativo FROM atendimento.destinos ORDER BY nome").fetchall()
            aj = {a["chave"]: a["valor"] for a in con.execute("SELECT chave, valor FROM atendimento.ajustes")}
        return {"opcoes": [dict(f) for f in folhas], "destinos": [dict(d) for d in ds],
                "horario": aj.get("horario"), "avisado_no_nao": aj.get("avisado_no_nao"),
                "campo_ligado": aj.get("campo.ligado") is True,   # #970: o canal de campo
                "vagas": [dict(v, fechada_em=v["fechada_em"].isoformat() if v["fechada_em"] else None)
                          for v in vagas]}   # #1098: a vaga aberta e o interruptor da pre-triagem

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
                                WHERE id = %s AND acao IN ('destino', 'vaga')""", (dados.destino_id, menu_id)).rowcount
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

    @r.put("/ajustes/campo")
    def canal_de_campo(dados: CanalDeCampo):
        """#970: a chave do canal de campo (decisao 8 do dono). Desligada, a foto da equipe volta a
        ser so gravada, como sempre foi; nada se apaga."""
        with conexao(cfg) as con:
            con.execute("""INSERT INTO atendimento.ajustes (chave, valor) VALUES ('campo.ligado', %s::jsonb)
                           ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor, atualizado_em = now()""",
                        ("true" if dados.ligado else "false",))
        return {"campo_ligado": dados.ligado}

    @r.post("/vagas/{vaga_id}/fechar")
    def fechar_vaga(vaga_id: int):
        """#1098: fechada, o anuncio cai no menu de sempre e o "Trabalhe conosco" diz que nao ha vaga
        aberta (e aceita o PDF para as proximas). Nada se apaga."""
        with conexao(cfg) as con:
            n = con.execute("""UPDATE atendimento.vagas SET aberta = false, fechada_em = now()
                                WHERE id = %s AND aberta""", (vaga_id,)).rowcount
        if not n:
            raise HTTPException(status_code=422, detail="esta vaga não está aberta")
        return {"fechada": vaga_id}

    @r.put("/vagas/{vaga_id}/triagem")
    def triagem(vaga_id: int, dados: Triagem):
        """#1098: o interruptor da pre-triagem. Desligada, o curriculo vai a Fran igual, sem a leitura da IA."""
        with conexao(cfg) as con:
            n = con.execute("UPDATE atendimento.vagas SET triagem_ligada = %s WHERE id = %s",
                            (dados.ligada, vaga_id)).rowcount
        if not n:
            raise HTTPException(status_code=404, detail="vaga não encontrada")
        return {"triagem_ligada": dados.ligada}

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
