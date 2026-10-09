"""Os ultimos avisos da Meta e o que o recepcionista fez com eles. #950 (diagnostico do ensaio).

So leitura. Mostra o numero como a Meta o mandou (wa_id), o tipo e o erro gravado; nunca o texto
da mensagem. Em producao, janela elevada:

    $env:AXIAATENDE_AMBIENTE = 'producao'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\ultimos_eventos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402


def main() -> int:
    cfg = config.carregar()
    with conexao(cfg) as con:
        print("MENSAGENS RECEBIDAS (da mais nova; os avisos de entrega e leitura ficam de fora)")
        for e in con.execute("""SELECT id, to_char(recebido_em, 'HH24:MI:SS') AS hora, tipo,
                                       corpo->'contacts'->0->>'wa_id' AS wa_id, corpo->'msg'->>'type' AS msg,
                                       processado_em IS NOT NULL AS feito, erro
                                  FROM atendimento.eventos_meta WHERE tipo = 'mensagem' ORDER BY id DESC LIMIT 10""").fetchall():
            print("  #%s %s %-8s wa_id=%s msg=%s feito=%s erro=%s"
                  % (e["id"], e["hora"], e["tipo"], e["wa_id"], e["msg"], e["feito"], e["erro"] or "-"))
        print("ENVIADAS (do mais novo)")
        for e in con.execute("""SELECT id, to_char(enviada_em, 'HH24:MI:SS') AS hora, para, tipo, resumo,
                                       wamid IS NOT NULL AS aceita
                                  FROM atendimento.enviadas ORDER BY id DESC LIMIT 12""").fetchall():
            print("  #%s %s para=%s %s aceita=%s %s" % (e["id"], e["hora"], e["para"], e["tipo"], e["aceita"], e["resumo"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
