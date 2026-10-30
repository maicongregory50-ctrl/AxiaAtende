"""#350: a auditoria de estoque do ERP venceu -- o aviso vai ao WhatsApp de quem cuida dela.

Spec: C:\\AxiaGestao\\docs\\specs\\2026-10-30-auditoria-quinzenal-de-estoque.md (plano ao lado, passo 6).

O job diario do ERP decide se a quinzena venceu e deixa um aviso PENDENTE (no dia do vencimento e de
novo a cada 7 dias). Daqui, as TELAS, a cada minuto (`volta`):

1. trazem os pendentes e gravam uma linha em `atendimento.avisos` (tipo `auditoria_estoque`) para cada
   destino do ajuste `auditoria_estoque_para` (o dono e a Fran, dono 30/10/2026);
2. devolvem ao ERP ENVIADO (quando ao menos um saiu) ou FALHOU (quando todos deram erro ou ficaram
   nao vistos), e o ERP para de perguntar.

Quem manda e a volta de sempre dos avisos (`envio.mandar_avisos`): com o porteiro ligado, texto dentro da
janela e reabertura fora dela; o texto e o do modelo `aviso_auditoria_estoque`.
"""
from __future__ import annotations

from . import erp
from .banco import conexao

INTERVALO_SEGUNDOS = 60
AJUSTE = "auditoria_estoque_para"


def destinos(con) -> list[dict]:
    """Os destinos ativos do ajuste, na ordem do ajuste. Ajuste ausente ou vazio: ninguem."""
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (AJUSTE,)).fetchone()
    ids = r["valor"] if r and isinstance(r["valor"], list) else ([r["valor"]] if r and isinstance(r["valor"], int) else [])
    if not ids:
        return []
    linhas = {d["id"]: dict(d) for d in con.execute(
        "SELECT id, nome, whatsapp FROM atendimento.destinos WHERE ativo AND id = ANY(%s)", (ids,)).fetchall()}
    return [linhas[i] for i in ids if i in linhas]


def _situacao(avisos: list[dict]) -> tuple[str, str, str] | None:
    """(estado, motivo, wamid) quando ja ha resposta para o ERP; None enquanto algum espera."""
    enviados = [a for a in avisos if a["enviado_em"]]
    if enviados:
        return "ENVIADO", "", enviados[0]["wamid"] or ""
    if avisos and all(a["erro"] or a["nao_visto_em"] for a in avisos):
        motivo = next((a["erro"] for a in avisos if a["erro"]), "") or "o aviso ficou sem ser visto"
        return "FALHOU", motivo, ""
    return None


def volta(cfg, ir=erp.auditoria_pendentes, devolver=erp.estado_do_aviso_auditoria) -> dict:
    """Uma volta das TELAS. Devolve a contagem, ou {"erro": motivo}. Sem o segredo, nem tenta."""
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    try:
        r = ir(cfg)
    except erp.ErpIndisponivel as e:
        return {"erro": str(e)}
    token, novos, devolvidos = r["token"], 0, 0

    with conexao(cfg) as con:
        ja = {x["erp_aviso_id"] for x in con.execute("SELECT erp_aviso_id FROM atendimento.avisos_auditoria_erp").fetchall()}
        para = destinos(con)
        for p in r["pendentes"]:
            if p["id"] in ja:
                continue
            partes = [str(x).replace("|", "/") for x in (p.get("partes") or [])][:3]
            ids = [con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                                  VALUES ('auditoria_estoque', %s, %s, %s) RETURNING id""",
                               (d["nome"], d["whatsapp"], "|".join(partes))).fetchone()["id"] for d in para]
            erro = "" if para else "Ninguém configurado para receber o aviso (ajuste %s)." % AJUSTE
            con.execute("""INSERT INTO atendimento.avisos_auditoria_erp (erp_aviso_id, aviso_ids, erro)
                           VALUES (%s, %s, %s) ON CONFLICT (erp_aviso_id) DO NOTHING""", (p["id"], ids, erro))
            novos += 1
        abertos = [dict(x) for x in con.execute(
            """SELECT erp_aviso_id, aviso_ids, erro FROM atendimento.avisos_auditoria_erp
                WHERE devolvido_em IS NULL ORDER BY erp_aviso_id""").fetchall()]
        respostas = []
        for v in abertos:
            if v["erro"]:
                respostas.append((v["erp_aviso_id"], ("FALHOU", v["erro"], "")))
                continue
            avisos = [dict(a) for a in con.execute(
                "SELECT enviado_em, wamid, erro, nao_visto_em FROM atendimento.avisos WHERE id = ANY(%s)",
                (v["aviso_ids"],)).fetchall()]
            s = _situacao(avisos)
            if s:
                respostas.append((v["erp_aviso_id"], s))

    for erp_id, (estado, motivo, wamid) in respostas:
        try:
            devolver(cfg, token, erp_id, estado, motivo=motivo, wamid=wamid)
        except erp.ErpIndisponivel as e:
            print("auditoria: estado do aviso %s: %s" % (erp_id, e), flush=True)
            continue
        with conexao(cfg) as con:
            con.execute("UPDATE atendimento.avisos_auditoria_erp SET devolvido_em = now() WHERE erp_aviso_id = %s",
                        (erp_id,))
        devolvidos += 1
    return {"pendentes": len(r["pendentes"]), "novos": novos, "devolvidos": devolvidos}
