"""#1542 (etapa 3): o TERMO DE REPROVACAO DE LOTE do ERP vai ao WhatsApp Legal do produtor, com o PDF e o botao
"Recebi e estou ciente". Plano: C:\\AxiaGestao\\docs\\specs\\2026-11-18-termo-de-reprovacao-do-lote-etapa3-plano.md

No molde do pedido de CT-e da Logistica (`logistica_erp.py`, #1128), com uma diferenca: aqui vai COM MODELO
(o produtor nao abriu janela nenhuma), o `termo_reprovacao_lote` da migracao 071.

1. **As TELAS** (a cada minuto, `volta`): trazem do ERP os pedidos pendentes (agente ATENDIMENTO, QUA.TRM),
   baixam o PDF do termo para `envios_pasta\\termos` e gravam a linha em `atendimento.termos_reprovacao`. Na
   mesma volta devolvem ao ERP o estado da Meta (Enviado, Entregue, Lido, Falhou) e a ciencia do botao.
2. **O RECEPCIONISTA** (na rotina do minuto, `mandar`): manda o modelo ao numero do pedido, SO com a chave
   `TERMO_REPROVACAO_ATIVO` ligada no .env.recepcionista. Os avisos de estado da Meta entram por
   `aplicar_status`, e o toque no botao por `tocar` (reconhecido pela carga `termo:ciente:<id>`).

A ciencia so vale do numero do pedido: quem recebeu a mensagem encaminhada nao da ciencia (o ERP confere e
recusa; a recusa fica gravada e nao se tenta de novo). O texto do modelo cita o contrato e pede so a
confirmacao do recebimento (dono, 18/11/2026: nao se fala em concordancia).

O recepcionista, que a internet alcanca, nao le o ERP; as telas nao falam com a Meta (config.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import erp
from .banco import conexao
from .envio import com_nove, modelo_do_uso, parametros, so_digitos

INTERVALO_SEGUNDOS = 60
PREFIXO_TOQUE = "termo:ciente:"
#: O termo so sai das 9h as 17h, hora de Brasilia (dono, 18/11/2026: reprovacao nao chega ao produtor fora do
#: expediente). Fora da janela o pedido espera "a_enviar" (no ERP, "Enviando...") e sai na primeira volta das 9h.
FUSO = ZoneInfo("America/Sao_Paulo")
JANELA_HORAS = (9, 17)
CONFIRMACAO = "Recebemos a sua confirmação de recebimento do termo {numero}. Obrigado."

#: o estado daqui -> o estado do ERP
PARA_O_ERP = {"enviada": "ENVIADO", "entregue": "ENTREGUE", "lida": "LIDO", "falhou": "FALHOU"}
_ORDEM = ["a_enviar", "enviada", "entregue", "lida"]


# ── as TELAS ─────────────────────────────────────────────────────────────────────────────────────

def volta(cfg, ir=erp.termos_reprovacao, pdf=erp.termo_pdf, estado=erp.estado_do_termo,
          ciencia=erp.ciencia_do_termo) -> dict:
    """Uma volta das TELAS. Devolve a contagem, ou {"erro": motivo}. Sem o segredo, nem tenta."""
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    try:
        r = ir(cfg)
    except erp.ErpIndisponivel as e:
        return {"erro": str(e)}
    token, novos = r["token"], 0
    with conexao(cfg) as con:
        ja = {x["erp_envio_id"] for x in con.execute("SELECT erp_envio_id FROM atendimento.termos_reprovacao").fetchall()}

    pasta = Path(cfg.envios_pasta) / "termos"
    for p in r["pendentes"]:
        if p["id"] in ja:
            continue
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            caminho = pasta / ("%d-%s" % (p["id"], p["arquivo"]))
            caminho.write_bytes(pdf(cfg, token, p["termo_id"]))
        except (erp.ErpIndisponivel, OSError) as e:
            print("termo: PDF do pedido %s: %s" % (p["id"], e), flush=True)
            continue   # tenta na proxima volta
        with conexao(cfg) as con:
            con.execute(
                """INSERT INTO atendimento.termos_reprovacao (erp_envio_id, erp_termo_id, numero_termo, produtor_nome,
                                                             lotes, valor, vencimento, para_whatsapp, arquivo)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (erp_envio_id) DO NOTHING""",
                (p["id"], p["termo_id"], p["numero_termo"], p.get("produtor_nome") or "", p.get("lotes") or "",
                 _valor_br(p.get("valor_total")), _data_br(p.get("data_vencimento")),
                 com_nove(so_digitos(p["destino"])), str(caminho)))
        novos += 1

    with conexao(cfg) as con:
        a_devolver = [dict(x) for x in con.execute(
            """SELECT id, erp_envio_id, estado, estado_devolvido, erro, wamid FROM atendimento.termos_reprovacao
                WHERE estado <> 'a_enviar' ORDER BY id""").fetchall()]
        cientes = [dict(x) for x in con.execute(
            """SELECT id, erp_envio_id, ciencia_em, ciencia_numero, ciencia_wamid FROM atendimento.termos_reprovacao
                WHERE ciencia_em IS NOT NULL AND ciencia_devolvida_em IS NULL AND ciencia_recusada IS NULL
                ORDER BY id""").fetchall()]
    devolvidos = 0
    for a in a_devolver:
        alvo = PARA_O_ERP[a["estado"]]
        if alvo == a["estado_devolvido"]:
            continue
        try:
            estado(cfg, token, a["erp_envio_id"], alvo, motivo=a["erro"], wamid=a["wamid"])
        except erp.ErpIndisponivel as e:
            print("termo: estado do pedido %s: %s" % (a["erp_envio_id"], e), flush=True)
            continue
        with conexao(cfg) as con:
            con.execute("UPDATE atendimento.termos_reprovacao SET estado_devolvido = %s WHERE id = %s", (alvo, a["id"]))
        devolvidos += 1
    for c in cientes:
        try:
            ciencia(cfg, token, c["erp_envio_id"], c["ciencia_numero"] or "", c["ciencia_em"].isoformat(),
                    wamid=c["ciencia_wamid"] or "")
            sql, args = "UPDATE atendimento.termos_reprovacao SET ciencia_devolvida_em = now() WHERE id = %s", (c["id"],)
        except erp.ErpRecusou as e:   # numero diferente do pedido: nao vira ciencia, e nao se tenta de novo
            sql, args = "UPDATE atendimento.termos_reprovacao SET ciencia_recusada = %s WHERE id = %s", (str(e)[:300], c["id"])
        except erp.ErpIndisponivel as e:
            print("termo: ciencia do pedido %s: %s" % (c["erp_envio_id"], e), flush=True)
            continue
        with conexao(cfg) as con:
            con.execute(sql, args)
        devolvidos += 1
    return {"pendentes": len(r["pendentes"]), "novos": novos, "devolvidos": devolvidos}


def _valor_br(v) -> str:
    try:
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(v or "")


def _data_br(v) -> str:
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(v or "")


# ── o RECEPCIONISTA ──────────────────────────────────────────────────────────────────────────────

def mandar(con, saida, ativo: bool, agora: datetime | None = None) -> int:
    """Manda o modelo com o PDF aos pedidos que as telas enfileiraram. Desligado, ou fora das 9h-17h, nada sai."""
    if not ativo:
        return 0
    agora = agora or datetime.now(timezone.utc)
    if not no_horario(agora):
        return 0
    saiu = 0
    m = modelo_do_uso(con, "termo_reprovacao")
    for p in con.execute("""SELECT * FROM atendimento.termos_reprovacao WHERE estado = 'a_enviar' AND erro = ''
                             ORDER BY id LIMIT 10""").fetchall():
        try:
            if not m:
                raise RuntimeError("nenhum modelo cadastrado para o termo de reprovação")
            dados = Path(p["arquivo"]).read_bytes()
            nome = Path(p["arquivo"]).name.split("-", 1)[-1]
            fontes = {"produtor": p["produtor_nome"], "numero_termo": p["numero_termo"], "lotes": p["lotes"],
                      "valor": p["valor"], "vencimento": p["vencimento"]}
            w = saida.modelo(p["para_whatsapp"], m["nome"], m["idioma"], parametros(m, fontes),
                             botoes=[PREFIXO_TOQUE + str(p["id"])], documento=(dados, nome))
            con.execute("""UPDATE atendimento.termos_reprovacao SET estado = 'enviada', enviado_em = %s, estado_em = %s,
                                  wamid = %s WHERE id = %s""", (agora, agora, w or "", p["id"]))
            if w:   # a Recepcao mostra a conversa a partir de `enviadas`, e o status da Meta acha a linha por ela
                con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo)
                               VALUES (%s, %s, 'modelo', %s) ON CONFLICT (wamid) DO NOTHING""",
                            (w, p["para_whatsapp"], "termo de reprovação %s" % p["numero_termo"]))
            saiu += 1
        except Exception as falha:  # noqa: BLE001 -- um pedido nao segura o outro
            motivo = "Não saiu: %s" % (str(falha)[:250] or type(falha).__name__)
            con.execute("""UPDATE atendimento.termos_reprovacao SET estado = 'falhou', erro = %s, estado_em = %s
                            WHERE id = %s""", (motivo, agora, p["id"]))
    return saiu


