"""Desfaz uma leva DIRETA gravada por `direto_do_envio.py` antes de ela sair. #1203.

Lista as levas feitas a partir de um envio de origem (o convite), com quantas linhas vieram de cada
grupo (`faltam`: o convite nem saiu; `reenvio`: recebeu o convite e nao tocou) e quantas ja sairam.
Com `--envio N --gravar`, APAGA a leva N -- so se nada dela saiu (nenhum convite_em, nenhuma falha):
o que nao foi mandado nao deixou rastro no ERP nem no WhatsApp, e o grupo volta a ser calculado do
zero na proxima vez (o `direto_do_envio.py` nao poe de novo quem ja esta numa leva).

Sem `--gravar`, SO MOSTRA. Em producao, janela elevada:

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\desfazer_leva.py --origem 6
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\desfazer_leva.py --origem 6 --envio N --gravar
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402


def levas(con, origem):
    return con.execute(
        """SELECT x.id, x.pedido_ref, x.situacao, x.modelo, x.recebido_em,
                  count(d.*) AS linhas,
                  count(d.*) FILTER (WHERE o.situacao = 'aguardando') AS faltam,
                  count(d.*) FILTER (WHERE o.situacao = 'convidado') AS reenvio,
                  count(d.*) FILTER (WHERE d.convite_em IS NOT NULL OR d.situacao <> 'aguardando') AS mexidas
             FROM atendimento.envios x
             JOIN atendimento.envio_destinatarios d ON d.envio_id = x.id
             LEFT JOIN atendimento.envio_destinatarios o ON o.envio_id = %s AND o.whatsapp = d.whatsapp
            WHERE x.pedido_ref LIKE %s AND x.pedido_ref NOT LIKE %s
            GROUP BY x.id ORDER BY x.id""",
        (origem["id"], origem["pedido_ref"] + "-direto-%", origem["pedido_ref"] + "-prova-%")).fetchall()


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--origem", type=int, required=True, help="o envio de origem (o convite)")
    a.add_argument("--envio", type=int, help="a leva a desfazer")
    a.add_argument("--gravar", action="store_true")
    args = a.parse_args()
    cfg = config.carregar()
    print("ambiente:", cfg.ambiente)
    with conexao(cfg) as con:
        o = con.execute("SELECT * FROM atendimento.envios WHERE id = %s", (args.origem,)).fetchone()
        if not o:
            sys.exit("envio %s nao existe" % args.origem)
        todas = levas(con, o)
        print("levas diretas do envio %s (%s):" % (o["id"], o["pedido_ref"]))
        for v in todas:
            print("  envio %(id)s  %(pedido_ref)s  %(situacao)s  %(linhas)s clientes "
                  "(faltam %(faltam)s, reenvio %(reenvio)s)  ja mexidas: %(mexidas)s" % v)
        if not args.envio:
            print("\ndiga a leva com --envio N")
            return
        v = next((v for v in todas if v["id"] == args.envio), None)
        if not v:
            sys.exit("o envio %s nao e uma leva direta do envio %s" % (args.envio, args.origem))
        if v["mexidas"]:
            sys.exit("a leva %s ja mandou (ou tentou) %s mensagem(ns): nao apago; suspenda com suspender_envio.py"
                     % (v["id"], v["mexidas"]))
        if not args.gravar:
            print("\nso mostrei. Para apagar a leva %s, repita com --gravar" % v["id"])
            return
        con.execute("DELETE FROM atendimento.envio_destinatarios WHERE envio_id = %s", (v["id"],))
        con.execute("DELETE FROM atendimento.envios WHERE id = %s", (v["id"],))
        print("\napagada: leva %s (%s), %s clientes. Nada dela tinha saido." % (v["id"], v["pedido_ref"], v["linhas"]))


if __name__ == "__main__":
    main()
