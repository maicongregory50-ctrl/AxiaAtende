"""O CANAL DE CAMPO (#970, etapa A; spec C:\\AxiaMarketing\\docs\\specs\\2026-10-10-canal-de-campo-no-whatsapp.md).

Quem esta no cadastro do ERP como EQUIPE ou REPRESENTANTE (#969) manda uma foto ou um video ao
WhatsApp da Renascer. Com a chave `campo.ligado` ligada, o recepcionista:

1. baixa o arquivo da Meta (o mesmo token) para `campo_pasta\\AAAA-MM-DD\\<wamid>.<ext>` e grava a
   linha em `atendimento.material_de_campo`;
2. responde "Recebi." e faz UMA rodada de perguntas, sem travar (decisao 3 do dono): sem legenda,
   "O que esta acontecendo nessa foto?"; depois "E de hoje?" com dois botoes (Sim / Outra data, que
   pede "Qual dia?"). Varias midias do mesmo numero em 10 minutos sao UM grupo: uma rodada, e a
   legenda e a data valem para todas. Quem nao responde nao e cobrado de novo: a data vale como a
   do dia do envio, marcada "presumida", e o marketing leva assim mesmo depois de 10 minutos;
3. nao abre conversa de atendimento: a pessoa nao veio pedir atendimento.

O marketing BUSCA (decisao 4): as rotas `/campo/*` (rotas_campo.py, no processo das telas) oferecem
o que esta pronto e recebem de volta "buscado", "catalogado" e "foi ao ar". Os AVISOS a quem mandou
(`mandar_avisos`, no laco do minuto do recepcionista) saem SO dentro das 24 horas da ultima mensagem
dela, como mensagem de sessao; passou, fica "fora_da_janela" e nao se manda. Nunca por modelo.

Chave desligada ou numero fora de equipe/representante: nada daqui acontece, e a midia segue como
sempre (gravada em eventos_meta, a pessoa recebe o menu).
"""
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import agenda
from .saida import Opcao

FUSO = ZoneInfo("America/Sao_Paulo")
PAPEIS = ("equipe", "representante")
RODADA = timedelta(minutes=10)     # midias do mesmo numero dentro deste tempo sao um grupo
ESPERA_PALPITE = timedelta(minutes=2)   # a rodada espera o palpite do marketing ate aqui
JANELA = timedelta(hours=24)       # a janela da Meta para mensagem de sessao
EXTENSOES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
             "video/mp4": ".mp4", "video/3gpp": ".3gp", "video/quicktime": ".mov"}

RECEBI = "Recebi."
PALPITE = "Parece %s. É isso?"
BASTIDORES = {"campo-de-sementes": "campo de sementes", "colheita": "colheita", "beneficiamento": "beneficiamento",
              "controle-de-qualidade": "controle de qualidade", "entrega": "entrega"}
PERGUNTA_LEGENDA = "O que está acontecendo nessa foto?"
PERGUNTA_DATA = "É de hoje?"
PERGUNTA_QUAL_DIA = "Qual dia? (ex.: 09/10)"
ANOTADO = "Anotado. Obrigado!"
NAO_ENTENDI_DATA = "Não entendi a data; vale o dia do envio."
AVISO_CATALOGO = "Sua foto entrou no catálogo da Renascer. Obrigado!"
ANOTADO_FRASE = "Anotado. Se for para falar com alguém da empresa, me escreva *menu*."
PEDE_MENU = ("menu", "menu.", "atendimento", "opções", "opcoes", "ajuda", "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite")
AVISO_AR = "A sua foto virou o Stories do dia."


def ligado(con) -> bool:
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'campo.ligado'").fetchone()
    return bool(r and r["valor"] is True)


def quem_e(con, wa_id: str | None) -> dict | None:
    """O cadastro de quem mandou, se for equipe ou representante reconhecido (um cadastro so)."""
    q = agenda.reconhecer(con, wa_id)
    if not q or q.get("erp_cadastros") != 1:
        return None
    papel = next((p for p in PAPEIS if p in (q.get("erp_papeis") or [])), None)
    if not papel:
        return None
    return {"codigo": q["erp_codigo"], "papel": papel, "nome": q["erp_nome"] or ""}


def _dia(momento: datetime) -> date:
    return momento.astimezone(FUSO).date()


