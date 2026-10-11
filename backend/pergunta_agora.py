"""A pergunta "Recebeu o atendimento?" de UMA conversa, agora, para provar o caminho (#969).

    python -m backend.pergunta_agora --ver             so leitura: as conversas que esperam a pergunta
    python -m backend.pergunta_agora --conversa N      manda a pergunta da conversa N ja

Sem isto a prova espera as 4h30 e a faixa da pergunta. Manda so para a conversa escolhida; as
outras continuam esperando a hora delas. O toque na resposta chega ao recepcionista como qualquer
outro, e dali em diante e o caminho de todo dia (a nota em tres botoes, o aviso do "Ruim").
"""
import argparse
import sys
from datetime import datetime, timezone

from . import config, motor
from .banco import conexao


def pendentes(con) -> list[dict]:
    return [dict(r) for r in con.execute(
        """SELECT c.id, right(coalesce(c.wa_id, ''), 4) AS final, c.caminho, d.nome AS atende,
                  to_char(c.link_em AT TIME ZONE 'America/Sao_Paulo', 'DD/MM HH24:MI') AS link,
                  to_char(c.pergunta_em AT TIME ZONE 'America/Sao_Paulo', 'DD/MM HH24:MI') AS pergunta
             FROM atendimento.conversas c LEFT JOIN atendimento.destinos d ON d.id = c.destino_id
            WHERE c.situacao = 'com_link' AND c.pergunta_feita_em IS NULL
            ORDER BY c.id DESC LIMIT 20""").fetchall()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ver", action="store_true")
    g.add_argument("--conversa", type=int)
    a = ap.parse_args(argv)
    cfg = config.carregar()
    with conexao(cfg) as con:
        if a.ver:
            linhas = pendentes(con)
            for p in linhas:
                print("conversa %(id)s  final %(final)s  %(caminho)s  com %(atende)s  link %(link)s  "
                      "pergunta marcada %(pergunta)s" % p)
            if not linhas:
                print("nenhuma conversa esperando a pergunta")
            return 0
        from .saida import SaidaMeta
        saiu = motor.perguntar_agora(con, SaidaMeta(cfg.meta_phone_id, cfg.meta_token), a.conversa,
                                     datetime.now(timezone.utc))
    print("pergunta enviada" if saiu else
          "nada saiu: a conversa %s nao espera pergunta, ou passou das 24h" % a.conversa)
    return 0 if saiu else 1


if __name__ == "__main__":
    sys.exit(main())
