"""O TRABALHE CONOSCO: a vaga aberta, o curriculo em PDF e a pre-triagem para a Fran. #1098.

Spec: docs/specs/2026-10-22-trabalhe-conosco-vaga-e-pre-triagem.md (caminho B, dono, 22/10/2026).

QUEM CHEGA: pelo anuncio da vaga (o `referral` da Meta), pelo no "Trabalhe conosco" do menu, ou de
volta em ate 30 dias depois de uma conversa de vaga ("voces receberam meu curriculo?"). A conversa
fica marcada (`conversas.trabalhe`) e termina como `curriculo_recebido` ou `sem_curriculo`, nunca
`parou_no_meio`: os leitores de decisao (marcar_paradas, retomar_paradas, a pergunta das 4h30) nao
leem esses dois valores, e e de proposito.

AS REGRAS DO DONO, e o codigo segue so elas:
- **So PDF, sempre** (decisao 7). Foto, Word, audio ou texto recebem "Precisamos do seu curriculo em
  PDF", e sem PDF nada vai a Fran.
- **A IA so escolhe a chave** de uma resposta aprovada (`respostas_da_vaga`, regra 3 do projeto). A
  pre-triagem e texto da IA, mas vai SO a Fran, nunca ao candidato (decisao 2).
- **Um curriculo por mensagem** a Fran, com o PDF, a triagem e os botoes "Triagem certa" / "Triagem
  errada" (decisao 3). A decisao e dela.
- **Doze meses** (decisao 5): vencido, o PDF, o texto, a triagem, o nome e o numero sao apagados.

A FRAN E "DA CASA" para o atendimento (`internos.quem_e` le os destinos). Por isso o retorno dela
(`retorno_da_fran`) e tratado ANTES do canal de campo em `motor.tratar`: senao o comentario dela
depois de "Triagem errada" viraria a frase da proxima foto.
"""
import hashlib
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from . import internos
from .envio import _assinatura, com_nove, primeiro_nome
from .saida import Opcao, Saida, wa_id_do_whatsapp

VOLTA = timedelta(days=30)           # quem volta em ate 30 dias cai de novo na vaga
DOZE_MESES = timedelta(days=365)
TRIAGEM_ATE = 10 * 1024 * 1024       # PDF maior que isso vai a Fran sem triagem
POR_MINUTO = 5                       # candidaturas mandadas a Fran por volta do laco
TENTAR_DE_NOVO = timedelta(hours=1)  # modelo recusado (ainda nao aprovado): uma tentativa por hora
COMENTARIO_ATE = timedelta(hours=24)

TODOS, NEM_TODOS, OUTRO = "vaga:todos", "vaga:nem_todos", "vaga:outro"
MANDAR, ENCERRAR = "vaga:mandar", "vaga:encerrar"

SITUACAO = {"consta": "consta", "nao": "não", "nao_consta": "não consta no currículo"}
DECLAROU = {"todos": "atende a todos os requisitos", "nem_todos": "não atende a todos os requisitos",
            None: "não respondeu"}


# ── o cadastro ──────────────────────────────────────────────────────────────

def vaga_aberta(con, anuncio: str | None = None):
    """A vaga aberta (a do anuncio, quando ele vem); None sem vaga aberta ou anuncio de outra coisa."""
    if anuncio:
        return con.execute("""SELECT * FROM atendimento.vagas WHERE aberta AND %s = ANY(anuncio_ids)
                               ORDER BY id LIMIT 1""", (anuncio,)).fetchone()
    return con.execute("SELECT * FROM atendimento.vagas WHERE aberta ORDER BY id LIMIT 1").fetchone()


def _vaga(con, vaga_id):
    return con.execute("SELECT * FROM atendimento.vagas WHERE id = %s", (vaga_id,)).fetchone() if vaga_id else None


def quem_atende(con):
    """O destino do no "Trabalhe conosco" (a Fran): quem recebe o curriculo e o "falar com uma pessoa".
    A tela Destinos troca esse destino."""
    return con.execute("""SELECT d.* FROM atendimento.menu m JOIN atendimento.destinos d ON d.id = m.destino_id
                           WHERE m.chave = 'trabalhe' AND d.ativo""").fetchone()


def _resposta(con, chave: str):
    return con.execute("SELECT * FROM atendimento.respostas_da_vaga WHERE chave = %s AND ativo",
                       (chave,)).fetchone()


