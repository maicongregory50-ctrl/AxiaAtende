"""#1097: a conversa de quem e da equipe e tocou "Foto do campo" termina com o que chegou ("Imagem
recebida" / "Logo recebida"), e nao "parou no meio"; a retomada da IA nao e gasta nela."""
from datetime import timedelta

from backend import motor
from backend.banco import conexao
from tests.avisos_meta import texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa
from tests.test_campo import AGORA, EQUIPE, canal, foto, ligar, passo  # noqa: F401 -- `canal` e fixture
from tests.test_logos import documento


def _menu_e_foto_do_campo(cfg, s):
    ligar(cfg)
    passo(cfg, s, texto("w1", "oi", numero=EQUIPE))
    passo(cfg, s, toque("w2", "menu:interna.campo", lista=True, numero=EQUIPE), agora=AGORA + timedelta(minutes=1))


def _ultima(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.conversas ORDER BY id DESC LIMIT 1").fetchone()


def test_tocou_foto_do_campo_e_mandou_a_foto_imagem_recebida(canal):
    s = SaidaFalsa()
    _menu_e_foto_do_campo(canal, s)
    passo(canal, s, foto("w3"), agora=AGORA + timedelta(minutes=2))
    passo(canal, s, foto("w4"), agora=AGORA + timedelta(minutes=2))   # a segunda do lote nao muda nada
    assert _ultima(canal)["situacao"] == "imagem_recebida"
    with conexao(canal) as con:
        assert motor.marcar_paradas(con, AGORA + timedelta(hours=2)) == 0


def test_tocou_foto_do_campo_e_mandou_a_logo_logo_recebida(canal):
    s = SaidaFalsa()
    _menu_e_foto_do_campo(canal, s)
    passo(canal, s, documento("w3", numero=EQUIPE), agora=AGORA + timedelta(minutes=2))
    assert _ultima(canal)["situacao"] == "logo_recebida"


def test_a_foto_chegou_depois_da_parada_ainda_fecha(canal):
    s = SaidaFalsa()
    _menu_e_foto_do_campo(canal, s)
    with conexao(canal) as con:
        motor.marcar_paradas(con, AGORA + timedelta(hours=1))
    assert _ultima(canal)["situacao"] == "parou_no_meio"
    passo(canal, s, foto("w3"), agora=AGORA + timedelta(hours=3))
    assert _ultima(canal)["situacao"] == "imagem_recebida"


def test_tocou_e_nao_mandou_e_parou_no_meio_sem_gastar_a_ia(canal):
    s = SaidaFalsa()
    _menu_e_foto_do_campo(canal, s)
    ia = IAFalsa(resposta="fretes")
    with conexao(canal) as con:
        motor.marcar_paradas(con, AGORA + timedelta(hours=1))
        assert motor.retomar_paradas(con, s, ia, AGORA + timedelta(hours=1)) == 0
    c = _ultima(canal)
    assert c["situacao"] == "parou_no_meio" and c["retomada_chave"] == "canal interno"
    assert ia.perguntas == []


def test_foto_sem_ter_tocado_no_menu_nao_mexe_em_conversa(canal):
    s = SaidaFalsa()
    ligar(canal)
    passo(canal, s, foto("w1"))
    with conexao(canal) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"] == 0


def test_conversa_de_cliente_no_meio_nao_vira_imagem(canal):
    s = SaidaFalsa()
    ligar(canal)
    passo(canal, s, texto("w1", "oi", numero=EQUIPE))
    passo(canal, s, toque("w2", "menu:interna.cliente", lista=True, numero=EQUIPE), agora=AGORA + timedelta(minutes=1))
    passo(canal, s, foto("w3"), agora=AGORA + timedelta(minutes=2))
    assert _ultima(canal)["situacao"] == "em_curso"   # a ultima escolha nao foi "Foto do campo"


def test_a_volta_da_026_devolve_a_parada_com_a_retomada_marcada(canal):
    from pathlib import Path
    s = SaidaFalsa()
    _menu_e_foto_do_campo(canal, s)
    passo(canal, s, foto("w3"), agora=AGORA + timedelta(minutes=2))
    volta = Path(__file__).resolve().parents[1] / "backend" / "migracoes" / "026_imagem_e_logo_recebida_VOLTA.sql"
    with conexao(canal) as con:
        con.execute(volta.read_text(encoding="utf-8").replace("BEGIN;", "").replace("COMMIT;", ""))
    c = _ultima(canal)
    assert c["situacao"] == "parou_no_meio" and c["retomada_em"] is not None
