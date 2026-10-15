"""O CANAL DE CAMPO (#970; spec C:\\AxiaMarketing\\docs\\specs\\2026-10-10-canal-de-campo-no-whatsapp.md,
decisoes 1 a 15 do dono).

Quem esta no cadastro do ERP como EQUIPE ou REPRESENTANTE (#969) manda uma foto ou um video ao
WhatsApp da Renascer. Com a chave `campo.ligado` ligada, o recepcionista:

1. baixa o arquivo da Meta (o mesmo token) para `campo_pasta\\AAAA-MM-DD\\<wamid>.<ext>`, grava a
   linha em `atendimento.material_de_campo` e responde "Recebi." (uma vez por GRUPO: as midias do
   mesmo numero em 10 minutos). Nao abre conversa de atendimento.
2. O ATENDENTE DE CAMPO tem um OBJETIVO, nao um roteiro (decisao 14, 12/10/2026): CLASSIFICAR a
   foto. O que ele precisa saber e curto e fechado: o BASTIDOR (campo de sementes, colheita,
   beneficiamento, controle de qualidade, entrega); se campo ou colheita, o PRODUTO e a FASE; e a
   DATA. Ele le o que a pessoa escreveu (a frase antes ou junto da foto) com a IA de texto da casa,
   com as listas como trava, e SO PERGUNTA O QUE FALTOU, uma por vez, no maximo tres perguntas de
   classificacao. AS LISTAS SAO DO AGENTE, NAO DE QUEM MANDA (decisao 15, 12/10/2026): as perguntas
   sao abertas ("o que a foto mostra?", "de que produto?", "em que fase?") e a IA encaixa a resposta;
   o que nao encaixa fica como legenda, a classificar para o dono. Cada pergunta e feita UMA vez.
   So a data e por botoes. O palpite de imagem do marketing (Gemini) e segunda opiniao: so molda a
   pergunta do bastidor ("Parece entrega. E isso?") quando a pessoa nao escreveu nada.
3. A foto ENTRA NO CATALOGO QUANDO A CONVERSA FECHA (decisao 15; o marketing busca `pendentes`, que
   so devolve grupo fechado): uma entrada so, ja classificada, e o aviso "entrou" vem depois do
   "Anotado". Quem nao responde e lembrado UMA vez, duas horas depois, dentro da janela de 24 h;
   depois disso o grupo fecha com o que tem, e o que ficou "a classificar" vai ao dono.
4. Colaborador e representante so recebem o menu se pedirem ("menu"); o texto deles e a frase da
   proxima foto (decisao 13). Reacao e silencio; figurinha e afins tambem, para eles.

Os AVISOS a quem mandou ("entrou no catalogo", "virou o Stories") saem so dentro das 24 h da ultima
mensagem dela. Nunca por modelo. Chave desligada ou numero de fora: nada daqui acontece.
"""
import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import agenda, internos
from .envio import com_nove
from .saida import Opcao

FUSO = ZoneInfo("America/Sao_Paulo")
PAPEIS = ("equipe", "representante")
RODADA = timedelta(minutes=10)         # midias do mesmo numero dentro deste tempo sao um grupo
ESPERA_PALPITE = timedelta(minutes=2)  # a primeira pergunta espera o palpite do marketing ate aqui
RETOMADA = timedelta(hours=2)          # sem resposta, lembra uma vez depois disto
JANELA = timedelta(hours=24)           # a janela da Meta para mensagem de sessao
MAX_PERGUNTAS = 3                      # perguntas de classificacao por grupo (a data nao conta)
EXTENSOES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
             "video/mp4": ".mp4", "video/3gpp": ".3gp", "video/quicktime": ".mov"}

BASTIDORES = {"campo-de-sementes": "Campo de sementes", "colheita": "Colheita", "beneficiamento": "Beneficiamento",
              "controle-de-qualidade": "Controle de qualidade", "entrega": "Entrega / carregamento"}
FASES = {"inicial": "Inicial (recém-nascida)", "vegetativo": "Vegetativo (verde)", "flor": "Flor / espigando",
         "pre-colheita": "Pré-colheita (madura)", "semente": "Semente (grão de perto)"}
COM_PRODUTO = ("campo-de-sementes", "colheita")

RECEBI = "Recebi."
PERGUNTA_LEGENDA = "O que está acontecendo nessa foto?"
PERGUNTA_BASTIDOR = ("Não entendi bem o que a foto mostra: é a lavoura em pé, a colheita, o beneficiamento, "
                     "a qualidade ou uma entrega? Me conta em uma linha.")
PERGUNTA_PALPITE = "Parece %s. É isso?"
PERGUNTA_PRODUTO = "De que produto é? (o nome como está na embalagem)"
PERGUNTA_FASE = "Em que fase está a lavoura? (recém-nascida, verde, florindo, madura ou já em semente)"
PERGUNTA_DATA = "É de hoje?"
PERGUNTA_QUAL_DIA = "Qual dia? (ex.: 09/10)"
RETOMANDO = "Ainda sobre a foto de há pouco: "
ANOTADO = "Anotado. Obrigado!"
NAO_ENTENDI_DATA = "Não entendi a data; vale o dia do envio."
NAO_ACHEI_PRODUTO = "Não achei esse produto na lista; deixo para o marketing conferir."
AVISO_CATALOGO = "Sua foto entrou no catálogo da Renascer. Obrigado!"
AVISO_AR = "A sua foto virou o Stories do dia."
ANOTADO_FRASE = "Anotado. Se for para falar com alguém da empresa, me escreva *menu*."
# A lista mudou de lugar no #1031: mora em internos.py, porque o motor tambem a pergunta.
PEDE_MENU = internos.PEDE_MENU