def _nome_seguro(wamid: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", wamid)[:120]


class Campo:
    """O canal, com a pasta onde a midia pousa. `tratar` do motor chama `receber` e `responder`."""

    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)

    # ── a chegada ────────────────────────────────────────────────────────────

    def receber(self, con, saida, e, agora: datetime) -> bool:
        """A midia de equipe/representante com a chave ligada. Devolve True quando o canal a tomou."""
        m = getattr(e, "midia", None)
        if m is None or not ligado(con):
            return False
        quem = quem_e(con, e.pessoa.wa_id)
        if not quem:
            return False
        grupo = con.execute("""SELECT * FROM atendimento.material_de_campo
                                WHERE wa_id = %s AND recebido_em > %s ORDER BY id""",
                            (e.pessoa.wa_id, agora - RODADA)).fetchall()
        primeiro = grupo[0] if grupo else None
        arquivo, erro = None, ""
        try:
            ext = EXTENSOES.get((m.mime or "").split(";")[0].strip(), ".mp4" if m.tipo == "video" else ".jpg")
            relativo = "%s/%s%s" % (_dia(agora).isoformat(), _nome_seguro(e.wamid), ext)
            saida.baixar(m.id, self.pasta / relativo)
            arquivo = relativo
        except Exception as falha:  # noqa: BLE001 -- a midia fica em eventos_meta; a linha diz o erro
            erro = ("%s: %s" % (type(falha).__name__, falha))[:300]
        legenda = (m.legenda or "").strip() or (primeiro["legenda"] if primeiro else "")
        if not legenda:   # a frase escrita ANTES da foto (decisao 13 do dono, 12/10/2026)
            frase = con.execute("""SELECT id, texto FROM atendimento.campo_frases
                                    WHERE wa_id = %s AND usada_em IS NULL AND recebido_em > %s
                                    ORDER BY id DESC LIMIT 1""", (e.pessoa.wa_id, agora - RODADA)).fetchone()
            if frase:
                legenda = frase["texto"]
                con.execute("UPDATE atendimento.campo_frases SET usada_em = %s WHERE id = %s", (agora, frase["id"]))
        linha = con.execute("""INSERT INTO atendimento.material_de_campo
                   (bsuid, wa_id, erp_codigo, erp_papel, erp_nome, wamid, tipo, mime, arquivo, legenda,
                    legenda_perguntada_em, data_dita, data_presumida, data_perguntada_em, recebido_em, erro)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (wamid) DO NOTHING RETURNING id""",
                            (e.pessoa.bsuid, e.pessoa.wa_id, quem["codigo"], quem["papel"], quem["nome"],
                             e.wamid, m.tipo, m.mime or "", arquivo, legenda,
                             primeiro["legenda_perguntada_em"] if primeiro else None,
                             primeiro["data_dita"] if primeiro else None,
                             primeiro["data_presumida"] if primeiro else False,
                             primeiro["data_perguntada_em"] if primeiro else None, agora, erro)).fetchone()
        if not linha:
            return True   # o mesmo aviso de novo: ja esta aqui
        if primeiro:
            # a rodada e do grupo: a pergunta pendente mora na primeira linha; nada a perguntar de novo
            return True
        saida.texto(e.pessoa.para, RECEBI)
        # A rodada de perguntas sai no laco do minuto (`fazer_perguntas`), quando o palpite do
        # marketing chegar ou passarem 2 minutos (emenda do dono, 11/10/2026).
        return True

    def fazer_perguntas(self, con, saida, agora: datetime) -> int:
        """A rodada de UMA vez por grupo: com o palpite ("Parece colheita de aveia. E isso?"), a
        pergunta da legenda se faltou, e "E de hoje?". Sai quando o palpite chegou ou passaram 2 min."""
        feitas = 0
        for r in con.execute("""SELECT * FROM atendimento.material_de_campo
                                 WHERE perguntas_em IS NULL AND recebido_em > %s
                                   AND (palpite_em IS NOT NULL OR recebido_em < %s)
                                 ORDER BY id""", (agora - JANELA, agora - ESPERA_PALPITE)).fetchall():
            # a lista veio de uma vez; a rodada da primeira linha ja pode ter marcado esta (o lote
            # de fotos do dono em 11/10 recebeu quatro rodadas por isso): le de novo antes de falar
            agora_mesmo = con.execute("SELECT perguntas_em FROM atendimento.material_de_campo WHERE id = %s",
                                      (r["id"],)).fetchone()
            if agora_mesmo is None or agora_mesmo["perguntas_em"] is not None:
                continue
            # o grupo e o das fotos dos 10 minutos ANTERIORES tambem: se alguma ja teve a rodada,
            # esta so herda a marca
            anterior = con.execute("""SELECT perguntas_em FROM atendimento.material_de_campo
                                       WHERE wa_id = %s AND id < %s AND recebido_em > %s AND perguntas_em IS NOT NULL
                                       ORDER BY id DESC LIMIT 1""", (r["wa_id"], r["id"], r["recebido_em"] - RODADA)).fetchone()
            if anterior:
                con.execute("UPDATE atendimento.material_de_campo SET perguntas_em = %s WHERE id = %s",
                            (anterior["perguntas_em"], r["id"]))
                continue
            grupo = self._grupo_de(con, r)
            para = r["wa_id"] or r["bsuid"]
            palpite = self._frase_do_palpite(r)
            if not (r["legenda"] or "").strip():
                saida.texto(para, ((palpite + " ") if palpite else "") + PERGUNTA_LEGENDA)
                con.execute("""UPDATE atendimento.material_de_campo SET pergunta_pendente = 'legenda',
                               legenda_perguntada_em = %s, perguntas_em = %s WHERE id = %s""", (agora, agora, r["id"]))
            else:
                if palpite:
                    saida.texto(para, palpite)
                con.execute("UPDATE atendimento.material_de_campo SET perguntas_em = %s WHERE id = %s", (agora, r["id"]))
                self._perguntar_data(con, saida, para, r["id"], agora)
            con.execute("""UPDATE atendimento.material_de_campo SET perguntas_em = %s
                            WHERE id = ANY(%s) AND perguntas_em IS NULL""", (agora, grupo))
            feitas += 1
        return feitas

    @staticmethod
    def _frase_do_palpite(r) -> str:
        b = BASTIDORES.get(r["palpite_bastidor"] or "", "")
        p = (r["palpite_produto"] or "").strip()
        if not b and not p:
            return ""
        return PALPITE % (("%s de %s" % (b, p.lower())) if b and p else (b or p.lower()))

    def _perguntar_data(self, con, saida, para, linha_id, agora):
        saida.botoes(para, PERGUNTA_DATA, [Opcao("campo:hoje:sim", "Sim"), Opcao("campo:hoje:outra", "Outra data")])
        con.execute("""UPDATE atendimento.material_de_campo SET pergunta_pendente = 'data',
                       data_perguntada_em = %s WHERE id = %s""", (agora, linha_id))

    # ── as respostas ─────────────────────────────────────────────────────────

    def _pendente(self, con, wa_id, agora):
        return con.execute("""SELECT * FROM atendimento.material_de_campo
                               WHERE wa_id = %s AND pergunta_pendente IS NOT NULL AND recebido_em > %s
                               ORDER BY id DESC LIMIT 1""", (wa_id, agora - JANELA)).fetchone()

    def _grupo_de(self, con, r):
        """As linhas do mesmo grupo (mesmo numero, 10 minutos a partir da primeira)."""
        return [x["id"] for x in con.execute(
            """SELECT id FROM atendimento.material_de_campo
                WHERE wa_id = %s AND recebido_em >= %s AND recebido_em < %s ORDER BY id""",
            (r["wa_id"], r["recebido_em"], r["recebido_em"] + RODADA)).fetchall()]

    def texto_de_interno(self, con, saida, e, agora: datetime) -> bool:
        """Decisao 13 do dono (12/10/2026): colaborador e representante so recebem o menu se
        pedirem. O texto deles, com o canal ligado, fica guardado como a frase da proxima foto; a
        primeira vez no dia, uma linha diz isso e ensina o "menu". True quando o canal o tomou."""
        texto = (e.texto or "").strip()
        if not texto or e.toque or not ligado(con):
            return False
        if texto.lower().strip(" !") in PEDE_MENU:
            return False   # pediu: o atendimento de sempre
        if not quem_e(con, e.pessoa.wa_id):
            return False
        avisado = con.execute("""SELECT 1 FROM atendimento.campo_frases
                                  WHERE wa_id = %s AND avisado AND recebido_em > %s""",
                              (e.pessoa.wa_id, agora - JANELA)).fetchone() is not None
        con.execute("""INSERT INTO atendimento.campo_frases (wa_id, texto, recebido_em, avisado)
                       VALUES (%s, %s, %s, %s)""", (e.pessoa.wa_id, texto[:500], agora, not avisado))
        if not avisado:
            saida.texto(e.pessoa.para, ANOTADO_FRASE)
        return True

    def responder(self, con, saida, e, agora: datetime) -> bool:
        """Texto ou toque `campo:*` de quem tem pergunta pendente. True quando o canal o tomou."""
        toque, texto = e.toque or "", (e.texto or "").strip()
        if not toque.startswith("campo:") and not texto:
            return False
        r = self._pendente(con, e.pessoa.wa_id, agora)
        if not r:
            # Texto solto logo depois da foto (a frase mandada em mensagem separada, o jeito mais
            # comum de celular): e a legenda do grupo, nao um pedido de atendimento -- sem menu.
            # Primeiro caso com o dono, 11/10/2026: "recebi o Recebi e o menu inicial".
            if texto and not toque:
                ids = [x["id"] for x in con.execute(
                    """SELECT id FROM atendimento.material_de_campo
                        WHERE wa_id = %s AND recebido_em > %s AND buscado_em IS NULL ORDER BY id""",
                    (e.pessoa.wa_id, agora - RODADA)).fetchall()]
                if ids:
                    con.execute("""UPDATE atendimento.material_de_campo
                                      SET legenda = CASE WHEN legenda = '' THEN %s ELSE legenda || ' · ' || %s END
                                    WHERE id = ANY(%s)""", (texto[:500], texto[:300], ids))
                    return True
            return toque.startswith("campo:")   # botao velho: engole, sem levar ao menu
        ids = self._grupo_de(con, r)
        if r["pergunta_pendente"] == "legenda":
            if not texto:
                return toque.startswith("campo:")
            con.execute("""UPDATE atendimento.material_de_campo SET legenda = %s, pergunta_pendente = NULL
                            WHERE id = ANY(%s) AND legenda = ''""", (texto[:500], ids))
            con.execute("UPDATE atendimento.material_de_campo SET pergunta_pendente = NULL WHERE id = %s", (r["id"],))
            self._perguntar_data(con, saida, e.pessoa.para, r["id"], agora)
            return True
        if r["pergunta_pendente"] == "data":
            if toque == "campo:hoje:sim":
                self._gravar_data(con, ids, r["id"], _dia(r["recebido_em"]), False)
                saida.texto(e.pessoa.para, ANOTADO)
                return True
            if toque == "campo:hoje:outra":
                saida.texto(e.pessoa.para, PERGUNTA_QUAL_DIA)
                con.execute("UPDATE atendimento.material_de_campo SET pergunta_pendente = 'qual_dia' WHERE id = %s", (r["id"],))
                return True
            dia = ler_data(texto, agora) if texto else None
            if dia:
                self._gravar_data(con, ids, r["id"], dia, False)
                saida.texto(e.pessoa.para, ANOTADO)
                return True
            return toque.startswith("campo:")   # texto solto com a data pendente: segue o seu caminho
        if r["pergunta_pendente"] == "qual_dia":
            dia = ler_data(texto, agora) if texto else None
            if dia:
                self._gravar_data(con, ids, r["id"], dia, False)
                saida.texto(e.pessoa.para, ANOTADO)
            else:
                self._gravar_data(con, ids, r["id"], _dia(r["recebido_em"]), True)
                saida.texto(e.pessoa.para, NAO_ENTENDI_DATA)
            return True
        return False

    def _gravar_data(self, con, ids, pendente_id, dia, presumida):
        con.execute("""UPDATE atendimento.material_de_campo SET data_dita = %s, data_presumida = %s
                        WHERE id = ANY(%s) AND data_dita IS NULL""", (dia, presumida, ids))
        con.execute("UPDATE atendimento.material_de_campo SET pergunta_pendente = NULL WHERE id = %s", (pendente_id,))

    # ── os avisos dentro da janela ───────────────────────────────────────────

    def mandar_avisos(self, con, saida, agora: datetime) -> int:
        """Quem mandou recebe "entrou no catalogo" e "virou o Stories" so dentro das 24 h da ultima
        mensagem dele; fora, fica anotado 'fora_da_janela' e nada sai (seria modelo pago)."""
        feitos = 0
        for campo, carimbo, mensagem, quando in (("aviso_catalogo", "aviso_catalogo_em", AVISO_CATALOGO, "catalogado_em"),
                                                  ("aviso_ar", "aviso_ar_em", AVISO_AR, "foi_ao_ar_em")):
            for r in con.execute("""SELECT id, wa_id, bsuid FROM atendimento.material_de_campo
                                     WHERE %s IS NOT NULL AND %s IS NULL ORDER BY id LIMIT 20"""
                                 % (quando, campo)).fetchall():
                ultima = ultima_mensagem_de(con, r["wa_id"])
                dentro = ultima is not None and agora - ultima < JANELA
                estado = "fora_da_janela"
                if dentro:
                    try:
                        saida.texto(r["wa_id"] or r["bsuid"], mensagem)
                        estado = "enviado"
                        feitos += 1
                    except Exception as falha:  # noqa: BLE001
                        con.execute("UPDATE atendimento.material_de_campo SET erro = %s WHERE id = %s",
                                    (("aviso: %s" % falha)[:300], r["id"]))
                        continue
                con.execute("UPDATE atendimento.material_de_campo SET %s = %%s, %s = %%s WHERE id = %%s"
                            % (campo, carimbo), (estado, agora, r["id"]))
        return feitos


