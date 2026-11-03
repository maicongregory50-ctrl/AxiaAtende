"""O ROTEADOR com contexto por contato (#1238, dono 03/11/2026). Spec e plano:
docs/specs/2026-11-03-roteador-com-contexto-por-contato*.md.

O QUE ELE FAZ. Quem e da casa escreve no WhatsApp da empresa do jeito que escreve para qualquer pessoa:
solto, sem citar, sem dizer de que assunto fala. Hoje a ORDEM dos degraus do motor decide para onde o
texto vai (o primeiro que aceita fica com ele), e na prova de 03/11 errou tres vezes no mesmo dia. Com a
chave `roteador.ligado`, o texto de interno, sem citacao e sem toque, de quem tem ao menos um ASSUNTO
ABERTO, passa antes por aqui:

1. o RETRATO: os assuntos abertos da pessoa (lidos onde cada fio guarda o estado dele, so leitura), as
   ultimas 24 h dela com a empresa e a mensagem que chegou, com ha quantos segundos;
2. a OlivIA (`ia.rotear`) escolhe UM assunto da lista fechada, ou "nenhum", ou "correcao";
3. confianca alta: o texto vai ao FIO daquele assunto pelo mesmo caminho de hoje, e a resposta do fio
   diz onde entrou. Baixa (ou "nenhum" com dois ou mais assuntos): botoes. "Nenhum" com um assunto so:
   a corrente de sempre.

O QUE ELE NAO FAZ. Nao escreve nas tabelas dos fios (quem grava e o fio), nao abre assunto novo, nao
toca conversa de cliente, nao le o que a pessoa falou com terceiros. Escreve so em
`atendimento.roteador`, o registro de decisao -- e e por ele que se mede se a equipe trava (a fracao de
textos que entram sem botao e sem correcao).

A CORRECAO ESCRITA. "Nao, era sobre a foto" desfaz o ULTIMO encaminhamento da pessoa, em ate 10 min,
com o estado que o fio tinha antes (`roteador.desfazer`), e leva o texto ao assunto certo. O texto que
foi a um chamado espera `roteador.carencia_minutos` antes de as telas o levarem ao ERP, justamente para
caber a correcao; o que ja chegou ao ERP ganha um segundo comentario (agente nao apaga registro).

DESLIGADO (`roteador.ligado = false`), nada daqui roda e nenhuma linha muda de caminho.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import campo as campo_mod
from . import clientes_do_dia, logos, pendencias, vaga
from .envio import HORA_DA_MENSAGEM, com_nove
from .saida import Opcao, wa_id_do_whatsapp

FUSO = ZoneInfo("America/Sao_Paulo")
HISTORICO = timedelta(hours=24)
MAX_HISTORICO = 20
CORRECAO_ATE = timedelta(minutes=10)
MAX_LISTA = 9            # a lista da Meta tem 10 linhas; a decima e "Outro assunto"
FIOS = ("chamado", "foto", "logo", "cliente", "curriculo")

PERGUNTA_DA_FOTO = {"legenda": campo_mod.PERGUNTA_LEGENDA, "bastidor": "o que a foto mostra?",
                    "produto": campo_mod.PERGUNTA_PRODUTO, "fase": campo_mod.PERGUNTA_FASE,
                    "data": campo_mod.PERGUNTA_DATA, "qual_dia": campo_mod.PERGUNTA_QUAL_DIA,
                    "mesmo": "é do mesmo assunto da anterior?"}
E_SOBRE = "É sobre {rotulo}?"
QUAL_ASSUNTO = "Sobre qual assunto é a sua mensagem?"
TIREI = "Certo, tirei de {rotulo}."
TIREI_SEM_DESTINO = ("Certo, tirei de {rotulo}. Se era para outro assunto, me diga qual; se não, escreva "
                     "*menu*.")
NAO_ERA = "(pelo WhatsApp) A mensagem anterior não era deste chamado; desconsidere."


@dataclass
class Assunto:
    fio: str
    id: int
    rotulo: str
    ultimo_trecho: str = ""
    ha_segundos: int | None = None

    @property
    def chave(self) -> str:
        return "%s:%d" % (self.fio, self.id)

    def para_json(self) -> dict:
        return {"chave": self.chave, "fio": self.fio, "id": self.id, "rotulo": self.rotulo}


def _ajuste(con, chave, padrao):
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (chave,)).fetchone()
    return padrao if r is None else r["valor"]


def ligado(con) -> bool:
    return _ajuste(con, "roteador.ligado", False) is True


def carencia(con) -> timedelta:
    try:
        return timedelta(minutes=max(0, int(_ajuste(con, "roteador.carencia_minutos", 3) or 0)))
    except (TypeError, ValueError):
        return timedelta(minutes=3)


def _formas(wa_id: str | None) -> list[str]:
    if not wa_id:
        return []
    return list({wa_id, com_nove(wa_id), wa_id_do_whatsapp(com_nove(wa_id))})


def _segundos(agora: datetime, quando) -> int | None:
    return None if quando is None else max(0, int((agora - quando).total_seconds()))


def _hora(quando) -> str:
    return quando.astimezone(FUSO).strftime("%H:%M")


# ── 1. os assuntos abertos (so leitura, onde cada fio guarda o estado) ─────────────────────────────

def _chamados(con, wa_id, agora) -> list[Assunto]:
    if not pendencias.ligado(con):
        return []
    saida = []
    for p in pendencias.pendencias_da_pessoa(con, wa_id):
        m = con.execute("""SELECT texto, enviada_em FROM atendimento.pendencias_mensagens
                            WHERE pendencia_id = %s AND sentido = 'saiu' AND estado = 'enviada'
                            ORDER BY id DESC LIMIT 1""", (p["id"],)).fetchone()
        espera = "esperando a resposta dela" if p["espera"] == "resposta" else "esperando ela validar a entrega"
        saida.append(Assunto("chamado", p["id"], pendencias.rotulo(p),
                             ("%s; a última nossa: \"%s\"" % (espera, m["texto"][:200])) if m else espera,
                             _segundos(agora, m["enviada_em"] if m else p["ultima_em"])))
    return saida


def _foto(con, wa_id, agora) -> list[Assunto]:
    r = campo_mod.assunto_aberto(con, wa_id, agora)
    if not r:
        return []
    g = con.execute("""SELECT count(*) AS n, max(recebido_em) AS ultima, bool_or(tipo = 'video') AS video,
                              max(pergunta_pendente) AS pergunta, max(legenda) AS legenda
                         FROM atendimento.material_de_campo WHERE grupo_id = %s""", (r["grupo_id"],)).fetchone()
    nome = ("vídeo" if g["video"] else "foto") + ("s" if g["n"] > 1 else "")
    rotulo = "%s de %s" % (nome.capitalize(), _hora(g["ultima"]))
    if g["pergunta"]:
        trecho = "perguntamos: \"%s\"" % PERGUNTA_DA_FOTO.get(g["pergunta"], g["pergunta"])
    else:
        trecho = "esperando a legenda" if not (g["legenda"] or "").strip() else "legenda até aqui: \"%s\"" % g["legenda"][:200]
    return [Assunto("foto", r["grupo_id"], rotulo, trecho, _segundos(agora, g["ultima"]))]


def _logo(con, bsuid, agora) -> list[Assunto]:
    if not bsuid:
        return []
    r = logos.pendente(con, bsuid)
    if not r:
        return []
    pergunta = "de qual cliente é a logo?" if r["pergunta_pendente"] == "erp_codigo" else "qual o nome da marca?"
    rotulo = "Logo %s" % (r["nome_arquivo"] or "de cliente")
    return [Assunto("logo", r["id"], rotulo[:80], "perguntamos: \"%s\"" % pergunta, _segundos(agora, r["recebida_em"]))]


def _cliente(con, wa_id, agora) -> list[Assunto]:
    r = clientes_do_dia.aberto(con, wa_id, agora)
    if not r:
        return []
    ficha = r["ficha"] or {}
    trecho = ("ele já contou: \"%s\"" % r["textos"][-200:]) if r["textos"] else \
        "mandamos a ficha e pedimos: \"%s\"" % clientes_do_dia.ME_CONTE
    return [Assunto("cliente", r["id"], "Cliente %s (Meus clientes)" % (ficha.get("nome") or r["codigo"]), trecho,
                    _segundos(agora, r["ultimo_texto_em"] or r["criado_em"]))]


def _curriculo(con, wa_id, agora) -> list[Assunto]:
    if not wa_id:
        return []
    saida = []
    for c in con.execute("""SELECT * FROM atendimento.candidaturas WHERE espera_comentario AND feedback_em > %s
                             ORDER BY feedback_em DESC LIMIT 3""", (agora - vaga.COMENTARIO_ATE,)).fetchall():
        if c["fran_para"] and com_nove(c["fran_para"]) == com_nove(wa_id):
            saida.append(Assunto("curriculo", c["id"], "Currículo de %s" % ((c["nome_perfil"] or "candidato").strip()),
                                 "perguntamos: \"O que ela errou?\" (a triagem)", _segundos(agora, c["feedback_em"])))
    return saida[:1]


def assuntos_abertos(con, wa_id: str | None, bsuid: str | None, agora: datetime) -> list[Assunto]:
    """Os assuntos abertos da pessoa, do mais recente ao mais antigo. Um fio com erro de leitura fica de
    fora (com linha no log): o retrato incompleto pede botao, nunca derruba o atendimento."""
    todos = []
    for ler, chave in ((_chamados, wa_id), (_foto, wa_id), (_logo, bsuid), (_cliente, wa_id), (_curriculo, wa_id)):
        try:
            with con.transaction():
                todos += ler(con, chave, agora)
        except Exception as falha:   # noqa: BLE001
            print("roteador: leitura de %s: %s" % (ler.__name__, falha), flush=True)
    return sorted(todos, key=lambda a: a.ha_segundos if a.ha_segundos is not None else 10 ** 9)


# ── 2. o historico e o retrato ───────────────────────────────────────────────────────────────────────

def _o_que_ela_mandou(msg: dict) -> str:
    t = msg.get("type")
    if t == "text":
        return (msg.get("text") or {}).get("body", "")
    if t in ("image", "video", "document"):
        nome = {"image": "foto", "video": "vídeo", "document": "documento"}[t]
        legenda = (msg.get(t) or {}).get("caption") or ""
        return "[%s]%s" % (nome, (" " + legenda) if legenda else "")
    if t == "interactive":
        i = msg.get("interactive") or {}
        return "[tocou: %s]" % ((i.get("button_reply") or i.get("list_reply") or {}).get("title", ""))
    if t == "button":
        return "[tocou: %s]" % ((msg.get("button") or {}).get("text", ""))
    if t == "audio":
        return "[áudio]"
    return ""


def historico(con, wa_id: str | None, agora: datetime, sem_wamid: str | None = None) -> list[tuple]:
    """As ultimas trocas dela com a empresa: [(quando, 'ela'|'nós', texto)], ate MAX_HISTORICO, da mais
    antiga para a mais nova. So o que passou pelo numero da empresa; nunca o que ela falou com terceiros."""
    formas = _formas(wa_id)
    if not formas:
        return []
    linhas = []
    for r in con.execute("SELECT " + HORA_DA_MENSAGEM + """ AS em, corpo FROM atendimento.eventos_meta
                            WHERE tipo = 'mensagem' AND corpo->'msg'->>'from' = ANY(%s)
                              AND recebido_em > %s AND """ + HORA_DA_MENSAGEM + """ <= %s
                              AND coalesce(corpo->'msg'->>'id', '') <> %s
                            ORDER BY id DESC LIMIT %s""",
                         (formas, agora - HISTORICO, agora + timedelta(minutes=1), sem_wamid or "",
                          MAX_HISTORICO)).fetchall():
        t = _o_que_ela_mandou((r["corpo"] or {}).get("msg") or {})
        if t.strip():
            linhas.append((r["em"], "ela", t[:300]))
    for r in con.execute("""SELECT enviada_em, resumo FROM atendimento.enviadas
                             WHERE para = ANY(%s) AND enviada_em > %s AND enviada_em <= %s
                             ORDER BY id DESC LIMIT %s""",
                         (formas, agora - HISTORICO, agora + timedelta(minutes=1), MAX_HISTORICO)).fetchall():
        if (r["resumo"] or "").strip():
            linhas.append((r["enviada_em"], "nós", r["resumo"][:300]))
    linhas.sort(key=lambda x: x[0])
    return linhas[-MAX_HISTORICO:]


def _ultima_nossa(con, wa_id, agora):
    r = con.execute("""SELECT max(enviada_em) AS em FROM atendimento.enviadas
                        WHERE para = ANY(%s) AND enviada_em > %s AND enviada_em <= %s""",
                    (_formas(wa_id), agora - HISTORICO, agora)).fetchone()
    return r["em"] if r else None


def _ultima_midia(con, wa_id, agora, sem_wamid):
    r = con.execute("SELECT max(" + HORA_DA_MENSAGEM + """) AS em FROM atendimento.eventos_meta
                      WHERE tipo = 'mensagem' AND corpo->'msg'->>'from' = ANY(%s) AND recebido_em > %s
                        AND corpo->'msg'->>'type' IN ('image', 'video', 'document', 'audio')
                        AND coalesce(corpo->'msg'->>'id', '') <> %s""",
                    (_formas(wa_id), agora - HISTORICO, sem_wamid or "")).fetchone()
    return r["em"] if r else None


def _ha(segundos: int | None) -> str:
    if segundos is None:
        return "sem registro"
    if segundos < 120:
        return "há %d s" % segundos
    if segundos < 7200:
        return "há %d min" % (segundos // 60)
    return "há %d h" % (segundos // 3600)


def montar_retrato(con, e, assuntos: list[Assunto], agora: datetime, ultimo=None) -> dict:
    """O que a OlivIA recebe: os tres blocos da spec. `ultimo` = a linha de `roteador` que ainda pode ser
    corrigida (encaminhada ha ate 10 min); com ela, "correcao" entra na lista."""
    wa_id = e.pessoa.wa_id
    partes = ["ASSUNTOS ABERTOS DELA (o número é o que você responde):"]
    for n, a in enumerate(assuntos, 1):
        partes.append("%d. %s — %s — %s" % (n, a.rotulo, a.ultimo_trecho or "sem trecho", _ha(a.ha_segundos)))
    if not assuntos:
        partes.append("(nenhum)")
    if ultimo is not None:
        partes.append("")
        partes.append("A MENSAGEM ANTERIOR DELA (\"%s\") foi encaminhada %s para: %s. Se ela agora diz que foi "
                      "para o lugar errado, é \"correcao\"."
                      % ((ultimo["texto"] or "")[:200], _ha(_segundos(agora, ultimo["criado_em"])),
                         _rotulo_do_destino(ultimo)))
    partes.append("")
    partes.append("AS ÚLTIMAS 24 H DELA COM A EMPRESA (a mais antiga primeiro):")
    hist = historico(con, wa_id, agora, e.wamid)
    partes += ["%s %s: %s" % (_hora(q), quem, t) for q, quem, t in hist] or ["(nada)"]
    partes.append("")
    partes.append("A MENSAGEM QUE CHEGOU AGORA (%s depois da última mensagem nossa; %s depois da última "
                  "foto, vídeo, documento ou áudio dela):"
                  % (_ha(_segundos(agora, _ultima_nossa(con, wa_id, agora))),
                     _ha(_segundos(agora, _ultima_midia(con, wa_id, agora, e.wamid)))))
    partes.append("<mensagem>\n%s\n</mensagem>" % (e.texto or "")[:1500])
    return {"texto": "\n".join(partes), "numeros": [str(n) for n in range(1, len(assuntos) + 1)],
            "pode_corrigir": ultimo is not None}


# ── o registro de decisao ────────────────────────────────────────────────────────────────────────────

def registrar(con, e, candidatos: list[Assunto], resposta: dict, agora: datetime, sinal: str | None = None) -> int | None:
    """Uma linha por texto que passou pelo roteador. None = esta mensagem ja passou (aviso repetido)."""
    destino = _assunto_do_numero(candidatos, resposta.get("destino"))
    r = con.execute(
        """INSERT INTO atendimento.roteador (wamid, wa_id, texto, candidatos, destino, sinal, confianca, criado_em)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (wamid) DO NOTHING RETURNING id""",
        (e.wamid, com_nove(e.pessoa.wa_id or ""), (e.texto or "")[:4000],
         json.dumps([a.para_json() for a in candidatos]),
         destino.chave if destino else ("correcao" if resposta.get("destino") == "correcao" else None),
         sinal or resposta.get("sinal") or "nenhum", resposta.get("confianca"), agora)).fetchone()
    return r["id"] if r else None


def _assunto_do_numero(assuntos: list[Assunto], numero) -> Assunto | None:
    if isinstance(numero, str) and numero.isdigit() and 1 <= int(numero) <= len(assuntos):
        return assuntos[int(numero) - 1]
    return None


def _rotulo_do_destino(linha) -> str:
    for c in linha["candidatos"] or []:
        if c.get("chave") == linha["destino"]:
            return c.get("rotulo") or linha["destino"]
    return linha["destino"] or "?"


def _linha(con, rid: int):
    return con.execute("SELECT * FROM atendimento.roteador WHERE id = %s", (rid,)).fetchone()


def _ultimo_aplicado(con, wa_id: str | None, agora: datetime):
    """O ultimo encaminhamento desta pessoa que ainda pode ser corrigido (ate 10 min, nao corrigido)."""
    if not wa_id:
        return None
    r = con.execute("""SELECT * FROM atendimento.roteador WHERE wa_id = %s ORDER BY id DESC LIMIT 1""",
                    (com_nove(wa_id),)).fetchone()
    if r and r["aplicado"] and r["corrigido_em"] is None and r["criado_em"] > agora - CORRECAO_ATE:
        return r
    return None


# ── 3. aplicar no fio, guardando o estado de antes ───────────────────────────────────────────────────

_COLUNAS = {
    "foto": ("material_de_campo", "grupo_id", ("legenda", "classe_bastidor", "classe_produto", "classe_fase",
                                               "data_dita", "safra_dita", "data_presumida", "pergunta_pendente",
                                               "retomar_em", "fechado_em", "lida_em")),
    "logo": ("logos_de_cliente", "id", ("erp_codigo", "cliente_dito", "pergunta_pendente", "insistiu",
                                         "nome_marca", "completada_em")),
    "cliente": ("clientes_registros", "id", ("textos", "ultimo_texto_em", "lido", "estado", "pergunta")),
    "curriculo": ("candidaturas", "id", ("feedback_texto", "espera_comentario")),
}


def _foto_tirada(con, fio: str, id_: int) -> list:
    tabela, chave, _ = _COLUNAS[fio]
    return [r["l"] for r in con.execute(
        "SELECT to_jsonb(t) AS l FROM atendimento.%s t WHERE t.%s = %%s" % (tabela, chave), (id_,)).fetchall()]


def _restaurar(con, fio: str, linhas: list) -> None:
    tabela, _, colunas = _COLUNAS[fio]
    sets = ", ".join("%s = s.%s" % (c, c) for c in colunas)
    con.execute("UPDATE atendimento.%s t SET %s FROM jsonb_populate_recordset(NULL::atendimento.%s, %%s::jsonb) s "
                "WHERE t.id = s.id" % (tabela, sets, tabela), (json.dumps(linhas),))


def _no_fio(con, saida, ia, e, agora: datetime, campo, a: Assunto, com_carencia: bool) -> tuple[bool, dict | None]:
    """Leva o texto ao fio do assunto pelo caminho de hoje. (aplicou, como_desfazer)."""
    so_texto = replace(e, toque=None, contexto=None)
    if a.fio == "chamado":
        p = pendencias.pendencia(con, a.id, e.pessoa.wa_id or "")
        if not p:
            return False, None
        apos = agora + carencia(con) if com_carencia else None
        mid = pendencias.anotar_resposta(con, saida, e.pessoa.para, p, e.texto, agora, entregar_apos=apos)
        return True, {"mensagem": mid, "espera": p["espera"], "pendencia": p["id"]}
    antes = {"linhas": _foto_tirada(con, a.fio, a.id)}
    if a.fio == "foto":
        feito = campo is not None and campo.aplicar_texto(con, saida, so_texto, agora)
    elif a.fio == "logo":
        feito = logos.responder(con, saida, so_texto, agora)
    elif a.fio == "cliente":
        feito = clientes_do_dia.tratar(con, saida, ia, so_texto, agora)
    else:
        feito = vaga.retorno_da_fran(con, saida, so_texto, agora)
    return bool(feito), antes


def _aplicado(con, rid: int, a: Assunto, desfazer, sinal: str | None = None, texto: str | None = None) -> None:
    con.execute("""UPDATE atendimento.roteador SET aplicado = true, destino = %s, desfazer = %s,
                          sinal = COALESCE(%s, sinal), texto = COALESCE(%s, texto) WHERE id = %s""",
                (a.chave, json.dumps(desfazer, default=str), sinal, texto, rid))


def _duvida(con, saida, e, rid: int, a: Assunto) -> None:
    w = saida.botoes(e.pessoa.para, E_SOBRE.format(rotulo=a.rotulo),
                     [Opcao("rot:sim:%d" % rid, "Sim"), Opcao("rot:lista:%d" % rid, "Ver os assuntos"),
                      Opcao("rot:outro:%d" % rid, "Outro assunto")])
    _enviada(con, w, e.pessoa.para, "botoes", "roteador %d: é sobre %s?" % (rid, a.rotulo))


def _lista(con, saida, para: str, rid: int, assuntos: list[Assunto]) -> None:
    linhas = [Opcao("rot:para:%d:%s" % (rid, a.chave), a.rotulo[:24], (a.ultimo_trecho or "")[:72])
              for a in assuntos[:MAX_LISTA]]
    linhas.append(Opcao("rot:outro:%d" % rid, "Outro assunto", "Seguir o atendimento de sempre"))
    w = saida.lista(para, QUAL_ASSUNTO, "Ver assuntos", linhas)
    _enviada(con, w, para, "lista", "roteador %d: qual assunto" % rid)


def _enviada(con, w, para, tipo, resumo) -> None:
    con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, %s, %s)
                   ON CONFLICT (wamid) DO NOTHING""", (w, para, tipo, (resumo or "")[:200]))


