"""O tempo da JUNCAO do chamado no WhatsApp (o ajuste `pendencias.juntar_minutos`, #1222): quanto o sistema
espera, sem mensagem nova para a mesma pessoa, antes de mandar o que esta na fila dela. Vale na proxima volta
do recepcionista, SEM restart. Dono, 17/11/2026: "vamos baixar 1 min; se ficar ruim, subimos" (a pergunta a
Fran do #1539 esperou os 10 minutos sozinha). Em producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\pendencias.py mostrar
    .\\.venv\\Scripts\\python.exe scripts\\pendencias.py juntar 1

So aceita de 0 a 30 minutos. 0 = manda na hora, sem juntar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402

CHAVE = "pendencias.juntar_minutos"


def main() -> int:
    args = sys.argv[1:] or ["mostrar"]
    if args[0] not in ("mostrar", "juntar") or (args[0] == "juntar" and (len(args) != 2 or not args[1].isdigit()
                                                                          or not 0 <= int(args[1]) <= 30)):
        print("uso: pendencias.py mostrar | juntar <minutos de 0 a 30>")
        return 2
    cfg = config.carregar()
    with conexao(cfg) as con:
        antes = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (CHAVE,)).fetchone()
        if antes is None:
            print("RECUSADO: o ajuste %s nao existe neste banco (a migracao 052 nao foi aplicada?)" % CHAVE)
            return 1
        if args[0] == "juntar":
            con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now() WHERE chave = %s",
                        (args[1], CHAVE))
        agora = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (CHAVE,)).fetchone()["valor"]
    print("juncao do chamado no WhatsApp: %s min (era %s; ambiente %s). Vale na proxima volta, sem restart."
          % (agora, antes["valor"], cfg.ambiente))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