def ultima_mensagem_de(con, wa_id: str | None) -> datetime | None:
    """Quando a pessoa falou pela ultima vez (a janela de 24 h da Meta conta dai)."""
    if not wa_id:
        return None
    r = con.execute("""SELECT max(recebido_em) AS em FROM atendimento.eventos_meta
                        WHERE tipo = 'mensagem' AND corpo->'msg'->>'from' = %s""", (wa_id,)).fetchone()
    return r["em"] if r else None


def ler_data(texto: str, agora: datetime) -> date | None:
    """"hoje", "ontem", DD/MM, DD/MM/AA, DD/MM/AAAA, DD-MM, AAAA-MM-DD. None quando nao e data."""
    t = (texto or "").strip().lower()
    hoje = _dia(agora)
    if t in ("hoje", "hj", "sim"):
        return hoje
    if t == "ontem":
        return hoje - timedelta(days=1)
    if t == "anteontem":
        return hoje - timedelta(days=2)
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        a, mes, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.search(r"(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?", t)
        if not m:
            return None
        d, mes = int(m.group(1)), int(m.group(2))
        a = int(m.group(3)) if m.group(3) else hoje.year
        if a < 100:
            a += 2000
    try:
        dia = date(a, mes, d)
    except ValueError:
        return None
    if dia > hoje + timedelta(days=1):   # DD/MM sem ano, de um mes a frente: era o ano passado
        dia = dia.replace(year=dia.year - 1) if not (m and m.lastindex and m.lastindex >= 3 and m.group(3)) else dia
    return dia


