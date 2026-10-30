"""A conversa de uma pessoa, em itens, em ordem de tempo. #1205 (a montagem saiu do
`scripts/ler_conversa.py`, #981, para servir tambem a janela da Recepcao).

Dois leitores e a mesma montagem: o script (a sessao, pelo papel `axiaatende_ro`) formata cada item
na `linha` de sempre; a rota das telas devolve os itens para a janela, que usa o `texto` (sem os ids
de botao e de midia, que so servem a quem depura). Nenhum dos dois escreve: isto so le.

Do nosso lado, o texto exato vem de `enviadas_texto` (pelo wamid, desde 30/10/2026); o que saiu antes
tem so o resumo de `enviadas`, e o item diz isso (`resumo: True`). NUNCA o conteudo do PDF da vaga,
nunca nada de `casa`, nunca a midia (diz que houve, com o id).
"""
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .envio import com_nove

FUSO = ZoneInfo("America/Sao_Paulo")
BASTIDORES = {"campo-de-sementes": "Campo de sementes", "colheita": "Colheita", "beneficiamento": "Beneficiamento",
              "controle-de-qualidade": "Controle de qualidade", "entrega": "Entrega / carregamento"}
FASES = {"inicial": "inicial", "vegetativo": "vegetativo", "flor": "flor", "pre-colheita": "pré-colheita", "semente": "semente"}
MIDIA = {"image": "foto", "video": "vídeo", "audio": "áudio", "document": "documento", "sticker": "figurinha"}


def hora(t) -> str:
    if t is None:
        return "--:--"
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(FUSO).strftime("%d/%m %H:%M")


def descrever_entrada(corpo: dict) -> str:
    """O que a pessoa mandou, em uma linha, pelo corpo da Meta (sem baixar nada). Forma do terminal."""
    msg = (corpo or {}).get("msg") or {}
    tipo = msg.get("type") or "?"
    if tipo == "text":
        return (msg.get("text") or {}).get("body", "")
    if tipo == "interactive":
        i = msg.get("interactive") or {}
        r = i.get("button_reply") or i.get("list_reply") or {}
        return "[%s] %s (%s)" % ("botão" if "button_reply" in i else "lista", r.get("title", ""), r.get("id", ""))
    if tipo in MIDIA:
        m = msg.get(tipo) or {}
        legenda = m.get("caption") or m.get("filename") or ""
        return ("[%s id=%s] %s" % (MIDIA[tipo], m.get("id", "?"), legenda)).rstrip()
    if tipo == "reaction":
        return "[reação %s]" % (msg.get("reaction") or {}).get("emoji", "")
    if tipo == "location":
        return "[localização]"
    if tipo == "contacts":
        return "[contato]"
    return "[%s]" % tipo


def _entrada_para_ler(corpo: dict) -> tuple[str, str]:
    """(tipo, texto) para a janela: o toque pelo nome do botao, a midia pelo que e e a legenda."""
    msg = (corpo or {}).get("msg") or {}
    tipo = msg.get("type") or "?"
    if tipo == "interactive":
        i = msg.get("interactive") or {}
        return "toque", (i.get("button_reply") or i.get("list_reply") or {}).get("title", "")
    if tipo == "button":   # o botao de resposta rapida de um modelo (o convite)
        return "toque", (msg.get("button") or {}).get("text", "")
    if tipo in MIDIA:
        m = msg.get(tipo) or {}
        return "midia", ("[%s] %s" % (MIDIA[tipo], m.get("caption") or m.get("filename") or "")).rstrip()
    if tipo == "text":
        return "texto", (msg.get("text") or {}).get("body", "")
    return tipo, descrever_entrada(corpo)


def bsuids_de(con, wa_id: str) -> list[str]:
    return [r["b"] for r in con.execute(
        """SELECT DISTINCT bsuid AS b FROM atendimento.eventos_meta
            WHERE tipo = 'mensagem' AND corpo->'msg'->>'from' = %s AND bsuid IS NOT NULL""", (wa_id,)).fetchall()]


