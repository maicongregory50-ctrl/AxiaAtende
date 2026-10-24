"""MEUS CLIENTES: o consultor recebe um cliente por vez e conta como foi. #1090 etapa 3, entrega 1.

Spec: C:\\AxiaGestao\\docs\\specs\\2026-10-23-relacionamento-etapa3-visita-pelo-whatsapp.md (maquete ao
lado). Decisoes do dono, 23/10/2026: um cliente por vez, na ordem da fila do Relacionamento; so texto
nesta entrega; nada grava sem o "Confere"; piloto so com ele.

O CAMINHO:
1. "📋 Meus clientes" no menu da casa (so quem esta em `clientes_consultores` ve) -> a FICHA do proximo
   cliente, com o botao de link para o WhatsApp dele, e "me conte como foi" com Depois / Parar por hoje.
2. O que ele escreve fica no registro aberto. Textos mandados ate ESPERA um do outro sao um so: a leitura
   pela IA roda quando ele para de escrever (`rodar`, chamado pelo laco do recepcionista).
3. A IA preenche os campos da tela do ERP; o que faltar e perguntado por botao, UMA coisa por vez
   (como foi, ofereceu, a resposta, o motivo). O proximo contato, se ele nao disse, e o sugerido pela
   cadencia (vem do ERP na ficha), como a tela faz.
4. "Confere?" com o cartao. Confere -> `confirmado`; o processo das TELAS leva ao ERP (`clientes_erp`)
   e marca `gravado` ou `recusado`; `rodar` avisa e manda o proximo cliente.

O QUE ISTO NAO FAZ: nao fala com o ERP (o recepcionista nao tem o segredo -- R4), nao manda nada ao
cliente (quem fala com ele e o consultor) e nao le audio, foto nem print (entrega 2).

A ORDEM NO MOTOR IMPORTA: `tratar` vem ANTES do canal de campo, que toma todo texto de quem e da casa
como a frase da proxima foto. Mas so toma o texto quando ha registro ABERTO -- sem ele, o texto segue
para o canal de campo como antes.
"""
from __future__ import annotations

import json
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import internos
from .envio import com_nove
from .saida import LIMITE_LINK, Opcao

FUSO = ZoneInfo("America/Sao_Paulo")
ESPERA = timedelta(seconds=30)        # textos mandados ate 30 s um do outro sao lidos juntos
JANELA = timedelta(hours=24)          # a janela da Meta para mensagem de sessao
VIVO = timedelta(hours=24)            # registro aberto ha mais que isto nao recebe mais texto

MEIOS = {"visita": "🚗 Visita", "ligacao": "📞 Ligação", "whatsapp": "💬 WhatsApp"}
MEIOS_ROTULO = {"visita": "Visita", "ligacao": "Ligação", "whatsapp": "WhatsApp", "email": "E-mail"}
# As mesmas listas da tela do ERP (relacionamento_regras.RESPOSTAS_*). O ERP confere de novo ao gravar.
RESPOSTAS_OFERTA = {"fechou": "Fechou (pedido)", "analisando": "Analisando", "pediu_proposta": "Pediu proposta",
                    "recusou": "Recusou", "nao_atendeu": "Não atendeu"}
RESPOSTAS_CORTESIA = {"conversou": "Conversou", "interesse": "Mostrou interesse", "comprou": "Comprou (pedido)",
                      "pediu_algo": "Pediu algo", "reclamou": "Reclamou de algo", "nao_atendeu": "Não atendeu"}
DESCRICAO_RESPOSTA = {"analisando": "vai pensar; retomar", "pediu_proposta": "proposta ou condição",
                      "interesse": "em comprar", "pediu_algo": "documento, visita técnica, retorno"}

