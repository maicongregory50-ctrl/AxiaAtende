"""#1222: os numeros da equipe que o Atende conhece, para copiar ao cadastro de usuario do ERP. So LE.
Em producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\numeros_da_equipe.py <arquivo.csv>

Duas fontes, as mesmas de `internos.quem_e`: a agenda lida do ERP (papel equipe ou representante) e os
destinos ativos. Para cada numero vai a ultima conversa e o nome de perfil do WhatsApp, que e o que
desempata quem tem dois numeros no cadastro (o que a pessoa usa e o que escreve para a empresa).
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import com_nove  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: numeros_da_equipe.py <arquivo.csv>")
        return 2
    cfg = config.carregar()
    linhas = []
    with conexao(cfg) as con:
        conversas = {}
        for c in con.execute("""SELECT wa_id, nome_perfil, ultimo_toque_em FROM atendimento.conversas
                                 WHERE wa_id IS NOT NULL ORDER BY ultimo_toque_em""").fetchall():
            conversas[com_nove(c["wa_id"])] = c
        for a in con.execute("""SELECT numero, codigo, nome, papeis, contato_nome FROM atendimento.agenda
                                 WHERE papeis && ARRAY['equipe', 'representante'] ORDER BY nome""").fetchall():
            linhas.append(("agenda", a["nome"], a["contato_nome"], com_nove(a["numero"]), ",".join(a["papeis"])))
        for d in con.execute("SELECT nome, whatsapp FROM atendimento.destinos WHERE ativo ORDER BY nome").fetchall():
            linhas.append(("destino", d["nome"], "", com_nove(d["whatsapp"]), "equipe"))
    with open(sys.argv[1], "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["fonte", "nome", "contato", "numero", "papeis", "nome_no_whatsapp", "ultima_conversa"])
        for fonte, nome, contato, numero, papeis in linhas:
            c = conversas.get(numero)
            w.writerow([fonte, nome, contato, numero, papeis, c["nome_perfil"] if c else "",
                        c["ultimo_toque_em"].strftime("%d/%m/%Y") if c else ""])
    print("%d numeros gravados em %s" % (len(linhas), sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
