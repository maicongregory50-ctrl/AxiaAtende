"""#1664: a RESPOSTA PADRAO ao produtor cooperante que responde a um aviso automatico do contrato.

Spec: docs/specs/2026-11-19-resposta-padrao-ao-aviso-de-contrato.md (D1 a D8). Manual:
docs/manuais/resposta-ao-cooperante.md.

O GATILHO (D1) e o proprio aviso, nao o cadastro: quem recebeu um aviso de contrato pelo numero da empresa
e escreve pelo mesmo numero dentro de `cooperante.dias` recebe o texto fixo (D2, sem IA) e o cartao do
contato legal (D4, o destino do ajuste `cooperante.destino`). O contato e avisado na hora (D5). Uma resposta
padrao por aviso; nas mensagens seguintes, a linha curta, e cada uma e repassada ao contato (D6).

`aviso_de_contrato_recente` e o PONTO UNICO onde os avisos entram: hoje so o termo de reprovacao (#1542);
os proximos avisos da jornada do contrato entram ali.

O desvio fica ANTES do portao do cliente (motor.tratar): um erro aqui calaria o atendimento de quem recebeu
o aviso. Por isso `tratar` so assume a mensagem quando conseguiu responder; em excecao, registra e devolve
False, e o caminho de hoje segue.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .envio import com_nove, janela_aberta, modelo_do_uso, primeiro_nome, so_digitos

FUSO = ZoneInfo("America/Sao_Paulo")

AJUSTE_CHAVE = "cooperante.resposta_padrao"
AJUSTE_DIAS = "cooperante.dias"
AJUSTE_TEXTO = "cooperante.texto"
AJUSTE_DESTINO = "cooperante.destino"
DIAS_PADRAO = 7

# Os resumos em `enviadas`: e pelo da resposta padrao que a segunda mensagem e reconhecida (D6), sem coluna nova.
RESUMO_PADRAO = "aviso de contrato: resposta padrao (termo %s)"
RESUMO_CARTAO = "aviso de contrato: cartao (termo %s)"
RESUMO_CURTA = "aviso de contrato: linha curta (termo %s)"
RESUMO_REPASSE = "aviso de contrato: repasse ao contato (termo %s)"

LINHA_CURTA = "{nome}, o {contato} já foi avisado da sua mensagem; o contato dele está logo acima."
USO_DO_MODELO = "aviso_olivia_resumo"   # o modelo `olivia_resumo` (UTILITY, uma variavel), o mesmo do #1660
LINHA_ATE = 900                          # o corpo do modelo e "Resumo da OlivIA: {{1}} ...": a Meta aceita 1024
ESCREVEU_ATE = 600


def _ajuste(con, chave, padrao=None):
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (chave,)).fetchone()
    return padrao if r is None else r["valor"]


def ligado(con) -> bool:
    """A chave (D8). Sem a linha (a migracao 073 nao aplicada, ou a VOLTA dela), desligada."""
    return _ajuste(con, AJUSTE_CHAVE, False) is True


def dias(con) -> int:
    try:
        return int(_ajuste(con, AJUSTE_DIAS, DIAS_PADRAO))
    except (TypeError, ValueError):
        return DIAS_PADRAO


def destino(con):
    """O contato legal do contrato: a linha da tela Destinos que o ajuste nomeia. None sem ajuste ou sem linha."""
    d = _ajuste(con, AJUSTE_DESTINO)
    if d is None:
        return None
    try:
        return con.execute("SELECT id, nome, whatsapp FROM atendimento.destinos WHERE id = %s", (int(d),)).fetchone()
    except (TypeError, ValueError):
        return None


def _mesmo_numero(a: str, b: str) -> bool:
    return bool(a and b) and com_nove(so_digitos(a)) == com_nove(so_digitos(b))


def aviso_de_contrato_recente(con, numero: str, agora: datetime):
    """O aviso de contrato mais novo mandado a `numero` dentro do prazo, ou None. Hoje: a linha de
    `termos_reprovacao` com `para_whatsapp` = o numero, `enviado_em` dentro de `cooperante.dias` e estado
    diferente de `falhou`. Devolve {tipo, id, numero, produtor_nome, enviado_em, para}.

    E o ponto unico onde os proximos avisos da jornada do contrato entram (D1). O numero e comparado com e
    sem o 9 (a Meta manda o celular sem ele; o ERP o guarda com ele)."""
    if not numero:
        return None
    desde = agora - timedelta(days=dias(con))
    for r in con.execute("""SELECT id, numero_termo, produtor_nome, enviado_em, para_whatsapp
                              FROM atendimento.termos_reprovacao
                             WHERE enviado_em IS NOT NULL AND enviado_em > %s AND enviado_em <= %s
                               AND estado <> 'falhou'
                             ORDER BY enviado_em DESC, id DESC""", (desde, agora)).fetchall():
        if _mesmo_numero(r["para_whatsapp"], numero):
            return {"tipo": "termo de reprovação", "id": r["id"], "numero": r["numero_termo"],
                    "produtor_nome": r["produtor_nome"] or "", "enviado_em": r["enviado_em"],
                    "para": r["para_whatsapp"]}
    return None


def saudacao(agora: datetime) -> str:
    """Pela hora de Brasilia: bom dia (5h-12h), boa tarde (12h-18h), boa noite."""
    h = agora.astimezone(FUSO).hour
    return "Bom dia" if 5 <= h < 12 else "Boa tarde" if 12 <= h < 18 else "Boa noite"


def nome_do_produtor(aviso, e) -> str:
    """O primeiro nome do `produtor_nome` do aviso, com a caixa arrumada (D3, sem genero); sem ele, o nome do
    perfil do WhatsApp; sem nenhum, vazio."""
    for nome in ((aviso.get("produtor_nome") or "").strip(), (e.pessoa.nome or "").strip()):
        if nome:
            return primeiro_nome(nome)
    return ""


def texto_padrao(con, aviso, e, d, agora: datetime) -> str:
    texto = _ajuste(con, AJUSTE_TEXTO, "") or ""
    nome = nome_do_produtor(aviso, e)
    if not nome:
        texto = texto.replace(", {nome}!", "!").replace(", {nome}", "")
    return texto.replace("{saudacao}", saudacao(agora)).replace("{nome}", nome).replace(
        "{contato}", primeiro_nome(d["nome"]))


def ja_respondeu(con, aviso, numero: str) -> bool:
    """A resposta padrao deste aviso ja saiu (D6): o resumo dela em `enviadas`, para este numero, depois do
    `enviado_em` do aviso. Um aviso novo ao mesmo produtor reinicia a contagem."""
    for r in con.execute("""SELECT para FROM atendimento.enviadas WHERE resumo = %s AND enviada_em >= %s""",
                         (RESUMO_PADRAO % aviso["numero"], aviso["enviado_em"])).fetchall():
        if _mesmo_numero(r["para"], numero):
            return True
    return False


def _registrar(con, para: str, tipo: str, resumo: str, wamid) -> None:
    if not wamid:
        return   # #1028: envio calado nao deixa linha -- enviadas conta o que a Meta aceitou
    con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, %s, %s)
                   ON CONFLICT (wamid) DO NOTHING""", (wamid, para, tipo, resumo[:200]))