def no_horario(agora: datetime) -> bool:
    """Das 9h (inclusive) as 17h (exclusive), hora de Brasilia."""
    return JANELA_HORAS[0] <= agora.astimezone(FUSO).hour < JANELA_HORAS[1]


def aplicar_status(con, wamid: str, novo: str, erro: str, agora: datetime) -> None:
    """O aviso de estado da Meta (`recepcionista.aplicar_status`, ja traduzido: enviada, entregue, lida,
    falhou). Fora de ordem e normal: so se avanca, e lida nao vira falha."""
    if not wamid:
        return
    r = con.execute("SELECT id, estado FROM atendimento.termos_reprovacao WHERE wamid = %s", (wamid,)).fetchone()
    if not r:
        return
    atual = r["estado"]
    if novo == "falhou":
        avanca = atual != "lida"
    else:
        avanca = atual in _ORDEM and novo in _ORDEM and _ORDEM.index(novo) > _ORDEM.index(atual)
    if avanca:
        con.execute("""UPDATE atendimento.termos_reprovacao SET estado = %s, estado_em = %s,
                              erro = CASE WHEN %s = 'falhou' THEN %s ELSE erro END WHERE id = %s""",
                    (novo, agora, novo, erro or "a Meta não entregou", r["id"]))


def tocar(con, saida, e, agora: datetime) -> bool:
    """O toque em "Recebi e estou ciente" (carga `termo:ciente:<id>`). Guarda quem tocou e quando; quem
    confere se o numero e o do pedido e o ERP, na volta das telas. Responde uma linha de confirmacao."""
    if not (e.toque or "").startswith(PREFIXO_TOQUE):
        return False
    try:
        termo_id = int(e.toque[len(PREFIXO_TOQUE):])
    except ValueError:
        return True
    r = con.execute("SELECT * FROM atendimento.termos_reprovacao WHERE id = %s", (termo_id,)).fetchone()
    if not r:
        return True
    numero = com_nove(so_digitos(e.pessoa.wa_id or ""))
    if r["ciencia_em"] is None:
        con.execute("""UPDATE atendimento.termos_reprovacao SET ciencia_em = %s, ciencia_numero = %s, ciencia_wamid = %s
                        WHERE id = %s""", (e.enviado_em or agora, numero, e.wamid, termo_id))
    para = e.pessoa.wa_id or r["para_whatsapp"]
    try:
        saida.texto(para, CONFIRMACAO.format(numero=r["numero_termo"]))
    except Exception as falha:  # noqa: BLE001 -- a ciencia ja esta gravada; a linha de volta e cortesia
        print("termo: confirmacao do %s: %s" % (r["numero_termo"], type(falha).__name__), flush=True)
    return True
