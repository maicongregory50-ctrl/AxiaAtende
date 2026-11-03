"""#1238, passo 1: a 054 nasce desligada, vai, volta e vai de novo."""
from pathlib import Path

import psycopg
import pytest

from backend import migracoes
from backend.banco import conexao

PASTA = Path(__file__).resolve().parents[1] / "backend" / "migracoes"


def _ajuste(con, chave):
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (chave,)).fetchone()
    return r["valor"] if r else None


def test_a_054_nasce_desligada(cfg):
    with conexao(cfg) as con:
        assert _ajuste(con, "roteador.ligado") is False
        assert _ajuste(con, "audio.transcrever") is False
        assert _ajuste(con, "roteador.carencia_minutos") == 3
        assert _ajuste(con, "audio.maximo_s") == 180
        p = con.execute("SELECT * FROM atendimento.precos WHERE servico = 'local'").fetchone()
        assert p["item"] == "faster-whisper-large-v3-turbo" and p["por_milhao_entrada"] == 0
        con.execute("""INSERT INTO atendimento.uso_ia (origem, servico, funcao, modelo, entrada, saida)
                       VALUES ('axiaatende', 'local', 'audio', 'faster-whisper-large-v3-turbo', 30, 120)""")


def test_o_sinal_e_a_confianca_sao_lista_fechada(cfg):
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao(cfg) as con:
            con.execute("INSERT INTO atendimento.roteador (wamid, wa_id, sinal) VALUES ('w1', '5549', 'palpite')")
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao(cfg) as con:
            con.execute("INSERT INTO atendimento.roteador (wamid, wa_id, confianca) VALUES ('w2', '5549', 'media')")


def test_a_054_vai_volta_e_vai(cfg):
    volta = (PASTA / "054_roteador_e_audio_VOLTA.sql").read_text(encoding="utf-8")
    with conexao(cfg) as con:
        con.execute(volta.replace("BEGIN;", "").replace("COMMIT;", ""))
        assert con.execute("SELECT to_regclass('atendimento.roteador') AS t").fetchone()["t"] is None
        assert _ajuste(con, "roteador.ligado") is None
    assert migracoes.aplicar(cfg) == ["054_roteador_e_audio.sql"]
    with conexao(cfg) as con:
        assert _ajuste(con, "roteador.ligado") is False