def o_que_escreveu(e) -> str:
    """O texto; para audio, foto, video ou documento, o tipo (e a legenda, quando houver)."""
    if e.texto:
        return " ".join(e.texto.split())[:ESCREVEU_ATE]
    if e.audio is not None:
        return "(mandou um áudio)"
    if e.midia is not None:
        o_que = "(mandou uma foto)" if e.midia.tipo == "foto" else "(mandou um vídeo)"
        return o_que + ((" " + " ".join(e.midia.legenda.split())[:ESCREVEU_ATE]) if e.midia.legenda else "")
    if e.documento is not None:
        o_que = "(mandou um documento%s)" % ((" " + e.documento.nome_arquivo) if e.documento.nome_arquivo else "")
        return o_que + ((" " + " ".join(e.documento.legenda.split())[:ESCREVEU_ATE]) if e.documento.legenda else "")
    return "(mandou uma mensagem sem texto)"


def telefone(numero: str) -> str:
    """+55 49 98888-3333: o numero escrito, para quem le o modelo fora da janela (sem link)."""
    n = so_digitos(numero)
    if n.startswith("55") and len(n) in (12, 13):
        local = n[4:]
        return "+55 %s %s-%s" % (n[2:4], local[:-4], local[-4:])
    return ("+" + n) if n else "sem número"


def _nome_inteiro(aviso, e) -> str:
    nome = " ".join((aviso.get("produtor_nome") or "").split()).title()
    return nome or (e.pessoa.nome or "").strip() or "sem nome"


def texto_do_repasse(aviso, e) -> str:
    """O aviso ao contato, dentro da janela dele (texto livre)."""
    n = so_digitos(e.pessoa.wa_id or "")
    return "\n".join([
        "*Cooperante respondeu ao aviso*",
        "Nome: %s" % _nome_inteiro(aviso, e),
        "Aviso: %s %s" % (aviso["tipo"], aviso["numero"]),
        "Escreveu: %s" % o_que_escreveu(e),
        ("Conversar com ele: https://wa.me/%s" % n) if n else "Sem número de WhatsApp na conversa."])


