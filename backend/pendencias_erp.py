"""#1222: o chamado no WhatsApp -- a ida e a volta com o ERP. Processo das TELAS (o unico com o segredo
do ERP), a cada minuto. O envio pela Meta e a leitura da resposta sao do RECEPCIONISTA
(`pendencias.py`); a tabela e a fila entre os dois.

Uma volta (`volta`):
1. TRAZ do ERP o que chegou aos autores depois do cursor e grava a mensagem `esperando` na pendencia do
   chamado (uma por chamado e numero). Pergunta faz a pendencia esperar RESPOSTA; entrega, VALIDACAO.
   Sem cursor (a primeira volta), so guarda o cursor de agora: ligar nao despeja o historico.
2. LEVA ao ERP o que a pessoa respondeu (`a_entregar`): comentario, Ficou bom, Nao ficou bom. O ERP
   recusando (numero que nao e o do autor, chamado fora da entrega): a mensagem fica com o erro. O ERP
   fora do ar: tenta na volta seguinte.
3. CONFERE as pendencias que esperam: a entrega que alguem ja validou na caixa, a pergunta que o autor
   ja respondeu por la, ou 7 dias sem resposta -- e ela deixa de esperar (sai da lista da OlivIA).

Desligado (`pendencias.ligado`), nada: nem o cursor anda.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import erp
from .banco import conexao

INTERVALO_SEGUNDOS = 60
SEM_RESPOSTA = timedelta(days=7)


def _ajuste(con, chave, padrao=None):
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (chave,)).fetchone()
    return padrao if r is None else r["valor"]


def _gravar_cursor(con, cursor: int) -> None:
    con.execute("""INSERT INTO atendimento.ajustes (chave, valor) VALUES ('pendencias.cursor', to_jsonb(%s::int))
                   ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor, atualizado_em = now()""", (cursor,))


def receber(con, linhas: list[dict], agora: datetime) -> int:
    """Grava as linhas do ERP. Idempotente pelo evento de origem (UNIQUE)."""
    novas = 0
    for li in linhas:
        espera = {"pergunta": "resposta", "entrega": "validacao"}.get(li["classe"])
        p = con.execute(
            """INSERT INTO atendimento.pendencias (tipo, referencia, titulo, para_whatsapp, espera, espera_desde,
                                                  espera_evento, ultima_em)
               VALUES ('chamado', %s, %s, %s, %s, CASE WHEN %s::text IS NULL THEN NULL ELSE %s::timestamptz END, %s, %s)
               ON CONFLICT (tipo, referencia, para_whatsapp) DO UPDATE SET
                   titulo = EXCLUDED.titulo, ultima_em = EXCLUDED.ultima_em,
                   espera = COALESCE(EXCLUDED.espera, atendimento.pendencias.espera),
                   espera_desde = COALESCE(EXCLUDED.espera_desde, atendimento.pendencias.espera_desde),
                   espera_evento = COALESCE(EXCLUDED.espera_evento, atendimento.pendencias.espera_evento),
                   aguardando_motivo = CASE WHEN EXCLUDED.espera IS NULL THEN atendimento.pendencias.aguardando_motivo
                                            ELSE false END
               RETURNING id""",
            (str(li["demanda_id"]), (li.get("titulo") or "")[:120], li["numero"], espera, espera, agora,
             li["evento_id"] if espera else None, agora)).fetchone()
        r = con.execute(
            """INSERT INTO atendimento.pendencias_mensagens (pendencia_id, sentido, classe, texto, origem_evento_id,
                                                            estado, criado_em)
               VALUES (%s, 'saiu', %s, %s, %s, 'esperando', %s) ON CONFLICT (origem_evento_id) DO NOTHING RETURNING id""",
            (p["id"], li["classe"], li["texto"][:4000], li["evento_id"], agora)).fetchone()
        novas += r is not None
    return novas


def _a_entregar(con) -> list[dict]:
    return [dict(r) for r in con.execute(
        """SELECT m.id, m.classe, m.texto, m.resultado, p.referencia, p.para_whatsapp
             FROM atendimento.pendencias_mensagens m
             JOIN atendimento.pendencias p ON p.id = m.pendencia_id
            WHERE m.sentido = 'entrou' AND m.estado = 'a_entregar' AND p.tipo = 'chamado'
            ORDER BY m.id""").fetchall()]


def conferir(con, demandas: list[dict], agora: datetime) -> int:
    """Fecha a espera das pendencias que deixaram de valer. Devolve quantas."""
    feitas = 0
    por_id = {str(d["id"]): d for d in demandas}
    for p in con.execute("""SELECT id, referencia, espera, espera_desde, espera_evento FROM atendimento.pendencias
                             WHERE tipo = 'chamado' AND espera IS NOT NULL""").fetchall():
        d = por_id.get(p["referencia"])
        vale = True
        if p["espera_desde"] and agora - p["espera_desde"] > SEM_RESPOSTA:
            vale = False
        elif d is not None and p["espera"] == "validacao" and not d["na_entrega"]:
            vale = False   # validada na caixa (ou por quem trata)
        elif (d is not None and p["espera"] == "resposta" and d["ultima_do_autor"]
              and p["espera_evento"] and d["ultima_do_autor"] > p["espera_evento"]):
            vale = False   # o autor respondeu pela caixa
        if not vale:
            con.execute("UPDATE atendimento.pendencias SET espera = NULL, aguardando_motivo = false WHERE id = %s",
                        (p["id"],))
            feitas += 1
    return feitas


def volta(cfg, trazer=erp.chamados_saida, estado=erp.chamados_estado, responder=erp.chamado_resposta,
          validar=erp.chamado_validar, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now(timezone.utc)
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    with conexao(cfg) as con:
        if _ajuste(con, "pendencias.ligado", False) is not True:
            return {"desligado": True}
        cursor = _ajuste(con, "pendencias.cursor")
    try:
        r = trazer(cfg, cursor if isinstance(cursor, int) else None)
    except erp.ErpIndisponivel as e:
        return {"erro": str(e)}
    token = r["token"]
    with conexao(cfg) as con:
        with con.transaction():   # o cursor so anda junto com o que foi gravado
            novas = receber(con, r["linhas"], agora) if isinstance(cursor, int) else 0
            _gravar_cursor(con, r["cursor"])
        entregar = _a_entregar(con)
        esperando = [int(x["referencia"]) for x in con.execute(
            "SELECT DISTINCT referencia FROM atendimento.pendencias WHERE tipo = 'chamado' AND espera IS NOT NULL"
        ).fetchall()]

    entregues = 0
    for m in entregar:
        erro = None
        try:
            if m["classe"] == "validacao":
                validar(cfg, token, int(m["referencia"]), m["para_whatsapp"], m["resultado"],
                        m["texto"] if m["resultado"] == "nao_ficou_bom" else None)
            else:
                responder(cfg, token, int(m["referencia"]), m["para_whatsapp"], m["texto"])
        except erp.ErpRecusou as e:
            erro = str(e)
        except erp.ErpIndisponivel as e:
            print("pendencias: entrega da mensagem %d: %s" % (m["id"], e), flush=True)
            continue
        with conexao(cfg) as con:
            con.execute("""UPDATE atendimento.pendencias_mensagens SET estado = %s, entregue_em = %s, erro = %s
                            WHERE id = %s""", ("erro" if erro else "entregue", agora, erro or "", m["id"]))
        entregues += erro is None

    fechadas = 0
    try:
        demandas = estado(cfg, token, esperando) if esperando else []
        with conexao(cfg) as con:
            fechadas = conferir(con, demandas, agora)
    except erp.ErpIndisponivel as e:
        print("pendencias: estado: %s" % e, flush=True)
    return {"novas": novas, "entregues": entregues, "fechadas": fechadas}
