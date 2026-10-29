"""Quem ficou "sem responsavel" num envio ATIVO e ja tem responsavel no ERP volta a fila (#1197).

Dono, 29/10/2026: "varios cadastros passaram a ser elegiveis de envio novamente, vamos rodar um lote
para estes" -- do Bom te ver de novo. A lista de um envio fica gravada quando ele nasce, e o AxiaAtende
nao le o ERP: quem estava sem responsavel naquele dia (a DISAM, pela CERES sem WhatsApp) continuaria
fora para sempre. Este script recebe o CSV dos responsaveis de hoje, tirado do ERP pela sessao
(`erp_codigo, responsavel_nome, responsavel_whatsapp, responsavel_canal`), e devolve a linha a
`aguardando`, na MESMA posicao do ranking: sai no proximo lote do envio, com as travas de sempre
(20 por dia, nota verde, janela de 9h30 as 17h, teto do comprador).

As outras travas da entrada do pedido (`envio.receber_pedido`), que a linha pulou por ter parado no
"sem responsavel", valem AQUI: quem recusou antes, quem ja recebeu a mesma peca e o numero que nao e
WhatsApp continuam fora.

Sem `--gravar`, SO MOSTRA. Em producao, janela elevada:

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\religar_sem_responsavel.py <csv>
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\religar_sem_responsavel.py <csv> --gravar
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import CELULAR, _ja_recebeu, _nao_e_whatsapp, _ultimo_consentimento  # noqa: E402

CANAIS = ("representante", "corretor", "dono", "flutuante")


def ler(caminho: str) -> dict:
    with open(caminho, encoding="utf-8") as fh:
        return {int(r["erp_codigo"]): r for r in csv.DictReader(fh)
                if CELULAR.match(r["responsavel_whatsapp"]) and r["responsavel_nome"]
                and r["responsavel_canal"] in CANAIS}


def religar(con, novos: dict, gravar: bool) -> list:
    """[(envio, erp_codigo, nome, posicao, o que acontece)] das linhas sem responsavel de envio ativo."""
    out = []
    for d in con.execute("""SELECT d.*, e.peca FROM atendimento.envio_destinatarios d
                              JOIN atendimento.envios e ON e.id = d.envio_id
                             WHERE e.situacao IN ('ativo', 'parado_nota') AND d.situacao = 'sem_responsavel'
                             ORDER BY e.id, d.posicao""").fetchall():
        r = novos.get(d["erp_codigo"])
        if not r:
            destino = "continua sem responsavel no ERP"
        # `aceite_cadastro` gravado e so True/False ("aceitou no ERP" ou nao), nao a recusa: a recusa e o
        # consentimento. O convite so leva quem aceitou (o marketing filtra antes do pedido).
        elif _ultimo_consentimento(con, d["whatsapp"]) == "recusa":
            destino = "recusou antes: fica fora"
        elif _ja_recebeu(con, d["whatsapp"], d["peca"]):
            destino = "ja recebeu esta peca: fica fora"
        elif _nao_e_whatsapp(con, d["whatsapp"]):
            destino = "o numero nao e WhatsApp: fica fora"
        else:
            destino = "volta a fila (responsavel: %s)" % r["responsavel_nome"]
            if gravar:
                con.execute("""UPDATE atendimento.envio_destinatarios
                                  SET situacao = 'aguardando', responsavel_nome = %s, responsavel_whatsapp = %s,
                                      responsavel_canal = %s
                                WHERE id = %s AND situacao = 'sem_responsavel'""",
                            (r["responsavel_nome"], r["responsavel_whatsapp"], r["responsavel_canal"], d["id"]))
        out.append((d["envio_id"], d["erp_codigo"], d["nome"], d["posicao"], destino))
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    gravar = "--gravar" in sys.argv
    novos = ler(args[0])
    cfg = config.carregar()
    with conexao(cfg) as con:
        linhas = religar(con, novos, gravar)
    voltam = [x for x in linhas if x[4].startswith("volta")]
    print("Envios ativos: %d linha(s) sem responsavel; %d voltam a fila" % (len(linhas), len(voltam)))
    for envio, codigo, nome, pos, destino in linhas:
        print("  envio %s  %3s  %-50s ERP %s  -> %s" % (envio, pos, (nome or "")[:50], codigo, destino))
    print("GRAVADO." if gravar else "Nada foi gravado. Para gravar: o mesmo comando com --gravar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
