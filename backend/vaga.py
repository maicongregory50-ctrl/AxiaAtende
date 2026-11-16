"""O TRABALHE CONOSCO: a vaga aberta, o curriculo em PDF e a pre-triagem para a Fran. #1098.

Spec: docs/specs/2026-10-22-trabalhe-conosco-vaga-e-pre-triagem.md (caminho B, dono, 22/10/2026).

QUEM CHEGA: pelo anuncio da vaga (o `referral` da Meta), pelo no "Trabalhe conosco" do menu, ou de
volta em ate 30 dias depois de uma conversa de vaga ("voces receberam meu curriculo?"). A conversa
fica marcada (`conversas.trabalhe`) e termina como `curriculo_recebido` ou `sem_curriculo`, nunca
`parou_no_meio`: os leitores de decisao (marcar_paradas, retomar_paradas, a pergunta das 4h30) nao
leem esses dois valores, e e de proposito.

AS REGRAS DO DONO, e o codigo segue so elas:
- **PDF ou foto** (decisao 7 do #1098, revogada para a foto pela D5 do #1520, 13/11/2026). A foto entra
  como curriculo SEM pre-triagem e vai a Fran como imagem. Word, audio ou texto recebem "Precisamos do
  seu curriculo em PDF ou em foto".
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

OUTRO = "vaga:outro"
ESTA, OUTRAS = "vaga:esta", "vaga:outras"   # quem vem pelo menu: a vaga aberta ou outras areas (029)
ESCOLHER = "vaga:escolher:"                 # #1474: a vaga escolhida na lista, com mais de uma aberta
# A pergunta "Voce atende a esses requisitos?" saiu em 22/10/2026 (029, dono: quem analisa e a
# triagem). Os toques dela continuam aceitos: a mensagem antiga pode estar na tela de alguem.
TODOS, NEM_TODOS = "vaga:todos", "vaga:nem_todos"
MANDAR, ENCERRAR = "vaga:mandar", "vaga:encerrar"

SITUACAO = {"consta": "consta", "nao": "não", "nao_consta": "não consta no currículo"}
DECLAROU = {"todos": "atende a todos os requisitos", "nem_todos": "não atende a todos os requisitos",
            None: "não foi perguntado"}
# o que mostra que o PDF ja foi pedido nesta conversa (`enviadas.resumo`)
PEDIU_PDF = ("vaga: abertura", "vaga: pedir pdf", "vaga: banco", "vaga: sem vaga aberta", "vaga: de novo o pdf")


# ── o cadastro ──────────────────────────────────────────────────────────────

def vaga_aberta(con, anuncio: str | None = None):
    """A vaga aberta (a do anuncio, quando ele vem); None sem vaga aberta ou anuncio de outra coisa."""
    if anuncio:
        return con.execute("""SELECT * FROM atendimento.vagas WHERE aberta AND %s = ANY(anuncio_ids)
                               ORDER BY id LIMIT 1""", (anuncio,)).fetchone()
    return con.execute("SELECT * FROM atendimento.vagas WHERE aberta ORDER BY id LIMIT 1").fetchone()


def vagas_abertas(con) -> list:
    """#1474: TODAS as vagas abertas, na ordem do cadastro. Com mais de uma, quem vem pelo menu
    escolhe a dele numa lista; quem vem pelo anuncio continua caindo na vaga do anuncio."""
    return con.execute("SELECT * FROM atendimento.vagas WHERE aberta ORDER BY id").fetchall()


def _vaga_unica(con):
    """#1522: a vaga aberta quando ha UMA so; None sem vaga aberta OU com mais de uma. Com duas
    abertas ninguem e posto numa delas sem escolher: `vaga_aberta(con)` devolve a de id menor, e
    quem queria a outra recebia os requisitos (e a triagem) da vaga errada."""
    abertas = vagas_abertas(con)
    return abertas[0] if len(abertas) == 1 else None


def _falta_escolher(con, conversa) -> bool:
    """#1522: a conversa de vaga ainda sem vaga, com mais de uma aberta, e que nao foi para o banco
    ("Outras areas" tambem deixa a conversa sem vaga, e ali e de proposito)."""
    return (conversa["vaga_id"] is None and len(vagas_abertas(con)) > 1
            and not _ja_mandou(con, conversa, ("vaga: banco",)))


def _titulo_curto(vaga) -> str:
    """O titulo sem o "Vaga " da frente, no limite da linha de lista da Meta (24)."""
    t = _uma_linha(vaga["titulo"])
    if t.lower().startswith("vaga "):
        t = t[5:]
    return _cortar(t, 24)


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


def _saudacao(pessoa) -> str:
    nome = primeiro_nome(pessoa.nome) if (pessoa.nome or "").strip() else ""
    return "Olá, %s!" % nome if nome else "Olá!"


def abrir(con, saida: Saida, pessoa, conversa, vaga, agora: datetime, pelo_menu: bool = False):
    """A conversa entra na vaga: os requisitos e o pedido do PDF. Quem veio pelo MENU escolhe antes
    se e para a vaga aberta ou para outras areas. Sem vaga aberta, o pedido do PDF para as proximas."""
    from .motor import _registrar
    conversa = _marcar(con, conversa, vaga)
    if vaga is None:
        w = saida.texto(pessoa.para, _texto(con, "sem_vaga"))
        _registrar(con, conversa["id"], pessoa.para, "texto", "vaga: sem vaga aberta", w)
    elif pelo_menu and len(abertas := vagas_abertas(con)) > 1:
        # #1474 (dono, 12/11/2026): com mais de uma vaga aberta, a lista das vagas -- o candidato
        # escolhe a dele (ate 8 vagas: a lista da Meta tem 10 linhas, e duas sao "Outras areas" e
        # "Era outro assunto"). A conversa ainda nao tem vaga: ela e marcada no toque da escolha.
        conversa = _marcar(con, conversa, None)
        linhas = [Opcao("%s%d" % (ESCOLHER, v["id"]), _titulo_curto(v),
                        _cortar(v["requisitos"][0], 72) if v["requisitos"] else "") for v in abertas[:8]]
        w = saida.lista(pessoa.para, _texto(con, "pergunta_menu_varias", saudacao=_saudacao(pessoa)),
                        "Ver as vagas", linhas + [Opcao(OUTRAS, "Outras áreas"), Opcao(OUTRO, "Era outro assunto")])
        _registrar(con, conversa["id"], pessoa.para, "lista", "vaga: pergunta do menu", w)
    elif pelo_menu:
        w = saida.botoes(pessoa.para, _texto(con, "pergunta_menu", vaga, saudacao=_saudacao(pessoa)),
                         [Opcao(ESTA, _cortar(vaga["titulo"], 20)), Opcao(OUTRAS, "Outras áreas"),
                          Opcao(OUTRO, "Era outro assunto")])
        _registrar(con, conversa["id"], pessoa.para, "botoes", "vaga: pergunta do menu", w)
    else:
        w = saida.botoes(pessoa.para, _texto(con, "abertura", vaga, saudacao=_saudacao(pessoa)),
                         [Opcao(OUTRO, "Era outro assunto")])
        _registrar(con, conversa["id"], pessoa.para, "botoes", "vaga: abertura", w)
    return conversa


def do_menu(con, saida: Saida, pessoa, conversa, no, agora: datetime) -> None:
    """O no "Trabalhe conosco" (acao `vaga`), tocado no menu."""
    abrir(con, saida, pessoa, conversa, vaga_aberta(con), agora, pelo_menu=True)


def _ja_mandou(con, conversa, resumos) -> bool:
    return con.execute("SELECT 1 FROM atendimento.enviadas WHERE conversa_id = %s AND resumo = ANY(%s) LIMIT 1",
                       (conversa["id"], list(resumos))).fetchone() is not None


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


def o_que_escreveu(con, conversa) -> str:
    """So o que o candidato ESCREVEU nesta conversa, para ir a Fran (dono, 22/10/2026: o 1o curriculo
    real levou "Ola! Posso ter mais informacoes sobre isso? / Nao atendo todos / Mandar curriculo",
    que nao diz nada a ela). Fica de fora a frase pronta do anuncio (a mensagem com `referral`) e os
    titulos dos botoes; o resto, em ordem."""
    partes = []
    for ev in con.execute("""SELECT corpo FROM atendimento.eventos_meta
                              WHERE tipo = 'mensagem' AND processado_em >= %s
                                AND (bsuid = %s OR corpo->'msg'->>'from' = %s) ORDER BY id""",
                          (conversa["iniciada_em"], conversa["bsuid"], conversa["wa_id"] or "")).fetchall():
        msg = (ev["corpo"] or {}).get("msg") or {}
        if msg.get("type") == "text" and not msg.get("referral"):
            partes.append(((msg.get("text") or {}).get("body") or "").strip())
    return " / ".join(p for p in partes if p)[:1000]


def e_imagem(e) -> bool:
    """#1520 (D5): a foto que a pessoa mandou (o curriculo fotografado)."""
    return e.midia is not None and e.midia.tipo == "foto"