def linha_do_repasse(aviso, e) -> str:
    """O aviso ao contato numa linha so, para a variavel do modelo `olivia_resumo` (fora da janela): sem
    quebra nem espaco repetido (a Meta recusa os dois numa variavel), com o telefone escrito."""
    fim = "; telefone %s." % telefone(e.pessoa.wa_id or "")
    corpo = "cooperante respondeu ao aviso do contrato: %s, %s %s; escreveu: %s" % (
        _nome_inteiro(aviso, e), aviso["tipo"], aviso["numero"], o_que_escreveu(e))
    corpo = " ".join(corpo.split())[:LINHA_ATE - len(fim)]
    return corpo + fim


def avisar(con, saida, aviso, e, agora: datetime) -> bool:
    """Repassa ao contato o que o produtor escreveu (D5). Na janela de 24 h do contato, texto livre; fora dela,
    o modelo `olivia_resumo`. NUNCA levanta: qualquer falha e registrada e devolve False, sem segurar a
    resposta ao produtor."""
    try:
        with con.transaction():   # ponto de retorno: um erro de SQL aqui nao aborta a transacao do evento
            d = destino(con)
            if d is None:
                raise RuntimeError("o ajuste %s não aponta um destino da tela Destinos" % AJUSTE_DESTINO)
            para = d["whatsapp"]
            if janela_aberta(con, para, agora):
                tipo, w = "texto", saida.texto(para, texto_do_repasse(aviso, e))
            else:
                m = modelo_do_uso(con, USO_DO_MODELO)
                if not m:
                    raise RuntimeError("nenhum modelo ativo para %s" % USO_DO_MODELO)
                tipo, w = "modelo", saida.modelo(para, m["nome"], m["idioma"], [linha_do_repasse(aviso, e)])
            if not w:
                raise RuntimeError("a Meta não aceitou a mensagem")
            _registrar(con, para, tipo, RESUMO_REPASSE % aviso["numero"], w)
        return True
    except Exception as falha:   # noqa: BLE001 -- o repasse nunca derruba a resposta ao produtor
        print("cooperante: repasse do termo %s (%s) nao saiu: %s: %s"
              % (aviso.get("numero"), e.wamid, type(falha).__name__, str(falha)[:200]), flush=True)
        return False


def tratar(con, saida, e, agora: datetime) -> bool:
    """A mensagem de quem recebeu um aviso de contrato recente. True: respondeu, e a mensagem e daqui. False:
    nao e caso (chave desligada, toque de botao, reacao, sem aviso no prazo) ou nao conseguiu responder -- o
    caminho de hoje segue."""
    p = e.pessoa
    if e.toque or e.tipo == "reaction" or not p.wa_id:
        return False
    try:
        with con.transaction():   # ponto de retorno: um erro de SQL aqui nao aborta a transacao do evento
            if not ligado(con):
                return False
            aviso = aviso_de_contrato_recente(con, p.wa_id, agora)
            if aviso is None:
                return False
            d = destino(con)
            if d is None:
                print("cooperante: %s respondeu ao termo %s, mas o ajuste %s nao aponta um destino: segue o caminho de hoje"
                      % (p.wa_id, aviso["numero"], AJUSTE_DESTINO), flush=True)
                return False
            if ja_respondeu(con, aviso, p.wa_id):
                nome = nome_do_produtor(aviso, e) or "Olá"
                w = saida.texto(p.para, LINHA_CURTA.format(nome=nome, contato=primeiro_nome(d["nome"])))
                if not w:
                    return False
                _registrar(con, p.para, "texto", RESUMO_CURTA % aviso["numero"], w)
            else:
                w = saida.texto(p.para, texto_padrao(con, aviso, e, d, agora))
                if not w:
                    return False
                _registrar(con, p.para, "texto", RESUMO_PADRAO % aviso["numero"], w)
                try:
                    with con.transaction():
                        _registrar(con, p.para, "texto", RESUMO_CARTAO % aviso["numero"],
                                   saida.contato(p.para, d["nome"], d["whatsapp"]))
                except Exception as falha:   # noqa: BLE001 -- o texto ja saiu; o cartao e o complemento
                    print("cooperante: cartao a %s: %s: %s" % (p.wa_id, type(falha).__name__, str(falha)[:200]), flush=True)
    except Exception as falha:   # noqa: BLE001 -- erro aqui nao cala o atendimento: o caminho de hoje segue
        print("cooperante: %s (%s): %s: %s" % (p.wa_id, e.wamid, type(falha).__name__, str(falha)[:200]), flush=True)
        return False
    avisar(con, saida, aviso, e, agora)
    return True
