"""O envio a carteira. #950, Fase E do plano.

QUEM PEDE E QUEM MANDA. O AxiaMarketing pede (campanha, peca, imagens e a lista de clientes ja com
o responsavel de cada um, lido do canal comercial do cadastro no ERP), depois de o dono aprovar la
(trava D7 do #923). As TELAS gravam o pedido (`receber_pedido`, chamado pela API local). O
RECEPCIONISTA, unico com a chave da Meta, manda (`rotina`, a cada minuto).

AS REGRAS (spec, Decisao e "Cuidado com a Meta", dono 09/10/2026):
- **Cada envio e UM convite pago** (modelo de Marketing com a capa e os botoes "Quero receber" /
  "Nao quero receber"). O toque abre a janela de 24h e as imagens vao como mensagem livre, sem
  custo. O aceite fica gravado.
- **Quem recusa** sai da lista (nunca mais recebe convite) e o RESPONSAVEL dele e avisado no
  WhatsApp por modelo de Utilidade, para um contato direto. "Quero receber" nao avisa ninguem.
- **Sem responsavel no cadastro** (canal comercial vazio), o cliente NAO recebe: fica como
  "sem responsavel", com o vendedor do ultimo pedido como sugestao.
- **Degraus:** lotes de ate 20 por dia, na ordem de faturamento (Top 20, Top 50, Top 100); o
  proximo lote so sai com a nota do numero em GREEN; em YELLOW ou RED o envio para sozinho.
- **Ninguem recebe o mesmo convite duas vezes**, e numero que a Meta recusou como "nao e
  WhatsApp" nao e tentado de novo.
- **O representante recebe copia do convite** dos clientes da carteira dele (uma copia por envio).

OS IDS DOS BOTOES do modelo (`payload` da resposta rapida): `envio:<id>:quero` e
`envio:<id>:nao_quero`. O motor entrega ao `tratar_toque` tudo o que comeca com `envio:`.
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .banco import conexao
from .saida import Saida

FUSO = ZoneInfo("America/Sao_Paulo")
MODELO_CONVITE = "pecas_da_revenda"
MODELO_RECUSA = "aviso_recusa"
MODELO_SEM_ATENDIMENTO = "aviso_sem_atendimento"
IDIOMA = "pt_BR"
JANELA = timedelta(hours=24)
# codigos da Meta para "este numero nao e WhatsApp" (131026: mensagem nao entregavel)
NAO_E_WHATSAPP = {"131026"}
CELULAR = re.compile(r"^55[1-9][0-9]9[0-9]{8}$")


def so_digitos(numero: str) -> str:
    d = re.sub(r"\D", "", numero or "")
    if d and not d.startswith("55"):
        d = "55" + d
    return d


# ── o pedido (lado das TELAS) ───────────────────────────────────────────────

def receber_pedido(con, pedido: dict) -> int:
    """Grava o pedido e a fila de destinatarios, ja classificada. Devolve o id do envio.
    Pedido repetido (mesma `pedido_ref`) devolve o envio que ja existe e nao muda nada."""
    ja = con.execute("SELECT id FROM atendimento.envios WHERE pedido_ref = %s", (pedido["pedido_ref"],)).fetchone()
    if ja:
        return ja["id"]
    envio = con.execute(
        """INSERT INTO atendimento.envios (pedido_ref, campanha, peca, modelo, capa, imagens,
                                           aprovado_por, aprovado_em, lote_tamanho)
           VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s) RETURNING id""",
        (pedido["pedido_ref"], pedido["campanha"], pedido["peca"], pedido.get("modelo", MODELO_CONVITE),
         pedido["capa"], _json(pedido["imagens"]), pedido["aprovado_por"], pedido["aprovado_em"],
         min(int(pedido.get("lote_tamanho", 20)), 20))).fetchone()["id"]

    ordenados = sorted(pedido["clientes"], key=lambda c: -float(c.get("faturamento") or 0))
    for pos, c in enumerate(ordenados, start=1):
        numero = so_digitos(c.get("whatsapp", ""))
        resp = so_digitos(c.get("responsavel_whatsapp", ""))
        if not CELULAR.match(numero):
            situacao = "sem_whatsapp"
        elif not c.get("responsavel_nome") or not CELULAR.match(resp):
            situacao = "sem_responsavel"
        elif _recusou(con, numero):
            situacao = "recusou_antes"
        elif _ja_recebeu(con, numero, pedido["peca"]):
            situacao = "ja_recebeu"
        elif _nao_e_whatsapp(con, numero):
            situacao = "nao_e_whatsapp"
        else:
            situacao = "aguardando"
        con.execute(
            """INSERT INTO atendimento.envio_destinatarios
                   (envio_id, erp_codigo, nome, cidade, uf, whatsapp, faturamento, posicao,
                    responsavel_nome, responsavel_whatsapp, sugestao_vendedor, situacao)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (envio_id, erp_codigo) DO NOTHING""",
            (envio, int(c["erp_codigo"]), c["nome"], c.get("cidade", ""), c.get("uf", ""), numero,
             c.get("faturamento") or 0, pos, c.get("responsavel_nome", ""), resp,
             c.get("sugestao_vendedor", ""), situacao))
    return envio


def _json(v):
    import json
    return json.dumps(v)


def _recusou(con, numero):
    return con.execute("""SELECT tipo FROM atendimento.consentimentos WHERE whatsapp = %s
                           ORDER BY em DESC, id DESC LIMIT 1""", (numero,)).fetchone() == {"tipo": "recusa"}


def _ja_recebeu(con, numero, peca):
    return con.execute("""SELECT 1 FROM atendimento.envio_destinatarios d JOIN atendimento.envios e ON e.id = d.envio_id
                           WHERE d.whatsapp = %s AND e.peca = %s AND d.convite_em IS NOT NULL""",
                       (numero, peca)).fetchone() is not None


def _nao_e_whatsapp(con, numero):
    return con.execute("""SELECT 1 FROM atendimento.envio_destinatarios
                           WHERE whatsapp = %s AND situacao = 'nao_e_whatsapp'""", (numero,)).fetchone() is not None


# ── a rotina (lado do RECEPCIONISTA) ────────────────────────────────────────

class Envio:
    """O que o motor e o recepcionista chamam. `ler_nota` devolve a nota do numero na Meta
    (GREEN/YELLOW/RED/UNKNOWN); nos testes, uma funcao falsa."""

    def __init__(self, ler_nota=None):
        self._ler_nota = ler_nota

    # -- a cada minuto --
    def rotina(self, cfg, saida: Saida, agora: datetime) -> None:
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
        nota = self.ler_nota_do_dia(con, agora)
        hoje = agora.astimezone(FUSO).date()
        mandados = 0
        for e in con.execute("SELECT * FROM atendimento.envios WHERE situacao IN ('ativo', 'parado_nota') ORDER BY id").fetchall():
            if nota != "GREEN":
                # Sem nota verde nao sai lote. Amarela ou vermelha PARA o envio (o dono decide);
                # sem leitura (UNKNOWN) so espera o proximo minuto.
                if nota in ("YELLOW", "RED") and e["situacao"] != "parado_nota":
                    con.execute("UPDATE atendimento.envios SET situacao = 'parado_nota' WHERE id = %s", (e["id"],))
                continue
            if e["situacao"] == "parado_nota":
                continue   # parado pela nota: so o dono religa (Envios), nem com a nota de volta ao verde
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
            if not fila and not ja_hoje:
                pend = con.execute("""SELECT 1 FROM atendimento.envio_destinatarios
                                       WHERE envio_id = %s AND situacao = 'aguardando' LIMIT 1""", (e["id"],)).fetchone()
                if not pend:
                    con.execute("UPDATE atendimento.envios SET situacao = 'concluido' WHERE id = %s", (e["id"],))
                continue
            # o lote e o do dia: o primeiro convite do dia abre um lote novo
            ultimo = con.execute("SELECT coalesce(max(lote), 0) AS m FROM atendimento.envio_destinatarios WHERE envio_id = %s",
                                 (e["id"],)).fetchone()["m"]
            lote = ultimo if ja_hoje else ultimo + 1
            for d in fila:
                self._convidar(con, saida, e, d, lote, agora)
                mandados += 1
            self._copias_aos_responsaveis(con, saida, e, fila, agora)
        return mandados

    def _convidar(self, con, saida, e, d, lote, agora):
        primeiro_nome = d["nome"].split(" ")[0].title() if d["nome"] else "tudo bem"
        n = len(e["imagens"])
        try:
            w = saida.modelo(d["whatsapp"], e["modelo"], IDIOMA, [primeiro_nome, str(n)], imagem=e["capa"],
                             botoes=["envio:%d:quero" % e["id"], "envio:%d:nao_quero" % e["id"]])
            con.execute("""UPDATE atendimento.envio_destinatarios
                              SET situacao = 'convidado', lote = %s, convite_wamid = %s, convite_em = %s,
                                  imagens_total = %s
                            WHERE id = %s""", (lote, w, agora, n, d["id"]))
            con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo)
                           VALUES (%s, %s, 'modelo', %s)""", (w, d["whatsapp"], "convite %s" % e["peca"]))
        except Exception as falha:  # noqa: BLE001 -- o proximo da fila segue
            con.execute("""UPDATE atendimento.envio_destinatarios SET situacao = 'falhou', lote = %s, erro = %s
                            WHERE id = %s""", (lote, str(falha)[:300], d["id"]))

    def _copias_aos_responsaveis(self, con, saida, e, fila, agora):
        """Uma copia do convite por responsavel por envio (o mesmo que o cliente recebe)."""
        for resp in sorted({(d["responsavel_whatsapp"], d["responsavel_nome"]) for d in fila}):
            numero, nome = resp
            ja = con.execute("""SELECT 1 FROM atendimento.enviadas WHERE para = %s AND resumo = %s""",
                             (numero, "copia %d" % e["id"])).fetchone()
            if ja:
                continue
            try:
                w = saida.modelo(numero, e["modelo"], IDIOMA, [nome.split(" ")[0], str(len(e["imagens"]))],
                                 imagem=e["capa"], botoes=["envio:%d:copia" % e["id"], "envio:%d:copia" % e["id"]])
                con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'modelo', %s)",
                            (w, numero, "copia %d" % e["id"]))
            except Exception:  # noqa: BLE001 -- a copia nunca trava o envio
                pass

    # -- as respostas --
    def tratar_toque(self, con, saida: Saida, entrada, agora: datetime) -> None:
        partes = (entrada.toque or "").split(":")
        if len(partes) != 3 or not partes[1].isdigit():
            return
        envio_id, acao = int(partes[1]), partes[2]
        numero = entrada.pessoa.wa_id or ""
        d = con.execute("""SELECT * FROM atendimento.envio_destinatarios
                            WHERE envio_id = %s AND whatsapp = %s""", (envio_id, numero)).fetchone()
        if acao == "copia" or not d:
            return   # o toque do representante na copia, ou de quem nao estava na lista: nada
        if d["resposta"] in ("quero", "nao_quero"):
            return   # ja respondeu; o segundo toque nao repete nada
        if acao == "quero":
            con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, bsuid, erp_codigo, tipo, wamid, envio_id)
                           VALUES (%s, %s, %s, 'aceite', %s, %s)""",
                        (numero, entrada.pessoa.bsuid, d["erp_codigo"], entrada.wamid, envio_id))
            con.execute("""UPDATE atendimento.envio_destinatarios SET resposta = 'quero', resposta_em = %s
                            WHERE id = %s""", (agora, d["id"]))
            self._mandar_imagens(con, saida, envio_id, d["id"], agora)
        elif acao == "nao_quero":
            con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, bsuid, erp_codigo, tipo, wamid, envio_id)
                           VALUES (%s, %s, %s, 'recusa', %s, %s)""",
                        (numero, entrada.pessoa.bsuid, d["erp_codigo"], entrada.wamid, envio_id))
            con.execute("""UPDATE atendimento.envio_destinatarios SET resposta = 'nao_quero', resposta_em = %s
                            WHERE id = %s""", (agora, d["id"]))
            # sai de todo envio ainda por mandar
            con.execute("""UPDATE atendimento.envio_destinatarios SET situacao = 'recusou_antes'
                            WHERE whatsapp = %s AND situacao = 'aguardando'""", (numero,))
            w = saida.texto(numero, "Tudo certo, você não vai mais receber estas mensagens. Obrigado pela atenção.")
            con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'texto', 'recusa confirmada')",
                        (w, numero))
            e = con.execute("SELECT peca FROM atendimento.envios WHERE id = %s", (envio_id,)).fetchone()
            sobre = "%s|%s · %s|%s|https://wa.me/%s" % (d["nome"], d["erp_codigo"], d["cidade"] or "?",
                                                         e["peca"], numero)
            con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                           VALUES ('recusa', %s, %s, %s)""", (d["responsavel_nome"], d["responsavel_whatsapp"], sobre))

    def tratar_texto_de_convidado(self, con, entrada, agora) -> bool:
        """Quem foi convidado e ESCREVEU (em vez de tocar): o texto fica na linha do Envios."""
        numero = entrada.pessoa.wa_id or ""
        d = con.execute("""SELECT d.id FROM atendimento.envio_destinatarios d
                            WHERE d.whatsapp = %s AND d.convite_em > %s AND d.resposta IS NULL
                            ORDER BY d.convite_em DESC LIMIT 1""", (numero, agora - JANELA)).fetchone()
        if not d or not entrada.texto:
            return False
        con.execute("""UPDATE atendimento.envio_destinatarios SET resposta = 'texto', resposta_texto = %s,
                              resposta_em = %s WHERE id = %s""", (entrada.texto[:500], agora, d["id"]))
        return True

    def _mandar_imagens(self, con, saida, envio_id, dest_id, agora):
        e = con.execute("SELECT imagens, peca FROM atendimento.envios WHERE id = %s", (envio_id,)).fetchone()
        d = con.execute("SELECT * FROM atendimento.envio_destinatarios WHERE id = %s", (dest_id,)).fetchone()
        if not d["resposta_em"] or agora - d["resposta_em"] > JANELA:
            return   # fora da janela a mensagem livre nao sai; o dono decide (Envios)
        imagens = e["imagens"]
        for i in range(d["imagens_enviadas"], len(imagens)):
            try:
                legenda = e["peca"] if i == 0 else ""
                w = saida.imagem(d["whatsapp"], imagens[i], legenda)
                con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'imagem', %s)",
                            (w, d["whatsapp"], "imagem %d de %s" % (i + 1, e["peca"])))
                con.execute("UPDATE atendimento.envio_destinatarios SET imagens_enviadas = %s WHERE id = %s",
                            (i + 1, dest_id))
            except Exception as falha:  # noqa: BLE001 -- tenta de novo no proximo minuto, dentro da janela
                con.execute("UPDATE atendimento.envio_destinatarios SET erro = %s WHERE id = %s",
                            (str(falha)[:300], dest_id))
                return

    def mandar_imagens_pendentes(self, con, saida, agora):
        for d in con.execute("""SELECT id, envio_id FROM atendimento.envio_destinatarios
                                 WHERE resposta = 'quero' AND imagens_enviadas < imagens_total
                                   AND resposta_em > %s""", (agora - JANELA,)).fetchall():
            self._mandar_imagens(con, saida, d["envio_id"], d["id"], agora)

    def mandar_avisos(self, con, saida, agora):
        for a in con.execute("""SELECT * FROM atendimento.avisos WHERE enviado_em IS NULL AND erro = ''
                                 ORDER BY id LIMIT 20""").fetchall():
            try:
                if a["tipo"] == "recusa":
                    nome, local, peca, link = (a["sobre"].split("|") + ["", "", "", ""])[:4]
                    w = saida.modelo(a["para_whatsapp"], MODELO_RECUSA, IDIOMA, [nome, local, link])
                else:
                    w = saida.modelo(a["para_whatsapp"], MODELO_SEM_ATENDIMENTO, IDIOMA,
                                     [a["sobre"][:200], "o atendimento", "veja a tela Recepção"])
                con.execute("UPDATE atendimento.avisos SET enviado_em = %s, wamid = %s WHERE id = %s", (agora, w, a["id"]))
            except Exception as falha:  # noqa: BLE001
                con.execute("UPDATE atendimento.avisos SET erro = %s WHERE id = %s", (str(falha)[:300], a["id"]))

    # -- os status da Meta para o convite --
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