SEM_TRIAGEM_FOTO = "foto: sem triagem"
EXTENSAO = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def baixar_arquivo(saida: Saida, e) -> tuple[bytes, str, str]:
    """(dados, nome, mime) do PDF ou da foto da mensagem atual, baixados da Meta. Nada fica no disco."""
    if e_imagem(e):
        mime = (e.midia.mime or "image/jpeg").split(";")[0].strip().lower()
        nome = "curriculo-foto" + EXTENSAO.get(mime, ".jpg")
        media_id = e.midia.id
    else:
        mime, nome, media_id = "application/pdf", (e.documento.nome_arquivo or "curriculo.pdf"), e.documento.id
    with tempfile.TemporaryDirectory() as pasta:
        dados = Path(saida.baixar(media_id, Path(pasta) / ("arquivo" + Path(nome).suffix))).read_bytes()
    return dados, nome[:200], mime


def receber_arquivo(con, saida: Saida, e, conversa, agora: datetime, tipo: str = "pdf",
                    responder: bool = True, baixado: tuple | None = None) -> int | None:
    """O curriculo da mensagem atual vira candidatura. `tipo` 'pdf' ou 'imagem' (#1520, D5: a foto
    entra como curriculo, nas mesmas colunas, SEM pre-triagem -- vai a Fran como imagem). `responder`:
    False quando quem fala com a pessoa e a OlivIA. `baixado`: (dados, nome, mime) ja baixados.
    Devolve o id da candidatura, ou None quando a Meta reenviou o aviso (ja estava guardada)."""
    from .motor import _registrar
    p = e.pessoa
    if con.execute("SELECT 1 FROM atendimento.candidaturas WHERE wamid = %s", (e.wamid,)).fetchone():
        return None   # a Meta reenviou o aviso: o curriculo ja esta guardado
    dados, nome, _ = baixado or baixar_arquivo(saida, e)
    texto = o_que_escreveu(con, conversa)
    legenda = ((e.midia.legenda if e_imagem(e) else e.documento.legenda if e.documento else "") or "").strip()
    if legenda and legenda not in texto:
        texto = " / ".join(x for x in (texto, legenda) if x)[:1000]
    foto = tipo == "imagem"
    c = con.execute("""INSERT INTO atendimento.candidaturas
                      (vaga_id, conversa_id, bsuid, wa_id, nome_perfil, declarou, texto, wamid,
                       pdf, pdf_nome, pdf_sha256, pdf_bytes, recebida_em, apagar_em, tipo_arquivo,
                       triagem_em, triagem_erro)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (conversa["vaga_id"], conversa["id"], p.bsuid, p.wa_id, p.nome or "", conversa["vaga_declarou"],
                     texto, e.wamid, dados, nome, hashlib.sha256(dados).hexdigest(), len(dados), agora,
                     agora + DOZE_MESES, tipo, agora if foto else None,
                     SEM_TRIAGEM_FOTO if foto else "")).fetchone()
    if responder:
        w = saida.texto(p.para, _texto(con, "recebido"))
        _registrar(con, conversa["id"], p.para, "texto", "vaga: curriculo recebido", w)
    _fechar(con, conversa, "curriculo_recebido")
    return c["id"]


# ── a ficha de contato (#1525): a candidatura sem arquivo ────────────────────

SEM_TRIAGEM_FICHA = "ficha: sem triagem"
CAMPOS_FICHA = (("nome", "Nome"), ("cidade", "Cidade onde mora"), ("experiencia", "Já trabalhou com"),
                ("quando_comeca", "Pode começar"), ("como_chega", "Como chega a Cunha Porã"))
FALTOU = {"nome": "o nome", "cidade": "a cidade", "experiencia": "no que já trabalhou",
          "quando_comeca": "quando pode começar", "como_chega": "como chega a Cunha Porã"}


def receber_ficha(con, conversa, ficha: dict, agora: datetime, parcial: bool = False) -> int:
    """A ficha de contato vira candidatura (D5): `tipo_arquivo = 'ficha'`, os campos em `ficha` (com a
    lingua, e `faltou` quando PARCIAL), sem arquivo e sem pre-triagem. Uma por conversa: havendo
    candidatura (ficha ou curriculo) nesta conversa, devolve a dela. Fecha a conversa como
    `curriculo_recebido`; doze meses, como o curriculo. Quem chama e a OlivIA (`anotar_ficha`) ou a parcial."""
    import json
    ja = con.execute("SELECT id FROM atendimento.candidaturas WHERE conversa_id = %s ORDER BY id LIMIT 1",
                     (conversa["id"],)).fetchone()
    if ja:
        return ja["id"]
    dados = {k: " ".join(str((ficha or {}).get(k) or "").split())[:200] for k, _ in CAMPOS_FICHA}
    dados["lingua"] = "es" if ((ficha or {}).get("lingua") or conversa.get("lingua")) == "es" else "pt"
    if parcial:
        dados["faltou"] = [k for k, _ in CAMPOS_FICHA if not dados[k]]
    c = con.execute("""INSERT INTO atendimento.candidaturas
                      (vaga_id, conversa_id, bsuid, wa_id, nome_perfil, texto, pdf_nome, recebida_em, apagar_em,
                       tipo_arquivo, triagem_em, triagem_erro, ficha)
                   VALUES (%s, %s, %s, %s, %s, %s, '', %s, %s, 'ficha', %s, %s, %s::jsonb) RETURNING id""",
                    (conversa["vaga_id"], conversa["id"], conversa["bsuid"], conversa["wa_id"],
                     conversa["nome_perfil"] or "", o_que_escreveu(con, conversa), agora, agora + DOZE_MESES,
                     agora, SEM_TRIAGEM_FICHA, json.dumps(dados))).fetchone()
    _fechar(con, conversa, "curriculo_recebido")
    print("vaga: ficha%s da conversa %d virou a candidatura %d"
          % (" PARCIAL" if parcial else "", conversa["id"], c["id"]), flush=True)
    return c["id"]


def _nome_da_ficha(c) -> str:
    return ((c["ficha"] or {}).get("nome") or c["nome_perfil"] or "sem nome").strip()


def _linhas_da_ficha(con, c) -> list[str]:
    """O que a Fran le, na pagina e na legenda: a vaga, as respostas como a pessoa deu, e as marcas."""
    vaga = _vaga(con, c["vaga_id"])
    f = c["ficha"] or {}
    linhas = ["Vaga: %s" % (vaga["titulo"] if vaga else "Banco de currículos"),
              "Número: %s" % numero_bonito(c["wa_id"])]
    for k, rotulo in CAMPOS_FICHA:
        linhas.append("%s: %s" % (rotulo, (f.get(k) or "").strip() or "—"))
    if f.get("faltou"):
        nomes = [FALTOU[k] for k, _ in CAMPOS_FICHA if k in f["faltou"]]
        e = " e ".join([", ".join(nomes[:-1]), nomes[-1]]) if len(nomes) > 1 else (nomes[0] if nomes else "")
        linhas.append("Incompleta: faltou %s (a pessoa parou de responder)" % e)
    if f.get("lingua") == "es":
        linhas.append("Respondeu em espanhol")
    if c["quer_visita"]:
        linhas.append("Quer visitar a empresa")
    return linhas


def legenda_da_ficha(con, c) -> str:
    return _cortar(" · ".join(["Ficha de contato (sem currículo, sem pré-triagem)"] + _linhas_da_ficha(con, c)), CORPO_ATE)


def _pdf_texto(t: str) -> bytes:
    b = t.encode("cp1252", errors="replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def pdf_da_ficha(con, c) -> bytes:
    """A ficha numa pagina A4 (molde de `pdf_da_foto`, sem biblioteca nova): Helvetica com WinAnsiEncoding,
    entao o acento sai certo; o que nao cabe em cp1252 (emoji) vira "?"."""
    import textwrap
    linhas = [(16, "Ficha de contato"), (10, "Trabalhe conosco · Sementes Renascer · recebida em %s"
                                          % c["recebida_em"].astimezone(_fuso()).strftime("%d/%m/%Y %H:%M")), (11, "")]
    for linha in _linhas_da_ficha(con, c):
        for i, parte in enumerate(textwrap.wrap(linha, 88) or [""]):
            linhas.append((11, ("    " if i else "") + parte))
    corpo = b"BT 50 790 Td"
    for tamanho, t in linhas:
        corpo += b" /F1 %d Tf 0 -%d Td (%s) Tj" % (tamanho, tamanho + 8, _pdf_texto(t))
    corpo += b" ET"
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(corpo) + corpo + b"\nendstream",
    ]
    pdf = b"%PDF-1.4\n"
    posicoes = []
    for n, o in enumerate(objetos, 1):
        posicoes.append(len(pdf))
        pdf += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % x for x in posicoes)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref)
    return pdf


def avisar_visita(con, c) -> None:
    """D7: a pessoa aceitou a visita DEPOIS de a candidatura ter ido a Fran: uma linha a ela, pelo caminho
    dos avisos (o porteiro manda como texto na janela, ou pela reabertura)."""
    d = quem_atende(con)
    if not d:
        return
    vaga = _vaga(con, c["vaga_id"])
    sobre = "%s (%s), da %s" % (_nome_da_ficha(c) if c["tipo_arquivo"] == "ficha" else
                               (c["nome_perfil"] or "sem nome").strip(),
                               numero_bonito(c["wa_id"]), vaga["titulo"] if vaga else "banco de currículos")
    con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                   VALUES ('vaga_visita', %s, %s, %s)""", (d["nome"], d["whatsapp"], sobre.replace("|", "/")))