def aplicar(con, saida, ia, e, agora: datetime, campo=None) -> bool:
    """O degrau do motor. True = o texto foi tratado aqui (no fio, na duvida ou na correcao); False = a
    corrente de sempre segue com ele. Quem chama ja conferiu: chave ligada, interno, texto sem citar."""
    p = e.pessoa
    assuntos = assuntos_abertos(con, p.wa_id, p.bsuid, agora)
    ultimo = _ultimo_aplicado(con, p.wa_id, agora)
    if (not assuntos and ultimo is None) or ia is None:
        return False
    resposta = ia.rotear(montar_retrato(con, e, assuntos, agora, ultimo))
    rid = registrar(con, e, assuntos, resposta, agora)
    if rid is None:
        return True   # o mesmo aviso de novo: ja passou por aqui
    if resposta.get("destino") == "correcao":
        if ultimo is not None:
            return corrigir(con, saida, ia, e, agora, campo, rid, ultimo, assuntos,
                            _assunto_do_numero(assuntos, resposta.get("destino_certo")))
        con.execute("UPDATE atendimento.roteador SET destino = NULL, sinal = 'nenhum' WHERE id = %s", (rid,))
        resposta = {"destino": "nenhum"}
    alvo = _assunto_do_numero(assuntos, resposta.get("destino"))
    if alvo is not None and resposta.get("confianca") == "alta":
        feito, desfazer = _no_fio(con, saida, ia, e, agora, campo, alvo, com_carencia=True)
        if feito:
            _aplicado(con, rid, alvo, desfazer)
            return True
        print("roteador: %s nao aceitou o texto %s: corrente de sempre" % (alvo.chave, e.wamid), flush=True)
        return False
    if alvo is not None:
        _duvida(con, saida, e, rid, alvo)
        return True
    if len(assuntos) >= 2:
        _lista(con, saida, p.para, rid, assuntos)
        return True
    return False