# ── o que o marketing busca (as rotas chamam) ───────────────────────────────

def pendentes(con, agora: datetime) -> list[dict]:
    """O material baixado que o marketing ainda nao levou e esta PRONTO: sem pergunta pendente, ou
    com mais de 10 minutos desde a ultima pergunta (quem nao respondeu nao e esperado)."""
    linhas = con.execute("""SELECT * FROM atendimento.material_de_campo
                             WHERE buscado_em IS NULL AND arquivo IS NOT NULL
                               AND ((perguntas_em IS NOT NULL AND pergunta_pendente IS NULL)
                                    OR coalesce(data_perguntada_em, legenda_perguntada_em, recebido_em) < %s)
                             ORDER BY id""", (agora - RODADA,)).fetchall()
    return [descrever(r) for r in linhas]


def descrever(r) -> dict:
    data = r["data_dita"] or _dia(r["recebido_em"])
    falta = []
    if not (r["legenda"] or "").strip():
        falta.append("legenda")
    if r["data_dita"] is None or r["data_presumida"]:
        falta.append("data")
    return {"id": r["id"], "contato": {"codigo": r["erp_codigo"], "papel": r["erp_papel"], "nome": r["erp_nome"]},
            "tipo": r["tipo"], "mime": r["mime"], "arquivo": r["arquivo"], "legenda": r["legenda"],
            "palpite": ({"bastidor": r["palpite_bastidor"], "produto": r["palpite_produto"]}
                        if r["palpite_em"] else None),
            "perguntado": r["perguntas_em"] is not None,
            "data": data.isoformat(), "data_presumida": r["data_dita"] is None or r["data_presumida"],
            "recebido_em": r["recebido_em"].isoformat(), "falta": falta,
            "lote": r["lote"], "atv": r["atv"], "buscado_em": r["buscado_em"].isoformat() if r["buscado_em"] else None}


