"""O motor da OlivIA: o que fazer com cada mensagem que chega. #950, Fase D do plano.

ENTRADA: um evento ja gravado em `atendimento.eventos_meta` (o receptor grava e responde 200; o
motor processa depois, um por um). SAIDA: o que a `Saida` manda e o estado da conversa.

AS REGRAS DO DONO (spec, Decisao, 09/10/2026):
- **Tudo e botao.** Ate 3 opcoes, botao na mensagem; mais de 3, lista. Nunca "tente de novo".
- **Quem escreve em vez de tocar:** a IA propoe o motivo e a pessoa confirma com "Sim" ou "Ver
  todas as opcoes". A IA so devolve uma chave do menu; o link sai sempre da tabela de destinos.
- **Todo destino e link** (wa.me) de quem atende. Fora do horario, o link vai igual, com aviso.
- **Depois de 4h30**, a pergunta "recebeu o atendimento?": Sim leva a nota em tres botoes (Bom, Normal, Ruim); o Nao e o Ruim avisam o
  dono (fila de avisos, que o despachante manda por modelo de Utilidade).
- **Uma pergunta por pessoa por dia** (#969, etapa 2, dono 10/10/2026): as 4h30 contam da ULTIMA
  mensagem da pessoa, e as conversas com link do mesmo dia ficam cobertas por essa pergunta. Ela so
  sai em horario comercial (ajuste `pergunta_janela`: seg a sab, 08-11 e 14-17); fora dele, espera a
  proxima faixa, se ainda couber na janela de 24h da Meta. A nota vai logo depois do "Sim".

O QUE VOLTA NO TOQUE (o `id` do botao ou da linha), e a unica coisa que o motor confia:
    menu:<chave>      uma opcao do menu
    ia:sim:<chave>    a pessoa confirmou o que a IA propos
    ia:menu           a pessoa pediu o menu inteiro
    pos:sim | pos:nao a resposta da pergunta das 4h30
    nota:<bom|normal|ruim>  a nota da pesquisa (1..5 = a lista antiga)
    envio:...         resposta a um convite da carteira (tratada pelo modulo de envio, Fase E)
"""
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import agenda, internos
from .saida import MAX_BOTOES, Opcao, Saida

FUSO = ZoneInfo("America/Sao_Paulo")

# #1028: o que este processo deixou de mandar desde que subiu. Vai ao /saude do recepcionista, e
# existe para a etapa nao ser ela mesma um fracasso silencioso: regra que cala sem deixar rastro e
# justamente o que este projeto combate. ZERO NAO QUER DIZER DESLIGADA -- quer dizer que ninguem
# esbarrou nela, ou que o servico acabou de subir.
calados = {"lista_recusada": 0, "nao_entendo": 0}


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
class Midia:
    """#970: a foto ou o video que veio na mensagem (o arquivo fica na Meta ate alguem baixar)."""
    id: str
    tipo: str                     # foto | video
    mime: str = ""
    legenda: str = ""


@dataclass
class Entrada:
    """O que a pessoa fez, ja lido do aviso da Meta."""
    wamid: str
    pessoa: Pessoa
    toque: str | None = None      # o id do botao ou da linha tocada
    texto: str | None = None      # o que ela escreveu (ou None para audio, foto...)
    contexto: str | None = None   # a mensagem nossa a que ela respondeu
    midia: Midia | None = None    # #970: foto ou video (so o canal de campo a usa)
    tipo: str = ""                # o `type` da Meta: text, interactive, button, image, reaction, sticker...


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
    e.tipo = tipo or ""
    if tipo == "interactive":
        i = msg.get("interactive", {})
        e.toque = (i.get("button_reply") or i.get("list_reply") or {}).get("id")
    elif tipo == "button":   # o botao de resposta rapida de um MODELO (o convite)
        e.toque = (msg.get("button") or {}).get("payload")
    elif tipo == "text":
        e.texto = (msg.get("text") or {}).get("body", "")
    elif tipo in ("image", "video"):   # #970: lida so pelo canal de campo; para o resto segue "sem texto"
        m = msg.get(tipo) or {}
        if m.get("id"):
            e.midia = Midia(id=m["id"], tipo="foto" if tipo == "image" else "video",
                            mime=m.get("mime_type", ""), legenda=m.get("caption", "") or "")
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


RAIZ = "raiz"                  # a arvore do cliente
RAIZ_INTERNA = "raiz_interna"  # a arvore de quem e da casa (#1031)
RAIZES = (RAIZ, RAIZ_INTERNA)


def folhas_e_menus(con) -> list[dict]:
    """O que a IA pode propor: toda opcao ativa DA ARVORE DO CLIENTE, com o caminho ate ela.

    PARTE DA RAIZ DO CLIENTE, e nao de `pai_id IS NULL` como partia (#1031). Essa linha era o fio
    mais perigoso desta etapa: com a segunda raiz no banco e a CTE partindo de toda raiz, a IA
    passaria a alcancar a arvore interna, e um CLIENTE escrevendo texto livre poderia ouvir
    "Entendi que voce quer: Mandar foto do campo. E isso?". Nao e hipotese remota -- e o caminho de
    todo mundo que escreve em vez de tocar, e a IA e oferecida a toda conversa.
    """
    linhas = con.execute("""
        WITH RECURSIVE c AS (
            SELECT id, chave, rotulo, descricao, acao, ARRAY[]::text[] AS caminho
              FROM atendimento.menu WHERE chave = %s AND ativo
            UNION ALL
            SELECT m.id, m.chave, m.rotulo, m.descricao, m.acao, c.caminho || m.rotulo
              FROM atendimento.menu m JOIN c ON m.pai_id = c.id WHERE m.ativo)
        SELECT chave, rotulo, descricao, acao, caminho FROM c
         WHERE chave <> %s AND acao <> 'encerrar' ORDER BY chave""", (RAIZ, RAIZ)).fetchall()
    return [dict(r) for r in linhas]


# #1028: a lista que a Meta recusou nao e tentada de novo para aquele destino. Em 15/10/2026 um robo
# do outro lado (5511933157031) produziu 7 envios com 131026 Message undeliverable em 100 minutos, e
# e a nota do numero que libera o envio em degraus -- regra permanente 1 do projeto.
# O discriminador e o 131026, NUNCA o texto da mensagem: consertar pela lista AUTOMATICA esta
# descartado pelo critorio escrito dela ("so frases que gente pedindo algo nao escreve"), porque
# "nao consegui entender" e exatamente o que pessoa confusa escreve.
# E cala a LISTA, nao o destino: medido naquele numero, texto entregou 13 de 13 e lista falhou 7 de 7.
ERRO_NAO_ENTREGAVEL = "131026"