def foto_primeiro(con, saida, e, agora: datetime, campo) -> bool:
    """A foto ou o video de ate 2 min com o grupo aberto vence antes de perguntar a OlivIA (spec). Vai pelo
    mesmo caminho do canal de campo, e fica no registro (sinal `proximidade`) -- inclusive para a correcao
    escrita, que e o que conserta quando a regra simples erra."""
    lider = campo.foto_agora(con, e.pessoa.wa_id, agora)
    if lider is None:
        return False
    a = Assunto("foto", lider["grupo_id"], "Foto de %s" % _hora(lider["recebido_em"]))
    rid = registrar(con, e, [a], {"destino": "1", "confianca": "alta", "sinal": "proximidade"}, agora)
    if rid is None:
        return True
    feito, desfazer = _no_fio(con, saida, None, e, agora, campo, a, com_carencia=False)
    if feito:
        _aplicado(con, rid, a, desfazer)
        return True
    con.execute("UPDATE atendimento.roteador SET destino = NULL WHERE id = %s", (rid,))
    return False


# ── 4. a correcao escrita ────────────────────────────────────────────────────────────────────────────

def _desfazer(con, agora: datetime, ultimo) -> None:
    fio = (ultimo["destino"] or "").split(":")[0]
    d = ultimo["desfazer"] or {}
    if fio == "chamado":
        m = con.execute("SELECT * FROM atendimento.pendencias_mensagens WHERE id = %s", (d.get("mensagem"),)).fetchone()
        if m and m["estado"] in ("a_entregar", "escolher", "erro"):
            con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'descartada', erro = 'corrigida pelo autor' "
                        "WHERE id = %s", (m["id"],))
        elif m and m["estado"] == "entregue":
            # ja chegou ao ERP: agente nao apaga registro -- um segundo comentario diz que o anterior nao era dali
            pendencias._entrou(con, m["pendencia_id"], "resposta", NAO_ERA)
        if d.get("pendencia") and d.get("espera"):
            con.execute("UPDATE atendimento.pendencias SET espera = %s WHERE id = %s", (d["espera"], d["pendencia"]))
    elif fio in _COLUNAS and d.get("linhas"):
        _restaurar(con, fio, d["linhas"])


