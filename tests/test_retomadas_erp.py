"""#1193: a retomada registrada no ERP vira um aceite novo, por cima da recusa (que nao se apaga). O numero
no formato do toque; a mesma retomada duas vezes grava uma; a hora e a da retomada; ERP fora nao levanta."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from backend import erp, retomadas_erp
from backend.banco import conexao
from backend.envio import _ultimo_consentimento

AGORA = datetime.now(timezone.utc)
NUMERO = "5546999990000"           # como o toque grava: com_nove(wa_id)


@pytest.fixture
def ligado(cfg):
    return replace(cfg, erp_segredo="segredo-de-teste")


def _recusa(cfg, numero=NUMERO, em=AGORA - timedelta(days=2)):
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, bsuid, erp_codigo, tipo, wamid, em)
                       VALUES (%s, 'bsuid', 4639, 'recusa', 'wamid.1', %s)""", (numero, em))


def _ultimo(cfg, numero=NUMERO):
    with conexao(cfg) as con:
        return _ultimo_consentimento(con, numero)


def _retomada(id_=1, whatsapp="46999990000", em=AGORA - timedelta(hours=1)):
    return {"id": id_, "erp_codigo": 4639, "whatsapp": whatsapp, "meio": "ligacao",
            "feito_por_nome": "Maicon", "feito_em": em.isoformat()}


def test_sem_o_segredo_nem_tenta(cfg):
    chamado = []
    assert retomadas_erp.buscar(cfg, ler=lambda c, d: chamado.append(d)) == {"erro": "a ligação com o ERP não está ligada"}
    assert chamado == []


def test_a_retomada_vira_aceite_e_a_recusa_fica(ligado):
    _recusa(ligado)
    assert _ultimo(ligado) == "recusa"
    pedidos = []
    r = retomadas_erp.buscar(ligado, ler=lambda c, d: pedidos.append(d) or [_retomada()])
    assert r == {"lidas": 1, "gravadas": 1} and pedidos == [0]
    assert _ultimo(ligado) == "aceite"
    with conexao(ligado) as con:
        linhas = con.execute("""SELECT tipo, origem, retomada_ref, registrado_por FROM atendimento.consentimentos
                                 WHERE whatsapp = %s ORDER BY id""", (NUMERO,)).fetchall()
    assert [l["tipo"] for l in linhas] == ["recusa", "aceite"]        # a recusa NAO saiu
    assert linhas[1]["origem"] == "retomada" and linhas[1]["retomada_ref"] == 1
    assert linhas[1]["registrado_por"] == "Maicon (ligacao)"


def test_a_mesma_retomada_duas_vezes_grava_uma_e_a_proxima_pede_depois_dela(ligado):
    _recusa(ligado)
    retomadas_erp.buscar(ligado, ler=lambda c, d: [_retomada()])
    pedidos = []
    r = retomadas_erp.buscar(ligado, ler=lambda c, d: pedidos.append(d) or [_retomada()])
    assert r["gravadas"] == 0 and pedidos == [1]


def test_numero_sem_o_nove_acha_a_recusa_gravada_com_nove(ligado):
    _recusa(ligado)
    retomadas_erp.buscar(ligado, ler=lambda c, d: [_retomada(whatsapp="554699990000")])   # 12 digitos
    assert _ultimo(ligado) == "aceite"


def test_recusa_tocada_depois_da_retomada_continua_valendo(ligado):
    _recusa(ligado, em=AGORA - timedelta(days=2))
    _recusa(ligado, em=AGORA - timedelta(minutes=5))          # tocou de novo depois de retomado no ERP
    retomadas_erp.buscar(ligado, ler=lambda c, d: [_retomada(em=AGORA - timedelta(hours=1))])
    assert _ultimo(ligado) == "recusa"


def test_erp_fora_vira_erro_e_nada_e_gravado(ligado):
    def fora(c, d):
        raise erp.ErpIndisponivel("o ERP não respondeu")
    assert retomadas_erp.buscar(ligado, ler=fora) == {"erro": "o ERP não respondeu"}
    with conexao(ligado) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.consentimentos").fetchone()["n"] == 0


def test_o_consentimento_continua_imutavel(ligado):
    retomadas_erp.buscar(ligado, ler=lambda c, d: [_retomada()])
    with pytest.raises(psycopg.errors.RaiseException):
        with conexao(ligado) as con:
            con.execute("DELETE FROM atendimento.consentimentos WHERE origem = 'retomada'")


def _volta(cfg):
    from backend import migracoes
    sql = (migracoes.PASTA / "041_consentimento_retomada_VOLTA.sql").read_text(encoding="utf-8")
    with conexao(cfg) as con:
        con.execute(sql)


def test_a_volta_recusa_com_retomada_gravada(ligado):
    retomadas_erp.buscar(ligado, ler=lambda c, d: [_retomada()])
    with pytest.raises(psycopg.errors.RaiseException, match="regra 4"):
        _volta(ligado)


def test_a_volta_sem_retomada_tira_as_colunas(ligado):
    _recusa(ligado)
    _volta(ligado)
    with conexao(ligado) as con:
        cols = {r["column_name"] for r in con.execute(
            """SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'atendimento' AND table_name = 'consentimentos'""")}
        assert not cols & {"origem", "retomada_ref", "registrado_por"}
        assert con.execute("SELECT count(*) AS n FROM atendimento.consentimentos").fetchone()["n"] == 1
