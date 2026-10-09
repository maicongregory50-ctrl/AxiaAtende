"""O motor da OlivIA: o que fazer com cada mensagem que chega. #950, Fase D do plano.

ENTRADA: um evento ja gravado em `atendimento.eventos_meta` (o receptor grava e responde 200; o
motor processa depois, um por um). SAIDA: o que a `Saida` manda e o estado da conversa.

AS REGRAS DO DONO (spec, Decisao, 09/10/2026):
- **Tudo e botao.** Ate 3 opcoes, botao na mensagem; mais de 3, lista. Nunca "tente de novo".
- **Quem escreve em vez de tocar:** a IA propoe o motivo e a pessoa confirma com "Sim" ou "Ver
  todas as opcoes". A IA so devolve uma chave do menu; o link sai sempre da tabela de destinos.
- **Todo destino e link** (wa.me) de quem atende. Fora do horario, o link vai igual, com aviso.
- **Depois de 4h30**, a pergunta "recebeu o atendimento?": Sim leva a nota de 1 a 5; Nao avisa o
  dono (fila de avisos, que o despachante manda por modelo de Utilidade).

O QUE VOLTA NO TOQUE (o `id` do botao ou da linha), e a unica coisa que o motor confia:
    menu:<chave>      uma opcao do menu
    ia:sim:<chave>    a pessoa confirmou o que a IA propos
    ia:menu           a pessoa pediu o menu inteiro
    pos:sim | pos:nao a resposta da pergunta das 4h30
    nota:<1..5>       a nota da pesquisa
    envio:...         resposta a um convite da carteira (tratada pelo modulo de envio, Fase E)
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .saida import MAX_BOTOES, Opcao, Saida

FUSO = ZoneInfo("America/Sao_Paulo")


@dataclass
class Pessoa:
    bsuid: str
    wa_id: str | None
    nome: str

    @property
    def para(self) -> str:
        # Responde-se pelo numero quando a Meta o manda; quem so tem nome de usuario, pelo BSUID.
        return self.wa_id or self.bsuid


@dataclass
class Entrada:
    """O que a pessoa fez, ja lido do aviso da Meta."""
    wamid: str
    pessoa: Pessoa
    toque: str | None = None      # o id do botao ou da linha tocada
    texto: str | None = None      # o que ela escreveu (ou None para audio, foto...)
    contexto: str | None = None   # a mensagem nossa a que ela respondeu


# ── leitura do aviso ────────────────────────────────────────────────────────

def ler_mensagem(valor: dict, msg: dict) -> Entrada:
    """`valor` e o `value` do aviso (com `contacts`), `msg` uma das `messages`."""
    contato = next((c for c in valor.get("contacts", [])
                    if c.get("wa_id") == msg.get("from") or c.get("user_id") == msg.get("from_user_id")),
                   (valor.get("contacts") or [{}])[0])
    bsuid = contato.get("user_id") or msg.get("from_user_id") or msg.get("from") or ""
    wa_id = contato.get("wa_id") or msg.get("from") or None
    pessoa = Pessoa(bsuid=bsuid, wa_id=wa_id, nome=(contato.get("profile") or {}).get("name", ""))
    e = Entrada(wamid=msg["id"], pessoa=pessoa, contexto=(msg.get("context") or {}).get("id"))
    tipo = msg.get("type")
    if tipo == "interactive":
        i = msg.get("interactive", {})
        e.toque = (i.get("button_reply") or i.get("list_reply") or {}).get("id")
    elif tipo == "button":   # o botao de resposta rapida de um MODELO (o convite)
        e.toque = (msg.get("button") or {}).get("payload")
    elif tipo == "text":
        e.texto = (msg.get("text") or {}).get("body", "")
    return e


# ── o menu ──────────────────────────────────────────────────────────────────

def _ajuste(con, chave, padrao=None):
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (chave,)).fetchone()
    return r["valor"] if r else padrao


def _no(con, chave: str):
    return con.execute("SELECT * FROM atendimento.menu WHERE chave = %s AND ativo", (chave,)).fetchone()


def _filhos(con, no_id: int):
    return con.execute("SELECT * FROM atendimento.menu WHERE pai_id = %s AND ativo ORDER BY ordem",
                       (no_id,)).fetchall()


def folhas_e_menus(con) -> list[dict]:
    """O que a IA pode propor: toda opcao ativa, com o caminho de rotulos ate ela."""
    linhas = con.execute("""
        WITH RECURSIVE c AS (
            SELECT id, chave, rotulo, descricao, acao, ARRAY[]::text[] AS caminho
              FROM atendimento.menu WHERE pai_id IS NULL AND ativo
            UNION ALL
            SELECT m.id, m.chave, m.rotulo, m.descricao, m.acao, c.caminho || m.rotulo
              FROM atendimento.menu m JOIN c ON m.pai_id = c.id WHERE m.ativo)
        SELECT chave, rotulo, descricao, acao, caminho FROM c
         WHERE chave <> 'raiz' AND acao <> 'encerrar' ORDER BY chave""").fetchall()
    return [dict(r) for r in linhas]


def perguntar(con, saida: Saida, pessoa: Pessoa, no, texto_antes: str = "") -> str:
    """Manda a pergunta do no com os filhos como botoes (ate 3) ou lista (mais de 3)."""
    filhos = _filhos(con, no["id"])
    opcoes = [Opcao("menu:%s" % f["chave"], f["rotulo"], f["descricao"]) for f in filhos]
    texto = (texto_antes + "\n\n" if texto_antes else "") + no["pergunta"]
    if len(opcoes) <= MAX_BOTOES:
        return saida.botoes(pessoa.para, texto, opcoes)
    return saida.lista(pessoa.para, texto, "Ver opções", opcoes)


def dentro_do_horario(con, agora: datetime) -> bool:
    h = _ajuste(con, "horario", {})
    local = agora.astimezone(FUSO)
    if local.isoweekday() not in h.get("dias", []):
        return False
    hm = local.strftime("%H:%M")
    return any(ini <= hm < fim for ini, fim in h.get("faixas", []))


def mandar_link(con, saida: Saida, pessoa: Pessoa, no, agora: datetime) -> str:
    d = con.execute("SELECT nome, whatsapp FROM atendimento.destinos WHERE id = %s",
                    (no["destino_id"],)).fetchone()
    partes = []
    if no["texto_antes"]:
        partes.append(no["texto_antes"])
    partes.append(_ajuste(con, "link", "{nome}: {link}").format(
        nome=d["nome"], link="https://wa.me/%s" % d["whatsapp"]))
    if not dentro_do_horario(con, agora):
        partes.append(_ajuste(con, "fora_do_horario", ""))
    return saida.texto(pessoa.para, "\n\n".join(p for p in partes if p))


# ── a conversa ──────────────────────────────────────────────────────────────

def _conversa_aberta(con, pessoa: Pessoa):
    return con.execute("""SELECT * FROM atendimento.conversas WHERE bsuid = %s AND situacao = 'em_curso'
                           ORDER BY id DESC LIMIT 1""", (pessoa.bsuid,)).fetchone()


def _ultima_com_link(con, pessoa: Pessoa):
    return con.execute("""SELECT * FROM atendimento.conversas WHERE bsuid = %s AND situacao = 'com_link'
                           ORDER BY id DESC LIMIT 1""", (pessoa.bsuid,)).fetchone()


def _nova_conversa(con, pessoa: Pessoa, agora: datetime):
    # Uma conversa que ficou em curso sem link e a pessoa voltou: a antiga parou no meio.
    con.execute("""UPDATE atendimento.conversas SET situacao = 'parou_no_meio'
                    WHERE bsuid = %s AND situacao = 'em_curso'""", (pessoa.bsuid,))
    return con.execute("""INSERT INTO atendimento.conversas (bsuid, wa_id, nome_perfil, iniciada_em, ultimo_toque_em)
                          VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                       (pessoa.bsuid, pessoa.wa_id, pessoa.nome, agora, agora)).fetchone()