def _pedir_de_novo(con, saida, pessoa, conversa, vaga) -> None:
    """Fora da lista: o pedido do PDF de novo, curto (nunca "tente de novo" nem os requisitos outra
    vez); a pergunta do menu ainda sem resposta volta inteira."""
    from .motor import _registrar
    if _ja_mandou(con, conversa, PEDIU_PDF):
        w = saida.texto(pessoa.para, _texto(con, "so_pdf", vaga))
        _registrar(con, conversa["id"], pessoa.para, "texto", "vaga: de novo o pdf", w)
    else:
        abrir(con, saida, pessoa, conversa, vaga, None,
              pelo_menu=_ja_mandou(con, conversa, ("vaga: pergunta do menu",)))


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
    # #1522: sem vaga escolhida e com mais de uma aberta, nada do que depende da vaga (a regiao, o
    # salario, o pedido do PDF) e respondido -- sairia em branco, ou com a vaga de outro. A lista das
    # vagas volta, e a resposta vem depois da escolha.
    sem_escolha = _falta_escolher(con, conversa)
    if chave == "apresentacao" and not sem_escolha:
        # um lembrete so; o texto ja fica na conversa e vai junto a Fran quando o PDF chegar
        ja = con.execute("""SELECT 1 FROM atendimento.enviadas WHERE conversa_id = %s
                             AND resumo = 'vaga: apresentacao' LIMIT 1""", (conversa["id"],)).fetchone()
        if ja:
            print("vaga: %s se apresentou de novo: sem segundo lembrete" % pessoa.para, flush=True)
            return
    if chave in ("regiao", "salario", "retorno", "apresentacao", "sem_pdf") and not sem_escolha:
        w = saida.texto(pessoa.para, _texto(con, chave, vaga))
        _registrar(con, conversa["id"], pessoa.para, "texto", "vaga: %s" % chave, w)
        return
    if _ultima_candidatura(con, pessoa) and not _ja_mandou(con, conversa, PEDIU_PDF + ("vaga: pergunta do menu",)):
        # quem ja mandou o curriculo e voltou com outra coisa: o "recebemos" e a saida para o menu
        c = _ultima_candidatura(con, pessoa)
        data = c["recebida_em"].astimezone(_fuso()).strftime("%d/%m")
        w = saida.botoes(pessoa.para, _texto(con, "recebemos", vaga, data=data), [Opcao(OUTRO, "Era outro assunto")])
        _registrar(con, conversa["id"], pessoa.para, "botoes", "vaga: recebemos", w)
        return
    if sem_escolha:
        abrir(con, saida, pessoa, conversa, vaga_aberta(con), None, pelo_menu=True)   # a lista das vagas
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
        # toque de vaga numa conversa antiga. #1522: com mais de uma aberta a conversa fica SEM vaga
        # ate a escolha (o toque `vaga:escolher:N` diz qual, logo abaixo)
        conversa = _marcar(con, conversa, _vaga_unica(con))
    else:
        _chegou(con, p, conversa, agora)
    vaga = _vaga(con, conversa["vaga_id"])

    if e.toque == OUTRO:
        _sair_da_vaga(con, saida, p, conversa)
    elif e.toque == ESTA:
        # #1522: o botao "esta vaga" sem vaga na conversa e com mais de uma aberta nao diz QUAL:
        # a lista das vagas, em vez da primeira do cadastro
        if vaga is None and len(vagas_abertas(con)) > 1:
            abrir(con, saida, p, conversa, vaga_aberta(con), agora, pelo_menu=True)
        else:
            abrir(con, saida, p, conversa, vaga or vaga_aberta(con), agora)
    elif e.toque.startswith(ESCOLHER) if e.toque else False:
        # #1474: a vaga escolhida na lista; fechada nesse meio-tempo, a lista volta
        escolhida = _vaga(con, int(e.toque[len(ESCOLHER):]) if e.toque[len(ESCOLHER):].isdigit() else None)
        if escolhida and escolhida["aberta"]:
            abrir(con, saida, p, conversa, escolhida, agora)
        else:
            abrir(con, saida, p, conversa, vaga_aberta(con), agora, pelo_menu=True)
    elif e.toque == OUTRAS:
        # outras areas: banco de curriculos, sem vaga e por isso sem triagem contra requisitos que nao
        # sao os dele
        conversa = con.execute("UPDATE atendimento.conversas SET vaga_id = NULL WHERE id = %s RETURNING *",
                               (conversa["id"],)).fetchone()
        w = saida.texto(p.para, _texto(con, "pedir_pdf_banco"))
        _registrar(con, conversa["id"], p.para, "texto", "vaga: banco", w)
    elif e.toque in (TODOS, NEM_TODOS, MANDAR):
        # os botoes da pergunta que saiu (029): quem ainda os tem na tela recebe o pedido do PDF
        if e.toque != MANDAR:
            con.execute("UPDATE atendimento.conversas SET vaga_declarou = %s WHERE id = %s",
                        ("todos" if e.toque == TODOS else "nem_todos", conversa["id"]))
        w = saida.texto(p.para, _texto(con, "pedir_pdf_assim" if e.toque != TODOS else "pedir_pdf", vaga))
        _registrar(con, conversa["id"], p.para, "texto", "vaga: pedir pdf", w)
    elif e.toque == ENCERRAR:
        from .motor import _ajuste
        w = saida.texto(p.para, _ajuste(con, "encerrar", "Obrigado."))
        _registrar(con, conversa["id"], p.para, "texto", "vaga: encerrar", w)
        _fechar(con, conversa, "sem_curriculo")
    elif e.toque:
        return False   # toque de outra coisa (o menu): o caminho de sempre
    elif e_pdf(e.documento):
        receber_arquivo(con, saida, e, conversa, agora, "pdf")
    elif e_imagem(e):
        # #1520 (D5, dono 13/11/2026): a foto do curriculo entra, sem pre-triagem. Revoga a decisao 7 do
        # #1098 para a foto. Vale com a voz da OlivIA desligada tambem.
        receber_arquivo(con, saida, e, conversa, agora, "imagem")
    elif e.texto:
        _responder_texto(con, saida, ia, p, conversa, e.texto)
    else:   # Word, audio, figurinha, video: PDF ou foto
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
    # #1522: quem volta NAO cai na primeira vaga aberta do cadastro. A vaga e a que ele mesmo tinha
    # na conversa anterior, se continua aberta; senao a unica aberta; e com mais de uma aberta a
    # conversa fica sem vaga, e `_responder_texto` devolve a lista para ele escolher.
    anterior = _vaga(con, antes["vaga_id"])
    vaga = anterior if anterior and anterior["aberta"] else _vaga_unica(con)
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
    if c.get("tipo_arquivo") == "ficha":   # #1525: o nome que a pessoa deu na ficha
        nome = _cortar("Ficha: " + _nome_da_ficha(c), 60)
    vs = [_uma_linha(x) for x in (
        vaga["titulo"] if vaga else "Banco de currículos",
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


def corpo_do_modelo(con, variaveis_: list[str], sem_botoes: bool = False) -> str:
    """O corpo do modelo com as variaveis. `sem_botoes`: sem a linha "Disse nos botoes" (a pergunta
    saiu na 029); so na mensagem comum, porque o texto do modelo aprovado na Meta nao muda."""
    m = con.execute("SELECT texto FROM atendimento.modelos WHERE uso = 'curriculo' AND ativo LIMIT 1").fetchone()
    t = m["texto"] if m else ""
    if sem_botoes:
        t = "\n".join(linha for linha in t.split("\n") if "{{3}}" not in linha)
    for i, v in enumerate(variaveis_, 1):
        t = t.replace("{{%d}}" % i, v)
    return t


def _triar(con, ia, c) -> None:
    vaga = _vaga(con, c["vaga_id"])
    erro, t = "", None
    if vaga is None:
        erro = "banco de currículos, sem vaga"
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
        ficha = c["tipo_arquivo"] == "ficha"
        if ficha:
            # #1525: a ficha vai como a foto -- uma pagina em PDF, sem os botoes da triagem (nao houve)
            pagina = pdf_da_ficha(con, c)
            pdf = (pagina, "ficha-de-contato.pdf")
        else:
            pdf = (bytes(c["pdf"]), c["pdf_nome"] or "curriculo.pdf")
        foto = c["tipo_arquivo"] == "imagem"
        pdf_modelo = None
        if foto:
            # #1520: fora da janela, o modelo da Fran so leva PDF no cabecalho; a foto (JPEG) vai embrulhada
            # num PDF de uma pagina, sem conversao nem biblioteca nova. Outro formato espera a janela.
            embrulho = pdf_da_foto(pdf[0])
            pdf_modelo = (embrulho, "curriculo-foto.pdf") if embrulho else None
        # o aviso da Meta traz o numero antigo (sem o 9); o cadastro, com o 9: vale o que houver
        ultimas = [u for u in (ultima_mensagem_de(con, wa_id_do_whatsapp(d["whatsapp"])),
                               ultima_mensagem_de(con, d["whatsapp"])) if u]
        ultima = max(ultimas) if ultimas else None
        try:
            if ficha and ultima is not None and agora - ultima < timedelta(hours=24):
                w = saida.documento(d["whatsapp"], pdf[0], pdf[1], legenda_da_ficha(con, c),
                                    [Opcao("vaga:falar:%d" % c["id"], "Conversar")])
                tipo = "documento"
            elif ficha:
                m = modelo_do_uso(con, "curriculo")
                if not m:
                    raise RuntimeError("nenhum modelo cadastrado para o curriculo")
                w = saida.modelo(d["whatsapp"], m["nome"], m["idioma"], vs,
                                 botoes=["vaga:certa:%d" % c["id"], "vaga:errada:%d" % c["id"]],
                                 url=codigo_candidato(segredo, c["id"]), documento=pdf)
                tipo = "modelo"
            elif foto and ultima is not None and agora - ultima < timedelta(hours=24):
                # dentro da janela: a foto como imagem, sem os botoes da triagem (nao houve triagem)
                w = saida.imagem(d["whatsapp"], pdf[0], legenda_da_foto(con, c),
                                 opcoes=[Opcao("vaga:falar:%d" % c["id"], "Conversar")])
                tipo = "imagem"
            elif foto and pdf_modelo is None:
                raise RuntimeError("foto que nao e JPEG: espera a janela de 24 h de quem recebe")
            elif ultima is not None and agora - ultima < timedelta(hours=24):
                w = saida.documento(d["whatsapp"], pdf[0], pdf[1],
                                    corpo_do_modelo(con, vs, sem_botoes=c["declarou"] is None),
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
                                 url=codigo_candidato(segredo, c["id"]), documento=pdf_modelo if foto else pdf)
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
                                                        # #1525: a medicao le a ficha (e a incompleta) por aqui
                                                        ("ficha%s %d para a fran" % (
                                                            " incompleta" if (c["ficha"] or {}).get("faltou") else "",
                                                            c["id"])) if ficha else
                                                        "curriculo %d para a fran" % c["id"]))
        mandadas += 1
    return mandadas


