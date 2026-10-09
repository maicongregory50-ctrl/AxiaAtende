"""A separacao dos segredos (#950): as telas nunca carregam a chave da Meta nem a da Anthropic, e
o recepcionista nasce sem responder ninguem."""
import pytest

from backend import config


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAIZ", tmp_path)
    (tmp_path / ".env.secrets").write_text(
        "AXIAATENDE_BANCO_SENHA=s1\nMETA_TOKEN=nao-devia-estar-aqui\n", encoding="utf-8")
    (tmp_path / ".env.recepcionista").write_text(
        "AXIAATENDE_BANCO_SENHA=s2\nMETA_TOKEN=t\nMETA_APP_SECRET=a\nMETA_VERIFY_TOKEN=v\n"
        "ANTHROPIC_API_KEY=k\n", encoding="utf-8")
    return tmp_path


def test_telas_em_producao_nao_tem_chave_de_fora(raiz, monkeypatch):
    monkeypatch.setenv("AXIAATENDE_PROCESSO", "telas")
    c = config.carregar("producao")
    assert c.banco_senha == "s1" and c.meta_token == "" and c.anthropic_chave == ""


def test_recepcionista_le_o_proprio_arquivo_e_nasce_sem_responder(raiz, monkeypatch):
    monkeypatch.setenv("AXIAATENDE_PROCESSO", "recepcionista")
    c = config.carregar("producao")
    assert (c.banco_senha, c.meta_token, c.meta_app_secret, c.anthropic_chave) == ("s2", "t", "a", "k")
    assert c.responde is False


def test_segredo_nao_aparece_no_repr(raiz, monkeypatch):
    monkeypatch.setenv("AXIAATENDE_PROCESSO", "recepcionista")
    texto = repr(config.carregar("producao"))
    for valor in ("s2", "=t", "'t'", "'a'", "'k'", "'v'"):
        assert valor not in texto


def test_processo_desconhecido_recusa(monkeypatch):
    monkeypatch.setenv("AXIAATENDE_PROCESSO", "outro")
    with pytest.raises(RuntimeError):
        config.carregar("teste")