def buscado(con, item_id: int, lote: str, linha: int | None, agora: datetime) -> dict | None:
    r = con.execute("SELECT * FROM atendimento.material_de_campo WHERE id = %s FOR UPDATE", (item_id,)).fetchone()
    if not r:
        return None
    if r["data_dita"] is None:   # ninguem respondeu: vale o dia do envio, marcado
        con.execute("""UPDATE atendimento.material_de_campo SET data_dita = %s, data_presumida = true
                        WHERE id = %s""", (_dia(r["recebido_em"]), item_id))
    con.execute("""UPDATE atendimento.material_de_campo SET buscado_em = coalesce(buscado_em, %s), lote = %s,
                   pergunta_pendente = NULL WHERE id = %s""", (agora, lote, item_id))
    return descrever(con.execute("SELECT * FROM atendimento.material_de_campo WHERE id = %s", (item_id,)).fetchone())


def palpite(con, item_id: int, bastidor: str | None, produto: str | None, agora: datetime) -> dict | None:
    """O que o marketing achou que a foto mostra (listas fechadas de la). Vazio tambem conta: a
    rodada de perguntas deixa de esperar."""
    n = con.execute("""UPDATE atendimento.material_de_campo SET palpite_bastidor = %s, palpite_produto = %s,
                       palpite_em = coalesce(palpite_em, %s) WHERE id = %s""",
                    ((bastidor or "").strip()[:40] or None, (produto or "").strip()[:80] or None, agora, item_id)).rowcount
    return {"id": item_id, "bastidor": bastidor, "produto": produto} if n else None


