"""Os testes rodam no banco `teste` (5437, `axiaatende_teste`), que e recriado do zero a cada
sessao de testes. Nunca em producao: `carregar("teste")` nao le segredo nenhum."""
import pytest

from backend import migracoes
from backend.banco import conexao
from backend.config import carregar


def _zerar(cfg):
    with conexao(cfg) as con:
        con.execute("DROP SCHEMA IF EXISTS atendimento CASCADE")
        con.execute("DROP SCHEMA IF EXISTS casa CASCADE")


@pytest.fixture
def cfg(tmp_path):
    c = carregar("teste", logs=tmp_path / "logs")
    _zerar(c)
    migracoes.aplicar(c)
    return c