def ligado(con) -> bool:
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'campo.ligado'").fetchone()
    return bool(r and r["valor"] is True)


def produtos(con) -> list[str]:
    """A lista do portfolio do marketing (ajuste `campo.produtos`, mantida pelo publicador de la)."""
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'campo.produtos'").fetchone()
    return [str(p) for p in (r["valor"] if r and isinstance(r["valor"], list) else [])]


def guardar_produtos(con, lista: list[str]) -> int:
    con.execute("""INSERT INTO atendimento.ajustes (chave, valor) VALUES ('campo.produtos', %s::jsonb)
                   ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor, atualizado_em = now()""",
                (json.dumps([str(p)[:80] for p in lista][:200], ensure_ascii=False),))
    return len(lista)


def quem_e(con, wa_id: str | None) -> dict | None:
    """Quem e da casa. A REGRA MUDOU DE LUGAR, nao de conteudo (#1031): ela mora em
    `backend/internos.py`, porque ser interno deixou de depender da chave do canal de fotos.

    Esta funcao fica como atalho de quem ja a chamava daqui -- uma verdade so, em um lugar so."""
    return internos.quem_e(con, wa_id)


def _dia(momento: datetime) -> date:
    return momento.astimezone(FUSO).date()


def _nome_seguro(wamid: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", wamid)[:120]


def _sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower().strip()


def casar_produto(texto: str, lista: list[str]) -> str | None:
    """O produto que a pessoa escreveu, casado com a lista: igual sem acento, ou um nome da lista
    contido no texto (o mais longo ganha: "aveia preta iapar61" vence "aveia preta"), ou o texto
    contido num nome so."""
    t = _sem_acento(texto)
    if not t:
        return None
    for p in lista:
        if _sem_acento(p) == t:
            return p
    contidos = [p for p in lista if _sem_acento(p) in t]
    if contidos:
        return max(contidos, key=len)
    dentro = [p for p in lista if len(t) >= 4 and t in _sem_acento(p)]
    return dentro[0] if len(dentro) == 1 else None


class Campo:
    """O canal, com a pasta onde a midia pousa e a IA de texto. `tratar` do motor chama `receber`,
    `responder` e `texto_de_interno`; o laco do minuto chama `fazer_perguntas` e `mandar_avisos`."""

    def __init__(self, pasta: Path, ia=None):
        self.pasta = Path(pasta)
        self.ia = ia

    # ── o que a OlivIA manda fica em `enviadas` (#981, 13/10/2026) ────────────
    # A primeira leitura da sessao mostrou a conversa SEM as falas dela: o motor registra o que
    # manda (motor._registrar), o canal de campo nao registrava. Sem isto o leitor nao reconstroi
    # o dialogo, e o status da Meta (entregue, lida) nao tem onde pousar.

    def _registrar(self, con, para, tipo: str, resumo: str, wamid) -> None:
        con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (wamid) DO NOTHING""", (wamid, para, tipo, (resumo or "")[:200]))

    def _texto(self, con, saida, para, texto: str):
        w = saida.texto(para, texto)
        self._registrar(con, para, "texto", texto, w)
        return w

    def _botoes(self, con, saida, para, texto: str, opcoes):
        w = saida.botoes(para, texto, opcoes)
        self._registrar(con, para, "botoes", texto, w)
        return w

    def _lista(self, con, saida, para, texto: str, botao: str, opcoes):
        w = saida.lista(para, texto, botao, opcoes)
        self._registrar(con, para, "lista", texto, w)
        return w

    # ── a chegada ────────────────────────────────────────────────────────────

    def receber(self, con, saida, e, agora: datetime) -> bool:
        """A midia de equipe/representante com a chave ligada. Devolve True quando o canal a tomou."""
        m = getattr(e, "midia", None)
        if m is None or not ligado(con):
            return False
        quem = quem_e(con, e.pessoa.wa_id)
        if not quem:
            return False
        lider = self._lider(con, e.pessoa.wa_id, agora)
        arquivo, erro = None, ""
        try:
            ext = EXTENSOES.get((m.mime or "").split(";")[0].strip(), ".mp4" if m.tipo == "video" else ".jpg")
            relativo = "%s/%s%s" % (_dia(agora).isoformat(), _nome_seguro(e.wamid), ext)
            saida.baixar(m.id, self.pasta / relativo)
            arquivo = relativo
        except Exception as falha:  # noqa: BLE001 -- a midia fica em eventos_meta; a linha diz o erro
            erro = ("%s: %s" % (type(falha).__name__, falha))[:300]
        legenda = (m.legenda or "").strip() or (lider["legenda"] if lider else "")
        if not legenda:   # a frase escrita ANTES da foto (decisao 13)
            frase = con.execute("""SELECT id, texto FROM atendimento.campo_frases
                                    WHERE wa_id = %s AND usada_em IS NULL AND recebido_em > %s
                                    ORDER BY id DESC LIMIT 1""", (e.pessoa.wa_id, agora - RODADA)).fetchone()
            if frase:
                legenda = frase["texto"]
                con.execute("UPDATE atendimento.campo_frases SET usada_em = %s WHERE id = %s", (agora, frase["id"]))
        herda = {k: (lider[k] if lider else None) for k in
                 ("classe_bastidor", "classe_produto", "classe_fase", "data_dita", "lida_em", "perguntas_em", "fechado_em",
                  "safra_dita")}
        # a foto que chega ao grupo ja fechado entra com ele (fechado_em herdado); a que chega ao
        # grupo aberto espera a conversa, como as outras
        linha = con.execute("""INSERT INTO atendimento.material_de_campo
                   (bsuid, wa_id, erp_codigo, erp_papel, erp_nome, wamid, tipo, mime, arquivo, legenda, recebido_em, erro,
                    classe_bastidor, classe_produto, classe_fase, data_dita, data_presumida, lida_em, perguntas_em, fechado_em,
                    grupo_id, safra_dita)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (wamid) DO NOTHING RETURNING id""",
                            (e.pessoa.bsuid, e.pessoa.wa_id, quem["codigo"], quem["papel"], quem["nome"],
                             e.wamid, m.tipo, m.mime or "", arquivo, legenda, agora, erro,
                             herda["classe_bastidor"], herda["classe_produto"], herda["classe_fase"], herda["data_dita"],
                             bool(lider and lider["data_presumida"]), herda["lida_em"], herda["perguntas_em"],
                             herda["fechado_em"], lider["grupo_id"] if lider else 0, herda["safra_dita"])).fetchone()
        if not linha:
            return True   # o mesmo aviso de novo: ja esta aqui
        if not lider:   # a primeira do grupo: o grupo e ela
            con.execute("UPDATE atendimento.material_de_campo SET grupo_id = id WHERE id = %s", (linha["id"],))
        if lider:
            # o grupo ja tem lider: a conversa e dele; esta so acompanha. Se a legenda chegou agora
            # (a foto nova trouxe caption) e o lider nao tinha, vale para o grupo
            if legenda and not (lider["legenda"] or "").strip():
                con.execute("UPDATE atendimento.material_de_campo SET legenda = %s WHERE id = ANY(%s) AND legenda = ''",
                            (legenda, self._grupo_de(con, lider)))
                self._ler(con, lider["id"], legenda, agora)
            return True
        self._texto(con, saida, e.pessoa.para, RECEBI)
        if legenda:
            self._ler(con, linha["id"], legenda, agora)
        # a primeira pergunta sai no laco do minuto (`fazer_perguntas`): da tempo de o palpite de
        # imagem chegar (ate 2 min) e de mais fotos do mesmo grupo entrarem
        return True

    def _lider(self, con, wa_id, agora):
        """O lider da conversa em curso deste numero: UMA conversa aberta por pessoa (12/10/2026, 14:25:
        cinco lembrancas de uma vez, uma por grupo de 10 min). Primeiro a conversa ABERTA (sem fechar,
        dentro das 24 h), mesmo que a ultima foto tenha mais de 10 min; senao, o grupo dos ultimos 10
        minutos (fechado: a foto entra com ele)."""
        aberta = con.execute("""SELECT l.* FROM atendimento.material_de_campo l
                                 WHERE l.wa_id = %s AND l.id = l.grupo_id AND l.fechado_em IS NULL
                                   AND l.desistiu_em IS NULL AND l.recebido_em > %s
                                 ORDER BY l.id DESC LIMIT 1""", (wa_id, agora - JANELA)).fetchone()
        if aberta:
            return aberta
        r = con.execute("""SELECT * FROM atendimento.material_de_campo
                            WHERE wa_id = %s AND recebido_em > %s ORDER BY id LIMIT 1""",
                        (wa_id, agora - RODADA)).fetchone()
        return self._linha(con, r["grupo_id"]) if r else None

    def _grupo_de(self, con, r) -> list[int]:
        """As linhas da mesma conversa (`grupo_id`). `r` pode ser qualquer linha do grupo."""
        return [x["id"] for x in con.execute(
            "SELECT id FROM atendimento.material_de_campo WHERE grupo_id = %s ORDER BY id", (r["grupo_id"],)).fetchall()]

    def _linha(self, con, id_):
        return con.execute("SELECT * FROM atendimento.material_de_campo WHERE id = %s", (id_,)).fetchone()

    # ── a leitura da frase ───────────────────────────────────────────────────

    def _ler(self, con, lider_id: int, texto: str, agora: datetime) -> dict | None:
        """A IA de texto le a frase e preenche o que der, so onde ainda nao ha resposta da pessoa.
        Sem IA, ao menos o produto e casado com a lista."""
        lido = None
        if self.ia is not None and hasattr(self.ia, "ler_campo"):
            try:
                lido = self.ia.ler_campo(texto, produtos(con))
            except Exception:  # noqa: BLE001 -- sem leitura, o atendente pergunta
                lido = None
        if not lido:
            p = casar_produto(texto, produtos(con))
            lido = {"bastidor": None, "produto": p, "fase": None} if p else None
        ids = self._grupo_de(con, self._linha(con, lider_id))
        if lido:
            con.execute("""UPDATE atendimento.material_de_campo
                              SET classe_bastidor = coalesce(classe_bastidor, %s),
                                  classe_produto = coalesce(classe_produto, %s),
                                  classe_fase = coalesce(classe_fase, %s), lida_em = %s
                            WHERE id = ANY(%s)""", (lido.get("bastidor"), lido.get("produto"), lido.get("fase"), agora, ids))
        else:
            con.execute("UPDATE atendimento.material_de_campo SET lida_em = %s WHERE id = ANY(%s)", (agora, ids))
        return lido

    # ── o atendente: o que falta, uma pergunta por vez ───────────────────────

    def fazer_perguntas(self, con, saida, agora: datetime) -> int:
        """Para cada grupo em aberto: a proxima pergunta (so o que falta), a retomada de quem nao
        respondeu (uma vez, 2 h depois) e a desistencia (fecha com o que tem)."""
        feitas = 0
        lideres = con.execute("""SELECT m.id FROM atendimento.material_de_campo m
                                  WHERE m.id = m.grupo_id AND m.fechado_em IS NULL AND m.desistiu_em IS NULL
                                    AND m.recebido_em > %s
                                    AND EXISTS (SELECT 1 FROM atendimento.material_de_campo a
                                                 WHERE a.grupo_id = m.id AND a.arquivo IS NOT NULL)
                                  ORDER BY m.id""", (agora - JANELA,)).fetchall()
        falados = set()   # uma mensagem por pessoa por volta: nunca a rajada de 14:25
        for x in lideres:
            r = self._linha(con, x["id"])
            if r is None or r["fechado_em"] or r["desistiu_em"] or r["wa_id"] in falados:
                continue
            falados.add(r["wa_id"])
            if r["pergunta_pendente"]:
                if r["retomar_em"] and agora >= r["retomar_em"]:
                    if not r["retomada"] and self._dentro_da_janela(con, r, agora):
                        self._perguntar(con, saida, r, agora, r["pergunta_pendente"], retomando=True)
                        feitas += 1
                    else:
                        self._desistir(con, r, agora)
                continue
            if r["perguntas_em"] is None and r["palpite_em"] is None and agora - r["recebido_em"] < ESPERA_PALPITE:
                continue   # a primeira pergunta espera o palpite de imagem ate 2 min
            if self._perguntar_proxima(con, saida, r, agora):
                feitas += 1
        return feitas

    @staticmethod
    def _falta(r) -> str | None:
        """O que ainda falta para classificar: a proxima pergunta, ou None quando esta fechado. Cada
        pergunta e feita UMA vez (decisao 15): a resposta que a IA nao encaixou fica na legenda."""
        feitas = r["perguntas_feitas"] or []
        legenda = (r["legenda"] or "").strip()
        if r["classe_bastidor"] is None:
            if not legenda and r["palpite_bastidor"] in BASTIDORES and "bastidor" not in feitas:
                return "bastidor"   # "Parece X. E isso?": so quando a pessoa nao escreveu nada
            if not legenda and "legenda" not in feitas:
                return "legenda"
            if legenda and "bastidor" not in feitas:
                return "bastidor"   # escreveu, mas a IA nao encaixou: pergunta aberta, uma vez
        if r["classe_bastidor"] in COM_PRODUTO and r["classe_produto"] is None and "produto" not in feitas:
            return "produto"
        if r["classe_bastidor"] == "campo-de-sementes" and r["classe_produto"] and r["classe_fase"] is None \
                and "fase" not in feitas:
            return "fase"
        if r["data_dita"] is None and r["safra_dita"] is None and "data" not in feitas:
            return "data"
        return None

    def _perguntar_proxima(self, con, saida, r, agora: datetime) -> bool:
        """Faz a proxima pergunta do grupo, respeitando o limite; sem nada a perguntar, fecha."""
        falta = self._falta(r)
        if falta and falta != "data" and r["pergunta_n"] >= MAX_PERGUNTAS:
            falta = "data" if r["data_dita"] is None else None   # estourou: so a data ainda vale
        if falta is None:
            self._fechar(con, r, agora)
            return False
        self._perguntar(con, saida, r, agora, falta)
        return True

    def _perguntar(self, con, saida, r, agora: datetime, qual: str, retomando: bool = False) -> None:
        para = r["wa_id"] or r["bsuid"]
        prefixo = RETOMANDO if retomando else ""
        if qual == "legenda":
            self._texto(con, saida, para, prefixo + PERGUNTA_LEGENDA)
        elif qual == "bastidor":
            if r["palpite_bastidor"] in BASTIDORES and not (r["legenda"] or "").strip() and not retomando and not r["retomada"]:
                self._botoes(con, saida, para, PERGUNTA_PALPITE % BASTIDORES[r["palpite_bastidor"]].lower(),
                             [Opcao("campo:bastidor:" + r["palpite_bastidor"], "Sim"), Opcao("campo:bastidor:outra", "Outra coisa")])
            else:
                self._texto(con, saida, para, prefixo + PERGUNTA_BASTIDOR)
        elif qual == "produto":
            self._texto(con, saida, para, prefixo + PERGUNTA_PRODUTO)
        elif qual == "fase":
            self._texto(con, saida, para, prefixo + PERGUNTA_FASE)
        elif qual == "data":
            self._botoes(con, saida, para, prefixo + PERGUNTA_DATA, [Opcao("campo:hoje:sim", "Sim"), Opcao("campo:hoje:outra", "Outra data")])
        elif qual == "qual_dia":
            self._texto(con, saida, para, prefixo + PERGUNTA_QUAL_DIA)
        n = r["pergunta_n"] + (0 if retomando or qual in ("data", "qual_dia") else 1)
        con.execute("""UPDATE atendimento.material_de_campo
                          SET pergunta_pendente = %s, perguntas_em = coalesce(perguntas_em, %s), pergunta_n = %s,
                              retomar_em = %s, retomada = %s,
                              perguntas_feitas = CASE WHEN %s = ANY(perguntas_feitas) THEN perguntas_feitas
                                                      ELSE array_append(perguntas_feitas, %s) END,
                              legenda_perguntada_em = CASE WHEN %s = 'legenda' THEN %s ELSE legenda_perguntada_em END,
                              data_perguntada_em = CASE WHEN %s IN ('data', 'qual_dia') THEN %s ELSE data_perguntada_em END
                        WHERE id = %s""",
                    (qual, agora, n, agora + RETOMADA, bool(retomando or r["retomada"]), qual, qual, qual, agora, qual, agora, r["id"]))
        con.execute("""UPDATE atendimento.material_de_campo SET perguntas_em = coalesce(perguntas_em, %s)
                        WHERE id = ANY(%s)""", (agora, self._grupo_de(con, r)))

    def _dentro_da_janela(self, con, r, agora: datetime) -> bool:
        ultima = ultima_mensagem_de(con, r["wa_id"])
        return ultima is not None and agora - ultima < JANELA

    def _fechar(self, con, r, agora: datetime) -> None:
        """O grupo fecha com o que tem: a classe e a data valem para todas as fotos dele."""
        ids = self._grupo_de(con, r)
        # o dia so e presumido quando nao ha dia dito NEM safra dita (#982: com a safra, a foto entra sem dia)
        con.execute("""UPDATE atendimento.material_de_campo
                          SET classe_bastidor = %s, classe_produto = %s, classe_fase = %s,
                              data_presumida = CASE WHEN data_dita IS NULL AND safra_dita IS NULL THEN true ELSE data_presumida END,
                              data_dita = CASE WHEN data_dita IS NULL AND safra_dita IS NULL THEN %s ELSE data_dita END,
                              fechado_em = %s, pergunta_pendente = NULL, retomar_em = NULL
                        WHERE id = ANY(%s)""",
                    (r["classe_bastidor"], r["classe_produto"], r["classe_fase"], _dia(r["recebido_em"]), agora, ids))

    def _desistir(self, con, r, agora: datetime) -> None:
        con.execute("UPDATE atendimento.material_de_campo SET desistiu_em = %s WHERE id = ANY(%s)",
                    (agora, self._grupo_de(con, r)))
        self._fechar(con, r, agora)

    # ── as respostas ─────────────────────────────────────────────────────────

    def _pendente(self, con, wa_id, agora):
        return con.execute("""SELECT * FROM atendimento.material_de_campo
                               WHERE wa_id = %s AND pergunta_pendente IS NOT NULL AND recebido_em > %s
                               ORDER BY id DESC LIMIT 1""", (wa_id, agora - JANELA)).fetchone()

    def _gravar(self, con, r, **campos) -> dict:
        """Grava a resposta no grupo inteiro e limpa a pergunta pendente; devolve o lider atualizado."""
        ids = self._grupo_de(con, r)
        for k, v in campos.items():
            con.execute("UPDATE atendimento.material_de_campo SET %s = %%s WHERE id = ANY(%%s)" % k, (v, ids))
        con.execute("UPDATE atendimento.material_de_campo SET pergunta_pendente = NULL, retomar_em = NULL WHERE id = ANY(%s)", (ids,))
        return self._linha(con, r["id"])

    def responder(self, con, saida, e, agora: datetime) -> bool:
        """Texto ou toque `campo:*` de quem tem pergunta pendente. True quando o canal o tomou."""
        toque, texto = e.toque or "", (e.texto or "").strip()
        if not toque.startswith("campo:") and not texto:
            return False
        r = self._pendente(con, e.pessoa.wa_id, agora)
        if not r:
            # Texto solto logo depois da foto, sem pergunta aberta: e a legenda do grupo, e e lido
            if texto and not toque:
                lider = self._lider(con, e.pessoa.wa_id, agora)
                if lider and lider["fechado_em"] is None:
                    ids = self._grupo_de(con, lider)
                    con.execute("""UPDATE atendimento.material_de_campo
                                      SET legenda = CASE WHEN legenda = '' THEN %s ELSE legenda || ' · ' || %s END
                                    WHERE id = ANY(%s)""", (texto[:500], texto[:300], ids))
                    self._ler(con, lider["id"], texto, agora)
                    return True
            return toque.startswith("campo:")   # botao velho: engole, sem levar ao menu
        q = r["pergunta_pendente"]
        if q == "legenda":
            if not texto:
                return toque.startswith("campo:")
            ids = self._grupo_de(con, r)
            con.execute("UPDATE atendimento.material_de_campo SET legenda = %s WHERE id = ANY(%s) AND legenda = ''", (texto[:500], ids))
            r = self._gravar(con, r)
            self._ler(con, r["id"], texto, agora)
            self._perguntar_proxima(con, saida, self._linha(con, r["id"]), agora)
            return True
        if q == "bastidor":
            if toque == "campo:bastidor:outra":   # o palpite errou: a pergunta aberta
                r = self._gravar(con, r)
                self._perguntar(con, saida, r, agora, "legenda")
                return True
            if toque.startswith("campo:bastidor:") and toque[15:] in BASTIDORES:
                r = self._gravar(con, r, classe_bastidor=toque[15:])
                self._perguntar_proxima(con, saida, r, agora)
                return True
            if texto:   # a resposta aberta: a IA encaixa; o que nao encaixa fica na legenda
                ids = self._grupo_de(con, r)
                con.execute("""UPDATE atendimento.material_de_campo
                                  SET legenda = CASE WHEN legenda = '' THEN %s ELSE legenda || ' · ' || %s END
                                WHERE id = ANY(%s)""", (texto[:500], texto[:300], ids))
                r = self._gravar(con, r)
                self._ler(con, r["id"], texto, agora)
                self._perguntar_proxima(con, saida, self._linha(con, r["id"]), agora)
                return True
            return toque.startswith("campo:")
        if q == "produto":
            if not texto:
                return toque.startswith("campo:")
            p = casar_produto(texto, produtos(con))
            if not p and self.ia is not None and hasattr(self.ia, "ler_campo"):
                try:
                    p = (self.ia.ler_campo(texto, produtos(con)) or {}).get("produto")
                except Exception:  # noqa: BLE001
                    p = None
            if not p:
                self._texto(con, saida, e.pessoa.para, NAO_ACHEI_PRODUTO)
            r = self._gravar(con, r, classe_produto=p)
            self._perguntar_proxima(con, saida, r, agora)
            return True
        if q == "fase":
            if toque.startswith("campo:fase:") and toque[11:] in FASES:
                r = self._gravar(con, r, classe_fase=toque[11:])
                self._perguntar_proxima(con, saida, r, agora)
                return True
            if texto:   # "madura", "florindo", "ta verde ainda": a IA encaixa; sem encaixe, fica sem fase
                fase = None
                if self.ia is not None and hasattr(self.ia, "ler_campo"):
                    try:
                        fase = (self.ia.ler_campo(texto, produtos(con)) or {}).get("fase")
                    except Exception:  # noqa: BLE001
                        fase = None
                r = self._gravar(con, r, classe_fase=fase if fase in FASES else None)
                self._perguntar_proxima(con, saida, r, agora)
                return True
            return toque.startswith("campo:")
        if q == "data":
            if toque == "campo:hoje:sim":
                r = self._gravar(con, r, data_dita=_dia(r["recebido_em"]), data_presumida=False)
                self._texto(con, saida, e.pessoa.para, ANOTADO)
                self._perguntar_proxima(con, saida, r, agora)
                return True
            if toque == "campo:hoje:outra":
                self._perguntar(con, saida, r, agora, "qual_dia")
                return True
            dia = ler_data(texto, agora) if texto else None
            if dia:
                r = self._gravar(con, r, data_dita=dia, data_presumida=False)
                self._texto(con, saida, e.pessoa.para, ANOTADO)
                self._perguntar_proxima(con, saida, r, agora)
                return True
            if texto:
                con.execute("""UPDATE atendimento.material_de_campo
                                  SET legenda = CASE WHEN legenda = '' THEN %s ELSE legenda || ' · ' || %s END
                                WHERE id = ANY(%s)""", (texto[:500], texto[:300], self._grupo_de(con, r)))
                self._ler(con, r["id"], texto, agora)
                safra = ler_safra(texto)
                if safra:
                    # "safra 2025", "2023", "24/25": e a resposta da pessoa a data, SEM dia (#982, 13/10/2026):
                    # a safra dita vai ao catalogo e o dia NAO e presumido (a foto entra sem dia)
                    r = self._gravar(con, r, safra_dita=safra, data_presumida=False)
                    self._texto(con, saida, e.pessoa.para, ANOTADO)
                    self._perguntar_proxima(con, saida, r, agora)
                    return True
                return True   # outro texto qualquer: fica na foto, em silencio; a data continua aberta
            return toque.startswith("campo:")
        if q == "qual_dia":
            dia = ler_data(texto, agora) if texto else None
            if dia:
                r = self._gravar(con, r, data_dita=dia, data_presumida=False)
                self._texto(con, saida, e.pessoa.para, ANOTADO)
            else:
                r = self._gravar(con, r, data_dita=_dia(r["recebido_em"]), data_presumida=True)
                self._texto(con, saida, e.pessoa.para, NAO_ENTENDI_DATA)
            self._perguntar_proxima(con, saida, r, agora)
            return True
        return False

    # ── o texto de quem e da casa ────────────────────────────────────────────

    @staticmethod
    def e_interno(con, wa_id: str | None) -> bool:
        """Equipe ou representante reconhecido, com o canal DE FOTOS ligado.

        #1031: continua exigindo `campo.ligado` de proposito -- o canal de fotos e deste modulo, e
        esta pergunta e "pode mandar foto?". Quem pergunta "e da casa?" usa `internos.e_interno`,
        que confere a chave `interno.ligado`."""
        return ligado(con) and quem_e(con, wa_id) is not None

    def texto_de_interno(self, con, saida, e, agora: datetime) -> bool:
        """Decisao 13: colaborador e representante so recebem o menu se pedirem. O texto deles, com
        o canal ligado, e a frase da proxima foto; a primeira vez no dia, uma linha diz isso."""
        texto = (e.texto or "").strip()
        if not texto or e.toque or not ligado(con):
            return False
        if internos.pede_menu(texto):
            return False   # pediu: o atendimento de sempre
        if not quem_e(con, e.pessoa.wa_id):
            return False
        avisado = con.execute("""SELECT 1 FROM atendimento.campo_frases
                                  WHERE wa_id = %s AND avisado AND recebido_em > %s""",
                              (e.pessoa.wa_id, agora - JANELA)).fetchone() is not None
        con.execute("""INSERT INTO atendimento.campo_frases (wa_id, texto, recebido_em, avisado)
                       VALUES (%s, %s, %s, %s)""", (e.pessoa.wa_id, texto[:500], agora, not avisado))
        if not avisado:
            self._texto(con, saida, e.pessoa.para, ANOTADO_FRASE)
        return True

    # ── os avisos dentro da janela ───────────────────────────────────────────

    def mandar_avisos(self, con, saida, agora: datetime) -> int:
        """Quem mandou recebe "entrou no catalogo" e "virou o Stories" so dentro das 24 h da ultima
        mensagem dele; fora, fica anotado 'fora_da_janela' e nada sai (seria modelo pago). O aviso
        sai UMA vez por grupo (o lote do dono em 11/10 recebeu tres)."""
        feitos = 0
        for campo, carimbo, mensagem, quando in (("aviso_catalogo", "aviso_catalogo_em", AVISO_CATALOGO, "catalogado_em"),
                                                  ("aviso_ar", "aviso_ar_em", AVISO_AR, "foi_ao_ar_em")):
            for r in con.execute("""SELECT * FROM atendimento.material_de_campo
                                     WHERE %s IS NOT NULL AND %s IS NULL ORDER BY id LIMIT 20"""
                                 % (quando, campo)).fetchall():
                grupo = self._grupo_de(con, r)
                ja_no_grupo = con.execute("""SELECT 1 FROM atendimento.material_de_campo
                                              WHERE id = ANY(%%s) AND %s = 'enviado'""" % campo, (grupo,)).fetchone()
                ultima = ultima_mensagem_de(con, r["wa_id"])
                dentro = ultima is not None and agora - ultima < JANELA
                estado = "fora_da_janela"
                if ja_no_grupo:
                    estado = "enviado"   # o grupo ja foi avisado: esta so herda a marca
                elif dentro:
                    try:
                        self._texto(con, saida, r["wa_id"] or r["bsuid"], mensagem)
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


def ler_safra(texto: str) -> int | None:
    """#982: "safra 2025", "safara 2025", "2025", "safra 25", "24/25", "2024/25" -> 2025 (o ano em que a
    safra termina: a safra N vai de 01/07/N-1 a 30/06/N, padrao da casa). None quando nao e safra.
    "inverno 2026" e "verao 25/26" tambem caem no ano (o ciclo nao e a safra)."""
    t = _sem_acento(texto)
    if not t or ler_data(texto, datetime(2000, 1, 1, tzinfo=FUSO)) is not None and "/" in t and not re.search(r"\bsaf", t):
        return None   # "09/10" e dia, nao safra
    m = re.search(r"(\d{2,4})\s*/\s*(\d{2,4})\s*$", t)
    if m and (len(m.group(1)) == 4 or len(m.group(2)) == 2 and re.search(r"\bsaf|\bverao|\binverno", t)):
        fim = m.group(2)
        ano = int(fim) if len(fim) == 4 else 2000 + int(fim[-2:])
        return ano if 2000 <= ano <= 2100 else None
    m = re.search(r"(?<![\d/])(\d{4})(?![\d/])", t)
    if m:
        ano = int(m.group(1))
        return ano if 2000 <= ano <= 2100 else None
    m = re.search(r"\b(?:saf[a-z]*ra|verao|inverno)\s*(\d{2})\b", t)
    if m:
        return 2000 + int(m.group(1))
    return None


def e_safra(texto: str) -> bool:
    return ler_safra(texto) is not None


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


# ── o que o marketing busca e devolve (as rotas chamam) ─────────────────────

def pendentes(con, agora: datetime) -> list[dict]:
    """O material baixado, de grupo FECHADO, que o marketing ainda nao levou (decisao 15: entra no
    catalogo quando a conversa fecha, ja com a classe; `classificados` fica para o que fechar de
    novo depois de levado)."""
    linhas = con.execute("""SELECT * FROM atendimento.material_de_campo
                             WHERE buscado_em IS NULL AND arquivo IS NOT NULL AND fechado_em IS NOT NULL
                             ORDER BY id""").fetchall()
    return [descrever(r) for r in linhas]


def classificados(con) -> list[dict]:
    """Os grupos que fecharam, com ATV conhecido, que o marketing ainda nao aplicou no catalogo."""
    linhas = con.execute("""SELECT * FROM atendimento.material_de_campo
                             WHERE fechado_em IS NOT NULL AND atv IS NOT NULL AND classe_aplicada_em IS NULL
                             ORDER BY id""").fetchall()
    return [descrever(r) for r in linhas]


def classe_aplicada(con, item_id: int, agora: datetime) -> dict | None:
    n = con.execute("UPDATE atendimento.material_de_campo SET classe_aplicada_em = coalesce(classe_aplicada_em, %s)"
                    " WHERE id = %s", (agora, item_id)).rowcount
    return {"id": item_id} if n else None


def descrever(r) -> dict:
    # #982: com a safra dita e sem dia, a data vai VAZIA (o marketing nao presume o dia)
    com_safra = r["safra_dita"] is not None and r["data_dita"] is None
    data = None if com_safra else (r["data_dita"] or _dia(r["recebido_em"]))
    falta = []
    if not (r["legenda"] or "").strip():
        falta.append("legenda")
    if (r["data_dita"] is None or r["data_presumida"]) and not com_safra:
        falta.append("data")
    if r["classe_bastidor"] is None:
        falta.append("bastidor")
    classe = {"bastidor": r["classe_bastidor"], "produto": r["classe_produto"], "fase": r["classe_fase"]}
    return {"id": r["id"], "contato": {"codigo": r["erp_codigo"], "papel": r["erp_papel"], "nome": r["erp_nome"]},
            "tipo": r["tipo"], "mime": r["mime"], "arquivo": r["arquivo"], "legenda": r["legenda"],
            "palpite": ({"bastidor": r["palpite_bastidor"], "produto": r["palpite_produto"], "fase": r["palpite_fase"]}
                        if r["palpite_em"] else None),
            "classe": classe, "fechado": r["fechado_em"] is not None, "desistiu": r["desistiu_em"] is not None,
            "perguntado": r["perguntas_em"] is not None, "safra": r["safra_dita"],
            "data": data.isoformat() if data else None,
            "data_presumida": (r["data_dita"] is None or r["data_presumida"]) and not com_safra,
            "recebido_em": r["recebido_em"].isoformat(), "falta": falta,
            "lote": r["lote"], "atv": r["atv"], "buscado_em": r["buscado_em"].isoformat() if r["buscado_em"] else None}


def buscado(con, item_id: int, lote: str, linha: int | None, agora: datetime) -> dict | None:
    r = con.execute("SELECT * FROM atendimento.material_de_campo WHERE id = %s FOR UPDATE", (item_id,)).fetchone()
    if not r:
        return None
    con.execute("""UPDATE atendimento.material_de_campo SET buscado_em = coalesce(buscado_em, %s), lote = %s
                    WHERE id = %s""", (agora, lote, item_id))
    return descrever(con.execute("SELECT * FROM atendimento.material_de_campo WHERE id = %s", (item_id,)).fetchone())


def palpite(con, item_id: int, bastidor: str | None, produto: str | None, agora: datetime,
            fase: str | None = None) -> dict | None:
    """O que o marketing achou que a foto mostra (listas fechadas de la). E segunda opiniao: molda a
    pergunta do bastidor quando a pessoa nao escreveu nada. Vazio tambem conta: a primeira pergunta
    deixa de esperar."""
    n = con.execute("""UPDATE atendimento.material_de_campo SET palpite_bastidor = %s, palpite_produto = %s,
                       palpite_fase = %s, palpite_em = coalesce(palpite_em, %s) WHERE id = %s""",
                    ((bastidor or "").strip()[:40] or None, (produto or "").strip()[:80] or None,
                     (fase or "").strip()[:20] or None, agora, item_id)).rowcount
    return {"id": item_id, "bastidor": bastidor, "produto": produto, "fase": fase} if n else None


def novos(con, agora: datetime | None = None) -> list[dict]:
    """O que chegou com arquivo e ainda nao teve palpite nem pergunta: o marketing olha a foto. So
    o do ultimo dia: palpite para foto velha nao molda pergunta nenhuma."""
    agora = agora or datetime.now(FUSO)
    return [descrever(l) for l in con.execute("""SELECT * FROM atendimento.material_de_campo
                WHERE palpite_em IS NULL AND perguntas_em IS NULL AND arquivo IS NOT NULL
                  AND recebido_em > %s ORDER BY id""", (agora - timedelta(days=1),)).fetchall()]


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
                              count(*) FILTER (WHERE classe_bastidor IS NOT NULL) AS classificados,
                              count(*) FILTER (WHERE desistiu_em IS NOT NULL) AS sem_resposta,
                              count(*) FILTER (WHERE buscado_em IS NOT NULL) AS buscados,
                              count(*) FILTER (WHERE catalogado_em IS NOT NULL) AS catalogados,
                              count(*) FILTER (WHERE aviso_catalogo = 'enviado' OR aviso_ar = 'enviado') AS avisos_enviados,
                              count(*) FILTER (WHERE aviso_catalogo = 'fora_da_janela' OR aviso_ar = 'fora_da_janela') AS avisos_fora,
                              count(*) FILTER (WHERE arquivo IS NULL) AS sem_arquivo
                         FROM atendimento.material_de_campo WHERE recebido_em > %s""", (desde,)).fetchone()
    return dict(r, ligado=ligado(con), dias=dias)
