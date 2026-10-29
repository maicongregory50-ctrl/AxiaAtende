"""O envio a carteira. #950, Fase E do plano, com a emenda do dono de 09/10/2026 (E1b).

QUEM PEDE E QUEM MANDA. O AxiaMarketing pede (o tipo, o modelo, a peca, as imagens e a lista de
clientes ja com o responsavel de cada um, lido do canal comercial do cadastro no ERP), depois de o
dono aprovar la (trava D7 do #923). As TELAS gravam o pedido (`receber_pedido`, pela porta local).
O RECEPCIONISTA, unico com a chave da Meta, manda (`rotina`, a cada minuto).

DOIS TIPOS DE ENVIO:
- `material` -- um servico que agrega ao produto (as pecas da revenda com a logo dela; cada
  cliente pode ter as SUAS imagens). Vai por CONVITE (modelo de uso `convite`: capa, "Quero
  receber" / "Nao quero receber"); o toque abre a janela de 24h e as imagens seguem sem custo.
- `direta` -- campanha de arte unica ("chegou a epoca do seu Trigo Mourisco"). Uma mensagem paga
  (modelo de uso `direta`) com a imagem, o texto e o botao de link "Falar com meu atendimento". A
  Meta recusa link direto para o WhatsApp em modelo, entao o botao abre o NOSSO endereco
  (`/falar/<codigo>`, no recepcionista), que anota o toque e manda na hora para o wa.me do
  responsavel: um toque so, do modelo a conversa (decisao do dono: "cada etapa reduz a chance").
  SO VAI A QUEM JA ACEITOU: tocou "Quero receber" em algum envio, ou tem o aceite de marketing no
  cadastro do #952. Quem nunca aceitou fica "sem aceite" e recebe primeiro um convite.

OS MODELOS SAO CADASTRO (`atendimento.modelos`): o nome aprovado na Meta, as variaveis do texto
em ordem (de uma lista fechada de fontes) e o tipo de botao. Modelo novo e linha nova, nao codigo.

AS REGRAS QUE VALEM PARA OS DOIS (spec, "Cuidado com a Meta"):
- **Sem responsavel no cadastro** (canal comercial vazio), o cliente NAO recebe.
- **Degraus:** lotes de ate 20 por dia, na ordem de faturamento (Top 20, Top 50, Top 100); o
  proximo lote so sai com a nota do numero em GREEN; em YELLOW ou RED o envio para sozinho.
- **Ninguem recebe o mesmo envio duas vezes**; quem recusou nao recebe mais nada; numero que a
  Meta recusou como "nao e WhatsApp" nao e tentado de novo.
- **O comprador recebe no maximo duas por mes** (#1163): o que ja recebeu duas no mes do calendario
  fica `teto_do_mes` naquele envio, decidido no laco do lote, e volta a receber no mes seguinte.
- **O responsavel recebe copia** do que os clientes dele recebem (uma por envio).
- **Quem recusa** e o responsavel dele e avisado (modelo de uso `aviso_recusa`, Utilidade).

OS IDS DOS BOTOES do convite (`payload`): `envio:<id>:quero` e `envio:<id>:nao_quero`. O codigo do
link da direta e `<id da linha>-<assinatura>` (`codigo_falar`): ninguem monta um endereco nosso que
leve a outro numero.

O NUMERO DO TOQUE: a Meta manda o celular brasileiro antigo, sem o 9 (`554991505565`); a lista do ERP
tem o 9. `com_nove` poe o 9 antes de comparar (medido no ensaio de 09/10/2026).
"""
import hashlib
import hmac
import json
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .banco import conexao
from .saida import Saida

FUSO = ZoneInfo("America/Sao_Paulo")
#: #1163 (o #1103, spec de 26/10, linha 27): "Teto de duas mensagens por mes por comprador". Conta o
#: convite e a peca. So o comprador: o tecnico tem a regua dele, e o contato sem papel fica como esta.
TETO_DO_COMPRADOR = 2
#: #1192 (dono, 29/10/2026): a janela do envio ao cliente -- de segunda a sexta, das 9h30 as 17h, no
#: relogio de Sao Paulo. O lote do dia virava a 00h01 (o cliente recebeu de madrugada); fora da janela
#: nada sai, e o que ficou segue no proximo dia util, as 9h30.
JANELA_INICIO = time(9, 30)
JANELA_FIM = time(17, 0)
DIAS_DA_JANELA = (0, 1, 2, 3, 4)   # weekday(): segunda a sexta
JANELA = timedelta(hours=24)
NAO_E_WHATSAPP = {"131026"}   # codigo da Meta: mensagem nao entregavel (numero sem WhatsApp)
CELULAR = re.compile(r"^55[1-9][0-9]9[0-9]{8}$")


def _assinatura(segredo: str, texto: str) -> str:
    chave = hmac.new(segredo.encode(), b"axiaatende-falar", hashlib.sha256).digest()
    return hmac.new(chave, texto.encode(), hashlib.sha256).hexdigest()[:16]


def codigo_falar(segredo: str, dest_id: int, copia: bool = False) -> str:
    """O final do botao de link da direta. `c` na frente: a copia do responsavel, que nao conta."""
    base = ("c%d" if copia else "%d") % dest_id
    return "%s-%s" % (base, _assinatura(segredo, base))


