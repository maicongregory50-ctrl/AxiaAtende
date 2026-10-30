"""Manda AGORA a prova gravada por `direto_do_envio.py --prova`, fora da janela de envio (9h30-17h).

So serve para PROVA: o envio tem de ter a campanha "PROVA - ..." e uma linha so, de codigo 0 (o numero
do dono). Envio de cliente continua saindo so pelo laco do recepcionista, dentro da janela.
Sem `--gravar`, SO MOSTRA. Em producao, janela elevada (le o token do .env.recepcionista):

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\prova_agora.py
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\prova_agora.py --gravar
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import Envio, modelo  # noqa: E402


def main(argv=None, saida=None):
    a = argparse.ArgumentParser()
    a.add_argument("--envio", type=int, help="o envio da prova; sem ele, a prova mais recente por mandar")
    a.add_argument("--gravar", action="store_true")
    args = a.parse_args(argv)
    cfg = config.carregar()
    print("ambiente:", cfg.ambiente)
    with conexao(cfg) as con:
        e = con.execute(
            """SELECT * FROM atendimento.envios WHERE campanha LIKE 'PROVA - %%'
                  AND (%s::int IS NULL OR id = %s) AND situacao = 'ativo'
                ORDER BY id DESC LIMIT 1""", (args.envio, args.envio)).fetchone()
        if not e:
            sys.exit("nenhuma prova ativa (grave antes com direto_do_envio.py --prova ... --gravar)")
        linhas = con.execute("SELECT * FROM atendimento.envio_destinatarios WHERE envio_id = %s",
                             (e["id"],)).fetchall()
        if len(linhas) != 1 or linhas[0]["erp_codigo"] != 0:
            sys.exit("o envio %s nao e uma prova (uma linha, codigo 0): nao mando fora da janela" % e["id"])
        d = linhas[0]
        m = modelo(con, e["modelo"])
        print("prova: envio %s (%s), modelo %s, para %s (%s), situacao %s"
              % (e["id"], e["pedido_ref"], e["modelo"], d["nome"], d["whatsapp"], d["situacao"]))
        if d["situacao"] != "aguardando":
            sys.exit("a prova ja saiu ou parou (%s); grave outra" % d["situacao"])
        if not args.gravar:
            print("\nso mostrei. Para mandar agora, repita com --gravar")
            return
        if saida is None:
            if not cfg.meta_token:
                sys.exit("sem o token da Meta: rode com AXIAATENDE_PROCESSO=recepcionista, em janela elevada")
            from backend.saida import SaidaMeta
            from backend.texto_enviado import guardar_no_banco   # #1205
            saida = SaidaMeta(cfg.meta_phone_id, cfg.meta_token, guardar=guardar_no_banco(cfg))
        env = Envio()
        env._segredo = cfg.meta_app_secret
        env._mandar_um(con, saida, e, m, d, 1, datetime.now(timezone.utc))
        r = con.execute("SELECT situacao, erro, convite_wamid FROM atendimento.envio_destinatarios WHERE id = %s",
                        (d["id"],)).fetchone()
        if r["situacao"] == "convidado":
            print("\nmandada: %s. Confira o WhatsApp." % r["convite_wamid"])
        else:
            print("\nNAO SAIU (%s): %s" % (r["situacao"], r["erro"]))


if __name__ == "__main__":
    main()
