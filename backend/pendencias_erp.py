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

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from psycopg.types.json import Jsonb

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
                                                            estado, criado_em, anexo)
               VALUES (%s, 'saiu', %s, %s, %s, 'esperando', %s, %s) ON CONFLICT (origem_evento_id) DO NOTHING RETURNING id""",
            (p["id"], li["classe"], li["texto"][:4000], li["evento_id"], agora,
             Jsonb(li["_anexo"]) if li.get("_anexo") else None)).fetchone()
        novas += r is not None
    return novas


def _a_entregar(con, agora: datetime) -> list[dict]:
    # #1238: a resposta que o roteador encaminhou espera a carencia (`entregar_apos`) -- e o tempo da
    # correcao escrita. Nula (citacao, botao, tudo o que ja existia) vai na volta seguinte, como sempre.
    return [dict(r) for r in con.execute(
        """SELECT m.id, m.classe, m.texto, m.resultado, p.referencia, p.para_whatsapp
             FROM atendimento.pendencias_mensagens m
             JOIN atendimento.pendencias p ON p.id = m.pendencia_id
            WHERE m.sentido = 'entrou' AND m.estado = 'a_entregar' AND p.tipo = 'chamado'
              AND (m.entregar_apos IS NULL OR m.entregar_apos <= %s)
            ORDER BY m.id""", (agora,)).fetchall()]


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


def _nome_seguro(nome: str) -> str:
    return re.sub(r"[^\w.\- ]", "_", Path(nome or "documento").name)[:120] or "documento"


def baixar_anexos(cfg, token: str, linhas: list[dict], baixar=erp.chamado_anexo) -> None:
    """#1381: baixa o arquivo de cada linha que tem `anexo` para envios_pasta\\chamados e poe em
    `_anexo` o que o recepcionista precisa. Uma falha levanta `ErpIndisponivel`: a volta para antes de
    gravar, o cursor nao anda, e a linha vem de novo na volta seguinte (o molde da ficha do frete)."""
    pasta = Path(cfg.envios_pasta) / "chamados"
    for li in linhas:
        a = li.get("anexo")
        if not a:
            continue
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / ("%d-%s" % (int(li["evento_id"]), _nome_seguro(a.get("nome"))))
        try:
            destino.write_bytes(baixar(cfg, token, int(a["id"])))
        except erp.ErpRecusou as e:
            # recusa definitiva: segurar a volta trancaria a ida de todos os chamados por um arquivo
            print("pendencias: %s -- a mensagem do evento %s sai so com o texto" % (e, li["evento_id"]),
                  flush=True)
            continue
        except OSError as e:
            raise erp.ErpIndisponivel("o anexo %s não pôde ser gravado: %s" % (a.get("id"), e)) from None
        li["_anexo"] = {"arquivo": str(destino), "nome": a.get("nome") or destino.name,
                        "media_type": a.get("media_type") or "application/pdf"}


# ── #1528: a volta com arquivo -- os arquivos que a pessoa devolveu vao ao ERP, e a rajada vira comentario ──

ESPERA_ANTIVIRUS = timedelta(hours=1)    # sem antivirus por mais que isso, o arquivo sai do transito
ESPERA_ERP = timedelta(hours=24)         # o ERP fora por mais que isso: a pessoa e avisada
AVISO_A_CADA = timedelta(hours=1)        # o aviso "sem antivirus" ao suporte: um por hora enquanto durar


def _hora(quando: datetime) -> str:
    from .vigia import _hora as h
    return h(quando)


def _marcar(con, mid: int, estado: str, mais: dict) -> None:
    con.execute("UPDATE atendimento.pendencias_mensagens SET estado = %s, arquivo = arquivo || %s WHERE id = %s",
                (estado, Jsonb(mais), mid))


def _apagar_copia(a: dict) -> None:
    if a.get("caminho"):
        Path(a["caminho"]).unlink(missing_ok=True)


def _gravar_ajuste(con, chave: str, valor) -> None:
    con.execute("""INSERT INTO atendimento.ajustes (chave, valor) VALUES (%s, %s)
                   ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor, atualizado_em = now()""",
                (chave, Jsonb(valor)))


def _avisar(con, tipo: str, texto: str) -> None:
    from .vigia import _avisar as av
    av(con, tipo, [texto])


def levar_arquivos(cfg, token: str, agora: datetime, enviar=erp.chamado_arquivo,
                   responder=erp.chamado_resposta) -> dict:
    """1. cada arquivo no transito vai a POST /demandas/whatsapp/{id}/arquivo; 2. cada rajada fechada, sem
    arquivo esperando o ERP, vira UM comentario com os anexos (a confirmacao a pessoa so nasce do evento
    que o ERP devolve: o fracasso silencioso da spec, item 7). Roda mesmo com a chave desligada: o que ja
    estava no caminho termina (ROLLBACK_PLAN 2)."""
    aceitos = recusados = sem_av = comentarios = 0
    with conexao(cfg) as con:
        transito = [dict(r) for r in con.execute(
            """SELECT m.id, m.arquivo, m.criado_em, p.referencia, p.para_whatsapp
                 FROM atendimento.pendencias_mensagens m JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                WHERE m.estado = 'arquivo_a_validar' AND p.tipo = 'chamado' ORDER BY m.id""").fetchall()]
        fora_desde = _ajuste(con, "pendencias.antivirus_fora_desde")
    voltou = 0
    for m in transito:
        a = dict(m["arquivo"] or {})
        if not a.get("caminho") or not Path(a["caminho"]).is_file():
            with conexao(cfg) as con:
                _marcar(con, m["id"], "arquivo_recusado", {"motivo": "sumiu", "texto": "o arquivo se perdeu no caminho"})
            recusados += 1
            continue
        try:
            r = enviar(cfg, token, int(m["referencia"]), m["para_whatsapp"], a["caminho"], a.get("nome") or "arquivo")
        except erp.SemAntivirus as x:
            sem_av += 1
            desde = a.get("av_desde") or agora.isoformat()
            with conexao(cfg) as con:
                if agora - datetime.fromisoformat(desde) > ESPERA_ANTIVIRUS:
                    _apagar_copia(a)
                    _marcar(con, m["id"], "arquivo_recusado", {"motivo": "antivirus_expirou", "texto": x.texto})
                else:
                    con.execute("UPDATE atendimento.pendencias_mensagens SET arquivo = arquivo || %s WHERE id = %s",
                                (Jsonb({"av_desde": desde, "texto": x.texto}), m["id"]))
                if not fora_desde:
                    fora_desde = agora.isoformat()
                    _gravar_ajuste(con, "pendencias.antivirus_fora_desde", fora_desde)
                ultimo = _ajuste(con, "pendencias.antivirus_aviso_em")
                if not ultimo or agora - datetime.fromisoformat(ultimo) >= AVISO_A_CADA:
                    _avisar(con, "arquivo_sem_antivirus",
                            "está recusando por falta de antivírus: o Defender não respondeu no servidor. Chamado %s, "
                            "de %s, %s. Os arquivos estão esperando." % (m["referencia"], a.get("quem") or "...%s"
                                                                         % m["para_whatsapp"][-4:], _hora(agora)))
                    _gravar_ajuste(con, "pendencias.antivirus_aviso_em", agora.isoformat())
            continue
        except erp.ArquivoRecusado as x:
            _apagar_copia(a)
            with conexao(cfg) as con:
                _marcar(con, m["id"], "arquivo_recusado", {"motivo": x.motivo, "texto": x.texto})
                if x.motivo == "ameaca":
                    _avisar(con, "arquivo_ameaca", "'%s', de %s (%s), chamado %s." % (
                        a.get("nome"), a.get("quem") or "quem mandou", m["para_whatsapp"], m["referencia"]))
            recusados += 1
            continue
        except erp.ErpRecusou as x:
            _apagar_copia(a)
            with conexao(cfg) as con:
                _marcar(con, m["id"], "arquivo_recusado", {"motivo": "erp", "texto": str(x)[:200]})
            recusados += 1
            continue
        except erp.ErpIndisponivel as x:
            print("pendencias: arquivo da mensagem %d: %s" % (m["id"], x), flush=True)
            if agora - m["criado_em"] > ESPERA_ERP:
                _apagar_copia(a)
                with conexao(cfg) as con:
                    _marcar(con, m["id"], "arquivo_recusado", {"motivo": "erp_fora",
                                                              "texto": "o sistema esteve fora do ar; mande de novo"})
            continue
        _apagar_copia(a)
        with conexao(cfg) as con:
            _marcar(con, m["id"], "arquivo_validado", {"anexo_id": int(r["anexo_id"]), "caminho": None})
        aceitos += 1
        voltou += 1 if a.get("av_desde") or fora_desde else 0
    if fora_desde and voltou and not sem_av:
        with conexao(cfg) as con:
            _avisar(con, "arquivo_sem_antivirus", "o antivírus voltou; %d %s." % (
                voltou, "arquivo entrou" if voltou == 1 else "arquivos entraram"))
            con.execute("DELETE FROM atendimento.ajustes WHERE chave IN ('pendencias.antivirus_fora_desde', "
                        "'pendencias.antivirus_aviso_em')")

    with conexao(cfg) as con:
        cabecas = [dict(r) for r in con.execute(
            """SELECT c.id, c.texto, c.pendencia_id, c.criado_em, p.referencia, p.para_whatsapp
                 FROM atendimento.pendencias_mensagens c JOIN atendimento.pendencias p ON p.id = c.pendencia_id
                WHERE c.estado = 'rajada' AND c.entregar_apos <= %s
                  AND NOT EXISTS (SELECT 1 FROM atendimento.pendencias_mensagens a
                                   WHERE a.rajada_id = c.id AND a.estado IN ('arquivo_a_validar', 'escolher'))
                ORDER BY c.id""", (agora,)).fetchall()]
    for c in cabecas:
        with conexao(cfg) as con:
            validos = [dict(r) for r in con.execute(
                """SELECT id, arquivo FROM atendimento.pendencias_mensagens
                    WHERE rajada_id = %s AND estado = 'arquivo_validado' ORDER BY id""", (c["id"],)).fetchall()]
        texto = (c["texto"] or "").strip()
        if not validos and not texto:
            with conexao(cfg) as con:
                con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'descartada' WHERE id = %s", (c["id"],))
            continue
        erro = None
        try:
            ev = responder(cfg, token, int(c["referencia"]), c["para_whatsapp"], texto,
                           [int(v["arquivo"]["anexo_id"]) for v in validos])
        except erp.ErpRecusou as x:
            erro = str(x)[:300]
        except erp.ErpIndisponivel as x:
            print("pendencias: rajada %d: %s" % (c["id"], x), flush=True)
            if agora - c["criado_em"] <= ESPERA_ERP:
                continue
            erro = "o ERP ficou fora do ar por mais de 24 h"
        with conexao(cfg) as con:
            with con.transaction():
                if erro:
                    con.execute("""UPDATE atendimento.pendencias_mensagens SET estado = 'confirmar', erro = %s,
                                          arquivo = %s WHERE id = %s""", (erro, Jsonb({"erro": erro}), c["id"]))
                    con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'erro', erro = %s WHERE id = ANY(%s)",
                                (erro, [v["id"] for v in validos]))
                    continue
                con.execute("""UPDATE atendimento.pendencias_mensagens SET estado = 'confirmar', entregue_em = %s,
                                      arquivo = %s WHERE id = %s""", (agora, Jsonb({"evento_id": ev}), c["id"]))
                con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'entregue', entregue_em = %s WHERE id = ANY(%s)",
                            (agora, [v["id"] for v in validos]))
                con.execute("""UPDATE atendimento.pendencias SET espera = CASE WHEN espera = 'resposta' THEN NULL ELSE espera END,
                                      ultima_em = %s WHERE id = %s""", (agora, c["pendencia_id"]))
        comentarios += 1
    return {"aceitos": aceitos, "recusados": recusados, "sem_antivirus": sem_av, "comentarios": comentarios}


def volta(cfg, trazer=erp.chamados_saida, estado=erp.chamados_estado, responder=erp.chamado_resposta,
          validar=erp.chamado_validar, agora: datetime | None = None, baixar=erp.chamado_anexo,
          enviar_arquivo=erp.chamado_arquivo) -> dict:
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
    if isinstance(cursor, int):
        try:
            baixar_anexos(cfg, token, r["linhas"], baixar)
        except erp.ErpIndisponivel as e:
            return {"erro": str(e)}   # nada gravado, cursor parado: a linha volta na proxima
    with conexao(cfg) as con:
        with con.transaction():   # o cursor so anda junto com o que foi gravado
            novas = receber(con, r["linhas"], agora) if isinstance(cursor, int) else 0
            _gravar_cursor(con, r["cursor"])
        entregar = _a_entregar(con, agora)
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

    arquivos = levar_arquivos(cfg, token, agora, enviar_arquivo, responder)   # #1528

    fechadas = 0
    try:
        demandas = estado(cfg, token, esperando) if esperando else []
        with conexao(cfg) as con:
            fechadas = conferir(con, demandas, agora)
    except erp.ErpIndisponivel as e:
        print("pendencias: estado: %s" % e, flush=True)
    return {"novas": novas, "entregues": entregues, "fechadas": fechadas, "arquivos": arquivos}


# ── #1276: o aviso de aprovação ──────────────────────────────────────────────────────────────────
# Outra fila do mesmo molde, com a regra própria: o ERP não manda eventos, manda o ESTADO (os pedidos
# que esperam aprovação agora). Cada pedido × etapa × número vira uma pendência `aprovacao` com UMA
# mensagem informativa; o RECEPCIONISTA manda (só na janela, juntando os pedidos da mesma pessoa).
# O pedido que some da lista foi decidido: a mensagem que ainda não saiu é descartada, e a pendência
# ganha o sufixo `~id` na referência -- libera a chave para um ciclo novo (o pedido recusado,
# corrigido e mandado de novo é aviso novo, não o mesmo).

def _filial_curta(nome) -> str:
    return (nome or "").split(" — ")[0].replace("FILIAL ", "").strip().title()


def texto_da_aprovacao(li: dict) -> str:
    valor = "R$ " + ("%.2f" % float(li.get("valor_total") or 0)).replace(".", ",")
    inteiro, cent = valor[3:].split(",")
    valor = "R$ " + "{:,}".format(int(inteiro)).replace(",", ".") + "," + cent
    partes = ["%s %s" % ("Venda" if li["tipo"] == "venda" else "Compra", li["numero"]), li.get("contraparte") or "",
              valor, li.get("condicao") or "", _filial_curta(li.get("filial"))]
    etapa = " (financeira)" if li.get("etapa") == "financeira" else ""
    return " · ".join(x for x in partes if x) + etapa


def receber_aprovacoes(con, linhas: list[dict], agora: datetime) -> int:
    """Grava o aviso dos pedidos que entraram na lista. Idempotente pela referência viva."""
    novas = 0
    for li in linhas:
        p = con.execute(
            """INSERT INTO atendimento.pendencias (tipo, referencia, titulo, para_whatsapp, ultima_em)
               VALUES ('aprovacao', %s, %s, %s, %s)
               ON CONFLICT (tipo, referencia, para_whatsapp) DO NOTHING RETURNING id""",
            (li["referencia"], (li.get("numero") or "")[:120], li["numero_whatsapp"], agora)).fetchone()
        if p is None:
            continue   # já avisado (ou esperando a janela) neste ciclo
        con.execute("""INSERT INTO atendimento.pendencias_mensagens (pendencia_id, sentido, classe, texto, estado, criado_em)
                       VALUES (%s, 'saiu', 'informativo', %s, 'esperando', %s)""",
                    (p["id"], texto_da_aprovacao(li)[:4000], agora))
        novas += 1
    return novas


def conferir_aprovacoes(con, linhas: list[dict], agora: datetime) -> int:
    """Encerra o ciclo do pedido que saiu da lista. Devolve quantos."""
    vivas = {(li["referencia"], li["numero_whatsapp"]) for li in linhas}
    feitas = 0
    for p in con.execute("""SELECT id, referencia, para_whatsapp FROM atendimento.pendencias
                             WHERE tipo = 'aprovacao' AND referencia NOT LIKE '%%~%%'""").fetchall():
        if (p["referencia"], p["para_whatsapp"]) in vivas:
            continue
        con.execute("""UPDATE atendimento.pendencias_mensagens SET estado = 'descartada', erro = 'decidido antes de sair'
                        WHERE pendencia_id = %s AND sentido = 'saiu' AND estado IN ('esperando', 'guardada')""", (p["id"],))
        con.execute("UPDATE atendimento.pendencias SET referencia = referencia || '~' || id, ultima_em = %s WHERE id = %s",
                    (agora, p["id"]))
        feitas += 1
    return feitas


def volta_aprovacoes(cfg, trazer=erp.aprovacoes, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now(timezone.utc)
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    with conexao(cfg) as con:
        if _ajuste(con, "pendencias.aprovacao.ligado", False) is not True:
            return {"desligado": True}
    try:
        linhas = trazer(cfg)
    except erp.ErpIndisponivel as e:
        return {"erro": str(e)}
    with conexao(cfg) as con:
        with con.transaction():
            fechadas = conferir_aprovacoes(con, linhas, agora)
            novas = receber_aprovacoes(con, linhas, agora)
    return {"novas": novas, "fechadas": fechadas}