def _registrar(con, conversa_id, para, tipo, resumo, wamid):
    con.execute("""INSERT INTO atendimento.enviadas (wamid, conversa_id, para, tipo, resumo)
                   VALUES (%s, %s, %s, %s, %s)""", (wamid, conversa_id, para, tipo, resumo[:200]))


def _tocar(con, conversa, no, agora):
    con.execute("""UPDATE atendimento.conversas
                      SET no_atual_id = %s, caminho = caminho || %s::text, ultimo_toque_em = %s
                    WHERE id = %s""", (no["id"], no["rotulo"], agora, conversa["id"]))


def escolher(con, saida: Saida, pessoa: Pessoa, conversa, no, agora: datetime) -> None:
    """A pessoa escolheu `no` (tocando, ou confirmando o que a IA propos)."""
    _tocar(con, conversa, no, agora)
    if no["acao"] == "menu":
        w = perguntar(con, saida, pessoa, no)
        _registrar(con, conversa["id"], pessoa.para, "botoes", no["pergunta"], w)
    elif no["acao"] == "destino":
        w = mandar_link(con, saida, pessoa, no, agora)
        horas = float(_ajuste(con, "pergunta_horas", 4.5))
        con.execute("""UPDATE atendimento.conversas
                          SET situacao = 'com_link', destino_id = %s, link_em = %s, pergunta_em = %s
                        WHERE id = %s""", (no["destino_id"], agora, agora + timedelta(hours=horas), conversa["id"]))
        _registrar(con, conversa["id"], pessoa.para, "texto", "link: %s" % no["chave"], w)
    else:   # encerrar
        w = saida.texto(pessoa.para, _ajuste(con, "encerrar", "Obrigado."))
        con.execute("UPDATE atendimento.conversas SET situacao = 'encerrada' WHERE id = %s", (conversa["id"],))
        _registrar(con, conversa["id"], pessoa.para, "texto", "encerrar", w)