ME_CONTE = "Quando falar com ele, me conte aqui como foi."
RECEBI = "Recebi. Vou montar o registro."
ANOTADO = "Anotado. Vai ao sistema agora."
GRAVADO = "Gravado no sistema ✔"
CORRIGIR = "Tudo bem. Me escreva de novo como foi, completo."
ATE_LOGO = "Até a próxima. Para voltar, escreva *meus clientes*."
SEM_LIBERACAO = "O 📋 Meus clientes ainda não está liberado para você."
SEM_FILA = "Sua lista ainda não chegou do sistema. Tente de novo em alguns minutos."
ACABOU = "Acabaram os clientes da sua lista por hoje. 👏"
# Escrever o nome da opcao tem o efeito do toque (dono, 24/10/2026, no piloto). Comparado sem acento,
# sem caixa e sem o emoji; vale tambem com cliente aberto, e entao repete a ficha dele.
PEDE_CLIENTES = {"meus clientes", "meu clientes", "clientes", "proximo cliente", "proximo"}


# ── quem e quem ──────────────────────────────────────────────────────────────

def ligado(con) -> bool:
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'clientes.ligado'").fetchone()
    return bool(r and r["valor"] is True)


def consultor(con, wa_id: str | None) -> dict | None:
    """O consultor do piloto por este numero (com ou sem o nono digito), com a chave ligada."""
    if not wa_id or not ligado(con):
        return None
    n = com_nove(wa_id)
    for c in con.execute("SELECT * FROM atendimento.clientes_consultores WHERE ativo").fetchall():
        if com_nove(c["wa_id"]) == n:
            return dict(c)
    return None


def pede_clientes(texto: str) -> bool:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return " ".join(t.strip(" !.?").split()) in PEDE_CLIENTES


def _hoje(agora: datetime) -> date:
    return agora.astimezone(FUSO).date()


def _aberto(con, wa_id: str, agora: datetime):
    """O registro em que o texto dele cai: aberto ou esperando o Confere, das ultimas 24 h."""
    return con.execute("""SELECT * FROM atendimento.clientes_registros
                           WHERE wa_id = %s AND estado IN ('aberto', 'conferir') AND criado_em > %s
                           ORDER BY id DESC LIMIT 1""", (wa_id, agora - VIVO)).fetchone()


# ── a ficha ──────────────────────────────────────────────────────────────────

def _data_br(v) -> str:
    try:
        d = date.fromisoformat(str(v)[:10])
    except ValueError:
        return ""
    return d.strftime("%d/%m")


def texto_da_ficha(ficha: dict, n: int, total: int) -> str:
    linhas = ["*Cliente %d de %d*" % (n, total)]
    pos = (" (%dº)" % ficha["posicao"]) if ficha.get("posicao") else ""
    linhas.append("*%s* · %s/%s · %s%s" % (ficha.get("nome") or "?", ficha.get("cidade") or "",
                                           ficha.get("uf") or "", ficha.get("faixa") or "", pos))
    if (ficha.get("atraso_dias") or 0) > 0:
        linhas.append("⏰ atrasado %d dia%s" % (ficha["atraso_dias"], "s" if ficha["atraso_dias"] > 1 else ""))
    c = ficha.get("contato") or {}
    if c.get("nome") or c.get("telefone"):
        linhas.append("👤 " + " · ".join(x for x in (c.get("nome"), c.get("telefone")) if x))
    ult = ("último contato %s (%s)" % (_data_br(ficha["ultimo_contato"]), (ficha.get("ultimo_meio") or "").lower())
           if ficha.get("ultimo_contato") else "nunca teve contato registrado")
    meses = ficha.get("meses_compra") or []
    linhas.append("📅 " + (("compra em %s · " % ", ".join(meses)) if meses else "") + ult)
    comprou = ficha.get("comprou") or {}
    if comprou:
        linhas.append("🌾 " + " · ".join("%s: %s" % (s, ", ".join(v)) for s, v in sorted(comprou.items())))
    camp = ficha.get("campanha")
    if camp:
        versao = {"recompra": " · *recompra*", "apresentacao": " · *apresentação*"}.get(camp.get("versao") or "", "")
        linhas.append("💬 campanha *%s*%s" % (camp.get("nome") or camp.get("codigo"), versao))
    else:
        linhas.append("💬 *cortesia* (sem campanha aberta para ele)")
    return "\n".join(linhas)