def novos(con) -> list[dict]:
    """O que chegou com arquivo e ainda nao teve palpite nem rodada: o marketing olha a foto."""
    return [descrever(l) for l in con.execute("""SELECT * FROM atendimento.material_de_campo
                WHERE palpite_em IS NULL AND perguntas_em IS NULL AND arquivo IS NOT NULL
                  AND recebido_em > now() - interval '1 day' ORDER BY id""").fetchall()]


def catalogado(con, item_id: int, atv: str, agora: datetime) -> dict | None:
    n = con.execute("""UPDATE atendimento.material_de_campo SET atv = %s, catalogado_em = coalesce(catalogado_em, %s)
                        WHERE id = %s""", (atv, agora, item_id)).rowcount
    return {"id": item_id, "atv": atv} if n else None


def foi_ao_ar(con, item_id: int, peca: str, agora: datetime) -> dict | None:
    n = con.execute("""UPDATE atendimento.material_de_campo SET peca = %s, foi_ao_ar_em = coalesce(foi_ao_ar_em, %s)
                        WHERE id = %s""", (peca, agora, item_id)).rowcount
    return {"id": item_id, "peca": peca} if n else None


def medidas(con, agora: datetime, dias: int = 7) -> dict:
    """A semana do canal: o que chegou, as lacunas e os avisos. Para a Caixa do marketing e a Recepcao."""
    desde = agora - timedelta(days=dias)
    r = con.execute("""SELECT count(*) AS recebidos,
                              count(*) FILTER (WHERE legenda = '') AS sem_legenda,
                              count(*) FILTER (WHERE data_dita IS NULL OR data_presumida) AS sem_data,
                              count(*) FILTER (WHERE buscado_em IS NOT NULL) AS buscados,
                              count(*) FILTER (WHERE catalogado_em IS NOT NULL) AS catalogados,
                              count(*) FILTER (WHERE aviso_catalogo = 'enviado' OR aviso_ar = 'enviado') AS avisos_enviados,
                              count(*) FILTER (WHERE aviso_catalogo = 'fora_da_janela' OR aviso_ar = 'fora_da_janela') AS avisos_fora,
                              count(*) FILTER (WHERE arquivo IS NULL) AS sem_arquivo
                         FROM atendimento.material_de_campo WHERE recebido_em > %s""", (desde,)).fetchone()
    return dict(r, ligado=ligado(con), dias=dias)