def lista_recusada(con, para: str) -> bool:
    """O WhatsApp desse destino ja recusou uma lista interativa? Entao nao mandamos outra."""
    return con.execute("""SELECT 1 FROM atendimento.enviadas
                           WHERE para = %s AND tipo = 'lista' AND erro LIKE %s LIMIT 1""",
                       (para, ERRO_NAO_ENTREGAVEL + "%")).fetchone() is not None


def perguntar(con, saida: Saida, pessoa: Pessoa, no, texto_antes: str = "") -> str | None:
    """Manda a pergunta do no com os filhos como botoes (ate 3) ou lista (mais de 3).

    None quando a lista foi calada pelo #1028 -- e `_registrar` nao grava envio que nao aconteceu.
    """
    filhos = _filhos(con, no["id"])
    opcoes = [Opcao("menu:%s" % f["chave"], f["rotulo"], f["descricao"]) for f in filhos]
    texto = (texto_antes + "\n\n" if texto_antes else "") + no["pergunta"]
    if len(opcoes) <= MAX_BOTOES:
        return saida.botoes(pessoa.para, texto, opcoes)
    if lista_recusada(con, pessoa.para):
        # o caminho de botoes acima NAO e calado: so a lista foi medida recusando (#1028)
        calados["lista_recusada"] += 1
        print("motor: %s ja recusou lista (131026): o menu '%s' nao foi mandado"
              % (pessoa.para, no["chave"]), flush=True)
        return None
    return saida.lista(pessoa.para, texto, "Ver opções", opcoes)


def dentro_do_horario(con, agora: datetime, chave: str = "horario", padrao=None) -> bool:
    h = _ajuste(con, chave, padrao or {})
    local = agora.astimezone(FUSO)
    if local.isoweekday() not in h.get("dias", []):
        return False
    hm = local.strftime("%H:%M")
    return any(ini <= hm < fim for ini, fim in h.get("faixas", []))


# Quando a pergunta "recebeu o atendimento?" pode sair (dono, 10/10/2026). Sabado entra para quem
# chamou sexta a tarde nao perder a janela de 24h ate segunda.
JANELA_DA_PERGUNTA = {"dias": [1, 2, 3, 4, 5, 6], "faixas": [["08:00", "11:00"], ["14:00", "17:00"]]}


