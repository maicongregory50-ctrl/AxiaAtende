"""#1090: o estado das mensagens enviadas a clientes vai ao Relacionamento do ERP. So o que SAIU (ou
falhou), com os campos crus; o ERP decide o estado. ERP fora do ar nao levanta nada."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import envio, erp, eventos_erp
from backend.banco import conexao
from tests.test_envio import cliente, pedido

AGORA = datetime.now(timezone.utc)


@pytest.fixture
def ligado(cfg):
    return replace(cfg, erp_segredo="segredo-de-teste")


@pytest.fixture
def um_envio(ligado, tmp_path):
    capa = tmp_path / "capa.jpg"
    capa.write_bytes(b"\xff\xd8\xff")
    p = {**pedido([str(capa), str(capa)], [cliente(4639, 10), cliente(7, 5)]), "campanha": "CAM-0008 · Plano safra de inverno 26/27"}
    with conexao(ligado) as con:
        envio.receber_pedido(con, p)
        con.execute("""UPDATE atendimento.envio_destinatarios SET convite_em = %s, entregue_em = %s, lido_em = %s,
                              resposta = 'falar', resposta_em = %s WHERE erp_codigo = 4639""", (AGORA, AGORA, AGORA, AGORA))
    return ligado


def test_sem_o_segredo_nem_tenta(cfg):
    chamado = []
    assert eventos_erp.empurrar(cfg, enviar=lambda c, e: chamado.append(e)) == {"erro": "a ligação com o ERP não está ligada"}
    assert chamado == []


def test_vai_so_quem_recebeu_com_os_campos_crus(um_envio):
    with conexao(um_envio) as con:
        ev = eventos_erp.montar(con, AGORA)
    assert [e["erp_codigo"] for e in ev] == [4639]          # o 7 nao saiu ainda: nao vai
    e = ev[0]
    assert e["resposta"] == "falar" and e["lido_em"] and e["campanha"].startswith("CAM-0008")
    assert isinstance(e["convite_em"], str)                  # vai como JSON


def test_mais_de_60_dias_nao_vai(um_envio):
    with conexao(um_envio) as con:
        assert eventos_erp.montar(con, AGORA + timedelta(days=61)) == []


def test_soma_as_respostas_do_erp_por_pedaco(um_envio, monkeypatch):
    monkeypatch.setattr(eventos_erp, "PEDACO", 1)
    lotes = []
    r = eventos_erp.empurrar(um_envio, enviar=lambda c, e: lotes.append(e) or {"novos": len(e), "iguais": 0})
    assert r == {"enviados": 1, "novos": 1, "iguais": 0} and len(lotes) == 1


def test_erp_fora_vira_erro_sem_levantar(um_envio):
    def fora(c, e):
        raise erp.ErpIndisponivel("o ERP não respondeu")
    assert eventos_erp.empurrar(um_envio, enviar=fora) == {"erro": "o ERP não respondeu", "enviados": 1}
