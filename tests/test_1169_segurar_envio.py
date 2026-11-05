"""#1169 (dono, 05/11/2026): segurar o envio a carteira -- por envio e o "segurar tudo".
Spec: docs/specs/2026-11-05-segurar-o-envio-a-carteira.md. Meta falsa: nada sai da maquina."""
from datetime import datetime, timedelta, timezone

from backend import segurar
from backend.banco import conexao
from backend.envio import Envio
from tests.saida_falsa import SaidaFalsa
from tests.test_envio import QUINTA_10H, cliente, destinatarios, imagens, ligado, pedido, pedir  # noqa: F401

AGORA = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
DONO = "5549991505565"


def _convites(s):
    return [x for x in s.enviadas if x[0] == "modelo" and x[1] != DONO]


def _envio(cfg, envio_id=1):
    with conexao(cfg) as con:
        return dict(con.execute("SELECT * FROM atendimento.envios WHERE id = %s", (envio_id,)).fetchone())


def test_a_058_nasce_com_a_chave_desligada(ligado):
    with conexao(ligado) as con:
        assert segurar.estado(con) == {"ligado": False, "por": None, "em": None}


def test_segurar_tudo_para_os_convites_e_soltar_volta_so_o_que_ele_parou(ligado, imagens):
    pedir(ligado, pedido(imagens, [cliente(i, 1000 - i) for i in range(1, 6)], ref="pub-ativo"))
    with conexao(ligado) as con:
        assert segurar.ligar(con, "maicon@axia.com.br", AGORA) == 1
        assert segurar.estado(con)["ligado"] is True and segurar.estado(con)["por"] == "maicon@axia.com.br"
    e = _envio(ligado)
    assert (e["situacao"], e["suspenso_por"]) == ("suspenso", segurar.POR_SEGURAR)
    # o pedido que chega com a trava ligada entra e nasce suspenso (decisao 1)
    r = pedir(ligado, pedido(imagens, [cliente(i, 500 - i) for i in range(11, 14)], ref="pub-novo"))
    novo = _envio(ligado, r.json()["envio_id"])
    assert (novo["situacao"], novo["suspenso_por"]) == ("suspenso", segurar.POR_CHEGOU)
    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, QUINTA_10H)
    assert _convites(s) == []                                                       # nada sai, de envio nenhum
    with conexao(ligado) as con:
        assert segurar.desligar(con, "maicon@axia.com.br", AGORA + timedelta(hours=1)) == 1
    assert _envio(ligado)["situacao"] == "ativo"                                    # o que ele parou volta
    assert _envio(ligado, r.json()["envio_id"])["situacao"] == "suspenso"           # o que chegou na trava, nao
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, QUINTA_10H + timedelta(days=1))
    assert len(_convites(s)) == 5


def test_pedido_repetido_nao_muda_com_a_trava(ligado, imagens):
    pedir(ligado, pedido(imagens, [cliente(1, 10)], ref="pub-1"))
    with conexao(ligado) as con:
        segurar.desligar(con, "x", AGORA)
        con.execute("UPDATE atendimento.envios SET situacao = 'concluido'")
        segurar.ligar(con, "x", AGORA)
    pedir(ligado, pedido(imagens, [cliente(1, 10)], ref="pub-1"))                  # o mesmo pedido de novo
    assert _envio(ligado)["situacao"] == "concluido"


def test_suspender_e_religar_por_envio_com_quem_e_quando(ligado, imagens):
    pedir(ligado, pedido(imagens, [cliente(1, 10)]))
    with conexao(ligado) as con:
        segurar.suspender(con, 1, "fran@axia.com.br", AGORA)
        e = con.execute("SELECT * FROM atendimento.envios WHERE id = 1").fetchone()
        assert (e["situacao"], e["suspenso_por"], e["suspenso_em"]) == ("suspenso", "fran@axia.com.br", AGORA)
        try:
            segurar.suspender(con, 1, "x", AGORA)
            assert False, "suspender o suspenso devia recusar"
        except segurar.Recusa:
            pass
        segurar.ligar(con, "maicon", AGORA)
        try:
            segurar.religar(con, 1, "x", AGORA)                                      # com a trava ligada, nao
            assert False, "religar com a trava ligada devia recusar"
        except segurar.Recusa as r:
            assert "SEGURADO" in str(r)
        segurar.desligar(con, "maicon", AGORA)
        assert con.execute("SELECT situacao FROM atendimento.envios WHERE id = 1").fetchone()["situacao"] == "suspenso"
        segurar.religar(con, 1, "maicon", AGORA)                                      # suspenso pela pessoa: so ela religa
        assert con.execute("SELECT situacao, suspenso_por FROM atendimento.envios WHERE id = 1").fetchone() == \
            {"situacao": "ativo", "suspenso_por": "maicon"}
