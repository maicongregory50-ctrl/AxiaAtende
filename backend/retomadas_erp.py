"""#1193: a retomada que uma pessoa registra no ERP vira um aceite novo aqui.

Spec: C:\\AxiaGestao\\docs\\specs\\2026-10-29-relacionamento-parar-e-retomar.md (passo 8 do plano).

O cliente que tocou "Nao quero receber" tem uma recusa em atendimento.consentimentos, e o envio olha o
ULTIMO consentimento do numero (envio._ultimo_consentimento; a tela Quem recebe do marketing, pelo
/pedido/aceites, idem). Quando o responsavel fala com ele e ele aceita voltar, o ERP grava a retomada
(axia.rel_retomadas, com quem, quando e o meio); esta volta a busca e grava um ACEITE com origem
'retomada'. A recusa NAO e apagada (regra 4): o aceite novo fica por cima, e uma recusa ainda mais nova
vence de novo. A HORA do aceite e a da retomada no ERP (`feito_em`), nao a da busca: uma recusa tocada
nesse meio tempo continua sendo a ultima.

O NUMERO no formato do toque: `com_nove(so_digitos(...))`, 55 + DDD + 9 + oito digitos. O ERP guarda
233 de 794 contatos sem o 9 (medido em 29/10); sem a normalizacao a retomada nao acharia a recusa.

Roda na volta de 15 minutos do processo das TELAS (main.empurrar_os_eventos), depois dos eventos, em
tentativa propria. O recepcionista, que a internet alcanca, nao carrega o segredo. Erro so vai ao log.
"""
from . import erp
from .banco import conexao
from .envio import com_nove, so_digitos


def buscar(cfg, ler=erp.retomadas) -> dict:
    """Uma volta. Devolve {"lidas": n, "gravadas": n} ou {"erro": motivo}. Sem o segredo, nem tenta."""
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    with conexao(cfg) as con:
        depois = con.execute("SELECT coalesce(max(retomada_ref), 0) AS m FROM atendimento.consentimentos").fetchone()["m"]
    try:
        linhas = ler(cfg, depois)
    except erp.ErpIndisponivel as e:
        return {"erro": str(e)}
    gravadas = 0
    with conexao(cfg) as con:
        for r in linhas:
            numero = com_nove(so_digitos(r.get("whatsapp") or ""))
            if not numero:
                continue
            gravadas += con.execute(
                """INSERT INTO atendimento.consentimentos
                       (whatsapp, bsuid, erp_codigo, tipo, wamid, origem, retomada_ref, registrado_por, em)
                   VALUES (%s, '', %s, 'aceite', '', 'retomada', %s, %s, coalesce(%s::timestamptz, now()))
                   ON CONFLICT (retomada_ref) WHERE retomada_ref IS NOT NULL DO NOTHING""",
                (numero, r.get("erp_codigo"), int(r["id"]),
                 "%s (%s)" % (r.get("feito_por_nome") or "ERP", r.get("meio") or "?"),
                 r.get("feito_em"))).rowcount
    return {"lidas": len(linhas), "gravadas": gravadas}