def _modelo_montado(con, nome: str, variaveis: list) -> str:
    r = con.execute("SELECT texto FROM atendimento.modelos WHERE nome = %s", (nome,)).fetchone()
    if not r or not r["texto"]:
        return ""
    return re.sub(r"\{\{(\d+)\}\}", lambda m: (variaveis or [])[int(m.group(1)) - 1]
                  if 0 < int(m.group(1)) <= len(variaveis or []) else m.group(0), r["texto"])


def _texto_guardado(con, g) -> str:
    """O texto exato, como o cliente viu, a partir da linha de `enviadas_texto`."""
    if g["tipo"] == "modelo":
        return _modelo_montado(con, g["modelo"] or "", g["variaveis"] or []) or "[modelo %s]" % g["modelo"]
    partes = [g["legenda"] if g["tipo"] in ("imagem", "documento") and g["legenda"] else "", g["texto"] or ""]
    if g["tipo"] in ("imagem", "documento"):
        partes[0] = "[%s] %s" % (g["tipo"], partes[0])
    return "\n".join(p for p in partes if p).strip()


def _opcoes(g) -> list[str]:
    """Os titulos que a pessoa viu para tocar: botoes, linhas da lista, o rotulo do link."""
    o = g["opcoes"]
    if not o:
        return []
    if isinstance(o, list):
        return [x.get("titulo", "") for x in o]
    if "linhas" in o:
        return [x.get("titulo", "") for x in o["linhas"]]
    if "rotulo" in o:
        return [o["rotulo"]]
    return []


