"""Os avisos que o ERP deixa PENDENTE para o WhatsApp da equipe, por CANAL.

#350: a auditoria de estoque do ERP venceu -- o aviso vai ao WhatsApp de quem cuida dela.
Spec: C:\\AxiaGestao\\docs\\specs\\2026-10-30-auditoria-quinzenal-de-estoque.md (plano ao lado, passo 6).

#1337: uma API externa do ERP passou a recusar (#1280) -- o aviso vai ao WhatsApp do dono, pelo MESMO
caminho. Spec: docs/specs/2026-11-09-aviso-de-api-recusando-no-whatsapp.md. O caminho foi generalizado
em canais, e nao copiado: duas voltas iguais seriam dois lugares para corrigir o mesmo defeito.

Cada canal diz de onde busca (`ir`), para onde devolve (`devolver`) e quem recebe (`ajuste`); o `nome`
e o `tipo` do aviso e o `canal` da correlacao. Daqui, as TELAS, a cada minuto (`volta`), por canal:

1. trazem os pendentes e gravam uma linha em `atendimento.avisos` (tipo = o canal) para cada destino do
   ajuste do canal;
2. devolvem ao ERP ENVIADO (quando ao menos um saiu) ou FALHOU (quando todos deram erro ou ficaram
   nao vistos), e o ERP para de perguntar.

UM CANAL FORA DO AR NAO PARA O OUTRO: cada um devolve a propria contagem ou o proprio erro.

Quem manda e a volta de sempre dos avisos (`envio.mandar_avisos`): com o porteiro ligado, texto dentro da
janela e reabertura fora dela; o texto e o do modelo de uso `aviso_<canal>`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import erp
from .banco import conexao

INTERVALO_SEGUNDOS = 60
AJUSTE = "auditoria_estoque_para"


@dataclass(frozen=True)
class Canal:
    nome: str            # o tipo do aviso e o canal da correlacao
    ir: Callable         # cfg -> {"pendentes": [{"id", "partes"}], "token"}
    devolver: Callable   # (cfg, token, id, estado, motivo=, wamid=) -> None
    ajuste: str          # a chave dos destinos em atendimento.ajustes


CANAIS = (
    Canal("auditoria_estoque", erp.auditoria_pendentes, erp.estado_do_aviso_auditoria, AJUSTE),
    Canal("integracao_recusada", erp.integracoes_pendentes, erp.estado_do_aviso_integracao, "integracoes_para"),
)


def destinos(con, ajuste: str = AJUSTE) -> list[dict]:
    """Os destinos ativos do ajuste, na ordem do ajuste. Ajuste ausente ou vazio: ninguem."""
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (ajuste,)).fetchone()
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


def volta(cfg, ir=None, devolver=None, canais=CANAIS) -> dict:
    """Uma volta das TELAS sobre todos os canais: {"canais": {nome: contagem | {"erro"}}}. Sem o segredo,
    nem tenta: {"erro": motivo}.

    A assinatura do #350, `volta(cfg, ir=..., devolver=...)`, continua aceita: ela monta o canal da
    auditoria com as funcoes dadas e devolve a contagem dele sozinho, como antes."""
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    if ir is not None or devolver is not None:
        c = CANAIS[0]
        return volta_do_canal(cfg, Canal(c.nome, ir or c.ir, devolver or c.devolver, c.ajuste))
    return {"canais": {c.nome: volta_do_canal(cfg, c) for c in canais}}


def volta_do_canal(cfg, canal: Canal) -> dict:
    """Uma volta de um canal. Devolve a contagem, ou {"erro": motivo}."""
    try:
        r = canal.ir(cfg)
    except erp.ErpIndisponivel as e:
        return {"erro": str(e)}
    token, novos, devolvidos = r["token"], 0, 0

    with conexao(cfg) as con:
        ja = {x["erp_aviso_id"] for x in con.execute(
            "SELECT erp_aviso_id FROM atendimento.avisos_auditoria_erp WHERE canal = %s", (canal.nome,)).fetchall()}
        para = destinos(con, canal.ajuste)
        for p in r["pendentes"]:
            if p["id"] in ja:
                continue
            partes = [str(x).replace("|", "/") for x in (p.get("partes") or [])][:3]
            ids = [con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                                  VALUES (%s, %s, %s, %s) RETURNING id""",
                               (canal.nome, d["nome"], d["whatsapp"], "|".join(partes))).fetchone()["id"] for d in para]
            erro = "" if para else "Ninguém configurado para receber o aviso (ajuste %s)." % canal.ajuste
            con.execute("""INSERT INTO atendimento.avisos_auditoria_erp (canal, erp_aviso_id, aviso_ids, erro)
                           VALUES (%s, %s, %s, %s) ON CONFLICT (canal, erp_aviso_id) DO NOTHING""",
                        (canal.nome, p["id"], ids, erro))
            novos += 1
        abertos = [dict(x) for x in con.execute(
            """SELECT erp_aviso_id, aviso_ids, erro FROM atendimento.avisos_auditoria_erp
                WHERE canal = %s AND devolvido_em IS NULL ORDER BY erp_aviso_id""", (canal.nome,)).fetchall()]
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
            canal.devolver(cfg, token, erp_id, estado, motivo=motivo, wamid=wamid)
        except erp.ErpIndisponivel as e:
            print("%s: estado do aviso %s: %s" % (canal.nome, erp_id, e), flush=True)
            continue
        with conexao(cfg) as con:
            con.execute("""UPDATE atendimento.avisos_auditoria_erp SET devolvido_em = now()
                            WHERE canal = %s AND erp_aviso_id = %s""", (canal.nome, erp_id))
        devolvidos += 1
    return {"pendentes": len(r["pendentes"]), "novos": novos, "devolvidos": devolvidos}