def legenda_da_foto(con, c) -> str:
    """#1520: a legenda da foto do curriculo a Fran -- a vaga, quem mandou e o que escreveu. Sem triagem."""
    vaga = _vaga(con, c["vaga_id"])
    partes = ["Currículo em foto (sem pré-triagem)",
              "Vaga: %s" % (vaga["titulo"] if vaga else "Banco de currículos"),
              "Candidato: %s (%s)" % (_cortar((c["nome_perfil"] or "sem nome no perfil").strip(), 60),
                                      numero_bonito(c["wa_id"]))]
    if c["texto"]:
        partes.append("Escreveu: %s" % c["texto"])
    return _cortar(" · ".join(partes), CORPO_ATE)


SOF = (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)


def _tamanho_jpeg(dados: bytes) -> tuple[int, int] | None:
    """(largura, altura) do JPEG, pelo marcador SOF; None quando nao e JPEG."""
    if dados[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(dados):
        if dados[i] != 0xFF:
            return None
        marca = dados[i + 1]
        if marca in (0xD8, 0x01, 0xFF) or 0xD0 <= marca <= 0xD7:
            i += 1 if marca == 0xFF else 2
            continue
        if marca in SOF:
            altura = int.from_bytes(dados[i + 5:i + 7], "big")
            largura = int.from_bytes(dados[i + 7:i + 9], "big")
            return (largura, altura) if largura and altura else None
        i += 2 + int.from_bytes(dados[i + 2:i + 4], "big")
    return None


def pdf_da_foto(dados: bytes) -> bytes | None:
    """O JPEG dentro de um PDF de uma pagina do tamanho da foto (o JPEG vai como esta, DCTDecode).
    None quando a foto nao e JPEG. E so embrulho: nada da imagem e lido alem do tamanho."""
    t = _tamanho_jpeg(dados or b"")
    if not t:
        return None
    w, h = t
    conteudo = b"q %d 0 0 %d 0 0 cm /F Do Q" % (w, h)
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << /XObject << /F 4 0 R >> >> "
         b"/Contents 5 0 R >>") % (w, h),
        (b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 "
         b"/Filter /DCTDecode /Length %d >>\nstream\n") % (w, h, len(dados)) + dados + b"\nendstream",
        b"<< /Length %d >>\nstream\n" % len(conteudo) + conteudo + b"\nendstream",
    ]
    pdf = b"%PDF-1.4\n"
    posicoes = []
    for n, o in enumerate(objetos, 1):
        posicoes.append(len(pdf))
        pdf += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % x for x in posicoes)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref)
    return pdf


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
    datas, a situacao e o retorno da Fran. #1525: a ficha tambem, e o rascunho dela na conversa; o
    rascunho que nunca virou candidatura sai com 12 meses da conversa."""
    con.execute("""UPDATE atendimento.conversas SET ficha = NULL
                    WHERE ficha IS NOT NULL
                      AND (iniciada_em < %s OR id IN (SELECT conversa_id FROM atendimento.candidaturas
                                                       WHERE apagar_em < %s AND apagada_em IS NULL))""",
                (agora - DOZE_MESES, agora))
    return con.execute("""UPDATE atendimento.candidaturas
                             SET pdf = NULL, texto = '', triagem = NULL, nome_perfil = '', wa_id = NULL,
                                 bsuid = NULL, pdf_nome = '', ficha = NULL, apagada_em = %s
                           WHERE apagar_em < %s AND apagada_em IS NULL""", (agora, agora)).rowcount