def ler_codigo(segredo: str, codigo: str):
    """(id da linha, e_copia), ou None se o codigo nao foi assinado por nos."""
    base, _, sig = (codigo or "").partition("-")
    copia = base.startswith("c")
    numero = base[1:] if copia else base
    if not numero.isdigit() or not hmac.compare_digest(sig, _assinatura(segredo, base)):
        return None
    return int(numero), copia


def falar(con, segredo: str, codigo: str, agora: datetime) -> str | None:
    """O toque no link da direta: anota (so o do cliente, so o primeiro) e devolve o WhatsApp do
    responsavel para onde a pessoa vai. None: codigo que nao e nosso."""
    if (codigo or "").startswith("v"):
        # #1098: "Conversar com o candidato", do modelo do curriculo para a Fran
        base, _, sig = codigo.partition("-")
        if not base[1:].isdigit() or not hmac.compare_digest(sig, _assinatura(segredo, base)):
            return None
        c = con.execute("SELECT wa_id FROM atendimento.candidaturas WHERE id = %s", (int(base[1:]),)).fetchone()
        return c["wa_id"] if c and c["wa_id"] else None
    lido = ler_codigo(segredo, codigo)
    if not lido:
        return None
    d = con.execute("SELECT id, resposta, responsavel_whatsapp FROM atendimento.envio_destinatarios WHERE id = %s",
                    (lido[0],)).fetchone()
    if not d or not d["responsavel_whatsapp"]:
        return None
    if not lido[1] and d["resposta"] in (None, "texto"):
        con.execute("""UPDATE atendimento.envio_destinatarios SET resposta = 'falar', resposta_em = %s
                        WHERE id = %s""", (agora, d["id"]))
    return d["responsavel_whatsapp"]


def com_nove(numero: str) -> str:
    """O celular brasileiro como a lista do ERP o guarda: 55 + DDD + 9 + oito digitos."""
    n = "".join(c for c in (numero or "") if c.isdigit())
    if len(n) == 12 and n.startswith("55") and n[4] in "6789":
        return n[:4] + "9" + n[4:]
    return n
USO_DO_TIPO = {"material": "convite", "direta": "direta"}


class PedidoInvalido(ValueError):
    pass


def so_digitos(numero: str) -> str:
    d = re.sub(r"\D", "", numero or "")
    if d and not d.startswith("55"):
        d = "55" + d
    return d


def primeiro_nome(nome: str) -> str:
    return (nome or "").split(" ")[0].title() or "tudo bem"


#: #1189: o responsavel pode ser uma EMPRESA (a DJ AGRO COMPANY LTDA, representante de cooperativa) --
#: e "Quem cuida de voce e Dj" nao serve. Empresa vai pelo nome, sem o tipo societario.
_SOCIETARIO = {"LTDA", "LTDA.", "ME", "EPP", "EIRELI", "S/A", "SA", "S.A.", "COMPANY", "CIA", "-ME"}


def nome_de_quem_atende(nome: str) -> str:
    palavras = (nome or "").replace("-ME", " ME").split()
    if not any(w.upper() in _SOCIETARIO for w in palavras):
        return primeiro_nome(nome)
    fica = [w for w in palavras if w.upper() not in _SOCIETARIO - {"COMPANY"}]
    return " ".join(w.upper() if len(w) <= 2 and w.isalpha() and w.upper() not in ("DE", "DA", "DO", "E") else w.title()
                    if w.upper() not in ("DE", "DA", "DO", "E") else w.lower() for w in fica) or primeiro_nome(nome)


def modelo(con, nome: str):
    return con.execute("SELECT * FROM atendimento.modelos WHERE nome = %s AND ativo", (nome,)).fetchone()


def modelo_do_uso(con, uso: str):
    return con.execute("SELECT * FROM atendimento.modelos WHERE uso = %s AND ativo ORDER BY id LIMIT 1",
                       (uso,)).fetchone()


def parametros(m, fontes: dict) -> list[str]:
    """As variaveis do modelo, na ordem do cadastro, tiradas das fontes."""
    return [str(fontes.get(v, "")) or "-" for v in m["variaveis"]]


# ── o pedido (lado das TELAS) ───────────────────────────────────────────────