def _rotulo_link(ficha: dict) -> str:
    nome = ((ficha.get("contato") or {}).get("nome") or "").split()
    r = "Chamar %s" % nome[0].capitalize() if nome else "Chamar no WhatsApp"
    return r if len(r) <= LIMITE_LINK else "Chamar no WhatsApp"


def proximo(con, saida, c: dict, para: str, agora: datetime) -> bool:
    """Manda a ficha do proximo cliente (ou repete a do que esta aberto). False: nao havia cliente."""
    hoje = _hoje(agora)
    aberto = _aberto(con, c["wa_id"], agora)
    fila = con.execute("SELECT * FROM atendimento.clientes_fila WHERE comercial_id = %s ORDER BY posicao",
                       (c["comercial_id"],)).fetchall()
    if not fila:
        saida.texto(para, SEM_FILA)
        return False
    feitos = {r["codigo"] for r in con.execute(
        """SELECT codigo FROM atendimento.clientes_registros
            WHERE wa_id = %s AND estado <> 'descartado' AND (criado_em AT TIME ZONE 'America/Sao_Paulo')::date = %s""",
        (c["wa_id"], hoje)).fetchall()}
    if aberto:
        reg = aberto
    else:
        # o que ficou aberto de ontem e nao recebeu nada nao prende mais ninguem
        con.execute("""UPDATE atendimento.clientes_registros SET estado = 'descartado'
                        WHERE wa_id = %s AND estado IN ('aberto', 'conferir') AND criado_em <= %s""",
                    (c["wa_id"], agora - VIVO))
        livre = next((f for f in fila if f["codigo"] not in feitos), None)
        if livre is None:
            saida.texto(para, ACABOU)
            return False
        reg = con.execute("""INSERT INTO atendimento.clientes_registros (wa_id, para, comercial_id, codigo, ficha, criado_em)
                             VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
                          (c["wa_id"], para, c["comercial_id"], livre["codigo"], json.dumps(livre["ficha"]), agora)).fetchone()
    ja = len(feitos - {reg["codigo"]})
    ficha = reg["ficha"]
    texto = texto_da_ficha(ficha, ja + 1, max(len(fila), ja + 1))
    url = (ficha.get("contato") or {}).get("link_whatsapp")
    if url:
        saida.link(para, texto, _rotulo_link(ficha), url)
    else:
        saida.texto(para, texto)
    saida.botoes(para, ME_CONTE, [Opcao("cli:depois:%d" % reg["id"], "⏭ Depois"),
                                  Opcao("cli:parar:%d" % reg["id"], "🛑 Parar por hoje")])
    return True


def do_menu(con, saida, pessoa, conversa, no, agora: datetime) -> None:
    """O toque em "📋 Meus clientes" (acao `clientes` do menu da casa)."""
    c = consultor(con, pessoa.wa_id)
    if not c:
        saida.texto(pessoa.para, SEM_LIBERACAO)
        return
    proximo(con, saida, c, pessoa.para, agora)


# ── o que ele escreve e toca ─────────────────────────────────────────────────

def tratar(con, saida, ia, e, agora: datetime) -> bool:
    """True quando a mensagem era deste fluxo. So texto e os toques `cli:`; o resto segue o motor."""
    if not (e.toque or "").startswith("cli:") and not e.texto:
        return False
    c = consultor(con, e.pessoa.wa_id)
    if not c:
        return False
    para = e.pessoa.para
    if (e.toque or "").startswith("cli:"):
        _toque(con, saida, ia, c, para, e.toque, agora)
        return True
    texto = (e.texto or "").strip()
    if not texto or internos.pede_menu(texto):
        return False
    if pede_clientes(texto):
        proximo(con, saida, c, para, agora)
        return True
    reg = _aberto(con, c["wa_id"], agora)
    if not reg:
        return False
    primeiro = not reg["textos"]
    textos = (reg["textos"] + "\n" + texto) if reg["textos"] else texto
    con.execute("""UPDATE atendimento.clientes_registros
                      SET textos = %s, ultimo_texto_em = %s, lido = false, estado = 'aberto', pergunta = NULL
                    WHERE id = %s""", (textos[:4000], agora, reg["id"]))
    if primeiro or reg["estado"] == "conferir":
        saida.texto(para, RECEBI)
    return True


def _registro(con, wa_id: str, rid: str):
    if not rid.isdigit():
        return None
    return con.execute("SELECT * FROM atendimento.clientes_registros WHERE id = %s AND wa_id = %s",
                       (int(rid), wa_id)).fetchone()


def _toque(con, saida, ia, c: dict, para: str, toque: str, agora: datetime) -> None:
    partes = toque.split(":")
    acao, rid = partes[1], (partes[2] if len(partes) > 2 else "")
    valor = ":".join(partes[3:]) if len(partes) > 3 else ""
    reg = _registro(con, c["wa_id"], rid)
    if reg is None:
        return
    vivo = reg["estado"] in ("aberto", "conferir")
    if acao == "depois" and vivo:
        con.execute("UPDATE atendimento.clientes_registros SET estado = 'depois' WHERE id = %s", (reg["id"],))
        proximo(con, saida, c, para, agora)
    elif acao == "parar" and vivo:
        con.execute("UPDATE atendimento.clientes_registros SET estado = 'descartado' WHERE id = %s", (reg["id"],))
        saida.texto(para, ATE_LOGO)
    elif acao == "confere" and reg["estado"] == "conferir":
        con.execute("""UPDATE atendimento.clientes_registros
                          SET estado = 'confirmado', confirmado_em = %s, avisado = false, erro = NULL
                        WHERE id = %s""", (agora, reg["id"]))
        saida.texto(para, ANOTADO)
    elif acao == "corrigir" and vivo:
        con.execute("""UPDATE atendimento.clientes_registros
                          SET estado = 'aberto', textos = '', proposta = '{}'::jsonb, pergunta = NULL, lido = true
                        WHERE id = %s""", (reg["id"],))
        saida.texto(para, CORRIGIR)
    elif acao in ("meio", "ofer", "resp", "motivo") and vivo:
        p = dict(reg["proposta"] or {})
        tocados = dict(p.get("_tocados") or {})
        if acao == "meio" and valor in MEIOS_ROTULO:
            tocados["meio"] = valor
        elif acao == "ofer" and valor in ("sim", "nao"):
            tocados["ofereceu"] = valor == "sim"
            tocados.pop("resposta", None)
        elif acao == "resp" and valor in {**RESPOSTAS_OFERTA, **RESPOSTAS_CORTESIA}:
            tocados["resposta"] = valor
        elif acao == "motivo" and valor.isdigit():
            tocados["motivo_id"] = int(valor)
        p["_tocados"] = tocados
        reg = con.execute("UPDATE atendimento.clientes_registros SET proposta = %s WHERE id = %s RETURNING *",
                          (json.dumps(p), reg["id"])).fetchone()
        seguir(con, saida, reg, para, agora)


# ── montar, perguntar o que falta, conferir ──────────────────────────────────

def _data(v, padrao: date | None) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return padrao


def completar(p: dict, ficha: dict, hoje: date) -> dict:
    """A proposta com os tocados por cima da leitura, e o que a tela poe sozinha (quando, proximo)."""
    t = p.get("_tocados") or {}
    r = {k: v for k, v in p.items() if k != "_tocados" and v not in (None, "")}
    r.update(t)
    r["_tocados"] = t
    quando = _data(r.get("quando"), hoje)
    r["quando"] = (quando if quando and quando <= hoje else hoje).isoformat()
    tem_campanha = bool(ficha.get("campanha"))
    if not tem_campanha:
        r["ofereceu"] = False
    if r.get("resposta"):
        validas = RESPOSTAS_OFERTA if r.get("ofereceu") else RESPOSTAS_CORTESIA
        if r["resposta"] not in validas:
            r.pop("resposta")
    if r.get("resposta") != "recusou":
        r.pop("motivo_id", None)
    if r.get("resposta") != "interesse":
        r.pop("interesse_texto", None)
    if r.get("resposta") not in ("fechou", "comprou"):
        r.pop("pedido_numero", None)
    retomar = _data(r.get("retomar_em"), None)
    if not retomar or retomar <= _data(r["quando"], hoje):
        retomar = _data(ficha.get("proximo_sugerido"), hoje + timedelta(days=15))
        r["retomar_sugerido"] = True
    else:
        r.pop("retomar_sugerido", None)
    r["retomar_em"] = retomar.isoformat()
    return r


def _falta(r: dict, ficha: dict) -> str | None:
    if not r.get("meio"):
        return "meio"
    if ficha.get("campanha") and "ofereceu" not in (r.get("_tocados") or {}) and not r.get("resposta"):
        return "ofer"
    if not r.get("resposta"):
        return "resp"
    if r["resposta"] == "recusou" and not r.get("motivo_id"):
        return "motivo"
    return None


def seguir(con, saida, reg, para: str, agora: datetime) -> None:
    """Pergunta o proximo campo que falta, ou manda o cartao "Confere?"."""
    ficha = reg["ficha"]
    r = completar(dict(reg["proposta"] or {}), ficha, _hoje(agora))
    falta = _falta(r, ficha)
    rid = reg["id"]
    con.execute("UPDATE atendimento.clientes_registros SET proposta = %s, pergunta = %s, estado = %s WHERE id = %s",
                (json.dumps(r), falta, "aberto" if falta else "conferir", rid))
    nome = ficha.get("nome") or "o cliente"
    if falta == "meio":
        saida.botoes(para, "Com %s, foi como?" % nome,
                     [Opcao("cli:meio:%d:%s" % (rid, k), v) for k, v in MEIOS.items()])
    elif falta == "ofer":
        camp = ficha["campanha"]
        saida.botoes(para, "Você ofereceu a campanha *%s*?" % (camp.get("nome") or camp.get("codigo")),
                     [Opcao("cli:ofer:%d:sim" % rid, "Sim, ofereci"), Opcao("cli:ofer:%d:nao" % rid, "Não, só conversa")])
    elif falta == "resp":
        lista = RESPOSTAS_OFERTA if r.get("ofereceu") else RESPOSTAS_CORTESIA
        saida.lista(para, "E como foi a conversa com %s?" % nome, "Escolher",
                    [Opcao("cli:resp:%d:%s" % (rid, k), v, DESCRICAO_RESPOSTA.get(k, "")) for k, v in lista.items()])
    elif falta == "motivo":
        motivos = con.execute("SELECT * FROM atendimento.clientes_motivos ORDER BY id").fetchall()
        saida.lista(para, "Qual o motivo da recusa?", "Escolher",
                    [Opcao("cli:motivo:%d:%d" % (rid, m["id"]), m["nome"][:24], m["nome"][24:72]) for m in motivos[:10]])
    else:
        nomes = {m["id"]: m["nome"] for m in con.execute("SELECT id, nome FROM atendimento.clientes_motivos").fetchall()}
        saida.botoes(para, cartao(r, ficha, nomes), [Opcao("cli:confere:%d" % rid, "✅ Confere"),
                                              Opcao("cli:corrigir:%d" % rid, "✏️ Corrigir")])


def cartao(r: dict, ficha: dict, motivos: dict | None = None) -> str:
    linhas = ["Confere?", "*%s* · %s · %s" % (ficha.get("nome") or "?", MEIOS_ROTULO.get(r.get("meio"), "?"),
                                              _data_br(r.get("quando")))]
    camp = ficha.get("campanha")
    if camp:
        linhas.append("ofereceu *%s*: %s" % (camp.get("nome") or camp.get("codigo"), "sim" if r.get("ofereceu") else "não"))
    lista = RESPOSTAS_OFERTA if r.get("ofereceu") else RESPOSTAS_CORTESIA
    linhas.append("resposta: *%s*" % lista.get(r.get("resposta"), "?"))
    if r.get("interesse_texto"):
        linhas.append("o quê: %s" % r["interesse_texto"])
    if r.get("motivo_id"):
        linhas.append("motivo: %s" % ((motivos or {}).get(r["motivo_id"]) or "(da lista)"))
    if r.get("pedido_numero"):
        linhas.append("pedido: %s" % r["pedido_numero"])
    linhas.append("próximo contato: *%s*%s" % (_data_br(r.get("retomar_em")),
                                              " (sugerido)" if r.get("retomar_sugerido") else ""))
    if r.get("anotacao"):
        linhas.append("anotação: %s" % r["anotacao"])
    return "\n".join(linhas)


# ── a rotina (laco do recepcionista) ─────────────────────────────────────────

def _dentro_da_janela(con, para: str, agora: datetime) -> bool:
    """Ele falou nas ultimas 24 h? `para` e o numero como a Meta o mandou (com ou sem o nono digito)."""
    from .campo import ultima_mensagem_de
    u = ultima_mensagem_de(con, para)
    return u is not None and agora - u < JANELA


def rodar(con, saida, ia, agora: datetime) -> int:
    """Le o que ele parou de escrever, e avisa gravado/recusado (com o proximo cliente). Devolve quantos."""
    feitos = 0
    if not ligado(con):
        return 0
    motivos = [dict(m) for m in con.execute("SELECT * FROM atendimento.clientes_motivos ORDER BY id").fetchall()]
    for reg in con.execute("""SELECT * FROM atendimento.clientes_registros
                               WHERE estado = 'aberto' AND NOT lido AND ultimo_texto_em <= %s
                               ORDER BY id LIMIT 10""", (agora - ESPERA,)).fetchall():
        lido = None
        if ia is not None:
            try:
                lido = ia.ler_visita(reg["textos"], reg["ficha"], motivos, _hoje(agora))
            except Exception as falha:  # noqa: BLE001 -- sem leitura, pergunta por botao
                print("clientes: leitura %s" % type(falha).__name__, flush=True)
        p = {**(lido or {}), "_tocados": (reg["proposta"] or {}).get("_tocados") or {}}
        reg = con.execute("UPDATE atendimento.clientes_registros SET proposta = %s, lido = true WHERE id = %s RETURNING *",
                          (json.dumps(p), reg["id"])).fetchone()
        seguir(con, saida, reg, reg["para"], agora)
        feitos += 1
    for reg in con.execute("""SELECT * FROM atendimento.clientes_registros
                               WHERE estado IN ('gravado', 'recusado') AND NOT avisado
                               ORDER BY id LIMIT 10""").fetchall():
        if not _dentro_da_janela(con, reg["para"], agora):
            continue
        c = consultor(con, reg["wa_id"])
        if reg["estado"] == "gravado":
            con.execute("UPDATE atendimento.clientes_registros SET avisado = true WHERE id = %s", (reg["id"],))
            saida.texto(reg["para"], "%s (%s)" % (GRAVADO, reg["ficha"].get("nome") or ""))
            if c:
                proximo(con, saida, c, reg["para"], agora)
        else:
            con.execute("""UPDATE atendimento.clientes_registros
                              SET avisado = true, estado = 'aberto', textos = '', proposta = '{}'::jsonb,
                                  pergunta = NULL, lido = true
                            WHERE id = %s""", (reg["id"],))
            saida.texto(reg["para"], "O sistema não aceitou o registro de %s: %s\nMe escreva de novo como foi."
                        % (reg["ficha"].get("nome") or "", reg["erro"] or "sem motivo"))
        feitos += 1
    return feitos
