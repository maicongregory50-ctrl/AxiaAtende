"""Suspende (ou religa) um envio da carteira: o laco do recepcionista so manda envio `ativo`.

Quem ainda esta `aguardando` fica parado na fila, sem perder a posicao. Religar e o mesmo comando
com --religar (volta a `ativo`). Sem `--gravar`, SO MOSTRA. Em producao, janela elevada:

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\suspender_envio.py --envio 6
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\suspender_envio.py --envio 6 --gravar
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--envio", type=int, required=True)
    a.add_argument("--religar", action="store_true")
    a.add_argument("--gravar", action="store_true")
    args = a.parse_args()
    cfg = config.carregar()
    novo = "ativo" if args.religar else "suspenso"
    with conexao(cfg) as con:
        e = con.execute("SELECT id, pedido_ref, campanha, situacao FROM atendimento.envios WHERE id = %s",
                        (args.envio,)).fetchone()
        if not e:
            sys.exit("envio %s nao existe" % args.envio)
        print("ambiente: %s" % cfg.ambiente)
        print("envio %(id)s  %(pedido_ref)s  %(campanha)s  situacao agora: %(situacao)s" % e)
        for s in con.execute("""SELECT situacao, count(*) AS n FROM atendimento.envio_destinatarios
                                 WHERE envio_id = %s GROUP BY situacao ORDER BY situacao""", (e["id"],)):
            print("  %-16s %s" % (s["situacao"], s["n"]))
        if e["situacao"] == novo:
            print("ja esta %s; nada a fazer" % novo)
            return
        if not args.gravar:
            print("\nso mostrei. Para passar a %s, repita com --gravar" % novo)
            return
        con.execute("UPDATE atendimento.envios SET situacao = %s WHERE id = %s", (novo, e["id"]))
        print("\ngravado: envio %s agora %s" % (e["id"], novo))


if __name__ == "__main__":
    main()