def receber_pedido(con, pedido: dict) -> int:
    """Grava o pedido e a fila de destinatarios, ja classificada. Devolve o id do envio.
    Pedido repetido (mesma `pedido_ref`) devolve o envio que ja existe e nao muda nada."""
    ja = con.execute("SELECT id FROM atendimento.envios WHERE pedido_ref = %s", (pedido["pedido_ref"],)).fetchone()
    if ja:
        return ja["id"]
    tipo = pedido.get("tipo", "material")
    if tipo not in USO_DO_TIPO:
        raise PedidoInvalido("tipo de envio desconhecido: %s" % tipo)
    m = modelo(con, pedido["modelo"])
    if not m or m["uso"] != USO_DO_TIPO[tipo]:
        raise PedidoInvalido("o modelo %r não existe ou não serve para envio %s" % (pedido["modelo"], tipo))
    envio = con.execute(
        """INSERT INTO atendimento.envios (pedido_ref, tipo, campanha, peca, assunto, modelo, capa, imagens,
                                           aprovado_por, aprovado_em, lote_tamanho, passa_do_teto)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s) RETURNING id""",
        (pedido["pedido_ref"], tipo, pedido["campanha"], pedido["peca"], pedido.get("assunto", ""), m["nome"],
         pedido["capa"], json.dumps(pedido.get("imagens") or []), pedido["aprovado_por"], pedido["aprovado_em"],
         min(int(pedido.get("lote_tamanho", 20)), 20), pedido.get("passa_do_teto") is True)).fetchone()["id"]

    ordenados = sorted(pedido["clientes"], key=lambda c: -float(c.get("faturamento") or 0))
    for pos, c in enumerate(ordenados, start=1):
        numero = so_digitos(c.get("whatsapp", ""))
        resp = so_digitos(c.get("responsavel_whatsapp", ""))
        # o aceite do cadastro (#952): True aceitou, False RECUSOU, None nao perguntado
        aceite_cadastro = c.get("aceite_cadastro") is True
        if not CELULAR.match(numero):
            situacao = "sem_whatsapp"
        elif not c.get("responsavel_nome") or not CELULAR.match(resp):
            situacao = "sem_responsavel"
        elif c.get("aceite_cadastro") is False or _ultimo_consentimento(con, numero) == "recusa":
            situacao = "recusou_antes"
        elif tipo == "direta" and not (aceite_cadastro or _ultimo_consentimento(con, numero) == "aceite"):
            situacao = "sem_aceite"
        elif _ja_recebeu(con, numero, pedido["peca"]):
            situacao = "ja_recebeu"
        elif _nao_e_whatsapp(con, numero):
            situacao = "nao_e_whatsapp"
        else:
            situacao = "aguardando"
        # #1142: O CONFLITO E POR NUMERO, e nao por cadastro -- uma pessoa uma vez por envio. Desde
        # o #1141 o ERP entrega uma linha por CONTATO, e na camada cooperativa o comprador e o
        # tecnico do mesmo cadastro caem no mesmo envio: pela regra antiga o segundo sumia calado.
        # O `WHERE whatsapp <> ''` e a mesma condicao do indice parcial da 033: quem nao tem celular
        # grava vazio, e dois assim no mesmo envio e caso legitimo (`sem_whatsapp`).
        con.execute(
            """INSERT INTO atendimento.envio_destinatarios
                   (envio_id, erp_codigo, nome, cidade, uf, whatsapp, faturamento, posicao,
                    responsavel_nome, responsavel_whatsapp, sugestao_vendedor, situacao,
                    capa, imagens, aceite_cadastro, papel, responsavel_canal)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
               ON CONFLICT (envio_id, whatsapp) WHERE whatsapp <> '' DO NOTHING""",
            (envio, int(c["erp_codigo"]), c["nome"], c.get("cidade", ""), c.get("uf", ""), numero,
             c.get("faturamento") or 0, pos, c.get("responsavel_nome", ""), resp,
             c.get("sugestao_vendedor", ""), situacao, c.get("capa"),
             json.dumps(c["imagens"]) if c.get("imagens") else None, aceite_cadastro,
             c.get("papel"), c.get("responsavel_canal")))
    return envio


def _ultimo_consentimento(con, numero):
    r = con.execute("""SELECT tipo FROM atendimento.consentimentos WHERE whatsapp = %s
                        ORDER BY em DESC, id DESC LIMIT 1""", (numero,)).fetchone()
    return r["tipo"] if r else None


def _ja_recebeu(con, numero, peca):
    return con.execute("""SELECT 1 FROM atendimento.envio_destinatarios d JOIN atendimento.envios e ON e.id = d.envio_id
                           WHERE d.whatsapp = %s AND e.peca = %s AND d.convite_em IS NOT NULL""",
                       (numero, peca)).fetchone() is not None


def _nao_e_whatsapp(con, numero):
    return con.execute("""SELECT 1 FROM atendimento.envio_destinatarios
                           WHERE whatsapp = %s AND situacao = 'nao_e_whatsapp'""", (numero,)).fetchone() is not None


# ── o porteiro dos avisos internos (#1188) ──────────────────────────────────
#
# Dono, 28/10/2026: "sempre que passou de 24 horas do ultimo contato, a proxima mensagem precisa de um
# botao, para receber mensagem do contato e abrir as 24 h de envio novamente". So os avisos INTERNOS
# (`atendimento.avisos`: o representante, a equipe, o dono); o cliente e o #1189. Com a chave
# `porteiro` ligada:
#   - a pessoa escreveu ao numero da empresa nas ultimas 24 h: o aviso sai como TEXTO, de graca;
#   - nao escreveu: o aviso fica GUARDADO, e sai UMA reabertura por numero (modelo de uso `reabertura`,
#     "Voce tem N aviso(s)... Toque em Ver"). Aviso novo com reabertura pendente so se soma;
#   - o toque em Ver (`reabrir:<numero>`) solta os guardados daquele numero, na ordem, como texto;
#   - 7 dias sem o toque: os guardados da reabertura viram NAO VISTO. Nao saem mais e nao somem.

NAO_VISTO = timedelta(days=7)