def corrigir(con, saida, ia, e, agora: datetime, campo, rid: int, ultimo, assuntos: list[Assunto],
             certo: Assunto | None) -> bool:
    """"Nao, era sobre a foto": desfaz o ultimo encaminhamento e leva o texto dele ao assunto certo (ou a
    lista, se ela nao disse qual). Grava `corrigido_em`/`corrigido_para` na linha corrigida."""
    _desfazer(con, agora, ultimo)
    rotulo = _rotulo_do_destino(ultimo)
    if certo is not None and certo.chave == ultimo["destino"]:
        certo = None
    con.execute("UPDATE atendimento.roteador SET corrigido_em = %s, corrigido_para = %s WHERE id = %s",
                (agora, certo.chave if certo else "", ultimo["id"]))
    con.execute("UPDATE atendimento.roteador SET sinal = 'correcao', destino = 'correcao', texto = %s WHERE id = %s",
                (ultimo["texto"], rid))
    original = replace(e, texto=ultimo["texto"], toque=None, contexto=None)
    outros = [a for a in assuntos if a.chave != ultimo["destino"]]
    frase = TIREI if (certo is not None or outros) else TIREI_SEM_DESTINO
    _enviada(con, saida.texto(e.pessoa.para, frase.format(rotulo=rotulo)), e.pessoa.para, "texto",
             "roteador %d: tirei de %s" % (rid, rotulo))
    if certo is not None:
        feito, desfazer = _no_fio(con, saida, ia, original, agora, campo, certo, com_carencia=True)
        if feito:
            _aplicado(con, rid, certo, desfazer, sinal="correcao", texto=ultimo["texto"])
            return True
    if outros:
        _lista(con, saida, e.pessoa.para, rid, outros)
    return True