def mostrar_menu(con, saida: Saida, pessoa: Pessoa, conversa, com_boas_vindas: bool) -> None:
    raiz = _no(con, "raiz")
    antes = _ajuste(con, "boas_vindas", "") if com_boas_vindas else ""
    w = perguntar(con, saida, pessoa, raiz, antes)
    con.execute("UPDATE atendimento.conversas SET no_atual_id = %s WHERE id = %s", (raiz["id"], conversa["id"]))
    _registrar(con, conversa["id"], pessoa.para, "lista", "menu principal", w)


def propor(con, saida: Saida, ia, pessoa: Pessoa, conversa, texto: str, com_boas_vindas: bool) -> None:
    """Quem escreveu: a IA propoe; sem proposta (ou sem IA), o menu."""
    chave = None
    if ia is not None and texto.strip():
        try:
            chave = ia.classificar(texto, folhas_e_menus(con))
        except Exception:   # noqa: BLE001 -- a IA nunca derruba o atendimento
            chave = None
    no = _no(con, chave) if chave else None
    if not no or no["chave"] == "raiz" or no["acao"] == "encerrar":
        mostrar_menu(con, saida, pessoa, conversa, com_boas_vindas)
        return
    explica = no["descricao"] or no["rotulo"]
    antes = _ajuste(con, "boas_vindas", "") + "\n\n" if com_boas_vindas else ""
    w = saida.botoes(pessoa.para, "%sEntendi que você quer: %s. É isso?" % (antes, explica),
                     [Opcao("ia:sim:%s" % no["chave"], "Sim"), Opcao("ia:menu", "Ver todas as opções")])
    con.execute("UPDATE atendimento.conversas SET ia_proposta_id = %s WHERE id = %s", (no["id"], conversa["id"]))
    _registrar(con, conversa["id"], pessoa.para, "botoes", "ia propos %s" % no["chave"], w)


def tratar(con, saida: Saida, ia, e: Entrada, agora: datetime, envio=None) -> None:
    """Uma mensagem que chegou. `envio` trata as respostas ao convite da carteira (Fase E)."""
    p = e.pessoa
    if e.toque and e.toque.startswith("envio:"):
        if envio is not None:
            envio.tratar_toque(con, saida, e, agora)
        return

    # A pergunta das 4h30 e a nota respondem a ULTIMA conversa com link.
    if e.toque in ("pos:sim", "pos:nao") or (e.toque or "").startswith("nota:"):
        c = _ultima_com_link(con, p)
        if c:
            responder_pos(con, saida, p, c, e.toque, agora)
        return

    conversa = _conversa_aberta(con, p)
    nova = conversa is None
    if nova:
        conversa = _nova_conversa(con, p, agora)

    if e.toque and e.toque.startswith("menu:"):
        no = _no(con, e.toque[5:])
        if no:
            escolher(con, saida, p, conversa, no, agora)
        else:
            mostrar_menu(con, saida, p, conversa, nova)
    elif e.toque and e.toque.startswith("ia:sim:"):
        no = _no(con, e.toque[7:])
        con.execute("UPDATE atendimento.conversas SET ia_confirmou = true WHERE id = %s", (conversa["id"],))
        if no:
            escolher(con, saida, p, conversa, no, agora)
        else:
            mostrar_menu(con, saida, p, conversa, False)
    elif e.toque == "ia:menu":
        con.execute("UPDATE atendimento.conversas SET ia_confirmou = false WHERE id = %s", (conversa["id"],))
        mostrar_menu(con, saida, p, conversa, False)
    else:
        # Quem foi convidado e escreveu: o texto fica tambem na linha dele na tela Envios.
        if envio is not None and e.texto:
            envio.tratar_texto_de_convidado(con, e, agora)
        # Texto, audio, foto, toque antigo: a IA le o que der; o resto vai para o menu.
        propor(con, saida, ia, p, conversa, e.texto or "", nova)