def janela_aberta(con, numero: str, agora: datetime) -> bool:
    """A pessoa mandou QUALQUER mensagem (texto, foto, toque, reacao) ao numero da empresa ha menos de
    24 h. A fonte e `eventos_meta`, e nao `conversas`: o interno que so manda foto ao canal de campo
    nao abre conversa nenhuma, e a janela dele esta aberta do mesmo jeito (o canal de campo mede
    assim, `campo.ultima_mensagem_de`). A Meta manda o celular sem o 9; o cadastro o guarda com o 9:
    procura-se pelas duas formas."""
    from .saida import wa_id_do_whatsapp
    formas = list({com_nove(numero), wa_id_do_whatsapp(com_nove(numero))})
    r = con.execute("""SELECT max(recebido_em) AS em FROM atendimento.eventos_meta
                        WHERE tipo = 'mensagem' AND corpo->'msg'->>'from' = ANY(%s)""", (formas,)).fetchone()
    return r is not None and r["em"] is not None and agora - r["em"] < JANELA


def texto_do_modelo(m, corpo: list[str]) -> str:
    """O texto do modelo com as variaveis no lugar, em texto corrido."""
    texto = m["texto"]
    for i, valor in enumerate(corpo, start=1):
        texto = texto.replace("{{%d}}" % i, valor)
    return texto


def _partes_do_aviso(m, a) -> list[str]:
    partes = (a["sobre"].split("|") + ["", "", ""])[:3]
    return parametros(m, {"aviso1": partes[0], "aviso2": partes[1], "aviso3": partes[2]})


def texto_do_aviso(con, a) -> str:
    """O aviso como TEXTO LIVRE: a frase do modelo do tipo, com os mesmos dados que o modelo levaria.
    O representante le a mesma frase pelos dois caminhos."""
    m = modelo_do_uso(con, "aviso_" + a["tipo"])
    if not m:
        raise RuntimeError("nenhum modelo cadastrado para aviso_%s" % a["tipo"])
    return texto_do_modelo(m, _partes_do_aviso(m, a))


# ── a rotina (lado do RECEPCIONISTA) ────────────────────────────────────────

