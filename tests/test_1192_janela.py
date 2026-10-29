"""#1192 (dono, 29/10/2026): a janela do envio ao cliente -- segunda a sexta, das 9h30 as 17h, no
relogio de Sao Paulo. O lote do dia virava a 00h01; fora da janela nada sai, e o que ficou segue no
proximo dia util, as 9h30. Meta falsa: nada sai da maquina."""
from datetime import datetime, timezone

import pytest

from backend.banco import conexao
from backend.envio import Envio
from tests.saida_falsa import SaidaFalsa
from tests.test_envio import cliente, ligado, imagens, pedido, pedir  # noqa: F401 (fixtures)


def dia_util_10h():
    """Para o teste que precisa do MES CORRENTE (a previa do teto conta o mes de agora): o primeiro dia
    util do mes, as 10h de Sao Paulo -- dentro da janela, seja qual for a hora em que a bateria roda."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date().replace(day=1)
    while hoje.weekday() > 4:
        hoje += timedelta(days=1)
    return datetime(hoje.year, hoje.month, hoje.day, 13, 0, tzinfo=timezone.utc)


def _sp(dia, hora, minuto=0):
    """Hora de Sao Paulo (UTC-3) em UTC."""
    return datetime(2026, 11, dia, hora + 3, minuto, tzinfo=timezone.utc)


@pytest.mark.parametrize("quando,sai", [
    (_sp(4, 0, 1), False),     # quarta, 00h01: o caso de 29/10
    (_sp(4, 9, 29), False),    # um minuto antes
    (_sp(4, 9, 30), True),     # abre
    (_sp(4, 16, 59), True),
    (_sp(4, 17, 0), False),    # fecha
    (_sp(7, 10, 0), False),    # sabado
    (_sp(8, 10, 0), False),    # domingo
    (_sp(9, 9, 30), True),     # segunda, 9h30
])
def test_so_sai_dentro_da_janela(ligado, imagens, quando, sai):
    assert pedir(ligado, pedido(imagens, [cliente(1, 1000, whatsapp="47991110001")])).status_code == 200
    s = SaidaFalsa()
    with conexao(ligado) as con:
        assert (Envio(ler_nota=lambda: "GREEN").mandar_lotes(con, s, quando) > 0) is sai
