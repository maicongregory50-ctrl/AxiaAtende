"""MEUS CLIENTES, o lado do ERP: a fila copiada e o registro conferido levado. #1090 etapa 3.

Roda no processo das TELAS (127.0.0.1:8009), o unico que tem o segredo do agente ATENDIMENTO -- o
recepcionista, que a internet alcanca, so le e grava o banco do atendimento (R4). Duas voltas:

- `copiar_filas`, a cada 10 min e ao subir: para cada consultor ativo, a fila dele no ERP (ordem do
  Relacionamento, com a ficha de cada cliente) troca a copia aqui numa transacao so; e os motivos.
- `enviar_registros`, a cada minuto: o que ele conferiu (`confirmado`) vai ao ERP. Aceito -> `gravado`;
  recusado com a frase da tela (422/403/404) -> `recusado` + a frase, que o recepcionista devolve a ele;
  ERP fora do ar ou agente sem CRM.WPP -> fica `confirmado` e vai na proxima volta. O ERP nao duplica
  (`ref_externa`), entao mandar de novo o que ja foi e inofensivo.
"""
import json
from datetime import datetime, timezone

from . import erp
from .banco import conexao

INTERVALO_FILA = 10 * 60
INTERVALO_ENVIO = 60
LIMITE = 60


def copiar_filas(cfg, ler=erp.fila_do_consultor) -> dict:
    """Uma volta da copia. Devolve {comercial_id: quantos} ou {"erro": motivo}."""
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    with conexao(cfg) as con:
        consultores = [r["comercial_id"] for r in con.execute(
            "SELECT DISTINCT comercial_id FROM atendimento.clientes_consultores WHERE ativo").fetchall()]
    out = {}
    for comercial in consultores:
        try:
            dados = ler(cfg, comercial, LIMITE)
        except erp.ErpIndisponivel as e:
            return {"erro": str(e), **out}
        with conexao(cfg) as con:
            with con.transaction():
                con.execute("DELETE FROM atendimento.clientes_fila WHERE comercial_id = %s", (comercial,))
                for i in dados.get("itens") or []:
                    con.execute("""INSERT INTO atendimento.clientes_fila (comercial_id, codigo, posicao, ficha)
                                   VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                                (comercial, int(i["codigo"]), int(i["posicao_fila"]), json.dumps(i, default=str)))
                if dados.get("motivos") is not None:
                    con.execute("DELETE FROM atendimento.clientes_motivos")
                    for m in dados["motivos"]:
                        con.execute("""INSERT INTO atendimento.clientes_motivos (id, nome, pede_texto)
                                       VALUES (%s, %s, %s)""", (int(m["id"]), m["nome"], bool(m.get("pede_texto"))))
        out[comercial] = len(dados.get("itens") or [])
    return out


def corpo_do_registro(reg) -> dict:
    p = reg["proposta"] or {}
    return {
        "stakeholder_id": reg["codigo"], "comercial_id": reg["comercial_id"],
        "ref_externa": "atende-cli:%d" % reg["id"],
        "meio": p.get("meio"), "quando": p.get("quando"), "ofereceu": bool(p.get("ofereceu")),
        "resposta": p.get("resposta"), "motivo_id": p.get("motivo_id"),
        "interesse_texto": p.get("interesse_texto") or None, "anotacao": _anotacao(reg, p),
        "retomar_em": p.get("retomar_em"), "pedido_numero": p.get("pedido_numero") or None,
    }


def _anotacao(reg, p: dict) -> str | None:
    """A anotacao que a IA resumiu; sem ela, o que ele escreveu (cortado). Fica no historico do cliente."""
    t = (p.get("anotacao") or "").strip() or (reg["textos"] or "").strip()
    return t[:2000] or None


def enviar_registros(cfg, gravar=erp.registrar_contato, agora: datetime | None = None) -> dict:
    """Uma volta do envio. Devolve as contagens, ou {"erro": motivo} quando o ERP nao pode receber."""
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    agora = agora or datetime.now(timezone.utc)
    conta = {"gravados": 0, "recusados": 0}
    with conexao(cfg) as con:
        pendentes = con.execute("""SELECT * FROM atendimento.clientes_registros WHERE estado = 'confirmado'
                                    ORDER BY id LIMIT 20""").fetchall()
    for reg in pendentes:
        try:
            r = gravar(cfg, corpo_do_registro(reg))
        except erp.ErpRecusou as e:
            with conexao(cfg) as con:
                con.execute("""UPDATE atendimento.clientes_registros SET estado = 'recusado', erro = %s, avisado = false
                                WHERE id = %s AND estado = 'confirmado'""", (str(e)[:300], reg["id"]))
            conta["recusados"] += 1
            continue
        except erp.ErpIndisponivel as e:
            return {"erro": str(e), **conta}
        with conexao(cfg) as con:
            con.execute("""UPDATE atendimento.clientes_registros
                              SET estado = 'gravado', erp_id = %s, gravado_em = %s, avisado = false
                            WHERE id = %s AND estado = 'confirmado'""", (r.get("id"), agora, reg["id"]))
        conta["gravados"] += 1
    return conta