class Envio:
    """O que o motor e o recepcionista chamam. `ler_nota` devolve a nota do numero na Meta
    (GREEN/YELLOW/RED/UNKNOWN); nos testes, uma funcao falsa."""

    def __init__(self, ler_nota=None):
        self._ler_nota = ler_nota
        self._segredo = ""
        self._porteiro = False

    def rotina(self, cfg, saida: Saida, agora: datetime) -> None:
        self._segredo = cfg.meta_app_secret
        self._porteiro = cfg.porteiro
        with conexao(cfg) as con:
            self.ler_nota_do_dia(con, agora)
            self.mandar_lotes(con, saida, agora)
            self.mandar_imagens_pendentes(con, saida, agora)
            self.mandar_avisos(con, saida, agora)

    def ler_nota_do_dia(self, con, agora: datetime) -> str:
        hoje = agora.astimezone(FUSO).date()
        r = con.execute("SELECT nota, lida_em FROM atendimento.nota_qualidade ORDER BY lida_em DESC LIMIT 1").fetchone()
        if r and r["lida_em"].astimezone(FUSO).date() == hoje:
            return r["nota"]
        nota = "UNKNOWN"
        if self._ler_nota:
            try:
                nota = (self._ler_nota() or "UNKNOWN").upper()
            except Exception:   # noqa: BLE001 -- sem nota, nao sai lote (abaixo)
                nota = "UNKNOWN"
        if nota not in ("GREEN", "YELLOW", "RED"):
            nota = "UNKNOWN"
        con.execute("INSERT INTO atendimento.nota_qualidade (lida_em, nota) VALUES (%s, %s)", (agora, nota))
        return nota

    def mandar_lotes(self, con, saida: Saida, agora: datetime) -> int:
        local = agora.astimezone(FUSO)
        if local.weekday() not in DIAS_DA_JANELA or not JANELA_INICIO <= local.time() < JANELA_FIM:
            return 0   # #1192: fora da janela nada sai; o lote espera o proximo dia util, 9h30
        nota = self.ler_nota_do_dia(con, agora)
        hoje = local.date()
        mandados = 0
        for e in con.execute("SELECT * FROM atendimento.envios WHERE situacao IN ('ativo', 'parado_nota') ORDER BY id").fetchall():
            if nota != "GREEN":
                # Amarela ou vermelha PARA o envio (o dono religa na tela Envios); sem leitura
                # (UNKNOWN) so espera o proximo minuto.
                if nota in ("YELLOW", "RED") and e["situacao"] != "parado_nota":
                    con.execute("UPDATE atendimento.envios SET situacao = 'parado_nota' WHERE id = %s", (e["id"],))
                continue
            if e["situacao"] == "parado_nota":
                continue   # so o dono religa, mesmo com a nota de volta ao verde
            ja_hoje = con.execute(
                """SELECT count(*) AS n FROM atendimento.envio_destinatarios
                    WHERE envio_id = %s AND convite_em IS NOT NULL
                      AND (convite_em AT TIME ZONE 'America/Sao_Paulo')::date = %s""",
                (e["id"], hoje)).fetchone()["n"]
            vagas = e["lote_tamanho"] - ja_hoje
            if vagas <= 0:
                continue
            fila = con.execute("""SELECT * FROM atendimento.envio_destinatarios
                                   WHERE envio_id = %s AND situacao = 'aguardando'
                                   ORDER BY posicao LIMIT %s""", (e["id"], vagas)).fetchall()
            if not fila:
                if not ja_hoje:
                    con.execute("UPDATE atendimento.envios SET situacao = 'concluido' WHERE id = %s", (e["id"],))
                continue
            m = modelo(con, e["modelo"])
            # o lote e o do dia: o primeiro convite do dia abre um lote novo
            ultimo = con.execute("SELECT coalesce(max(lote), 0) AS m FROM atendimento.envio_destinatarios WHERE envio_id = %s",
                                 (e["id"],)).fetchone()["m"]
            lote = ultimo if ja_hoje else ultimo + 1
            saiu = []
            for d in fila:
                # #1163: o teto do comprador, decidido AQUI, na hora de sair -- e quando se sabe o mes
                # #1175: a peca a mais (o dono marcou, no marketing) passa do teto
                if (not e["passa_do_teto"] and d["papel"] == "comprador"
                        and self.recebidas_no_mes(con, d["whatsapp"], agora) >= TETO_DO_COMPRADOR):
                    con.execute("UPDATE atendimento.envio_destinatarios SET situacao = 'teto_do_mes' WHERE id = %s",
                                (d["id"],))
                    continue
                self._mandar_um(con, saida, e, m, d, lote, agora)
                saiu.append(d)
                mandados += 1
            self._resumo_ao_representante(con, e, saiu)
        return mandados

    @staticmethod
    def recebidas_no_mes(con, numero: str, agora: datetime) -> int:
        """#1163: quantas mensagens de envio (convite ou peca, o que a Meta ACEITOU mandar: so essas
        tem `convite_em`) o numero recebeu no mes do calendario de `agora`, em Sao Paulo."""
        local = agora.astimezone(FUSO)
        ini = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fim = (ini + timedelta(days=32)).replace(day=1)
        return con.execute("""SELECT count(*) AS n FROM atendimento.envio_destinatarios
                               WHERE whatsapp = %s AND convite_em >= %s AND convite_em < %s""",
                           (numero, ini, fim)).fetchone()["n"]

    def _mensagem(self, e, m, d, para_nome, numero_resp):
        imagens = d["imagens"] if d["imagens"] is not None else e["imagens"]
        fontes = {"primeiro_nome": primeiro_nome(para_nome), "nome": para_nome, "assunto": e["assunto"],
                  "peca": e["peca"], "n_imagens": len(imagens), "responsavel": d["responsavel_nome"]}
        # o informativo ao comprador (043): "Nao quero mais receber" leva a mesma carga do "Nao quero" do
        # convite (a recusa), e o link e o da direta
        botoes = (["envio:%d:quero" % e["id"], "envio:%d:nao_quero" % e["id"]] if m["botao"] == "quero_nao_quero"
                  else ["envio:%d:nao_quero" % e["id"]] if m["botao"] == "parar_e_falar" else None)
        url = (codigo_falar(self._segredo, d["id"], copia=para_nome == d["responsavel_nome"])
               if m["botao"] in ("falar_responsavel", "parar_e_falar") else None)
        capa = (d["capa"] or e["capa"]) if m["cabecalho_imagem"] else None
        return parametros(m, fontes), capa, botoes, url, len(imagens)

    def _mandar_um(self, con, saida, e, m, d, lote, agora):
        corpo, capa, botoes, url, n = self._mensagem(e, m, d, d["nome"], d["responsavel_whatsapp"])
        try:
            w = saida.modelo(d["whatsapp"], m["nome"], m["idioma"], corpo, imagem=capa, botoes=botoes, url=url)
            con.execute("""UPDATE atendimento.envio_destinatarios
                              SET situacao = 'convidado', lote = %s, convite_wamid = %s, convite_em = %s,
                                  imagens_total = %s
                            WHERE id = %s""", (lote, w, agora, n if e["tipo"] == "material" else 0, d["id"]))
            con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo)
                           VALUES (%s, %s, 'modelo', %s)""", (w, d["whatsapp"], "%s %s" % (e["tipo"], e["peca"])))
        except Exception as falha:  # noqa: BLE001 -- o proximo da fila segue
            con.execute("""UPDATE atendimento.envio_destinatarios SET situacao = 'falhou', lote = %s, erro = %s
                            WHERE id = %s""", (lote, str(falha)[:300], d["id"]))

    #: o canal de quem RECEBE o resumo do lote. O dono e o flutuante ficam de fora: a copia por
    #: cliente ia ao dono (o marketing o poe como responsavel de toda revenda) e foi assim que as
    #: artes da Agro Real e da Agro Simil chegaram ao WhatsApp dele em 23/10. E o CORRETOR tambem
    #: (#1197, dono 29/10/2026): "corretor nao e representante; corretor nao recebe aviso nosso".
    CANAIS_DO_RESUMO = ("representante",)

    def _resumo_ao_representante(self, con, e, fila):
        """#1142 (dono, 26/10/2026): UM RESUMO POR LOTE ao representante, no lugar de uma copia por
        cliente ao responsavel.

        A copia era a unica coisa que avisava o representante de que o material saiu para os
        clientes dele -- e a tela Envios, que seria o outro caminho, roda em 127.0.0.1:8009 e ele
        nao a alcanca. Entao o aviso continua, com outra forma: uma mensagem por lote, sem imagem e
        sem botao, que o manda olhar o Relacionamento no ERP, que e a tela dele.

        NAO MANDA NADA AQUI: so enfileira em `atendimento.avisos`, e quem manda e `mandar_avisos`,
        pelo modelo `aviso_lote_do_representante` (UTILITY). Sem o modelo aprovado na Meta o aviso
        fica com `erro` preenchido -- ninguem recebe, e nada se perde."""
        por_responsavel: dict = {}
        for d in fila:
            if d["responsavel_canal"] not in self.CANAIS_DO_RESUMO or not d["responsavel_whatsapp"]:
                continue
            por_responsavel.setdefault(d["responsavel_whatsapp"], []).append(d)
        for numero, dele in por_responsavel.items():
            quantos = ("1 cliente seu" if len(dele) == 1 else "%d clientes seus" % len(dele))
            sobre = "|".join((primeiro_nome(dele[0]["responsavel_nome"]), quantos,
                              e["assunto"] or e["peca"] or "a nossa campanha"))
            con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                           VALUES ('lote_do_representante', %s, %s, %s)""",
                        (dele[0]["responsavel_nome"], numero, sobre))

    # -- as respostas ao convite --
    def tratar_toque(self, con, saida: Saida, entrada, agora: datetime) -> None:
        partes = (entrada.toque or "").split(":")
        if len(partes) != 3 or not partes[1].isdigit():
            return
        envio_id, acao = int(partes[1]), partes[2]
        numero = com_nove(entrada.pessoa.wa_id)
        d = con.execute("""SELECT * FROM atendimento.envio_destinatarios
                            WHERE envio_id = %s AND whatsapp = %s""", (envio_id, numero)).fetchone()
        # O guarda de `copia` FICA, mesmo depois de a copia acabar (#1142): ha mensagens com esse
        # botao na rua, e um toque delas ainda chega. Tirar o guarda nao ganharia nada e deixaria o
        # toque cair nos ramos de baixo.
        if acao == "copia" or not d or d["resposta"] in ("quero", "nao_quero"):
            return   # o toque do responsavel na copia, de quem nao estava na lista, ou o segundo toque
        tipo = "aceite" if acao == "quero" else "recusa" if acao == "nao_quero" else None
        if not tipo:
            return
        con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, bsuid, erp_codigo, tipo, wamid, envio_id)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (numero, entrada.pessoa.bsuid, d["erp_codigo"], tipo, entrada.wamid, envio_id))
        con.execute("""UPDATE atendimento.envio_destinatarios SET resposta = %s, resposta_em = %s WHERE id = %s""",
                    ("quero" if tipo == "aceite" else "nao_quero", agora, d["id"]))
        if tipo == "aceite":
            self._mandar_imagens(con, saida, d["id"], agora)
            return
        # recusa: sai de todo envio ainda por mandar, confirma, e o responsavel e avisado
        con.execute("""UPDATE atendimento.envio_destinatarios SET situacao = 'recusou_antes'
                        WHERE whatsapp = %s AND situacao = 'aguardando'""", (numero,))
        w = saida.texto(numero, "Tudo certo, você não vai mais receber estas mensagens. Obrigado pela atenção.")
        con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'texto', 'recusa confirmada')",
                    (w, numero))
        local = "%s · %s" % (d["erp_codigo"], d["cidade"] or "?")
        con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                       VALUES ('recusa', %s, %s, %s)""",
                    (d["responsavel_nome"], d["responsavel_whatsapp"],
                     "|".join([d["nome"], local, "https://wa.me/%s" % numero])))

    #: #1189 (dono, 28/10/2026): o cliente que recebeu um envio da carteira nos ultimos 30 dias e
    #: escreve ao numero da empresa nao cai no fluxo geral ("nao podemos ligar no fluxo geral"). O
    #: portao mora no motor (`motor.portao_do_cliente`); daqui saem quem e e a linha do representante.
    PORTAO_DIAS = 30

    def convidado_recente(self, con, wa_id: str, agora: datetime):
        """O destinatario do envio mais recente a este numero nos ultimos 30 dias, ou None."""
        return con.execute("""SELECT * FROM atendimento.envio_destinatarios
                               WHERE whatsapp = %s AND convite_em > %s
                               ORDER BY convite_em DESC LIMIT 1""",
                           (com_nove(wa_id), agora - timedelta(days=self.PORTAO_DIAS))).fetchone()

    @staticmethod
    def linha_do_representante(d) -> str:
        """"Quem cuida de voce ... e Fulano", com o endereco dele; vazio quando o envio nao tem o numero."""
        rep = so_digitos(d["responsavel_whatsapp"] or "")
        if not rep:
            return ""
        if not (d["responsavel_nome"] or "").strip():
            return "Quem cuida de você na Sementes Renascer fala direto por aqui: https://wa.me/%s" % rep
        return ("Quem cuida de você na Sementes Renascer é %s. Fale direto por aqui: https://wa.me/%s"
                % (nome_de_quem_atende(d["responsavel_nome"]), rep))

    def tratar_texto_de_convidado(self, con, entrada, agora) -> bool:
        """Quem recebeu um envio e ESCREVEU: o texto fica na linha dele na tela Envios."""
        numero = com_nove(entrada.pessoa.wa_id)
        d = con.execute("""SELECT d.id FROM atendimento.envio_destinatarios d
                            WHERE d.whatsapp = %s AND d.convite_em > %s AND d.resposta IS NULL
                            ORDER BY d.convite_em DESC LIMIT 1""", (numero, agora - JANELA)).fetchone()
        if not d or not entrada.texto:
            return False
        con.execute("""UPDATE atendimento.envio_destinatarios SET resposta = 'texto', resposta_texto = %s,
                              resposta_em = %s WHERE id = %s""", (entrada.texto[:500], agora, d["id"]))
        return True

    def _mandar_imagens(self, con, saida, dest_id, agora):
        d = con.execute("""SELECT d.*, e.imagens AS imagens_envio, e.peca FROM atendimento.envio_destinatarios d
                            JOIN atendimento.envios e ON e.id = d.envio_id WHERE d.id = %s""", (dest_id,)).fetchone()
        if not d["resposta_em"] or agora - d["resposta_em"] > JANELA:
            return   # fora da janela a mensagem livre nao sai; o dono decide (Envios)
        imagens = d["imagens"] if d["imagens"] is not None else d["imagens_envio"]
        for i in range(d["imagens_enviadas"], len(imagens)):
            try:
                w = saida.imagem(d["whatsapp"], imagens[i], d["peca"] if i == 0 else "")
                con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'imagem', %s)",
                            (w, d["whatsapp"], "imagem %d de %s" % (i + 1, d["peca"])))
                con.execute("UPDATE atendimento.envio_destinatarios SET imagens_enviadas = %s WHERE id = %s",
                            (i + 1, dest_id))
            except Exception as falha:  # noqa: BLE001 -- tenta de novo no proximo minuto, dentro da janela
                con.execute("UPDATE atendimento.envio_destinatarios SET erro = %s WHERE id = %s",
                            (str(falha)[:300], dest_id))
                return

    def mandar_imagens_pendentes(self, con, saida, agora):
        for d in con.execute("""SELECT id FROM atendimento.envio_destinatarios
                                 WHERE resposta = 'quero' AND imagens_enviadas < imagens_total
                                   AND resposta_em > %s""", (agora - JANELA,)).fetchall():
            self._mandar_imagens(con, saida, d["id"], agora)

    def mandar_avisos(self, con, saida, agora):
        if self._porteiro:
            self._porteiro_dos_avisos(con, saida, agora)
            return
        # Chave desligada: um modelo por aviso, como sempre. O guardado de quando ela estava ligada sai
        # aqui tambem (o ROLLBACK da spec); o nao visto, nao: "nao reenvia o que ficou nao visto".
        for a in con.execute("""SELECT * FROM atendimento.avisos WHERE enviado_em IS NULL AND erro = ''
                                   AND nao_visto_em IS NULL
                                 ORDER BY id LIMIT 20""").fetchall():
            m = modelo_do_uso(con, "aviso_" + a["tipo"])
            try:
                if not m:
                    raise RuntimeError("nenhum modelo cadastrado para aviso_%s" % a["tipo"])
                w = saida.modelo(a["para_whatsapp"], m["nome"], m["idioma"], _partes_do_aviso(m, a))
                con.execute("UPDATE atendimento.avisos SET enviado_em = %s, wamid = %s, como = 'modelo' WHERE id = %s",
                            (agora, w, a["id"]))
            except Exception as falha:  # noqa: BLE001
                con.execute("UPDATE atendimento.avisos SET erro = %s WHERE id = %s", (str(falha)[:300], a["id"]))

    def _porteiro_dos_avisos(self, con, saida, agora):
        # 1. os guardados: 7 dias sem toque viram nao visto; com a janela aberta (a pessoa escreveu,
        #    mesmo sem tocar Ver), saem como texto. Uma linha por numero: os guardados nao entram no
        #    lote de 20 de baixo, senao vinte guardados parariam a fila inteira.
        # (a reabertura saiu no instante em que guardou o primeiro: `min(guardado_em)` e a hora dela)
        for g in con.execute("""SELECT a.para_whatsapp, min(a.guardado_em) AS reaberto_em
                                  FROM atendimento.avisos a
                                 WHERE a.enviado_em IS NULL AND a.erro = '' AND a.guardado_em IS NOT NULL
                                   AND a.nao_visto_em IS NULL
                                 GROUP BY a.para_whatsapp""").fetchall():
            numero = g["para_whatsapp"]
            if janela_aberta(con, numero, agora):
                self.soltar_guardados(con, saida, numero, agora)
            elif agora - g["reaberto_em"] >= NAO_VISTO:
                con.execute("""UPDATE atendimento.avisos SET nao_visto_em = %s
                                WHERE para_whatsapp = %s AND enviado_em IS NULL AND erro = ''
                                  AND guardado_em IS NOT NULL AND nao_visto_em IS NULL""", (agora, numero))
        # 2. os novos
        for a in con.execute("""SELECT * FROM atendimento.avisos
                                 WHERE enviado_em IS NULL AND erro = '' AND guardado_em IS NULL
                                   AND nao_visto_em IS NULL
                                 ORDER BY id LIMIT 20""").fetchall():
            try:
                # um ponto de retorno por aviso: o erro de banco de um nao derruba a volta dos outros
                with con.transaction():
                    self._porteiro_de_um(con, saida, a, agora)
            except Exception as falha:  # noqa: BLE001 -- o proximo aviso segue; a linha diz o erro
                con.execute("UPDATE atendimento.avisos SET erro = %s WHERE id = %s", (str(falha)[:300], a["id"]))

    def _porteiro_de_um(self, con, saida, a, agora):
        numero = a["para_whatsapp"]
        if janela_aberta(con, numero, agora):
            self._aviso_como_texto(con, saida, a, agora)
            return
        pendente = con.execute("""SELECT reabertura_id FROM atendimento.avisos
                                   WHERE para_whatsapp = %s AND enviado_em IS NULL AND erro = ''
                                     AND guardado_em IS NOT NULL AND nao_visto_em IS NULL
                                   LIMIT 1""", (numero,)).fetchone()
        if pendente:   # ja ha reabertura sem toque: so se soma ao guardado
            con.execute("UPDATE atendimento.avisos SET guardado_em = %s, reabertura_id = %s WHERE id = %s",
                        (agora, pendente["reabertura_id"], a["id"]))
            return
        self._reabrir(con, saida, a, agora)

    def _aviso_como_texto(self, con, saida, a, agora):
        w = saida.texto(a["para_whatsapp"], texto_do_aviso(con, a))
        con.execute("""UPDATE atendimento.avisos SET enviado_em = %s, wamid = %s, como = 'texto' WHERE id = %s""",
                    (agora, w, a["id"]))
        con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'texto', %s)",
                    (w, a["para_whatsapp"], "aviso %s" % a["tipo"]))

    def _reabrir(self, con, saida, a, agora):
        """UMA reabertura ao numero, com o total que fica guardado (este aviso e os novos do mesmo numero
        ainda na fila, que na mesma volta se somam a ela pelo `pendente`). Falhou na Meta: o aviso fica
        com o erro, e nada se guarda."""
        m = modelo_do_uso(con, "reabertura")
        if not m:
            raise RuntimeError("nenhum modelo cadastrado para reabertura")
        numero = a["para_whatsapp"]
        quantos = 1 + con.execute("""SELECT count(*) AS n FROM atendimento.avisos
                                      WHERE para_whatsapp = %s AND id <> %s AND enviado_em IS NULL AND erro = ''
                                        AND guardado_em IS NULL AND nao_visto_em IS NULL""",
                                  (numero, a["id"])).fetchone()["n"]
        w = saida.modelo(numero, m["nome"], m["idioma"], parametros(m, {"n_avisos": quantos}),
                         botoes=["reabrir:%s" % numero])
        r = con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo)
                           VALUES (%s, %s, 'modelo', 'reabertura dos avisos') RETURNING id""", (w, numero)).fetchone()
        con.execute("UPDATE atendimento.avisos SET guardado_em = %s, reabertura_id = %s WHERE id = %s",
                    (agora, r["id"], a["id"]))

    def soltar_guardados(self, con, saida, numero: str, agora: datetime) -> int:
        """Os guardados do numero saem como texto, na ordem em que nasceram. O nao visto fica como esta."""
        feitos = 0
        for a in con.execute("""SELECT * FROM atendimento.avisos
                                 WHERE para_whatsapp = %s AND enviado_em IS NULL AND erro = ''
                                   AND guardado_em IS NOT NULL AND nao_visto_em IS NULL
                                 ORDER BY criado_em, id""", (numero,)).fetchall():
            try:
                with con.transaction():
                    self._aviso_como_texto(con, saida, a, agora)
                feitos += 1
            except Exception as falha:  # noqa: BLE001
                con.execute("UPDATE atendimento.avisos SET erro = %s WHERE id = %s", (str(falha)[:300], a["id"]))
        return feitos

    def tratar_reabrir(self, con, saida, entrada, agora: datetime) -> None:
        """O toque em Ver da reabertura (`reabrir:<numero>`). So vale do proprio numero da carga: um
        toque de outro numero nao solta o aviso de ninguem. Segundo toque: nada a soltar."""
        numero = (entrada.toque or "").partition(":")[2]
        if not numero or com_nove(entrada.pessoa.wa_id) != com_nove(numero):
            return
        self.soltar_guardados(con, saida, numero, agora)

    # -- os status da Meta para o envio --
    def aplicar_status(self, con, st: dict, novo: str, erro: str, agora: datetime) -> None:
        d = con.execute("SELECT id, entregue_em, lido_em FROM atendimento.envio_destinatarios WHERE convite_wamid = %s",
                        (st["id"],)).fetchone()
        if not d:
            return
        if novo == "entregue" and not d["entregue_em"]:
            con.execute("UPDATE atendimento.envio_destinatarios SET entregue_em = %s WHERE id = %s", (agora, d["id"]))
        elif novo == "lida":
            con.execute("""UPDATE atendimento.envio_destinatarios
                              SET lido_em = coalesce(lido_em, %s), entregue_em = coalesce(entregue_em, %s)
                            WHERE id = %s""", (agora, agora, d["id"]))
        elif novo == "falhou":
            codigos = {str(x.get("code")) for x in st.get("errors", [])}
            situacao = "nao_e_whatsapp" if codigos & NAO_E_WHATSAPP else "falhou"
            con.execute("UPDATE atendimento.envio_destinatarios SET situacao = %s, erro = %s WHERE id = %s",
                        (situacao, erro, d["id"]))
