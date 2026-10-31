"""O molde de PENDENCIA: um assunto aberto com uma pessoa, as mensagens que saem e a resposta que volta.
#1222, dono 31/10/2026. Spec: docs/specs/2026-10-31-o-chamado-no-whatsapp.md.

O chamado e o primeiro tipo. Tipo novo (a triagem de curriculo, o cliente aberto, a pergunta de foto,
anotados para o fim do #1222) e linha em `TIPOS`, nao tabela: o rotulo, e o que a resposta vira.

ESTE MODULO E DO RECEPCIONISTA (Meta e banco, nunca o ERP). A ida e a volta com o ERP sao das TELAS
(`pendencias_erp.py`); a tabela e a fila entre os dois.

O QUE SAI (`mandar`, a cada minuto):
- as mensagens `esperando` da mesma pessoa saem JUNTAS, um bloco por chamado, depois de
  `pendencias.juntar_minutos` sem mensagem nova para ela (a rajada de "esta no ar" + "fechado");
- dentro da janela de 24 h: texto; a entrega ganha em seguida os botoes Ficou bom / Nao ficou bom;
- fora dela: o informativo espera CALADO; a pergunta e a entrega levam a reabertura de sempre
  ("Voce tem N aviso(s)... Ver"), uma por pessoa por vez. O toque abre a janela e a volta seguinte manda.

O QUE VOLTA (`tratar`, no topo da corrente do motor; `oferecer`, no lugar do pega-tudo):
- resposta CITADA a uma mensagem nossa: vai a pendencia daquela mensagem, sem IA;
- os toques `pend:` (Ficou bom, Nao ficou bom, a escolha do chamado);
- o texto depois de "Nao ficou bom" e o motivo;
- texto SEM citar de quem tem pendencia esperando: a OlivIA propoe uma, a pessoa confirma.
O que volta fica `a_entregar`, e as TELAS levam ao ERP.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .envio import com_nove, janela_aberta, modelo_do_uso, parametros
from .saida import Opcao

NAO_VISTO = timedelta(days=7)
LIMITE_TEXTO = 3800        # a Meta aceita 4096 no texto; a margem e do rotulo e do rodape
SEPARADOR = "\n\n— — —\n\n"

TIPOS = {"chamado": {"rotulo": "Chamado"}}

RODAPE = {"pergunta": "_Para responder, deslize esta mensagem para o lado._",
          "informativo": "_Só aviso, não precisa responder._",
          "entrega": ""}
SO_AVISO = ("Anotado. Esta mensagem é só um aviso; se precisar falar do chamado, responda no sistema "
            "ou na próxima pergunta.")
QUAL_FALHOU = "O que não ficou bom? Escreva em uma linha."


def rotulo(p) -> str:
    base = "%s %s" % (TIPOS[p["tipo"]]["rotulo"], p["referencia"])
    return ("%s · %s" % (base, p["titulo"])) if p["titulo"] else base


def _ajuste(con, chave, padrao):
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (chave,)).fetchone()
    return padrao if r is None else r["valor"]


def ligado(con) -> bool:
    return _ajuste(con, "pendencias.ligado", False) is True


def _enviada(con, w, para, tipo, resumo):
    con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, %s, %s)",
                (w, para, tipo, resumo[:200]))


# ── o que sai ────────────────────────────────────────────────────────────────

def _blocos(con, numero: str) -> list[tuple[dict, list[dict]]]:
    """[(pendencia, [mensagens])] das que esperam sair para o numero, na ordem em que chegaram."""
    msgs = con.execute("""SELECT m.*, p.tipo, p.referencia, p.titulo, p.espera, p.id AS pid
                            FROM atendimento.pendencias_mensagens m
                            JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                           WHERE m.sentido = 'saiu' AND m.estado IN ('esperando', 'guardada')
                             AND p.para_whatsapp = %s
                           ORDER BY m.id""", (numero,)).fetchall()
    ordem, grupos = [], {}
    for m in msgs:
        if m["pid"] not in grupos:
            ordem.append(m["pid"])
            grupos[m["pid"]] = (dict(m), [])
        grupos[m["pid"]][1].append(dict(m))
    return [grupos[pid] for pid in ordem]


def _texto_do_bloco(p, msgs) -> str:
    classes = {m["classe"] for m in msgs}
    rodape = RODAPE["pergunta"] if "pergunta" in classes else (
        "" if "entrega" in classes else RODAPE["informativo"])
    corpo = "\n\n".join(m["texto"] for m in msgs)
    return "*%s*\n%s%s" % (rotulo(p), corpo, ("\n\n" + rodape) if rodape else "")


def _mandar_numero(con, saida, numero: str, agora: datetime) -> int:
    """Manda tudo o que espera para o numero (a janela ja foi conferida). Devolve quantas mensagens."""
    blocos = _blocos(con, numero)
    if not blocos:
        return 0
    # os blocos viram mensagens de ate LIMITE_TEXTO; um bloco maior que isso vai sozinho, cortado
    lotes, atual = [], []
    for p, msgs in blocos:
        t = _texto_do_bloco(p, msgs)
        if atual and len(SEPARADOR.join(x[0] for x in atual)) + len(SEPARADOR) + len(t) > LIMITE_TEXTO:
            lotes.append(atual)
            atual = []
        atual.append((t[:4000], p, msgs))
    lotes.append(atual)
    feitas = 0
    for lote in lotes:
        w = saida.texto(numero, SEPARADOR.join(x[0] for x in lote))
        _enviada(con, w, numero, "texto", "pendencias: " + ", ".join(rotulo(x[1]) for x in lote))
        ids = [m["id"] for x in lote for m in x[2]]
        con.execute("""UPDATE atendimento.pendencias_mensagens SET estado = 'enviada', wamid = %s, enviada_em = %s
                        WHERE id = ANY(%s)""", (w, agora, ids))
        feitas += 1
        for _t, p, msgs in lote:
            if any(m["classe"] == "entrega" for m in msgs) and p["espera"] == "validacao":
                wb = saida.botoes(numero, "%s: ficou bom?" % rotulo(p),
                                  [Opcao("pend:ok:%d" % p["pid"], "Ficou bom"),
                                   Opcao("pend:nao:%d" % p["pid"], "Não ficou bom")])
                _enviada(con, wb, numero, "botoes", "pendencia %d: ficou bom?" % p["pid"])
                feitas += 1
    return feitas


def _reabrir(con, saida, numero: str, agora: datetime, quantos: int) -> None:
    m = modelo_do_uso(con, "reabertura")
    if not m:
        raise RuntimeError("nenhum modelo cadastrado para reabertura")
    w = saida.modelo(numero, m["nome"], m["idioma"], parametros(m, {"n_avisos": quantos}),
                     botoes=["reabrir:%s" % numero])
    _enviada(con, w, numero, "modelo", "reabertura das pendencias")


def mandar(con, saida, agora: datetime) -> int:
    """A volta do minuto (RECEPCIONISTA). Desligado, nada."""
    if not ligado(con):
        return 0
    juntar = timedelta(minutes=int(_ajuste(con, "pendencias.juntar_minutos", 10) or 0))
    feitas = 0
    # 7 dias guardada sem a pessoa voltar: nao sai mais, e a pendencia deixa de esperar
    velhas = con.execute("""UPDATE atendimento.pendencias_mensagens SET estado = 'descartada',
                                   erro = 'nao vista em 7 dias'
                             WHERE sentido = 'saiu' AND estado = 'guardada' AND criado_em < %s
                         RETURNING pendencia_id""", (agora - NAO_VISTO,)).fetchall()
    if velhas:
        con.execute("UPDATE atendimento.pendencias SET espera = NULL WHERE id = ANY(%s)",
                    ([v["pendencia_id"] for v in velhas],))
    for g in con.execute("""SELECT p.para_whatsapp AS numero, max(m.criado_em) AS ultima,
                                   bool_or(m.estado = 'guardada') AS guardada,
                                   bool_or(m.classe IN ('pergunta', 'entrega')) AS pede,
                                   count(DISTINCT p.id) AS assuntos
                              FROM atendimento.pendencias_mensagens m
                              JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                             WHERE m.sentido = 'saiu' AND m.estado IN ('esperando', 'guardada')
                             GROUP BY p.para_whatsapp""").fetchall():
        if agora - g["ultima"] < juntar:
            continue   # a rajada ainda pode crescer
        try:
            with con.transaction():
                if janela_aberta(con, g["numero"], agora):
                    feitas += _mandar_numero(con, saida, g["numero"], agora)
                elif g["pede"] and not g["guardada"]:
                    _reabrir(con, saida, g["numero"], agora, g["assuntos"])
                    con.execute("""UPDATE atendimento.pendencias_mensagens m SET estado = 'guardada'
                                     FROM atendimento.pendencias p
                                    WHERE p.id = m.pendencia_id AND p.para_whatsapp = %s
                                      AND m.sentido = 'saiu' AND m.estado = 'esperando'""", (g["numero"],))
                    feitas += 1
                # fora da janela e so informativo: espera calado (dono, 31/10/2026)
        except Exception as falha:  # noqa: BLE001 -- um numero com erro nao segura os outros
            print("pendencias: envio a ...%s: %s" % (g["numero"][-4:], falha), flush=True)
    return feitas


def soltar_agora(con, saida, numero: str, agora: datetime) -> int:
    """A pessoa acabou de escrever (a janela abriu): o que espera por ela sai ja, sem a juncao.
    Usado no lugar do menu da casa quando o "Bom dia" encontra mensagem esperando (spec, decisao 7)."""
    if not ligado(con):
        return 0
    return _mandar_numero(con, saida, com_nove(numero), agora)


# ── o que volta ──────────────────────────────────────────────────────────────

def _pendencias_da_pessoa(con, numero: str, so_esperando: bool = True) -> list[dict]:
    filtro = "AND espera IS NOT NULL" if so_esperando else ""
    return [dict(r) for r in con.execute(
        "SELECT * FROM atendimento.pendencias WHERE para_whatsapp = %s " + filtro + " ORDER BY ultima_em DESC, id DESC",
        (com_nove(numero),)).fetchall()]


def _entrou(con, pendencia_id: int, classe: str, texto: str, estado: str = "a_entregar",
            resultado: str | None = None) -> int:
    return con.execute("""INSERT INTO atendimento.pendencias_mensagens
                              (pendencia_id, sentido, classe, texto, estado, resultado)
                          VALUES (%s, 'entrou', %s, %s, %s, %s) RETURNING id""",
                       (pendencia_id, classe, texto[:4000], estado, resultado)).fetchone()["id"]


def _responder(con, saida, para, texto, resumo):
    w = saida.texto(para, texto)
    _enviada(con, w, para, "texto", resumo)


def _anotar_resposta(con, saida, para, p, texto, agora) -> None:
    _entrou(con, p["id"], "resposta", texto)
    con.execute("""UPDATE atendimento.pendencias SET espera = CASE WHEN espera = 'resposta' THEN NULL ELSE espera END,
                          ultima_em = %s WHERE id = %s""", (agora, p["id"]))
    _responder(con, saida, para, "Anotado no %s. ✓" % rotulo(p).split(" · ")[0].lower(),
               "pendencia %d: anotado" % p["id"])


def _pendencia(con, pid: int, numero: str):
    """A pendencia, so se for DESTE numero: um toque de outro numero nao mexe no assunto de ninguem."""
    p = con.execute("SELECT * FROM atendimento.pendencias WHERE id = %s", (pid,)).fetchone()
    return dict(p) if p and p["para_whatsapp"] == com_nove(numero) else None


def _lista_de_escolha(con, saida, para, numero, mid) -> None:
    pend = _pendencias_da_pessoa(con, numero)[:9]
    linhas = [Opcao("pend:para:%d:%d" % (mid, p["id"]), ("%s %s" % (TIPOS[p["tipo"]]["rotulo"], p["referencia"]))[:24],
                    (p["titulo"] or "")[:72]) for p in pend]
    linhas.append(Opcao("pend:outro:%d" % mid, "Outro assunto", "Seguir o atendimento de sempre"))
    w = saida.lista(para, "Sobre qual assunto é a sua mensagem?", "Ver assuntos", linhas)
    _enviada(con, w, para, "lista", "pendencias: escolher o assunto")


def _toque(con, saida, e, agora) -> str | None:
    """Os toques `pend:`. Devolve o texto guardado quando a pessoa escolheu "Outro assunto" (o motor
    segue a corrente de sempre com ele); senao None."""
    para, numero = e.pessoa.para, e.pessoa.wa_id or ""
    partes = e.toque.split(":")
    acao = partes[1] if len(partes) > 1 else ""
    if acao in ("ok", "nao") and len(partes) == 3 and partes[2].isdigit():
        p = _pendencia(con, int(partes[2]), numero)
        if not p or p["espera"] != "validacao":
            _responder(con, saida, para, "Esta entrega já foi respondida. ✓", "pendencia: toque repetido")
            return None
        if acao == "ok":
            _entrou(con, p["id"], "validacao", "Ficou bom", resultado="entregue")
            con.execute("UPDATE atendimento.pendencias SET espera = NULL, ultima_em = %s WHERE id = %s", (agora, p["id"]))
            _responder(con, saida, para, "Obrigado! O %s foi fechado. ✓" % rotulo(p).split(" · ")[0].lower(),
                       "pendencia %d: ficou bom" % p["id"])
        else:
            con.execute("UPDATE atendimento.pendencias SET aguardando_motivo = true, ultima_em = %s WHERE id = %s",
                        (agora, p["id"]))
            _responder(con, saida, para, QUAL_FALHOU, "pendencia %d: qual falhou" % p["id"])
        return None
    mid = int(partes[2]) if len(partes) > 2 and partes[2].isdigit() else None
    m = con.execute("""SELECT m.*, p.para_whatsapp FROM atendimento.pendencias_mensagens m
                         JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                        WHERE m.id = %s AND m.estado = 'escolher'""", (mid,)).fetchone() if mid else None
    if not m or m["para_whatsapp"] != com_nove(numero):
        return None   # toque antigo ou de outro numero: nada a fazer, e nao e menu
    if acao == "sim":
        p = _pendencia(con, m["pendencia_id"], numero)
        con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'descartada' WHERE id = %s", (mid,))
        if p:
            _anotar_resposta(con, saida, para, p, m["texto"], agora)
    elif acao == "para" and len(partes) == 4 and partes[3].isdigit():
        p = _pendencia(con, int(partes[3]), numero)
        con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'descartada' WHERE id = %s", (mid,))
        if p:
            _anotar_resposta(con, saida, para, p, m["texto"], agora)
    elif acao == "lista":
        _lista_de_escolha(con, saida, para, numero, mid)
    elif acao == "outro":
        con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'descartada' WHERE id = %s", (mid,))
        return m["texto"]
    return None


def tratar(con, saida, e, agora: datetime):
    """O degrau do TOPO da corrente. Devolve False (nao era daqui), True (tratado) ou um texto (a pessoa
    escolheu "Outro assunto": o motor segue a corrente com ele)."""
    if not ligado(con):
        return False
    numero = e.pessoa.wa_id or ""
    if e.toque and e.toque.startswith("pend:"):
        texto = _toque(con, saida, e, agora)
        return texto if texto else True
    if not e.texto or e.toque:
        return False
    # o motivo do "Nao ficou bom"
    p = next((x for x in _pendencias_da_pessoa(con, numero) if x["aguardando_motivo"]), None)
    if p:
        _entrou(con, p["id"], "validacao", e.texto, resultado="nao_ficou_bom")
        con.execute("""UPDATE atendimento.pendencias SET espera = NULL, aguardando_motivo = false, ultima_em = %s
                        WHERE id = %s""", (agora, p["id"]))
        _responder(con, saida, e.pessoa.para, "Anotado. O %s voltou para ajuste e avisamos aqui."
                   % rotulo(p).split(" · ")[0].lower(), "pendencia %d: nao ficou bom" % p["id"])
        return True
    # a resposta CITADA a uma mensagem nossa
    if not e.contexto:
        return False
    alvo = [dict(r) for r in con.execute(
        """SELECT DISTINCT p.* FROM atendimento.pendencias_mensagens m
             JOIN atendimento.pendencias p ON p.id = m.pendencia_id
            WHERE m.wamid = %s AND m.sentido = 'saiu'""", (e.contexto,)).fetchall()]
    alvo = [p for p in alvo if p["para_whatsapp"] == com_nove(numero)]
    if not alvo:
        return False
    esperando = [p for p in alvo if p["espera"]]
    if len(esperando) == 1:
        _anotar_resposta(con, saida, e.pessoa.para, esperando[0], e.texto, agora)
    elif esperando:
        mid = _entrou(con, esperando[0]["id"], "resposta", e.texto, estado="escolher")
        _lista_de_escolha(con, saida, e.pessoa.para, numero, mid)
    else:
        p = alvo[0]
        _entrou(con, p["id"], "resposta", e.texto, estado="descartada")
        if not p["avisou_informativo"]:
            con.execute("UPDATE atendimento.pendencias SET avisou_informativo = true WHERE id = %s", (p["id"],))
            _responder(con, saida, e.pessoa.para, SO_AVISO, "pendencia %d: so aviso" % p["id"])
    return True


def oferecer(con, saida, ia, e, agora: datetime) -> bool:
    """O degrau no lugar do pega-tudo: texto SEM citar de quem tem pendencia esperando. A OlivIA propoe
    uma (lista fechada, ou "nenhuma") e a pessoa confirma. "Nenhuma", ou IA fora: False, e a corrente
    segue como hoje."""
    if ia is None or not e.texto or e.toque or not ligado(con):
        return False
    pend = _pendencias_da_pessoa(con, e.pessoa.wa_id or "")
    if not pend:
        return False
    escolhida = ia.escolher_pendencia(e.texto, [{"id": p["id"], "rotulo": rotulo(p)} for p in pend])
    p = next((x for x in pend if x["id"] == escolhida), None)
    if not p:
        return False
    mid = _entrou(con, p["id"], "resposta", e.texto, estado="escolher")
    w = saida.botoes(e.pessoa.para, "É sobre o %s?" % rotulo(p),
                     [Opcao("pend:sim:%d" % mid, "Sim"), Opcao("pend:lista:%d" % mid, "Outro chamado"),
                      Opcao("pend:outro:%d" % mid, "Outro assunto")])
    _enviada(con, w, e.pessoa.para, "botoes", "pendencia %d: e sobre?" % p["id"])
    return True


def tem_esperando(con, numero: str) -> bool:
    return con.execute("""SELECT 1 FROM atendimento.pendencias_mensagens m
                            JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                           WHERE p.para_whatsapp = %s AND m.sentido = 'saiu'
                             AND m.estado IN ('esperando', 'guardada') LIMIT 1""",
                       (com_nove(numero),)).fetchone() is not None