# ── depois do link: a pergunta das 4h30 ─────────────────────────────────────

def fazer_perguntas_vencidas(con, saida: Saida, agora: datetime) -> int:
    """As conversas com link cuja hora de perguntar chegou. Devolve quantas."""
    vencidas = con.execute("""SELECT * FROM atendimento.conversas
                               WHERE situacao = 'com_link' AND pergunta_feita_em IS NULL AND pergunta_em <= %s
                               ORDER BY pergunta_em LIMIT 50""", (agora,)).fetchall()
    for c in vencidas:
        para = c["wa_id"] or c["bsuid"]
        if agora - c["ultimo_toque_em"] > timedelta(hours=23):
            # Fora da janela de 24h a mensagem livre nao sai; nao se insiste.
            con.execute("UPDATE atendimento.conversas SET pergunta_feita_em = %s WHERE id = %s", (agora, c["id"]))
            continue
        w = saida.botoes(para, _ajuste(con, "pergunta_recebeu", "Recebeu o atendimento?"),
                         [Opcao("pos:sim", "Sim, fui atendido"), Opcao("pos:nao", "Ainda não")])
        con.execute("UPDATE atendimento.conversas SET pergunta_feita_em = %s WHERE id = %s", (agora, c["id"]))
        _registrar(con, c["id"], para, "botoes", "pergunta das 4h30", w)
    return len(vencidas)


def responder_pos(con, saida: Saida, pessoa: Pessoa, c, toque: str, agora: datetime) -> None:
    if toque == "pos:sim":
        con.execute("UPDATE atendimento.conversas SET recebeu = true WHERE id = %s", (c["id"],))
        notas = [Opcao("nota:5", "🤩 Excelente"), Opcao("nota:4", "😃 Bom"), Opcao("nota:3", "😐 Regular"),
                 Opcao("nota:2", "🙁 Ruim"), Opcao("nota:1", "☹️ Péssimo")]
        w = saida.lista(pessoa.para, "Como foi nosso atendimento?", "Dar a nota", notas)
        _registrar(con, c["id"], pessoa.para, "lista", "pesquisa", w)
    elif toque == "pos:nao":
        con.execute("UPDATE atendimento.conversas SET recebeu = false, aviso_nao_em = %s WHERE id = %s",
                    (agora, c["id"]))
        w = saida.texto(pessoa.para, _ajuste(con, "nao_recebeu", ""))
        _registrar(con, c["id"], pessoa.para, "texto", "nao recebeu", w)
        quem = con.execute("SELECT nome, whatsapp FROM atendimento.destinos WHERE id = %s",
                           (_ajuste(con, "avisado_no_nao"),)).fetchone()
        destino = con.execute("SELECT nome FROM atendimento.destinos WHERE id = %s", (c["destino_id"],)).fetchone()
        if quem:
            # as tres partes do modelo aviso_sem_atendimento: quem, sobre o que, o contato
            sobre = "|".join([
                "%s (%s)" % (c["nome_perfil"] or "quem chamou", c["wa_id"] or "sem número"),
                "%s, com %s" % (" › ".join(c["caminho"]) or "?", destino["nome"] if destino else "?"),
                "https://wa.me/%s" % c["wa_id"] if c["wa_id"] else "sem número (veja a Recepção)"])
            con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                           VALUES ('sem_atendimento', %s, %s, %s)""", (quem["nome"], quem["whatsapp"], sobre))
    elif toque.startswith("nota:") and toque[5:].isdigit():
        con.execute("UPDATE atendimento.conversas SET satisfacao = %s WHERE id = %s", (int(toque[5:]), c["id"]))
        w = saida.texto(pessoa.para, _ajuste(con, "encerrar", "Obrigado."))
        _registrar(con, c["id"], pessoa.para, "texto", "obrigado pela nota", w)


def marcar_paradas(con, agora: datetime, minutos: int = 30) -> int:
    """D5: conversa em curso sem link 30 min depois do ultimo toque parou no meio."""
    return con.execute("""UPDATE atendimento.conversas SET situacao = 'parou_no_meio'
                           WHERE situacao = 'em_curso' AND ultimo_toque_em < %s""",
                       (agora - timedelta(minutes=minutos),)).rowcount