# ── 5. os toques `rot:` ──────────────────────────────────────────────────────────────────────────────

def tocar(con, saida, ia, e, agora: datetime, campo=None):
    """Os botoes da duvida. True (tratado), ou o TEXTO guardado quando a pessoa tocou "Outro assunto" (o
    motor segue a corrente de sempre com ele, sem o roteador)."""
    partes = (e.toque or "").split(":")
    if len(partes) < 3 or not partes[2].isdigit():
        return True
    r = _linha(con, int(partes[2]))
    if r is None or r["wa_id"] != com_nove(e.pessoa.wa_id or "") or r["aplicado"]:
        return True   # toque antigo, ja resolvido ou de outro numero: nada a fazer, e nao e menu
    acao = partes[1]
    if acao == "outro":
        con.execute("UPDATE atendimento.roteador SET destino = NULL, sinal = 'botao' WHERE id = %s", (r["id"],))
        return r["texto"]
    abertos = assuntos_abertos(con, e.pessoa.wa_id, e.pessoa.bsuid, agora)
    if acao == "lista":
        if abertos:
            _lista(con, saida, e.pessoa.para, r["id"], abertos)
            return True
        con.execute("UPDATE atendimento.roteador SET destino = NULL, sinal = 'botao' WHERE id = %s", (r["id"],))
        return r["texto"]
    chave = r["destino"] if acao == "sim" else ":".join(partes[3:5]) if acao == "para" else None
    alvo = next((a for a in abertos if a.chave == chave), None)
    if alvo is None:
        # o assunto fechou entre a pergunta e o toque: a lista do que esta aberto agora
        if abertos:
            _lista(con, saida, e.pessoa.para, r["id"], abertos)
            return True
        return r["texto"]
    original = replace(e, texto=r["texto"], toque=None, contexto=None)
    feito, desfazer = _no_fio(con, saida, ia, original, agora, campo, alvo, com_carencia=False)
    if feito:
        _aplicado(con, r["id"], alvo, desfazer, sinal="botao")
        return True
    return r["texto"]


# ── 6. a medida ──────────────────────────────────────────────────────────────────────────────────────

def medida(con, agora: datetime, dias: int = 7) -> dict:
    """A contagem por sinal dos ultimos `dias`, as correcoes e a fracao que entrou sem botao e sem
    correcao -- o numero da spec ("e o que diz se a equipe trava")."""
    linhas = con.execute("""SELECT sinal, count(*) AS n, count(*) FILTER (WHERE corrigido_em IS NOT NULL) AS corrigidas,
                                   count(*) FILTER (WHERE aplicado) AS aplicadas
                              FROM atendimento.roteador WHERE criado_em > %s GROUP BY sinal ORDER BY sinal""",
                         (agora - timedelta(days=dias),)).fetchall()
    por_sinal = {r["sinal"]: r["n"] for r in linhas}
    total = sum(por_sinal.values())
    direto = sum(r["aplicadas"] - r["corrigidas"] for r in linhas if r["sinal"] in ("nomeado", "proximidade"))
    return {"dias": dias, "total": total, "por_sinal": por_sinal,
            "corrigidas": sum(r["corrigidas"] for r in linhas),
            "sem_botao_nem_correcao": direto, "fracao": round(direto / total, 2) if total else None}
