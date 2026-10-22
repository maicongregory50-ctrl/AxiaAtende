"""#1090: o estado de cada mensagem enviada a um cliente vai para o Relacionamento do ERP.

Spec: C:\\AxiaGestao\\docs\\specs\\2026-10-22-relacionamento-crm-contato-ativo.md (passo 8 do plano).

O QUE VAI: cada destinatario de envio que SAIU (tem convite) ou que falhou, dos ultimos 60 dias, com
os campos crus -- convite, entregue, lido, resposta (quero / nao_quero / texto / falar), campanha,
tipo e peca. O ERP decide o estado e so o deixa avancar; mandar de novo o que ja foi nao duplica nada.
Por isso nao ha marca de "ja empurrado" aqui, nem migracao: o estado inteiro dos 60 dias vai a cada
volta, e e pequeno (lotes de ate 20 por dia).

O ENVIO AO CLIENTE NUNCA ESPERA O ERP: a volta roda numa thread propria do processo das TELAS, a cada
15 minutos, e erro so vai para o log. O recepcionista, que a internet alcanca, nao carrega o segredo.
"""
from datetime import datetime, timedelta, timezone

from . import erp
from .banco import conexao

DIAS = 60
PEDACO = 200
INTERVALO_SEGUNDOS = 15 * 60


def montar(con, agora: datetime | None = None) -> list[dict]:
    agora = agora or datetime.now(timezone.utc)
    linhas = con.execute(
        """SELECT d.id, d.erp_codigo, d.situacao, d.convite_em, d.entregue_em, d.lido_em,
                  d.resposta, d.resposta_em, d.resposta_texto, e.campanha, e.tipo, e.peca
             FROM atendimento.envio_destinatarios d
             JOIN atendimento.envios e ON e.id = d.envio_id
            WHERE (d.convite_em IS NOT NULL OR d.situacao = 'falhou')
              AND coalesce(d.convite_em, e.aprovado_em) >= %s
            ORDER BY d.id""", (agora - timedelta(days=DIAS),)).fetchall()
    def iso(v):
        return v.isoformat() if v else None
    return [{"destinatario_id": l["id"], "erp_codigo": l["erp_codigo"], "campanha": l["campanha"] or None,
             "tipo": l["tipo"], "peca": l["peca"], "situacao": l["situacao"], "convite_em": iso(l["convite_em"]),
             "entregue_em": iso(l["entregue_em"]), "lido_em": iso(l["lido_em"]), "resposta": l["resposta"],
             "resposta_em": iso(l["resposta_em"]), "resposta_texto": (l["resposta_texto"] or None) and l["resposta_texto"][:500]}
            for l in linhas]


def empurrar(cfg, enviar=erp.empurrar_eventos, agora: datetime | None = None) -> dict:
    """Uma volta. Devolve as contagens somadas do ERP, ou {"erro": motivo}. Sem o segredo, nem tenta."""
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    with conexao(cfg) as con:
        eventos = montar(con, agora)
    soma = {"enviados": len(eventos)}
    try:
        for i in range(0, len(eventos), PEDACO):
            for k, v in (enviar(cfg, eventos[i:i + PEDACO]) or {}).items():
                soma[k] = soma.get(k, 0) + int(v)
    except erp.ErpIndisponivel as e:
        return {"erro": str(e), **soma}
    return soma