def _texto(con, chave: str, vaga=None, **extra) -> str:
    r = _resposta(con, chave)
    t = r["texto"] if r else ""
    valores = {"vaga": vaga["titulo"] if vaga else "", "regiao": vaga["regiao"] if vaga else "",
               "beneficios": vaga["beneficios"] if vaga else "",
               "requisitos": "\n".join("• " + q for q in (vaga["requisitos"] if vaga else [])), **extra}
    for k, v in valores.items():
        t = t.replace("{%s}" % k, str(v))
    return t


def _para_ia(con) -> list[dict]:
    return [{"chave": r["chave"], "rotulo": r["chave"], "descricao": r["descricao"], "caminho": []}
            for r in con.execute("""SELECT chave, descricao FROM atendimento.respostas_da_vaga
                                     WHERE para_ia AND ativo ORDER BY ordem""")]


# ── a conversa ──────────────────────────────────────────────────────────────

def _conversa_de_vaga(con, pessoa):
    return con.execute("""SELECT * FROM atendimento.conversas WHERE bsuid = %s AND situacao = 'em_curso'
                           AND trabalhe ORDER BY id DESC LIMIT 1""", (pessoa.bsuid,)).fetchone()


def _marcar(con, conversa, vaga) -> dict:
    return con.execute("""UPDATE atendimento.conversas SET trabalhe = true, vaga_id = %s
                           WHERE id = %s RETURNING *""", (vaga["id"] if vaga else None, conversa["id"])).fetchone()


def abrir(con, saida: Saida, pessoa, conversa, vaga, agora: datetime):
    """A conversa entra na vaga: os requisitos e os tres botoes. Sem vaga aberta, o pedido do PDF
    para as proximas."""
    from .motor import _registrar
    conversa = _marcar(con, conversa, vaga)
    if vaga is None:
        w = saida.texto(pessoa.para, _texto(con, "sem_vaga"))
        _registrar(con, conversa["id"], pessoa.para, "texto", "vaga: sem vaga aberta", w)
        return conversa
    nome = primeiro_nome(pessoa.nome) if (pessoa.nome or "").strip() else ""
    saudacao = "Olá, %s!" % nome if nome else "Olá!"
    w = saida.botoes(pessoa.para, _texto(con, "abertura", vaga, saudacao=saudacao),
                     [Opcao(TODOS, "Sim, atendo todos"), Opcao(NEM_TODOS, "Não atendo todos"),
                      Opcao(OUTRO, "Era outro assunto")])
    _registrar(con, conversa["id"], pessoa.para, "botoes", "vaga: abertura", w)
    return conversa


def do_menu(con, saida: Saida, pessoa, conversa, no, agora: datetime) -> None:
    """O no "Trabalhe conosco" (acao `vaga`), tocado no menu."""
    abrir(con, saida, pessoa, conversa, vaga_aberta(con), agora)


def _fechar(con, conversa, situacao: str) -> None:
    con.execute("UPDATE atendimento.conversas SET situacao = %s WHERE id = %s", (situacao, conversa["id"]))


def _sair_da_vaga(con, saida, pessoa, conversa) -> None:
    """"Era outro assunto": a conversa deixa de ser de vaga e a pessoa ve o menu principal."""
    from .motor import mostrar_menu
    conversa = con.execute("""UPDATE atendimento.conversas SET trabalhe = false, vaga_id = NULL, vaga_declarou = NULL
                               WHERE id = %s RETURNING *""", (conversa["id"],)).fetchone()
    mostrar_menu(con, saida, pessoa, conversa, False)


def e_pdf(documento) -> bool:
    return documento is not None and ((documento.mime or "").lower() == "application/pdf"
                                      or (documento.nome_arquivo or "").lower().endswith(".pdf"))


def _ultima_candidatura(con, pessoa):
    return con.execute("""SELECT * FROM atendimento.candidaturas WHERE bsuid = %s AND apagada_em IS NULL
                           ORDER BY recebida_em DESC LIMIT 1""", (pessoa.bsuid,)).fetchone()