def itens(con, wa_id: str | None = None, bsuid: str | None = None, desde: datetime | None = None):
    """(wa_id, bsuids, itens) da pessoa. Cada item: quando, lado (cliente | nos | marco), tipo, texto,
    opcoes, estado, erro, resumo (o envio sem texto guardado), conversa_id (no marco), linha (terminal)."""
    if not wa_id and not bsuid:
        raise ValueError("numero ou bsuid")
    desde = desde or datetime(2000, 1, 1, tzinfo=timezone.utc)
    bsuids = ([bsuid] if bsuid else []) + (bsuids_de(con, wa_id) if wa_id else [])
    bsuids = list(dict.fromkeys(bsuids))
    if bsuid and not wa_id:
        w = con.execute("""SELECT corpo->'msg'->>'from' AS w FROM atendimento.eventos_meta
                            WHERE bsuid = %s AND tipo = 'mensagem' ORDER BY id DESC LIMIT 1""", (bsuid,)).fetchone()
        wa_id = w["w"] if w else None
    # o envio da carteira vai ao numero COM o nono digito (como o ERP o guarda) e a Meta devolve o
    # wa_id SEM ele: sem as duas formas, o convite que provocou a resposta some da conversa (a
    # COPERMAP, 28/10: os dois materiais nao apareciam)
    paras = list(dict.fromkeys(p for p in [wa_id, com_nove(wa_id) if wa_id else None] + bsuids if p))
    lista = []

    def item(quando, lado, linha, **k):
        lista.append(dict({"quando": quando, "lado": lado, "linha": linha, "tipo": "", "texto": "", "opcoes": [],
                           "estado": None, "erro": "", "resumo": False, "conversa_id": None}, **k))

    abriu = {}   # processado_em -> recebido_em: a mensagem que abriu cada atendimento (abaixo)
    for e in con.execute("""SELECT recebido_em, processado_em, corpo, erro FROM atendimento.eventos_meta
                             WHERE tipo = 'mensagem' AND recebido_em >= %s
                               AND (corpo->'msg'->>'from' = %s OR bsuid = ANY(%s)) ORDER BY id""",
                         (desde, wa_id or "", bsuids)).fetchall():
        linha = descrever_entrada(e["corpo"])
        # #1099: o celular sem rede entrega com atraso (ate 33 h medidas) e fora de ordem; o canal de
        # campo agrupa pela hora de ENVIO, entao a leitura a mostra quando difere da chegada
        ts = str(((e["corpo"] or {}).get("msg") or {}).get("timestamp") or "")
        if ts.isdigit():
            mandada = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            if abs((e["recebido_em"] - mandada).total_seconds()) > 60:
                linha += " (mandada %s)" % hora(mandada)
        tipo, texto = _entrada_para_ler(e["corpo"])
        if e["processado_em"] is not None:
            abriu.setdefault(e["processado_em"], e["recebido_em"])
        item(e["recebido_em"], "cliente", "→ %s%s" % (linha, (" !! %s" % e["erro"]) if e["erro"] else ""),
             tipo=tipo, texto=texto)

    # o texto exato existe desde a 047; antes dela (ou com o banco ainda sem a tabela) fica o resumo
    com_texto = con.execute("SELECT to_regclass('atendimento.enviadas_texto') IS NOT NULL AS ha").fetchone()["ha"]
    juntar = ("LEFT JOIN atendimento.enviadas_texto g ON g.wamid = s.wamid" if com_texto else
              "LEFT JOIN (SELECT NULL::text AS wamid, NULL::text AS tipo, NULL::text AS texto, NULL::jsonb AS opcoes,"
              " NULL::text AS modelo, NULL::text[] AS variaveis, NULL::text AS legenda) g ON false")
    for s in con.execute("""SELECT s.enviada_em, s.tipo, s.resumo, s.status, s.erro, g.wamid AS g_wamid, g.tipo AS g_tipo,
                                   g.texto AS g_texto, g.opcoes AS g_opcoes, g.modelo AS g_modelo,
                                   g.variaveis AS g_variaveis, g.legenda AS g_legenda
                              FROM atendimento.enviadas s """ + juntar + """
                             WHERE s.para = ANY(%s) AND s.enviada_em >= %s ORDER BY s.id""", (paras, desde)).fetchall():
        erro = (" !! %s" % s["erro"]) if s["erro"] else ""
        linha = "← [%s, %s] %s%s" % (s["tipo"], s["status"], s["resumo"], erro)
        if s["g_wamid"]:
            g = {"tipo": s["g_tipo"], "texto": s["g_texto"], "opcoes": s["g_opcoes"], "modelo": s["g_modelo"],
                 "variaveis": s["g_variaveis"], "legenda": s["g_legenda"]}
            texto, opcoes = _texto_guardado(con, g), _opcoes(g)
            linha += " | %r%s" % (texto, (" %s" % opcoes) if opcoes else "")
            item(s["enviada_em"], "nos", linha, tipo=s["tipo"], texto=texto, opcoes=opcoes,
                 estado=s["status"], erro=s["erro"] or "")
        else:
            item(s["enviada_em"], "nos", linha, tipo=s["tipo"], texto=s["resumo"], estado=s["status"],
                 erro=s["erro"] or "", resumo=True)

    for c in con.execute("""SELECT id, iniciada_em, caminho, erp_codigo, nome_perfil, origem
                             FROM atendimento.conversas WHERE (wa_id = %s OR bsuid = ANY(%s)) AND iniciada_em >= %s
                             ORDER BY id""", (wa_id or "", bsuids, desde)).fetchall():
        caminho = " > ".join(c["caminho"] or []) or "-"
        # a conversa nasce quando a mensagem que a abriu e PROCESSADA (o mesmo `agora`, regra da 046),
        # ~1 s depois de ela chegar: o marco vai para a chegada dela, para a mensagem ficar DENTRO do
        # atendimento que abriu (e no destaque da janela), e nao no fim do anterior
        item(min(c["iniciada_em"], abriu.get(c["iniciada_em"], c["iniciada_em"])), "marco", "  [atendimento] abriu (%s%s); caminho: %s" % (
            c["nome_perfil"] or "sem nome", (", cadastro %s" % c["erp_codigo"]) if c["erp_codigo"] else "", caminho),
            tipo="atendimento", conversa_id=c["id"],
            texto=("atendimento aberto por nós (portão retroativo)" if c["origem"] != "mensagem" else "atendimento")
            + ("" if caminho == "-" else " · " + caminho))

    for m in con.execute("""SELECT recebido_em, tipo, legenda, perguntas_feitas, classe_bastidor, classe_produto,
                                   classe_fase, data_dita, data_presumida, fechado_em, desistiu_em, atv, lote, grupo_id, id
                              FROM atendimento.material_de_campo WHERE wa_id = %s AND recebido_em >= %s ORDER BY id""",
                         (wa_id or "", desde)).fetchall():
        classe = ", ".join(x for x in [BASTIDORES.get(m["classe_bastidor"] or "", m["classe_bastidor"]),
                                       m["classe_produto"], FASES.get(m["classe_fase"] or "", m["classe_fase"])] if x)
        estado = "desistiu" if m["desistiu_em"] else ("fechado" if m["fechado_em"] else "aberto")
        item(m["recebido_em"], "marco", "  [campo] %s #%s (grupo %s): legenda %r; perguntas %s; classe: %s; data %s%s; %s%s" % (
            m["tipo"], m["id"], m["grupo_id"], m["legenda"] or "", list(m["perguntas_feitas"] or []) or "-",
            classe or "a classificar", m["data_dita"] or "-", " (presumida)" if m["data_presumida"] else "",
            estado, (", %s" % m["atv"]) if m["atv"] else ""),
            tipo="campo", texto="canal de campo: %s %s" % (m["tipo"], classe or "a classificar"))

    # #1098: a candidatura do Trabalhe conosco -- quando chegou, se teve triagem, se foi a Fran e o
    # retorno dela. NUNCA o conteudo do PDF (o papel de leitura nem tem a coluna).
    for k in con.execute("""SELECT id, recebida_em, pdf_nome, pdf_bytes, declarou, triagem_em, triagem_erro,
                                   fran_em, fran_erro, feedback, feedback_texto, apagada_em
                              FROM atendimento.candidaturas WHERE (wa_id = %s OR bsuid = ANY(%s)) AND recebida_em >= %s
                             ORDER BY id""", (wa_id or "", bsuids, desde)).fetchall():
        triagem = "sem triagem (%s)" % k["triagem_erro"] if k["triagem_erro"] else ("triada" if k["triagem_em"] else "na fila")
        fran = ("na Fran" if k["fran_em"] else ("não foi: %s" % k["fran_erro"] if k["fran_erro"] else "a mandar"))
        retorno = (", Fran: triagem %s%s" % (k["feedback"], (" (%r)" % k["feedback_texto"]) if k["feedback_texto"] else "")
                   if k["feedback"] else "")
        item(k["recebida_em"], "marco", "  [vaga] currículo #%s %r (%s KB, declarou %s): %s; %s%s%s" % (
            k["id"], k["pdf_nome"], (k["pdf_bytes"] or 0) // 1024, k["declarou"] or "-", triagem, fran, retorno,
            "; apagado em %s" % hora(k["apagada_em"]) if k["apagada_em"] else ""),
            tipo="vaga", texto="currículo recebido: %s" % triagem)

    for f in con.execute("""SELECT recebido_em, texto, usada_em FROM atendimento.campo_frases
                             WHERE wa_id = %s AND recebido_em >= %s ORDER BY id""", (wa_id or "", desde)).fetchall():
        item(f["recebido_em"], "marco", "  [campo] frase guardada %r%s" % (f["texto"], " (usada)" if f["usada_em"] else ""),
             tipo="campo", texto="frase guardada para a próxima foto")

    # no empate de hora, o marco do atendimento vem antes do que aconteceu nele
    lista.sort(key=lambda x: (x["quando"] if x["quando"].tzinfo else x["quando"].replace(tzinfo=timezone.utc),
                              0 if x["tipo"] == "atendimento" else 1))
    return wa_id, bsuids, lista
