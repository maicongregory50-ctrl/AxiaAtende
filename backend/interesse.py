"""#1754: o cliente da carteira que quer saber mais do boletim -- a conversa, o interesse e a FICHA.

Spec: docs/specs/2026-11-24-olivia-atende-a-carteira-no-boletim.md (D1 a D12). Manual: docs/manuais/olivia.md.

QUEM ENTRA (D1): quem tocou "Quero saber mais" num boletim (modelo de botao `saber_e_parar`), ou quem recebeu
um boletim assim nos ultimos 7 DIAS e escreve. Fora disso, o portao do cliente de hoje (#1189).

A CHAVE (D11): `olivia.atende_carteira`, em `atendimento.ajustes`, nasce desligada (077) e so o dono liga
(`scripts/olivia.py ligar-carteira`). E so vale com o texto da parceria APROVADO pelo dono
(`docs/olivia/parceria-da-carteira.md`): sem ele, `atende` responde False, como a chave desligada.

A CONVERSA DA CARTEIRA e a que tem uma linha em `atendimento.interesses`. Ela nasce com o no atual na
`raiz_carteira`, para o "Ver todas as opcoes" de um botao cair no menu do cliente, nunca no geral.

O PRIMEIRO BLOCO E DO CODIGO (D3): a saudacao pelo primeiro nome, as imagens da versao maior e o texto da
parceria, literal. Nenhuma fala de IA nele.

A FICHA E DO CODIGO (D7): uma por conversa, ao WhatsApp do RESPONSAVEL DA LINHA DO ENVIO -- texto dentro da
janela de 24 h dele, o modelo `olivia_resumo` fora dela. `mandar` NUNCA levanta: a falha vai para
`interesses.erro` e devolve False, e e por esse False que a OlivIA nao diz que avisou quem cuida do cliente.
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

from . import motor
from .envio import Envio, com_nove, janela_aberta, modelo_do_uso, nome_de_quem_atende, primeiro_nome

AJUSTE = "olivia.atende_carteira"
PARCERIA = Path(__file__).resolve().parent.parent / "docs" / "olivia" / "parceria-da-carteira.md"
DIAS = timedelta(days=7)
BOTAO = "saber_e_parar"
USO_DO_MODELO = "aviso_olivia_resumo"
RESUMO_SAUDACAO = "carteira: saudacao"
RESUMO_PARCERIA = "carteira: parceria"
RESUMO_REPRESENTANTE = "carteira: representante"
RESUMO_FICHA = "carteira: ficha"
TEXTO_ATE = 600
LINHA_ATE = 900   # o corpo do modelo e "Resumo da OlivIA: {{1}} O detalhe ...": a Meta aceita ate 1024
PAPEL_DITO = {"comprador": "comprador", "tecnico": "técnico"}
_SITUACAO = re.compile(r"^\*\*Situa[cç][aã]o:\*\*\s*(\S+)", re.MULTILINE)
_TEXTO = re.compile(r"<!-- texto -->\s*(.*?)\s*<!-- /texto -->", re.DOTALL)


# ── a chave e o texto do dono ───────────────────────────────────────────────

def parceria(caminho: Path | None = None) -> tuple[bool, str]:
    """(aprovado, texto). O texto e o que esta entre as marcas, literal; aprovado so com a situacao
    APROVADO (a palavra RASCUNHO, ou o arquivo ausente, e nao). Relido a cada vez: o dono corrige sem restart."""
    try:
        bruto = (caminho or PARCERIA).read_text(encoding="utf-8")
    except OSError:
        return False, ""
    m, t = _SITUACAO.search(bruto), _TEXTO.search(bruto)
    texto = t.group(1).strip() if t else ""
    return bool(m and m.group(1).strip(" .—-").upper() == "APROVADO" and texto), texto


def ligado(con) -> bool:
    return motor._ajuste(con, AJUSTE, False) is True


def atende(con, caminho: Path | None = None) -> bool:
    """A chave ligada E o texto da parceria aprovado."""
    return ligado(con) and parceria(caminho)[0]


# ── quem e ──────────────────────────────────────────────────────────────────

def _destinatario(con, dest_id):
    return con.execute("""SELECT d.*, e.imagens AS imagens_envio, e.peca, e.culturas, e.modelo
                            FROM atendimento.envio_destinatarios d JOIN atendimento.envios e ON e.id = d.envio_id
                           WHERE d.id = %s""", (dest_id,)).fetchone()


def do_boletim(con, wa_id: str, agora: datetime):
    """D1b: o destinatario do boletim com "Quero saber mais" mais recente a este numero, com o convite nos
    ultimos 7 dias e sem recusa. None: nao recebeu, passou dos 7 dias, ou pediu para parar."""
    r = con.execute("""SELECT d.id FROM atendimento.envio_destinatarios d
                         JOIN atendimento.envios e ON e.id = d.envio_id
                         JOIN atendimento.modelos m ON m.nome = e.modelo
                        WHERE d.whatsapp = %s AND d.convite_em > %s AND m.botao = %s
                          AND d.resposta IS DISTINCT FROM 'nao_quero'
                        ORDER BY d.convite_em DESC LIMIT 1""",
                    (com_nove(wa_id), agora - DIAS, BOTAO)).fetchone()
    return _destinatario(con, r["id"]) if r else None


def da_conversa(con, conversa_id):
    """A linha de interesse da conversa: so a conversa da carteira tem."""
    return con.execute("SELECT * FROM atendimento.interesses WHERE conversa_id = %s", (conversa_id,)).fetchone()


def e_da_carteira(con, conversa) -> bool:
    return bool(conversa) and da_conversa(con, conversa["id"]) is not None


# ── a conversa e a resposta ─────────────────────────────────────────────────

def abrir(con, pessoa, d, entrada: str, agora: datetime):
    """(conversa, interesse) da carteira para o destinatario `d`. A conversa dele ainda aberta, ou parada ha
    menos de 7 dias, volta (`em_curso`); senao nasce uma, conduzida pela OlivIA, no no da `raiz_carteira`."""
    velha = con.execute("""SELECT c.* FROM atendimento.interesses i
                             JOIN atendimento.conversas c ON c.id = i.conversa_id
                            WHERE i.destinatario_id = %s AND c.bsuid = %s
                              AND c.situacao IN ('em_curso', 'parou_no_meio') AND c.ultimo_toque_em > %s
                            ORDER BY c.id DESC LIMIT 1""", (d["id"], pessoa.bsuid, agora - DIAS)).fetchone()
    aberta = motor._conversa_aberta(con, pessoa)
    if velha is not None and (aberta is None or aberta["id"] == velha["id"]):
        conversa = con.execute("UPDATE atendimento.conversas SET situacao = 'em_curso' WHERE id = %s RETURNING *",
                               (velha["id"],)).fetchone()
    else:
        conversa = motor._nova_conversa(con, pessoa, agora)
        raiz = motor._no(con, motor.RAIZ_CARTEIRA)
        conversa = con.execute("""UPDATE atendimento.conversas SET conduzida_por = 'olivia', no_atual_id = %s
                                   WHERE id = %s RETURNING *""",
                               (raiz["id"] if raiz else None, conversa["id"])).fetchone()
        con.execute("""INSERT INTO atendimento.interesses (destinatario_id, conversa_id, entrada, papel, criado_em)
                       VALUES (%s, %s, %s, %s, %s)""", (d["id"], conversa["id"], entrada, d["papel"], agora))
    motor._chegou(con, pessoa, conversa, agora)
    return conversa, da_conversa(con, conversa["id"])


def marcar_saber(con, d, agora: datetime, texto: str | None = None) -> None:
    """A resposta `saber` na linha do envio (D1, D9). Nao passa por cima de recusa nem de aceite; o texto de
    quem entrou escrevendo fica em `resposta_texto`, como o `tratar_texto_de_convidado` de hoje."""
    con.execute("""UPDATE atendimento.envio_destinatarios
                      SET resposta = 'saber', resposta_em = CASE WHEN resposta = 'saber' THEN resposta_em ELSE %s END,
                          resposta_texto = coalesce(nullif(resposta_texto, ''), %s, resposta_texto)
                    WHERE id = %s AND (resposta IS NULL OR resposta IN ('texto', 'falar', 'saber'))""",
                (agora, (texto or "")[:500] or None, d["id"]))


# ── o primeiro bloco (D3) e a versao maior ──────────────────────────────────

def imagens_do(d) -> list:
    return list(d["imagens"] if d["imagens"] is not None else (d["imagens_envio"] or []))


def faltam_imagens(con, d) -> bool:
    atual = _destinatario(con, d["id"])
    return atual["imagens_enviadas"] < len(imagens_do(atual))


def mandar_material(con, saida, d, conversa_id, agora: datetime) -> int:
    """As imagens da versao maior que ainda nao sairam, na ordem; a primeira com o nome da peca. Quem chama
    sabe que a janela esta aberta (a pessoa acabou de tocar ou escrever). Devolve quantas sairam agora."""
    atual = _destinatario(con, d["id"])
    imagens = imagens_do(atual)
    con.execute("UPDATE atendimento.envio_destinatarios SET imagens_total = %s WHERE id = %s", (len(imagens), d["id"]))
    feitas = 0
    for i in range(atual["imagens_enviadas"], len(imagens)):
        try:
            w = saida.imagem(atual["whatsapp"], imagens[i], atual["peca"] if i == 0 else "")
        except Exception as falha:   # noqa: BLE001 -- a imagem que falhou fica para a OlivIA oferecer de novo
            con.execute("UPDATE atendimento.envio_destinatarios SET erro = %s WHERE id = %s", (str(falha)[:300], d["id"]))
            break
        motor._registrar(con, conversa_id, atual["whatsapp"], "imagem", "imagem %d de %s" % (i + 1, atual["peca"]), w)
        con.execute("UPDATE atendimento.envio_destinatarios SET imagens_enviadas = %s WHERE id = %s", (i + 1, d["id"]))
        feitas += 1
    return feitas


def saudacao(d, com_material: bool) -> str:
    nome = primeiro_nome(d["nome"])
    if com_material:
        return "Olá, %s! Aqui está o material completo do boletim." % nome
    return "Olá, %s! Que bom que você quer saber mais." % nome


def primeiro_bloco(con, saida, pessoa, d, conversa, agora: datetime, caminho: Path | None = None) -> None:
    """D3: a saudacao, as imagens e o texto da parceria. Do codigo, sem IA."""
    para = pessoa.para
    tem = bool(imagens_do(d))
    w = saida.texto(para, saudacao(d, tem))
    motor._registrar(con, conversa["id"], para, "texto", RESUMO_SAUDACAO, w)
    if tem:
        mandar_material(con, saida, d, conversa["id"], agora)
    texto = parceria(caminho)[1]
    if texto:
        w = saida.texto(para, texto)
        motor._registrar(con, conversa["id"], para, "texto", RESUMO_PARCERIA, w)


def passar_representante(con, saida, pessoa, d, conversa) -> bool:
    """A linha de quem cuida do cliente, com o endereco dele (a mesma do portao e do toque "falar")."""
    linha = Envio.linha_do_representante(d)
    if not linha:
        return False
    w = saida.texto(pessoa.para, linha)
    motor._registrar(con, conversa["id"], pessoa.para, "texto", RESUMO_REPRESENTANTE, w)
    return bool(w)


# ── o interesse e a ficha (D5, D7) ──────────────────────────────────────────

def anotar(con, interesse, culturas: list[str], validas: list[str], agora: datetime):
    """Soma as culturas (so as da lista fechada do envio) as que ja estavam. Devolve a linha nova."""
    por_nome = {v.lower(): v for v in validas}
    novas = [por_nome[c.strip().lower()] for c in culturas or [] if c and c.strip().lower() in por_nome]
    juntas = list(interesse["culturas"] or [])
    for c in novas:
        if c not in juntas:
            juntas.append(c)
    return con.execute("""UPDATE atendimento.interesses SET culturas = %s, anotado_em = %s
                           WHERE id = %s RETURNING *""", (juntas, agora, interesse["id"])).fetchone()


def o_que_escreveu(con, conversa, atual: str = "") -> str:
    """O que o cliente escreveu nesta conversa, literal, numa linha (os textos e os toques, como a retomada le).
    `atual`: a mensagem desta vez, que ainda nao conta como processada e por isso nao esta no que se le."""
    ja = " ".join(motor._o_que_a_pessoa_disse(con, conversa).split())
    atual = " ".join((atual or "").split())
    if atual and atual not in ja:
        ja = (ja + " / " + atual) if ja else atual
    return ja[:TEXTO_ATE]


def _culturas_ditas(interesse) -> str:
    c = list(interesse["culturas"] or [])
    if not c:
        return "não indicou"
    return c[0] if len(c) == 1 else ", ".join(c[:-1]) + " e " + c[-1]


def _quem(d) -> str:
    local = " · ".join(x for x in ((d["cidade"] or "").strip(), (d["uf"] or "").strip()) if x)
    return "%s (código %s%s)" % ((d["nome"] or "").strip() or "sem nome", d["erp_codigo"], (", " + local) if local else "")


def texto_da_ficha(d, interesse, texto: str, numero: str) -> str:
    papel = PAPEL_DITO.get(interesse["papel"] or "", "contato do cadastro")
    linhas = ["*Interesse no boletim* (conversa com a OlivIA)",
              "Cliente: %s" % _quem(d),
              "Quem falou: %s" % papel,
              "Culturas: %s" % _culturas_ditas(interesse),
              "Escreveu: %s" % (("\"%s\"" % texto) if texto else "nada além do toque em Quero saber mais")]
    n = "".join(c for c in (numero or "") if c.isdigit())
    linhas.append(("Conversar com ele: https://wa.me/%s" % n) if n else "Sem número de WhatsApp na conversa.")
    return "\n".join(linhas)


def linha_da_ficha(d, interesse, texto: str, numero: str) -> str:
    """A ficha numa linha so, para a variavel do `olivia_resumo` (fora da janela): sem quebra nem espaco
    repetido (a Meta recusa os dois numa variavel), com o telefone escrito, cortada para caber."""
    from .lead import limpo, telefone
    papel = PAPEL_DITO.get(interesse["papel"] or "", "contato do cadastro")
    fim = "telefone %s." % telefone(numero)
    partes = ["Interesse no boletim: %s" % _quem(d), "falou o %s" % papel,
              "culturas: %s" % _culturas_ditas(interesse),
              "escreveu: %s" % (texto or "só tocou em Quero saber mais")]
    corpo = limpo("; ".join(partes), LINHA_ATE - len(fim) - 2)
    return limpo(corpo + "; " + fim, LINHA_ATE)


def mandar(con, saida, interesse, d, conversa, numero: str, agora: datetime, atual: str = "") -> bool:
    """A ficha ao responsavel da linha do envio. True: a Meta aceitou. NUNCA levanta."""
    def falhou(motivo: str) -> bool:
        print("interesse: ficha %d nao saiu: %s" % (interesse["id"], motivo[:200]), flush=True)
        con.execute("UPDATE atendimento.interesses SET erro = %s WHERE id = %s", (motivo[:500], interesse["id"]))
        return False

    if interesse["enviada_em"] is not None:
        return True
    para = "".join(c for c in (d["responsavel_whatsapp"] or "") if c.isdigit())
    if not para:
        return falhou("a linha do envio não tem o WhatsApp do responsável")
    if com_nove(para) == com_nove(numero):
        return falhou("o responsável é a própria pessoa que conversou")
    texto = o_que_escreveu(con, conversa, atual)
    try:
        if janela_aberta(con, para, agora):
            como, w = "texto", saida.texto(para, texto_da_ficha(d, interesse, texto, numero))
        else:
            m = modelo_do_uso(con, USO_DO_MODELO)
            if not m:
                return falhou("nenhum modelo ativo para %s" % USO_DO_MODELO)
            como, w = "modelo", saida.modelo(para, m["nome"], m["idioma"], [linha_da_ficha(d, interesse, texto, numero)])
    except Exception as falha:   # noqa: BLE001 -- a ficha nunca derruba a conversa
        return falhou("%s: %s" % (type(falha).__name__, falha))
    if not w:
        return falhou("a Meta não aceitou a mensagem")
    con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, %s, %s)",
                (w, para, como, RESUMO_FICHA))
    con.execute("""UPDATE atendimento.interesses SET enviada_em = %s, enviada_como = %s, wamid = %s, erro = '',
                          texto = %s WHERE id = %s""", (agora, como, w, texto, interesse["id"]))
    return True


def quem_atende(d) -> str:
    return nome_de_quem_atende(d["responsavel_nome"]) if (d["responsavel_nome"] or "").strip() else "quem cuida de você"


# ── o que vai ao ERP (D9) ───────────────────────────────────────────────────

ERP_ATE = 500
ERP_FECHA = timedelta(hours=24)


def resposta_ao_erp(linha: dict, agora: datetime) -> tuple[str, str | None]:
    """(resposta, texto) que o ERP ja conhece, para a resposta `saber` (passo 2: o ERP grava o texto so no
    estado "respondeu", e o estado so avanca -- o primeiro texto que chega fica). Enquanto a conversa corre:
    `falar` (tocou), sem texto. Com a ficha mandada, a conversa fechada, ou 24 h depois do toque: `texto`,
    com "Quis saber mais. Interesse: ..." e o que ele escreveu, ate 500 letras."""
    if not (linha.get("ficha_em") or not linha.get("conversa_aberta")
            or (linha.get("resposta_em") and agora - linha["resposta_em"] >= ERP_FECHA)):
        return "falar", None
    culturas = [c for c in (linha.get("culturas") or []) if c]
    texto = "Quis saber mais."
    if culturas:
        texto += " Interesse: %s." % ", ".join(culturas)
    escreveu = " ".join(((linha.get("escreveu") or "") or (linha.get("resposta_texto") or "")).split())
    if escreveu:
        texto += " Escreveu: \"%s\"" % escreveu
    if len(texto) > ERP_ATE:
        texto = texto[:ERP_ATE - 1].rstrip() + "…"
    return "texto", texto