def hora_da_pergunta(con, ultima: datetime) -> datetime:
    """4h30 depois da ultima mensagem, empurrada para a proxima faixa da janela da pergunta."""
    horas = float(_ajuste(con, "pergunta_horas", 4.5))
    j = _ajuste(con, "pergunta_janela", JANELA_DA_PERGUNTA)
    t = (ultima + timedelta(hours=horas)).astimezone(FUSO)
    for _ in range(8):
        if t.isoweekday() in j["dias"]:
            for ini, fim in sorted(j["faixas"]):
                a = t.replace(hour=int(ini[:2]), minute=int(ini[3:]), second=0, microsecond=0)
                b = t.replace(hour=int(fim[:2]), minute=int(fim[3:]), second=0, microsecond=0)
                if t < b:
                    return max(t, a)
        t = (t + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return ultima + timedelta(hours=horas)   # janela sem dia nenhum: como era


# #1031: a linha de quem chegou ao proprio destino. Diz o que aconteceu e oferece o caminho de
# volta, em vez de mandar a pessoa conversar consigo mesma.
ESSE_E_VOCE = ("Esse atendimento é você mesmo, {nome}. Se quiser falar com outra pessoa da equipe, "
               "escreva *menu* e escolha outro caminho.")


def mandar_link(con, saida: Saida, pessoa: Pessoa, no, agora: datetime) -> str:
    """O destino. `link_formato` (ajuste): `cartao` (o padrao, decisao do dono no ensaio de
    09/10/2026: o endereco solto "nao sai bonito") manda o texto e depois o cartao de contato de
    quem atende; `texto` manda o endereco wa.me no texto, como era."""
    d = con.execute("SELECT nome, whatsapp FROM atendimento.destinos WHERE id = %s",
                    (no["destino_id"],)).fetchone()
    if internos.destino_proprio(con, pessoa.wa_id, no["destino_id"]):
        # #1031: ninguem recebe o proprio cartao. Medido em 15/10/2026: o Benedito percorreu o menu
        # de cliente e recebeu o cartao de contato DELE MESMO tres vezes, por ser o destino de
        # Fretes. A conversa segue marcada com link (ela chegou ao fim do caminho); o que nao sai e
        # o cartao, porque mandar a pessoa conversar consigo e a unica resposta que nao serve.
        print("motor: %s escolheu o destino que e ele mesmo (%s): sem cartao" % (pessoa.wa_id, d["nome"]), flush=True)
        return saida.texto(pessoa.para, ESSE_E_VOCE.format(nome=d["nome"].split()[0]))
    cartao = _ajuste(con, "link_formato", "cartao") == "cartao"
    partes = []
    if no["texto_antes"]:
        partes.append(no["texto_antes"])
    if cartao:
        partes.append(_ajuste(con, "link_cartao", "Para falar com {nome}, toque em Conversar no contato abaixo.")
                      .format(nome=d["nome"].split()[0]))
    else:
        partes.append(_ajuste(con, "link", "{nome}: {link}").format(
            nome=d["nome"], link="https://wa.me/%s" % d["whatsapp"]))
    if not dentro_do_horario(con, agora):
        partes.append(_ajuste(con, "fora_do_horario", ""))
    w = saida.texto(pessoa.para, "\n\n".join(p for p in partes if p))
    if cartao:
        w = saida.contato(pessoa.para, d["nome"], d["whatsapp"])
    return w


# ── a conversa ──────────────────────────────────────────────────────────────

def _conversa_aberta(con, pessoa: Pessoa):
    return con.execute("""SELECT * FROM atendimento.conversas WHERE bsuid = %s AND situacao = 'em_curso'
                           ORDER BY id DESC LIMIT 1""", (pessoa.bsuid,)).fetchone()


def _ultima_pergunta(con, pessoa: Pessoa):
    """A conversa que levou a ultima pergunta: a resposta vale para todas as que ela cobre."""
    return con.execute("""SELECT * FROM atendimento.conversas WHERE bsuid = %s AND pergunta_da = id
                           ORDER BY pergunta_feita_em DESC, id DESC LIMIT 1""", (pessoa.bsuid,)).fetchone()


def _conversa_retomada(con, pessoa: Pessoa, agora: datetime):
    """A ultima conversa desta pessoa que a OlivIA retomou e que voltou a parar (ate 24 h): reaberta."""
    c = con.execute("""SELECT * FROM atendimento.conversas
                        WHERE bsuid = %s AND situacao = 'parou_no_meio' AND retomada_em IS NOT NULL
                          AND retomada_em > %s ORDER BY id DESC LIMIT 1""",
                    (pessoa.bsuid, agora - timedelta(hours=24))).fetchone()
    if c:
        con.execute("UPDATE atendimento.conversas SET situacao = 'em_curso' WHERE id = %s", (c["id"],))
    return c


def _chegou(con, pessoa: Pessoa, conversa, agora: datetime) -> None:
    """Toda mensagem conta como a ultima interacao, e a pergunta ainda nao feita anda junto."""
    con.execute("UPDATE atendimento.conversas SET ultimo_toque_em = %s WHERE id = %s", (agora, conversa["id"]))
    _empurrar_a_pergunta(con, pessoa, agora)


def _empurrar_a_pergunta(con, pessoa: Pessoa, agora: datetime) -> None:
    """As 4h30 contam da ultima mensagem da pessoa, inclusive do "obrigado" que nao abre conversa."""
    con.execute("""UPDATE atendimento.conversas SET pergunta_em = %s
                    WHERE bsuid = %s AND situacao = 'com_link' AND pergunta_feita_em IS NULL""",
                (hora_da_pergunta(con, agora), pessoa.bsuid))


def _nova_conversa(con, pessoa: Pessoa, agora: datetime):
    # Uma conversa que ficou em curso sem link e a pessoa voltou: a antiga parou no meio.
    con.execute("""UPDATE atendimento.conversas SET situacao = 'parou_no_meio'
                    WHERE bsuid = %s AND situacao = 'em_curso'""", (pessoa.bsuid,))
    c = con.execute("""INSERT INTO atendimento.conversas (bsuid, wa_id, nome_perfil, iniciada_em, ultimo_toque_em)
                          VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                    (pessoa.bsuid, pessoa.wa_id, pessoa.nome, agora, agora)).fetchone()
    # #969: quem e, pelo cadastro do ERP. So o retrato na conversa: o caminho nao muda por isso.
    quem = agenda.reconhecer(con, pessoa.wa_id)
    if quem:
        c = con.execute("""UPDATE atendimento.conversas
                              SET erp_cadastros = %(erp_cadastros)s, erp_codigo = %(erp_codigo)s,
                                  erp_nome = %(erp_nome)s, erp_papeis = %(erp_papeis)s,
                                  erp_contato_setor = %(erp_contato_setor)s, erp_contato_nome = %(erp_contato_nome)s
                            WHERE id = %(id)s RETURNING *""", dict(quem, id=c["id"])).fetchone()
    return c


def _registrar(con, conversa_id, para, tipo, resumo, wamid):
    if not wamid:
        return   # #1028: envio calado nao deixa linha -- enviadas conta o que a Meta aceitou
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
        con.execute("""UPDATE atendimento.conversas
                          SET situacao = 'com_link', destino_id = %s, link_em = %s, pergunta_em = %s
                        WHERE id = %s""", (no["destino_id"], agora, hora_da_pergunta(con, agora), conversa["id"]))
        _registrar(con, conversa["id"], pessoa.para, "texto", "link: %s" % no["chave"], w)
    elif no["acao"] == "texto":
        # #1031: o no diz a sua linha e PARA. Serve a opcao interna que explica o canal de campo:
        # nao leva a destino nem abre submenu, porque o que vem depois e a pessoa mandar a foto.
        w = saida.texto(pessoa.para, no["pergunta"])
        _registrar(con, conversa["id"], pessoa.para, "texto", "diz: %s" % no["chave"], w)
    elif no["acao"] == "menu_cliente":
        # #1031: a saida de quem e da casa para o atendimento de cliente -- e por onde falar com um
        # colega continua acontecendo, ja que "falar com um colega" nao e opcao do menu interno.
        mostrar_menu(con, saida, pessoa, conversa, False)
    else:   # encerrar
        w = saida.texto(pessoa.para, _ajuste(con, "encerrar", "Obrigado."))
        con.execute("UPDATE atendimento.conversas SET situacao = 'encerrada' WHERE id = %s", (conversa["id"],))
        _registrar(con, conversa["id"], pessoa.para, "texto", "encerrar", w)


def mostrar_menu(con, saida: Saida, pessoa: Pessoa, conversa, com_boas_vindas: bool) -> None:
    raiz = _no(con, RAIZ)
    antes = _ajuste(con, "boas_vindas", "") if com_boas_vindas else ""
    w = perguntar(con, saida, pessoa, raiz, antes)
    con.execute("UPDATE atendimento.conversas SET no_atual_id = %s WHERE id = %s", (raiz["id"], conversa["id"]))
    _registrar(con, conversa["id"], pessoa.para, "lista", "menu principal", w)


def mostrar_menu_interno(con, saida: Saida, pessoa: Pessoa, conversa) -> None:
    """O menu da casa (#1031). Sem boas-vindas de cliente: quem e da casa nao precisa ser acolhido.

    Se a raiz interna nao existir (migracao 018 nao aplicada), cai no menu do cliente -- degradar
    para o comportamento de antes e melhor que nao responder a ninguem.
    """
    raiz = _no(con, RAIZ_INTERNA)
    if not raiz:
        print("motor: raiz_interna ausente (migracao 018?): menu de cliente", flush=True)
        mostrar_menu(con, saida, pessoa, conversa, True)
        return
    w = perguntar(con, saida, pessoa, raiz)
    con.execute("UPDATE atendimento.conversas SET no_atual_id = %s WHERE id = %s", (raiz["id"], conversa["id"]))
    # "botoes" e nao "lista": sao duas opcoes, e `perguntar` manda botoes com MAX_BOTOES ou menos
    _registrar(con, conversa["id"], pessoa.para, "botoes", "menu da casa", w)


NAO_ENTENDO = ("Recebi, mas por aqui eu entendo texto e os botões. Me conta em uma linha o que você "
               "precisa.")

# #1028: o teto do "nao entendo". POR DESTINO e nao por conversa, de proposito -- a linha so e
# registrada quando ha conversa aberta, entao contar por conversa deixaria o caso SEM conversa
# sempre em zero, que e justamente onde o teto precisa engatar.
# Medido em 15/10/2026: gente de verdade levou UM "nao entendo" cada (tres casos em 169 envios); o
# robo levou 13 numa conversa. O teto tem folga de 100% sobre o pior caso real.
TETO_NAO_ENTENDO = 2
TETO_JANELA_H = 24
JANELA_NAO_ENTENDO = timedelta(hours=TETO_JANELA_H)


def _ja_avisou_bastante(con, para: str, agora: datetime) -> bool:
    """Ja mandamos a linha curta TETO_NAO_ENTENDO vezes para esse destino na janela? (#1028)

    LIMITE CONHECIDO: a linha curta so e REGISTRADA quando ha conversa aberta (ver o `if aberta` no
    fim de `processar`), entao o teto so engata nesse caso -- que era o do robo de 15/10 (conversa
    34, 13 linhas). Um robo que mandasse so `unsupported`, sem nunca escrever texto, nao abriria
    conversa e nao seria contado. Fechar isso exigiria gravar linha de envio calado, o que a spec
    deste chamado decidiu NAO fazer (nada escrito nesta etapa); se acontecer, e chamado proprio.
    """
    r = con.execute("""SELECT count(*) AS n FROM atendimento.enviadas
                        WHERE para = %s AND resumo LIKE 'nao entendo:%%' AND enviada_em > %s""",
                    (para, agora - JANELA_NAO_ENTENDO)).fetchone()
    return r["n"] >= TETO_NAO_ENTENDO


LISTA_ANTIGA = "Essa lista é antiga; escolha de novo aqui:"


def _no_atual(con, conversa):
    """O no cujas opcoes estao na tela da pessoa (o ultimo escolhido, ou a raiz); None sem nenhum."""
    if not conversa or not conversa["no_atual_id"]:
        return None
    return con.execute("SELECT * FROM atendimento.menu WHERE id = %s AND ativo", (conversa["no_atual_id"],)).fetchone()


def _no_por_id(con, toque: str):
    """O toque numerico de uma lista antiga: quando e o id de um no ativo, e esse no."""
    if not (toque or "").strip().isdigit():
        return None
    # #1031: as DUAS raizes ficam fora. Um toque numerico que acertasse o id da raiz interna poria
    # um cliente dentro da arvore da casa -- e e justamente de lista velha que vem esse toque.
    return con.execute("""SELECT * FROM atendimento.menu
                           WHERE id = %s AND ativo AND chave <> ALL(%s)""",
                       (int(toque), list(RAIZES))).fetchone()


def _sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower().strip()


def casar_opcao(con, ia, no, texto: str):
    """O texto escrito contra as opcoes do no onde a pessoa esta. Devolve (certo, parecido): `certo`
    e o UNICO filho cujo rotulo (ou o fim da chave) e o texto, sem acento nem maiuscula ("Sc" = SC,
    "revenda" = Revendedor); `parecido` e o que a IA, restrita a esses filhos, propoe quando nao ha
    casamento exato. Os dois None: nada aqui, segue o caminho de antes."""
    t = _sem_acento(texto)
    if not no or not t or len(t) > 80:
        return None, None
    filhos = [f for f in _filhos(con, no["id"]) if f["acao"] != "encerrar"]
    if not filhos:
        return None, None
    exatos = [f for f in filhos if _sem_acento(f["rotulo"]) == t or f["chave"].rsplit(".", 1)[-1] == t
              or _sem_acento(f["rotulo"]).split()[0] == t]
    if len(exatos) == 1:
        return exatos[0], None
    if ia is None:
        return None, None
    try:
        chave = ia.classificar(texto, [{"chave": f["chave"], "rotulo": f["rotulo"], "descricao": f["descricao"],
                                        "acao": f["acao"], "caminho": []} for f in filhos])
    except Exception:   # noqa: BLE001 -- a IA nunca derruba o atendimento
        chave = None
    parecido = next((f for f in filhos if chave and f["chave"] == chave), None)
    return None, parecido


def reperguntar(con, saida: Saida, pessoa: Pessoa, conversa, aviso: str) -> None:
    """A pergunta do no atual de novo, com uma linha antes (se houver); sem no, o menu (com a linha)."""
    no = _no_atual(con, conversa)
    if no and no["chave"] != "raiz" and _filhos(con, no["id"]):
        w = perguntar(con, saida, pessoa, no, aviso)
        _registrar(con, conversa["id"], pessoa.para, "botoes", "de novo: %s" % no["chave"], w)
        return
    if aviso:
        w = saida.texto(pessoa.para, aviso)
        _registrar(con, conversa["id"], pessoa.para, "texto", "lista antiga", w)
    mostrar_menu(con, saida, pessoa, conversa, False)


def propor(con, saida: Saida, ia, pessoa: Pessoa, conversa, texto: str, com_boas_vindas: bool, no=None) -> None:
    """Quem escreveu: a IA propoe; sem proposta (ou sem IA), o menu. `no` ja proposto (pelas opcoes
    do no atual, #988) pula a IA sobre a arvore inteira."""
    chave = None
    if no is None and ia is not None and texto.strip():
        try:
            chave = ia.classificar(texto, folhas_e_menus(con))
        except Exception:   # noqa: BLE001 -- a IA nunca derruba o atendimento
            chave = None
    no = no if no is not None else (_no(con, chave) if chave else None)
    if not no or no["chave"] == "raiz" or no["acao"] == "encerrar":
        mostrar_menu(con, saida, pessoa, conversa, com_boas_vindas)
        return
    explica = no["descricao"] or no["rotulo"]
    antes = _ajuste(con, "boas_vindas", "") + "\n\n" if com_boas_vindas else ""
    w = saida.botoes(pessoa.para, "%sEntendi que você quer: %s. É isso?" % (antes, explica),
                     [Opcao("ia:sim:%s" % no["chave"], "Sim"), Opcao("ia:menu", "Ver todas as opções")])
    con.execute("UPDATE atendimento.conversas SET ia_proposta_id = %s WHERE id = %s", (no["id"], conversa["id"]))
    _registrar(con, conversa["id"], pessoa.para, "botoes", "ia propos %s" % no["chave"], w)


def tratar(con, saida: Saida, ia, e: Entrada, agora: datetime, envio=None, campo=None) -> None:
    """Uma mensagem que chegou. `envio` trata as respostas ao convite da carteira (Fase E);
    `campo` (#970) toma a foto ou o video de equipe/representante e as respostas as perguntas dele,
    antes de qualquer conversa de atendimento abrir."""
    p = e.pessoa
    if e.toque and e.toque.startswith("envio:"):
        if envio is not None:
            envio.tratar_toque(con, saida, e, agora)
        return
    if campo is not None:
        if e.midia is not None and campo.receber(con, saida, e, agora):
            return
        if campo.responder(con, saida, e, agora):
            return
        if campo.texto_de_interno(con, saida, e, agora):
            return
    # O que nao e texto nem botao (dono, 12/10/2026, depois de um menu as 00:15): a REACAO (o joinha
    # numa mensagem nossa) nao e pedido de nada e nao se responde; figurinha, audio, foto de quem
    # nao e da equipe, localizacao, contato e documento recebem uma linha curta, nunca as
    # boas-vindas com o menu inteiro -- o menu vem quando a pessoa escrever.
    if e.tipo == "reaction":
        return
    if not e.texto and not e.toque:
        # quem e da equipe com o canal de campo ligado nao recebe esta linha: o que ele manda e
        # material, e a duvida fica no log (12/10/2026: a segunda foto do lote do dono recebeu-a)
        if campo is not None and campo.e_interno(con, p.wa_id):
            print("campo: %s de %s (%s) sem texto nem midia: ignorado" % (e.tipo or "?", p.wa_id, e.wamid), flush=True)
            return
        if _ja_avisou_bastante(con, p.para, agora):
            # #1028: avisar uma terceira vez nao ajuda ninguem, e do outro lado pode ser maquina
            calados["nao_entendo"] += 1
            print("motor: %s de %s (%s): ja avisei %d vezes em %dh -- calado"
                  % (e.tipo or "?", p.wa_id, e.wamid, TETO_NAO_ENTENDO, TETO_JANELA_H), flush=True)
            return
        print("motor: %s de %s (%s) nao e texto nem botao: linha curta" % (e.tipo or "?", p.wa_id, e.wamid), flush=True)
        w = saida.texto(p.para, NAO_ENTENDO)
        aberta = _conversa_aberta(con, p)
        if aberta:
            _chegou(con, p, aberta, agora)
            _registrar(con, aberta["id"], p.para, "texto", "nao entendo: %s" % (e.tipo or "?"), w)
        return

    # A pergunta das 4h30 e a nota respondem a ULTIMA pergunta (e todas as conversas que ela cobre).
    if e.toque in ("pos:sim", "pos:nao") or (e.toque or "").startswith("nota:"):
        c = _ultima_pergunta(con, p)
        if c:
            responder_pos(con, saida, p, c, e.toque, agora)
        return

    if e.texto and not e.toque and depois_do_atendimento(con, saida, p, e.texto, agora):
        return

    conversa = _conversa_aberta(con, p)
    if conversa is None and e.toque and (e.toque.startswith("ia:sim:") or e.toque == "ia:volta"):
        # a resposta a RETOMADA (#989) que chegou depois de a conversa voltar a "parou no meio":
        # cai na conversa retomada, nao numa nova (o Sim manda o link dela)
        conversa = _conversa_retomada(con, p, agora)
    nova = conversa is None
    if nova:
        conversa = _nova_conversa(con, p, agora)
    _chegou(con, p, conversa, agora)

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
    elif e.toque == "ia:volta":
        # "Ver opcoes" da RETOMADA (#989, dono 13/10/2026): a pergunta do ponto onde a opcao proposta
        # mora (o pai dela: "Em qual estado voce atua?" para SC), com as opcoes daquele ponto -- nao o
        # menu principal. O no atual da conversa nao serve de guia: o texto nao entendido ja a tinha
        # levado a raiz. Sem proposta (ou proposta na raiz), a pergunta do no atual; sem no, o menu.
        con.execute("UPDATE atendimento.conversas SET ia_confirmou = false WHERE id = %s", (conversa["id"],))
        pai = None
        if conversa["ia_proposta_id"]:
            pai = con.execute("""SELECT pai.* FROM atendimento.menu pai JOIN atendimento.menu filho ON filho.pai_id = pai.id
                                  WHERE filho.id = %s AND pai.ativo AND pai.chave <> ALL(%s)""",
                              (conversa["ia_proposta_id"], list(RAIZES))).fetchone()
        if pai:
            con.execute("UPDATE atendimento.conversas SET no_atual_id = %s WHERE id = %s", (pai["id"], conversa["id"]))
            w = perguntar(con, saida, p, pai)
            _registrar(con, conversa["id"], p.para, "botoes", "de novo: %s" % pai["chave"], w)
        else:
            reperguntar(con, saida, p, conversa, "")
    elif e.toque:
        # Toque que o menu de hoje nao conhece (#988, 13/10/2026: a Giovana tocou uma lista antiga,
        # ids 4 e 1, e recebeu o menu principal em silencio, duas vezes). Se o id e o de um no ativo
        # do menu, e esse no; senao, uma linha dizendo que a lista mudou e a pergunta de agora.
        no = _no_por_id(con, e.toque)
        if no:
            escolher(con, saida, p, conversa, no, agora)
        else:
            reperguntar(con, saida, p, conversa, LISTA_ANTIGA)
    else:
        # Quem foi convidado e escreveu: o texto fica tambem na linha dele na tela Envios.
        if envio is not None and e.texto:
            envio.tratar_texto_de_convidado(con, e, agora)
        # #1031: quem e da casa pedindo menu recebe o MENU DA CASA. Era aqui o furo: o Benedito
        # escreveu "Boa Tarde" (que esta no PEDE_MENU), o canal de campo devolveu False por isso, e
        # o fluxo de cliente rodou -- 15 das 20 conversas de interno abriram assim. A pergunta de
        # texto vem antes da do banco de proposito: ela e barata e descarta quase tudo.
        if internos.pede_menu(e.texto or "") and internos.e_interno(con, p.wa_id):
            mostrar_menu_interno(con, saida, p, conversa)
            return
        # Texto numa pergunta de botoes ou lista (#988: o Vinicius escreveu "Sc" no "em qual estado?"
        # e voltou ao menu principal tres vezes): primeiro as opcoes do no onde a pessoa esta --
        # o casamento exato escolhe na hora; a IA restrita as opcoes propoe com a confirmacao de
        # sempre. So depois o caminho de antes: a IA sobre a arvore inteira, e o menu.
        no_atual = _no_atual(con, conversa)
        certo, parecido = casar_opcao(con, ia, no_atual, e.texto or "")
        if certo:
            escolher(con, saida, p, conversa, certo, agora)
        elif parecido:
            propor(con, saida, ia, p, conversa, e.texto or "", nova, no=parecido)
        else:
            propor(con, saida, ia, p, conversa, e.texto or "", nova)


# ── depois do link: o joinha e a resposta automatica (dono, 14/10/2026) ──────
# Os dois "parados" de 13 e 14/10 eram isto: o dionaton mandou "👍🏻" dois minutos depois do link,
# e a ausencia automatica da Giovana respondeu a pergunta das 4h30 no mesmo minuto. Os dois abriram
# conversa, levaram o menu principal e viraram "parou no meio". Decisao do dono, sem IA (so regra):
# - a resposta automatica, a qualquer hora em que mandamos algo nas ultimas 24h: SILENCIO, porque
#   do outro lado e uma maquina e responder arrisca o vaivem entre os dois robos;
# - o agradecimento (so emoji, ou so palavras de "obrigado/ok/valeu"), sem conversa em curso e com
#   link, encerramento ou pergunta nas ultimas 24h: UMA LINHA CURTA, nunca silencio -- se a regra
#   errar, quem pediu algo le "Por nada" e escreve de novo, e a segunda mensagem segue o caminho normal.
# Nenhum dos dois abre conversa nem entra na conta de "pararam no meio".

DEPOIS_DO_ATENDIMENTO = timedelta(hours=24)
POR_NADA = "Por nada! Se precisar de mais alguma coisa, é só escrever."
# so frases que gente pedindo algo nao escreve: "assim que possivel" ficou de fora de proposito
# ("preciso do boleto assim que possivel" seria silenciado)
AUTOMATICA = ("mensagem automatica", "resposta automatica", "nao estou disponivel", "nao estamos disponiveis",
              "agradeco sua mensagem", "agradecemos sua mensagem", "agradecemos o contato", "agradecemos seu contato",
              "obrigado por entrar em contato", "obrigada por entrar em contato", "obrigado pelo contato",
              "obrigada pelo contato")
AGRADECE = {"obrigado", "obrigada", "obrigadao", "obg", "obgd", "brigado", "brigada", "valeu", "vlw", "ok", "okay",
            "blz", "beleza", "show", "top", "certo", "perfeito", "otimo", "grato", "grata", "agradeco", "joia", "tmj"}
ACOMPANHA = {"muito", "mt", "mto", "muitissimo", "de", "nada", "boa", "bom", "tarde", "noite", "dia", "entao", "ta",
             "tudo", "sim", "e", "a", "o", "pela", "pelo", "ajuda", "atencao", "abraco", "abs", "att", "deus", "abencoe"}


def e_automatica(texto: str) -> bool:
    t = _sem_acento(texto)
    return any(f in t for f in AUTOMATICA)


def e_agradecimento(texto: str) -> bool:
    """So emoji (e pontuacao), ou so palavras de agradecimento com pelo menos uma de AGRADECE."""
    if len(texto or "") > 60:
        return False
    palavras = "".join(c if c.isalnum() else " " for c in _sem_acento(texto)).split()
    if not palavras:   # so emoji: pelo menos um simbolo fora do ASCII ("?" sozinho nao e joinha)
        return any(ord(c) > 0x2000 for c in texto or "")
    return all(w in AGRADECE or w in ACOMPANHA for w in palavras) and any(w in AGRADECE for w in palavras)


def depois_do_atendimento(con, saida: Saida, pessoa: Pessoa, texto: str, agora: datetime) -> bool:
    """True quando a mensagem foi tratada aqui (e nao abre conversa)."""
    desde = agora - DEPOIS_DO_ATENDIMENTO
    if e_automatica(texto):
        if con.execute("SELECT 1 FROM atendimento.enviadas WHERE para = ANY(%s) AND enviada_em > %s LIMIT 1",
                       ([x for x in (pessoa.wa_id, pessoa.bsuid) if x], desde)).fetchone():
            print("motor: resposta automatica de %s: sem resposta" % pessoa.para, flush=True)
            return True
        return False
    if not e_agradecimento(texto) or _conversa_aberta(con, pessoa):
        return False
    c = con.execute("""SELECT id FROM atendimento.conversas
                        WHERE bsuid = %s AND situacao IN ('com_link', 'encerrada')
                          AND GREATEST(link_em, pergunta_feita_em, ultimo_toque_em) > %s
                        ORDER BY id DESC LIMIT 1""", (pessoa.bsuid, desde)).fetchone()
    if not c:
        return False
    _empurrar_a_pergunta(con, pessoa, agora)
    w = saida.texto(pessoa.para, _ajuste(con, "agradecimento", POR_NADA))
    _registrar(con, c["id"], pessoa.para, "texto", "por nada: %s" % texto, w)
    return True


# ── depois do link: a pergunta das 4h30 ─────────────────────────────────────

_PENDENTES = "bsuid = %s AND situacao = 'com_link' AND pergunta_feita_em IS NULL"


def fazer_perguntas_vencidas(con, saida: Saida, agora: datetime) -> int:
    """Uma pergunta por pessoa por dia, 4h30 depois da ultima mensagem dela (o `pergunta_em` anda a
    cada mensagem, em `_chegou`), so na janela da pergunta. A pergunta sai na conversa com link mais
    nova; as outras pendentes da pessoa ficam cobertas por ela. Devolve quantas perguntas sairam."""
    pessoas = con.execute("""SELECT bsuid, max(id) AS conversa_id, max(link_em) AS link_em
                               FROM atendimento.conversas
                              WHERE situacao = 'com_link' AND pergunta_feita_em IS NULL AND pergunta_em <= %s
                              GROUP BY bsuid ORDER BY min(pergunta_em) LIMIT 50""", (agora,)).fetchall()
    na_janela = dentro_do_horario(con, agora, "pergunta_janela", JANELA_DA_PERGUNTA)
    feitas = 0
    for p in pessoas:
        # o dia e o do atendimento: quem chamou quinta a tarde e foi perguntado quinta nao e de novo sexta
        dia = p["link_em"].astimezone(FUSO).replace(hour=0, minute=0, second=0, microsecond=0)
        hoje = con.execute("""SELECT id FROM atendimento.conversas
                               WHERE bsuid = %s AND pergunta_da = id AND pergunta_feita_em >= %s
                               ORDER BY pergunta_feita_em DESC LIMIT 1""", (p["bsuid"], dia)).fetchone()
        if hoje:
            # Ja se perguntou naquele dia: fica coberta por aquela pergunta, sem mensagem nova.
            con.execute("UPDATE atendimento.conversas SET pergunta_feita_em = %s, pergunta_da = %s WHERE " + _PENDENTES,
                        (agora, hoje["id"], p["bsuid"]))
            continue
        ultima = con.execute("SELECT max(ultimo_toque_em) AS em FROM atendimento.conversas WHERE bsuid = %s",
                             (p["bsuid"],)).fetchone()["em"]
        if agora - ultima > timedelta(hours=23):
            # Fora da janela de 24h a mensagem livre nao sai; nao se insiste.
            con.execute("UPDATE atendimento.conversas SET pergunta_feita_em = %s WHERE " + _PENDENTES,
                        (agora, p["bsuid"]))
            continue
        if not na_janela:
            continue    # o servico ficou fora na hora certa: espera a proxima faixa
        c = con.execute("SELECT * FROM atendimento.conversas WHERE id = %s", (p["conversa_id"],)).fetchone()
        _fazer_a_pergunta(con, saida, c, agora, "pergunta das 4h30")
        feitas += 1
    return feitas


def _fazer_a_pergunta(con, saida: Saida, c, agora: datetime, registro: str) -> None:
    para = c["wa_id"] or c["bsuid"]
    w = saida.botoes(para, _ajuste(con, "pergunta_recebeu", "Recebeu o atendimento?"),
                     [Opcao("pos:sim", "Sim, fui atendido"), Opcao("pos:nao", "Ainda não")])
    con.execute("UPDATE atendimento.conversas SET pergunta_feita_em = %s, pergunta_da = %s WHERE " + _PENDENTES,
                (agora, c["id"], c["bsuid"]))
    _registrar(con, c["id"], para, "botoes", registro, w)


def perguntar_agora(con, saida: Saida, conversa_id: int, agora: datetime) -> bool:
    """A pergunta de UMA conversa, ja, sem esperar as 4h30 nem a faixa (prova pedida pelo dono em
    11/10/2026, `python -m backend.pergunta_agora`). So a que esta com link, sem pergunta feita e
    dentro das 24h da ultima mensagem; qualquer outra devolve False e nada sai."""
    c = con.execute("""SELECT * FROM atendimento.conversas
                        WHERE id = %s AND situacao = 'com_link' AND pergunta_feita_em IS NULL""",
                    (conversa_id,)).fetchone()
    if not c or agora - c["ultimo_toque_em"] > timedelta(hours=23):
        return False
    _fazer_a_pergunta(con, saida, c, agora, "pergunta pedida a mao")
    return True


#: A nota em tres botoes, direto na tela (dono, 11/10/2026): a lista de cinco pedia abrir, escolher
#: e confirmar. Gravada 3, 2, 1. O toque numerico e o da lista antiga, que ainda pode chegar de
#: quem a recebeu antes: 5 e 4 = bom, 3 = normal, 2 e 1 = ruim.
NOTAS = (("bom", 3, "😃 Bom"), ("normal", 2, "😐 Normal"), ("ruim", 1, "🙁 Ruim"))
_NOTA_DO_TOQUE = {"bom": 3, "normal": 2, "ruim": 1, "5": 3, "4": 3, "3": 2, "2": 1, "1": 1}


def _avisar_o_gestor(con, c, tipo: str) -> None:
    """O aviso ao gestor (o "Nao" e a nota ruim), com todos os assuntos do dia que a pergunta cobriu."""
    quem = con.execute("SELECT nome, whatsapp FROM atendimento.destinos WHERE id = %s",
                       (_ajuste(con, "avisado_no_nao"),)).fetchone()
    if not quem:
        return
    cobertas = con.execute("""SELECT c.caminho, d.nome FROM atendimento.conversas c
                                LEFT JOIN atendimento.destinos d ON d.id = c.destino_id
                               WHERE c.pergunta_da = %s ORDER BY c.id""", (c["id"],)).fetchall()
    # as tres partes do modelo de aviso: quem, sobre o que, o contato
    sobre = "|".join([
        "%s (%s)" % (c["nome_perfil"] or "quem chamou", c["wa_id"] or "sem número"),
        "; ".join("%s, com %s" % (" › ".join(x["caminho"]) or "?", x["nome"] or "?") for x in cobertas),
        "https://wa.me/%s" % c["wa_id"] if c["wa_id"] else "sem número (veja a Recepção)"])
    con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                   VALUES (%s, %s, %s, %s)""", (tipo, quem["nome"], quem["whatsapp"], sobre))


def responder_pos(con, saida: Saida, pessoa: Pessoa, c, toque: str, agora: datetime) -> None:
    if toque == "pos:sim":
        con.execute("UPDATE atendimento.conversas SET recebeu = true WHERE pergunta_da = %s", (c["id"],))
        w = saida.botoes(pessoa.para, "Como foi nosso atendimento?",
                         [Opcao("nota:" + chave, rotulo) for chave, _, rotulo in NOTAS])
        _registrar(con, c["id"], pessoa.para, "botoes", "pesquisa", w)
    elif toque == "pos:nao":
        con.execute("UPDATE atendimento.conversas SET recebeu = false, aviso_nao_em = %s WHERE pergunta_da = %s",
                    (agora, c["id"]))
        w = saida.texto(pessoa.para, _ajuste(con, "nao_recebeu", ""))
        _registrar(con, c["id"], pessoa.para, "texto", "nao recebeu", w)
        _avisar_o_gestor(con, c, "sem_atendimento")
    elif toque.startswith("nota:") and toque[5:] in _NOTA_DO_TOQUE:
        nota = _NOTA_DO_TOQUE[toque[5:]]
        # so a primeira nota ruim avisa: tocar de novo no botao nao manda outro aviso
        ja_ruim = con.execute("SELECT satisfacao FROM atendimento.conversas WHERE id = %s", (c["id"],)).fetchone()["satisfacao"] == 1
        con.execute("UPDATE atendimento.conversas SET satisfacao = %s WHERE pergunta_da = %s", (nota, c["id"]))
        w = saida.texto(pessoa.para, _ajuste(con, "encerrar", "Obrigado."))
        _registrar(con, c["id"], pessoa.para, "texto", "obrigado pela nota", w)
        if nota == 1 and not ja_ruim:
            _avisar_o_gestor(con, c, "avaliacao_ruim")


def marcar_paradas(con, agora: datetime, minutos: int = 30) -> int:
    """D5: conversa em curso sem link 30 min depois do ultimo toque parou no meio."""
    return con.execute("""UPDATE atendimento.conversas SET situacao = 'parou_no_meio'
                           WHERE situacao = 'em_curso' AND ultimo_toque_em < %s""",
                       (agora - timedelta(minutes=minutos),)).rowcount


# ── a retomada pela OlivIA (#989, dono 13/10/2026) ───────────────────────────

RETOMADA_PADRAO = "Pelo que entendi da nossa conversa, você quer: {opcao}. É isso?"
JANELA_DA_META = timedelta(hours=24)


def _o_que_a_pessoa_disse(con, conversa) -> str:
    """Os textos e os titulos dos toques da pessoa nesta conversa, juntos: e o que a IA rele.
    Pelo `processado_em`, e nao pelo `recebido_em` (14/10/2026): o evento e gravado quando a Meta
    avisa e a conversa nasce quando ele e processado, com o MESMO momento do `processado_em`. Pelo
    `recebido_em` a mensagem que abriu a conversa ficava de fora, e quem mandou uma so dava "sem texto"."""
    partes = []
    for e in con.execute("""SELECT corpo FROM atendimento.eventos_meta
                             WHERE tipo = 'mensagem' AND processado_em >= %s
                               AND (bsuid = %s OR corpo->'msg'->>'from' = %s) ORDER BY id""",
                         (conversa["iniciada_em"], conversa["bsuid"], conversa["wa_id"] or "")).fetchall():
        msg = (e["corpo"] or {}).get("msg") or {}
        if msg.get("type") == "text":
            partes.append((msg.get("text") or {}).get("body", ""))
        elif msg.get("type") == "interactive":
            i = msg.get("interactive") or {}
            partes.append((i.get("button_reply") or i.get("list_reply") or {}).get("title", ""))
    return " / ".join(p.strip() for p in partes if p and p.strip())[:1000]


def retomar_paradas(con, saida: Saida, ia, agora: datetime) -> int:
    """Para cada conversa que parou no meio e ainda nao foi retomada: dentro das 24 h da ultima
    mensagem da pessoa, a IA rele o que ela disse e propoe a opcao do menu que resolve, com Sim e
    Ver opcoes. UMA tentativa por conversa, com ou sem mensagem: `retomada_em` e a marca. Nunca
    texto livre: so o que o menu ja daria. Devolve quantas mensagens sairam."""
    from .campo import ultima_mensagem_de   # o mesmo relogio da janela do canal de campo
    mandadas = 0
    paradas = con.execute("""SELECT * FROM atendimento.conversas
                              WHERE situacao = 'parou_no_meio' AND retomada_em IS NULL AND iniciada_em > %s
                              ORDER BY id LIMIT 20""", (agora - timedelta(days=2),)).fetchall()
    if ia is None:
        return 0   # a IA fora nao gasta a tentativa: a conversa espera o minuto em que ela voltar
    for c in paradas:
        motivo = None
        ultima = ultima_mensagem_de(con, c["wa_id"])
        if ultima is None or agora - ultima >= JANELA_DA_META:
            motivo = "fora da janela"
        texto = "" if motivo else _o_que_a_pessoa_disse(con, c)
        if not motivo and not texto:
            motivo = "sem texto"
        no = None
        if not motivo:
            try:
                chave = ia.classificar(texto, folhas_e_menus(con))
            except Exception:   # noqa: BLE001 -- a IA nunca derruba o laco
                chave = None
            no = _no(con, chave) if chave else None
            if not no or no["chave"] == "raiz" or no["acao"] == "encerrar":
                no, motivo = None, "sem opcao"
        if no is None:
            con.execute("UPDATE atendimento.conversas SET retomada_em = %s, retomada_chave = %s WHERE id = %s",
                        (agora, motivo, c["id"]))
            continue
        caminho = [r["rotulo"] for r in _caminho_ate(con, no)]
        opcao = no["rotulo"] + ((" (%s)" % " › ".join(caminho[:-1])) if len(caminho) > 1 else "")
        frase = str(_ajuste(con, "retomada", RETOMADA_PADRAO) or RETOMADA_PADRAO).replace("{opcao}", opcao)
        para = c["wa_id"] or c["bsuid"]
        try:
            w = saida.botoes(para, frase, [Opcao("ia:sim:%s" % no["chave"], "Sim"), Opcao("ia:volta", "Ver opções")])
        except Exception as falha:   # noqa: BLE001 -- a Meta recusou: uma tentativa, fica dito
            con.execute("UPDATE atendimento.conversas SET retomada_em = %s, retomada_chave = %s WHERE id = %s",
                        (agora, ("erro: %s" % falha)[:200], c["id"]))
            continue
        # a conversa volta a `em_curso` com o toque de agora: o Sim cai NELA (escolher manda o link),
        # e sem resposta `marcar_paradas` a marca de novo em 30 min -- sem segunda retomada
        con.execute("""UPDATE atendimento.conversas
                          SET situacao = 'em_curso', ultimo_toque_em = %s, ia_proposta_id = %s,
                              retomada_em = %s, retomada_chave = %s
                        WHERE id = %s""", (agora, no["id"], agora, no["chave"], c["id"]))
        _registrar(con, c["id"], para, "botoes", "ia retomou %s" % no["chave"], w)
        mandadas += 1
    return mandadas


def _caminho_ate(con, no) -> list:
    """Os nos da raiz ate `no` (sem a raiz)."""
    caminho, atual = [], no
    while atual and atual["pai_id"]:
        caminho.append(atual)
        atual = con.execute("SELECT * FROM atendimento.menu WHERE id = %s", (atual["pai_id"],)).fetchone()
    return list(reversed(caminho))