def _receber_pdf(con, saida: Saida, e, conversa, agora: datetime) -> None:
    from .motor import _o_que_a_pessoa_disse, _registrar
    p = e.pessoa
    if con.execute("SELECT 1 FROM atendimento.candidaturas WHERE wamid = %s", (e.wamid,)).fetchone():
        return   # a Meta reenviou o aviso: o curriculo ja esta guardado
    with tempfile.TemporaryDirectory() as pasta:
        arquivo = Path(saida.baixar(e.documento.id, Path(pasta) / "curriculo.pdf"))
        dados = arquivo.read_bytes()
    con.execute("""INSERT INTO atendimento.candidaturas
                      (vaga_id, conversa_id, bsuid, wa_id, nome_perfil, declarou, texto, wamid,
                       pdf, pdf_nome, pdf_sha256, pdf_bytes, recebida_em, apagar_em)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (conversa["vaga_id"], conversa["id"], p.bsuid, p.wa_id, p.nome or "", conversa["vaga_declarou"],
                 _o_que_a_pessoa_disse(con, conversa)[:1000], e.wamid, dados,
                 (e.documento.nome_arquivo or "curriculo.pdf")[:200], hashlib.sha256(dados).hexdigest(),
                 len(dados), agora, agora + DOZE_MESES))
    w = saida.texto(p.para, _texto(con, "recebido"))
    _registrar(con, conversa["id"], p.para, "texto", "vaga: curriculo recebido", w)
    _fechar(con, conversa, "curriculo_recebido")


def _pedir_de_novo(con, saida, pessoa, conversa, vaga) -> None:
    """Fora da lista: a pergunta da vaga de novo (nunca "tente de novo")."""
    from .motor import _registrar
    if conversa["vaga_declarou"] or vaga is None:
        w = saida.texto(pessoa.para, _texto(con, "pedir_pdf" if vaga else "sem_vaga", vaga))
        _registrar(con, conversa["id"], pessoa.para, "texto", "vaga: de novo o pdf", w)
    else:
        abrir(con, saida, pessoa, conversa, vaga, None)


def _responder_texto(con, saida: Saida, ia, pessoa, conversa, texto: str) -> None:
    from .motor import _registrar, _sem_acento
    vaga = _vaga(con, conversa["vaga_id"])
    if _sem_acento(texto) in ("menu", "inicio", "voltar"):
        _sair_da_vaga(con, saida, pessoa, conversa)   # quem pede o menu recebe o menu
        return
    chave = None
    if ia is not None and texto.strip():
        try:
            chave = ia.classificar(texto, _para_ia(con))
        except Exception:   # noqa: BLE001 -- a IA nunca derruba o atendimento
            chave = None
    if chave == "outro_assunto":
        _sair_da_vaga(con, saida, pessoa, conversa)
        return
    if chave == "pessoa":
        d = quem_atende(con)
        if d:
            w = saida.texto(pessoa.para, _texto(con, "pessoa", vaga, nome=d["nome"].split()[0]))
            w = saida.contato(pessoa.para, d["nome"], d["whatsapp"])
            _registrar(con, conversa["id"], pessoa.para, "texto", "vaga: pessoa (cartao)", w)
            return
    if chave == "recebemos":
        c = _ultima_candidatura(con, pessoa)
        if c:
            data = c["recebida_em"].astimezone(_fuso()).strftime("%d/%m")
            w = saida.texto(pessoa.para, _texto(con, "recebemos", vaga, data=data))
        else:
            w = saida.texto(pessoa.para, _texto(con, "recebemos_nao", vaga))
        _registrar(con, conversa["id"], pessoa.para, "texto", "vaga: recebemos", w)
        return
    if chave == "apresentacao":
        # um lembrete so; o texto ja fica na conversa e vai junto a Fran quando o PDF chegar
        ja = con.execute("""SELECT 1 FROM atendimento.enviadas WHERE conversa_id = %s
                             AND resumo = 'vaga: apresentacao' LIMIT 1""", (conversa["id"],)).fetchone()
        if ja:
            print("vaga: %s se apresentou de novo: sem segundo lembrete" % pessoa.para, flush=True)
            return
    if chave in ("regiao", "salario", "retorno", "apresentacao", "sem_pdf"):
        w = saida.texto(pessoa.para, _texto(con, chave, vaga))
        _registrar(con, conversa["id"], pessoa.para, "texto", "vaga: %s" % chave, w)
        return
    if _ultima_candidatura(con, pessoa) and conversa["vaga_declarou"] is None:
        # quem ja mandou o curriculo e voltou com outra coisa: o "recebemos" e a saida para o menu
        c = _ultima_candidatura(con, pessoa)
        data = c["recebida_em"].astimezone(_fuso()).strftime("%d/%m")
        w = saida.botoes(pessoa.para, _texto(con, "recebemos", vaga, data=data), [Opcao(OUTRO, "Era outro assunto")])
        _registrar(con, conversa["id"], pessoa.para, "botoes", "vaga: recebemos", w)
        return
    _pedir_de_novo(con, saida, pessoa, conversa, vaga)


def _fuso():
    from .motor import FUSO
    return FUSO


def tratar(con, saida: Saida, ia, e, agora: datetime) -> bool:
    """Uma mensagem que e da vaga. True quando foi tratada aqui.

    E da vaga: o toque `vaga:*` (fora o da Fran, que e `retorno_da_fran`), a mensagem de quem chegou
    pelo anuncio de uma vaga aberta, e tudo o que chega numa conversa de vaga em curso.
    """
    from .motor import _chegou, _conversa_aberta, _nova_conversa, _registrar
    p = e.pessoa
    conversa = _conversa_de_vaga(con, p)
    vaga_do_anuncio = vaga_aberta(con, e.anuncio) if e.anuncio else None
    if conversa is None and vaga_do_anuncio is None and not (e.toque or "").startswith("vaga:"):
        return False
    if e.toque and e.toque.startswith(("vaga:certa:", "vaga:errada:", "vaga:falar:")):
        return False   # e da Fran: retorno_da_fran
    if e.tipo == "reaction":
        return conversa is not None   # o joinha na conversa da vaga nao e pedido de nada
    if conversa is None:
        conversa = _conversa_aberta(con, p) or _nova_conversa(con, p, agora)
        _chegou(con, p, conversa, agora)
        if vaga_do_anuncio is not None:
            abrir(con, saida, p, conversa, vaga_do_anuncio, agora)
            return True
        if not (e.toque or "").startswith("vaga:"):
            return False
        conversa = _marcar(con, conversa, vaga_aberta(con))   # toque de vaga numa conversa antiga
    else:
        _chegou(con, p, conversa, agora)
    vaga = _vaga(con, conversa["vaga_id"])

    if e.toque == OUTRO:
        _sair_da_vaga(con, saida, p, conversa)
    elif e.toque in (TODOS, NEM_TODOS):
        con.execute("UPDATE atendimento.conversas SET vaga_declarou = %s WHERE id = %s",
                    ("todos" if e.toque == TODOS else "nem_todos", conversa["id"]))
        if e.toque == TODOS:
            w = saida.texto(p.para, _texto(con, "pedir_pdf", vaga))
            _registrar(con, conversa["id"], p.para, "texto", "vaga: pedir pdf", w)
        else:
            w = saida.botoes(p.para, _texto(con, "nao_atende", vaga),
                             [Opcao(MANDAR, "Mandar currículo"), Opcao(ENCERRAR, "Encerrar")])
            _registrar(con, conversa["id"], p.para, "botoes", "vaga: nao atende", w)
    elif e.toque == MANDAR:
        w = saida.texto(p.para, _texto(con, "pedir_pdf", vaga))
        _registrar(con, conversa["id"], p.para, "texto", "vaga: pedir pdf", w)
    elif e.toque == ENCERRAR:
        from .motor import _ajuste
        w = saida.texto(p.para, _ajuste(con, "encerrar", "Obrigado."))
        _registrar(con, conversa["id"], p.para, "texto", "vaga: encerrar", w)
        _fechar(con, conversa, "sem_curriculo")
    elif e.toque:
        return False   # toque de outra coisa (o menu): o caminho de sempre
    elif e_pdf(e.documento):
        _receber_pdf(con, saida, e, conversa, agora)
    elif e.texto:
        _responder_texto(con, saida, ia, p, conversa, e.texto)
    else:   # foto, Word, audio, figurinha: so PDF
        w = saida.texto(p.para, _texto(con, "so_pdf", vaga))
        _registrar(con, conversa["id"], p.para, "texto", "vaga: so pdf (%s)" % (e.tipo or "?"), w)
    return True


def volta(con, saida: Saida, ia, pessoa, conversa, texto: str, agora: datetime) -> bool:
    """Conversa NOVA de quem teve conversa de vaga nos ultimos 30 dias (e nao e da casa): o texto e
    respondido como da vaga ("voces receberam meu curriculo?"). True quando foi."""
    if internos.e_interno(con, pessoa.wa_id):
        return False
    antes = con.execute("""SELECT vaga_id FROM atendimento.conversas WHERE bsuid = %s AND trabalhe AND id <> %s
                            AND iniciada_em > %s ORDER BY id DESC LIMIT 1""",
                        (pessoa.bsuid, conversa["id"], agora - VOLTA)).fetchone()
    if not antes:
        return False
    vaga = vaga_aberta(con)
    conversa = _marcar(con, conversa, vaga)
    _responder_texto(con, saida, ia, pessoa, conversa, texto)
    return True


def fim_da_conversa(con, conversa_id: int) -> str:
    """Como termina a conversa de vaga que ficou parada: com curriculo ou sem."""
    tem = con.execute("SELECT 1 FROM atendimento.candidaturas WHERE conversa_id = %s LIMIT 1",
                      (conversa_id,)).fetchone()
    return "curriculo_recebido" if tem else "sem_curriculo"


# ── a Fran: a mensagem, um curriculo por vez ────────────────────────────────

def codigo_candidato(segredo: str, candidatura_id: int) -> str:
    """O final do botao "Conversar com o candidato" do modelo: `v<id>-<assinatura>` (envio.falar)."""
    base = "v%d" % candidatura_id
    return "%s-%s" % (base, _assinatura(segredo, base))


def numero_bonito(wa_id: str | None) -> str:
    n = com_nove(wa_id or "")
    if len(n) == 13:
        return "%s %s %s-%s" % (n[2:4], n[4], n[5:9], n[9:])
    return n or "sem número"


def variaveis(con, c) -> list[str]:
    """As 8 variaveis do modelo, cada uma numa linha so (a Meta recusa quebra de linha em variavel)."""
    vaga = _vaga(con, c["vaga_id"])
    t = c["triagem"]
    linhas = []
    reqs = list(vaga["requisitos"]) if vaga else []
    if t and t.get("requisitos"):
        for req, r in zip(reqs, t["requisitos"]):
            fonte = (" (%s)" % _cortar(r["fonte"], FONTE_ATE)) if r.get("fonte") and r["situacao"] != "nao_consta" else ""
            linhas.append("%s: %s%s" % (req, SITUACAO.get(r["situacao"], "não consta no currículo"), fonte))
    else:
        motivo = (c["triagem_erro"] or "sem pré-triagem")
        linhas.append("Sem pré-triagem (%s)" % motivo)
    linhas = (linhas + ["—"] * 4)[:4]
    resumo = (t or {}).get("resumo") or "—"
    if t and t.get("legivel") is False:
        resumo = "Não consegui ler o arquivo; abra o PDF e leia você."
    if c["texto"]:
        resumo = "%s · Escreveu: %s" % (resumo, c["texto"])
    nome = _cortar((c["nome_perfil"] or "sem nome no perfil").strip(), 60)
    vs = [_uma_linha(x) for x in (
        vaga["titulo"] if vaga else "Banco de currículos (sem vaga aberta)",
        "%s (%s)" % (nome, numero_bonito(c["wa_id"])),
        DECLAROU.get(c["declarou"], DECLAROU[None]),
        *[_cortar(x, LINHA_ATE) for x in linhas], _cortar(resumo, RESUMO_ATE))]
    # o corpo do modelo, ja com as variaveis, tem teto na Meta (1024; 22/10/2026, o 2o curriculo real
    # foi recusado com 131009 "Body text length invalid"): o resumo encolhe ate caber
    base = len(corpo_do_modelo(con, vs)) - len(vs[-1])
    vs[-1] = _cortar(vs[-1], max(40, CORPO_ATE - base))
    return vs


# Os tetos da mensagem a Fran. O corpo do modelo (e a legenda do documento) vai ate 1024 caracteres;
# com o texto fixo (~170), quatro linhas de requisito e o resumo cabem com folga.
CORPO_ATE = 1000
LINHA_ATE = 150
FONTE_ATE = 70
RESUMO_ATE = 260


def _uma_linha(t: str) -> str:
    return " ".join(str(t or "").split())


def _cortar(t: str, ate: int) -> str:
    """No fim de uma palavra, com reticencias: "pos-graduacao em Protecao de Plantas (200" nao serve."""
    t = _uma_linha(t)
    if len(t) <= ate:
        return t
    corte = t[:ate - 1].rsplit(" ", 1)[0].rstrip(" ,;:(")
    return (corte or t[:ate - 1]) + "…"


def corpo_do_modelo(con, variaveis_: list[str]) -> str:
    m = con.execute("SELECT texto FROM atendimento.modelos WHERE uso = 'curriculo' AND ativo LIMIT 1").fetchone()
    t = m["texto"] if m else ""
    for i, v in enumerate(variaveis_, 1):
        t = t.replace("{{%d}}" % i, v)
    return t


def _triar(con, ia, c) -> None:
    vaga = _vaga(con, c["vaga_id"])
    erro, t = "", None
    if vaga is None:
        erro = "sem vaga aberta"
    elif not vaga["triagem_ligada"]:
        erro = "pré-triagem desligada"
    elif ia is None or not hasattr(ia, "triar"):
        erro = "a IA não respondeu"
    elif (c["pdf_bytes"] or 0) > TRIAGEM_ATE:
        erro = "arquivo grande demais para a pré-triagem"
    else:
        try:
            t = ia.triar(bytes(c["pdf"]), dict(vaga))
        except Exception:   # noqa: BLE001 -- sem triagem, o curriculo vai igual
            t = None
        if t is None:
            erro = "a IA não respondeu"
    import json
    con.execute("""UPDATE atendimento.candidaturas SET triagem = %s, triagem_em = now(), triagem_erro = %s
                    WHERE id = %s""", (json.dumps(t) if t else None, erro, c["id"]))


def mandar_a_fran(con, saida: Saida, ia, segredo: str, agora: datetime) -> int:
    """A cada minuto: triagem e mensagem, um curriculo por mensagem. Devolve quantas sairam."""
    from .campo import ultima_mensagem_de
    from .envio import modelo_do_uso
    d = quem_atende(con)
    if not d:
        return 0
    pendentes = con.execute("""SELECT id FROM atendimento.candidaturas
                                WHERE fran_em IS NULL AND apagada_em IS NULL
                                  AND (fran_tentativa_em IS NULL OR fran_tentativa_em < %s)
                                ORDER BY id LIMIT %s""", (agora - TENTAR_DE_NOVO, POR_MINUTO)).fetchall()
    mandadas = 0
    for linha in pendentes:
        c = con.execute("SELECT * FROM atendimento.candidaturas WHERE id = %s", (linha["id"],)).fetchone()
        if c["triagem_em"] is None:
            _triar(con, ia, c)
            c = con.execute("SELECT * FROM atendimento.candidaturas WHERE id = %s", (c["id"],)).fetchone()
        vs = variaveis(con, c)
        pdf = (bytes(c["pdf"]), c["pdf_nome"] or "curriculo.pdf")
        # o aviso da Meta traz o numero antigo (sem o 9); o cadastro, com o 9: vale o que houver
        ultimas = [u for u in (ultima_mensagem_de(con, wa_id_do_whatsapp(d["whatsapp"])),
                               ultima_mensagem_de(con, d["whatsapp"])) if u]
        ultima = max(ultimas) if ultimas else None
        try:
            if ultima is not None and agora - ultima < timedelta(hours=24):
                w = saida.documento(d["whatsapp"], pdf[0], pdf[1], corpo_do_modelo(con, vs),
                                    [Opcao("vaga:certa:%d" % c["id"], "Triagem certa"),
                                     Opcao("vaga:errada:%d" % c["id"], "Triagem errada"),
                                     Opcao("vaga:falar:%d" % c["id"], "Conversar")])
                tipo = "documento"
            else:
                m = modelo_do_uso(con, "curriculo")
                if not m:
                    raise RuntimeError("nenhum modelo cadastrado para o curriculo")
                w = saida.modelo(d["whatsapp"], m["nome"], m["idioma"], vs,
                                 botoes=["vaga:certa:%d" % c["id"], "vaga:errada:%d" % c["id"]],
                                 url=codigo_candidato(segredo, c["id"]), documento=pdf)
                tipo = "modelo"
        except Exception as falha:  # noqa: BLE001 -- fica na fila; tenta de novo em uma hora
            con.execute("""UPDATE atendimento.candidaturas SET fran_erro = %s, fran_tentativa_em = %s
                            WHERE id = %s""", (("%s: %s" % (type(falha).__name__, falha))[:300], agora, c["id"]))
            continue
        con.execute("""UPDATE atendimento.candidaturas SET fran_para = %s, fran_wamid = %s, fran_em = %s,
                              fran_erro = '', fran_tentativa_em = %s WHERE id = %s""",
                    (d["whatsapp"], w, agora, agora, c["id"]))
        con.execute("""INSERT INTO atendimento.enviadas (wamid, conversa_id, para, tipo, resumo)
                       VALUES (%s, %s, %s, %s, %s)""", (w, c["conversa_id"], d["whatsapp"], tipo,
                                                        "curriculo %d para a fran" % c["id"]))
        mandadas += 1
    return mandadas


# ── a Fran: o retorno sobre a triagem ───────────────────────────────────────

def _e_a_fran(con, c, pessoa) -> bool:
    return bool(c["fran_para"]) and com_nove(c["fran_para"]) == com_nove(pessoa.wa_id or "")


def retorno_da_fran(con, saida: Saida, e, agora: datetime) -> bool:
    """O toque da Fran (certa, errada, conversar) e o comentario dela depois do "errada"."""
    p = e.pessoa
    toque = e.toque or ""
    for prefixo, valor in (("vaga:certa:", "certa"), ("vaga:errada:", "errada"), ("vaga:falar:", None)):
        if toque.startswith(prefixo) and toque[len(prefixo):].isdigit():
            c = con.execute("SELECT * FROM atendimento.candidaturas WHERE id = %s",
                            (int(toque[len(prefixo):]),)).fetchone()
            if not c or not _e_a_fran(con, c, p):
                return True   # botao de curriculo que nao e dela: nada a fazer, e nao e menu
            if valor is None:
                if c["wa_id"]:
                    saida.contato(p.para, (c["nome_perfil"] or "Candidato").strip() or "Candidato",
                                  com_nove(c["wa_id"]), empresa="Candidato · Trabalhe conosco")
                return True
            con.execute("""UPDATE atendimento.candidaturas SET feedback = %s, feedback_em = %s,
                                  espera_comentario = %s WHERE id = %s""",
                        (valor, agora, valor == "errada", c["id"]))
            # o comentario em espera e so o deste curriculo: outro "errada" depois vale para o novo
            con.execute("""UPDATE atendimento.candidaturas SET espera_comentario = false
                            WHERE espera_comentario AND id <> %s AND fran_para = %s""", (c["id"], c["fran_para"]))
            w = saida.texto(p.para, "O que ela errou? Escreva em uma linha. Isso ajusta as próximas."
                            if valor == "errada" else "Anotado, obrigado.")
            con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'texto', %s)",
                        (w, p.para, "vaga: triagem %s %d" % (valor, c["id"])))
            return True
    if e.texto and not e.toque:
        c = con.execute("""SELECT * FROM atendimento.candidaturas WHERE espera_comentario AND feedback_em > %s
                            ORDER BY feedback_em DESC LIMIT 1""", (agora - COMENTARIO_ATE,)).fetchone()
        if c and _e_a_fran(con, c, p):
            con.execute("""UPDATE atendimento.candidaturas SET feedback_texto = %s, espera_comentario = false
                            WHERE id = %s""", (e.texto[:1000], c["id"]))
            w = saida.texto(p.para, "Anotado, obrigado.")
            con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'texto', %s)",
                        (w, p.para, "vaga: comentario %d" % c["id"]))
            return True
    return False


# ── os doze meses ───────────────────────────────────────────────────────────

def limpar(con, agora: datetime) -> int:
    """Vencidos os 12 meses: o PDF, o texto, a triagem, o nome e o numero saem; ficam a vaga, as
    datas, a situacao e o retorno da Fran."""
    return con.execute("""UPDATE atendimento.candidaturas
                             SET pdf = NULL, texto = '', triagem = NULL, nome_perfil = '', wa_id = NULL,
                                 bsuid = NULL, pdf_nome = '', apagada_em = %s
                           WHERE apagar_em < %s AND apagada_em IS NULL""", (agora, agora)).rowcount
