"""O texto exato do que nos mandamos, por wamid. #1205 (dono, 30/10/2026).

O UNICO escritor de `atendimento.enviadas_texto`. Quem chama e a `SaidaMeta`, depois de a Meta aceitar
o envio -- e por isso a gravacao vai numa CONEXAO PROPRIA e curta, e nao na transacao de quem mandou:
o envio ja saiu, e se a transacao do motor desfizer, o texto continua sendo a verdade do que o
cliente leu. Os 13 pontos que gravam `enviadas` (o resumo) nao mudam: a janela da Recepcao junta os
dois pelo wamid.

A chave: o ajuste `enviadas.guardar_texto`. Em `false`, nada e gravado a partir do proximo envio,
sem restart (ROLLBACK 1 da spec). Qualquer erro aqui sobe para `SaidaMeta._guardado`, que o anota no
log e devolve o wamid: guardar o texto nunca derruba o envio.
"""
import json

from .banco import conexao
from .config import Config


def guardar_no_banco(cfg: Config):
    """A funcao que a `SaidaMeta` recebe em `guardar`."""
    def guardar(wamid: str, tipo: str, conteudo: dict) -> None:
        with conexao(cfg) as con:
            r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'enviadas.guardar_texto'").fetchone()
            if r is not None and r["valor"] is False:
                return
            opcoes = conteudo.get("opcoes")
            con.execute(
                """INSERT INTO atendimento.enviadas_texto (wamid, tipo, texto, opcoes, modelo, variaveis, legenda)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (wamid) DO NOTHING""",
                (wamid, tipo, conteudo.get("texto") or "",
                 json.dumps(opcoes, ensure_ascii=False) if opcoes is not None else None,
                 conteudo.get("modelo"), conteudo.get("variaveis"), conteudo.get("legenda") or ""))
    return guardar
