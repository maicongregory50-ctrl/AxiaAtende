"""O uso de cada chamada a modelo pago, por funcao. #1223 (dono, 31/10/2026).

O UNICO escritor de `atendimento.uso_ia` neste processo. Quem chama e a `IA` (backend/ia.py), depois de
a API responder -- e por isso a gravacao vai numa CONEXAO PROPRIA e curta, no molde de
`texto_enviado.guardar_no_banco`: a chamada ja foi paga, e se a transacao de quem pediu desfizer, o
gasto continua sendo verdade. Qualquer erro aqui sobe para `IA._anotar`, que o poe no log e segue:
registrar o custo nunca derruba a resposta.

O uso do AxiaMarketing (Gemini) nao passa por aqui: chega por POST /pedido/uso-ia (rotas_pedido.py).
"""
from .banco import conexao
from .config import Config


def guardar_no_banco(cfg: Config):
    """A funcao que a `IA` recebe em `registrar`."""
    def registrar(funcao: str, modelo: str, entrada: int, saida: int) -> None:
        with conexao(cfg) as con:
            con.execute(
                """INSERT INTO atendimento.uso_ia (origem, servico, funcao, modelo, entrada, saida)
                   VALUES ('axiaatende', 'claude', %s, %s, %s, %s)""",
                (funcao, modelo, int(entrada or 0), int(saida or 0)))
    return registrar
