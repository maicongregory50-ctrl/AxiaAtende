"""Conexao com o banco do atendimento. #950 (molde: AxiaMarketing #869).

Uma conexao por pedido, aberta e fechada aqui. O volume e de dezenas de conversas por dia: pool
seria peca a mais para manter, e conexao presa e o defeito que pool esconde.
"""
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .config import Config


@contextmanager
def conexao(cfg: Config):
    """Abre, entrega, e fecha. COMMIT se o bloco terminou; ROLLBACK se levantou."""
    con = psycopg.connect(cfg.dsn(), row_factory=dict_row, connect_timeout=5)
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
