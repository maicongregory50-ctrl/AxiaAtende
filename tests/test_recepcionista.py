"""D1 do plano #950: o receptor confere a assinatura, grava cada aviso uma vez so, responde 200, e
EM ESCUTA nao responde ninguem."""
import hashlib
import hmac
import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend import recepcionista as R
from backend.banco import conexao
from tests.avisos_meta import aviso, status, texto, toque
from tests.saida_falsa import SaidaFalsa

QUINTA_14H = datetime(2026, 10, 8, 17, 0, tzinfo=timezone.utc)   # 14:00 em Sao Paulo, dia util


def assinar(corpo: bytes, segredo="segredo") -> dict:
    return {"X-Hub-Signature-256": "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest(),
            "Content-Type": "application/json"}


@pytest.fixture
def ligado(cfg):
    return replace(cfg, meta_app_secret="segredo", meta_verify_token="aperto", responde=True)


def _postar(c, dados, segredo="segredo"):
    corpo = json.dumps(dados).encode()
    return c.post("/webhook", content=corpo, headers=assinar(corpo, segredo))


def _eventos(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT chave_meta, tipo, processado_em, erro FROM atendimento.eventos_meta ORDER BY id").fetchall()


def test_aperto_de_mao_so_com_o_token_certo(ligado):
    with TestClient(R.criar_app(ligado, saida=SaidaFalsa(), trabalhador=False)) as c:
        ok = c.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "aperto", "hub.challenge": "123"})
        ruim = c.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "outro", "hub.challenge": "123"})
    assert ok.status_code == 200 and ok.text == "123"
    assert ruim.status_code == 403


def test_assinatura_errada_ou_ausente_e_recusada_e_nada_e_gravado(ligado):
    with TestClient(R.criar_app(ligado, saida=SaidaFalsa(), trabalhador=False)) as c:
        assert _postar(c, aviso([texto("wamid.1", "oi")]), segredo="errado").status_code == 401
        assert c.post("/webhook", json=aviso([texto("wamid.1", "oi")])).status_code == 401
        assert _postar(c, aviso([texto("wamid.2", "oi")])).status_code == 200
        ch = c.get("/saude").json()["chegadas"]      # a recusa aparece na saude (#969, 11/10)
        assert ch["recusadas"] == 2 and ch["aceitas"] == 1 and ch["ultima_recusada"] and ch["ultima_aceita"]
    assert [e["chave_meta"] for e in _eventos(ligado)] == ["wamid.2"]


def test_sem_segredo_configurado_recusa_tudo(cfg):
    with TestClient(R.criar_app(replace(cfg, meta_app_secret=""), saida=SaidaFalsa(), trabalhador=False)) as c:
        assert _postar(c, aviso([texto("wamid.1", "oi")])).status_code == 401


def test_o_mesmo_aviso_duas_vezes_entra_uma_vez_e_responde_uma_vez(ligado):
    s = SaidaFalsa()
    with TestClient(R.criar_app(ligado, saida=s, trabalhador=False)) as c:
        assert _postar(c, aviso([texto("wamid.1", "oi")])).status_code == 200
        assert _postar(c, aviso([texto("wamid.1", "oi")])).status_code == 200
    assert len(_eventos(ligado)) == 1
    R.processar_pendentes(ligado, s, None, agora=QUINTA_14H)
    R.processar_pendentes(ligado, s, None, agora=QUINTA_14H)
    assert len(s.enviadas) == 1


def test_em_escuta_grava_e_nao_responde_ninguem(ligado):
    escuta = replace(ligado, responde=False)
    s = SaidaFalsa()
    with TestClient(R.criar_app(escuta, saida=s, trabalhador=False)) as c:
        _postar(c, aviso([texto("wamid.1", "oi"), toque("wamid.2", "menu:fretes")]))
    R.processar_pendentes(escuta, s, None, agora=QUINTA_14H)
    R.rotina_do_minuto(escuta, s, agora=QUINTA_14H)
    assert s.enviadas == []
    ev = _eventos(escuta)
    assert len(ev) == 2 and all(e["processado_em"] and e["erro"] == "escuta" for e in ev)
    with conexao(escuta) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"] == 0


def test_no_ensaio_responde_so_aos_numeros_do_ensaio(ligado):
    ensaio = replace(ligado, responde_so_para=("5549991505565",))
    s = SaidaFalsa()
    with TestClient(R.criar_app(ensaio, saida=s, trabalhador=False)) as c:
        _postar(c, aviso([texto("wamid.1", "oi")]))                                    # um cliente
        _postar(c, aviso([texto("wamid.2", "oi", numero="5549991505565")], numero="5549991505565"))
    R.processar_pendentes(ensaio, s, None, agora=QUINTA_14H)
    assert [e["erro"] for e in _eventos(ensaio)] == ["escuta (ensaio)", ""]
    assert len(s.enviadas) == 1 and "5549991505565" in str(s.enviadas[0])


def test_status_da_meta_avanca_e_nao_volta(ligado):
    s = SaidaFalsa()
    with conexao(ligado) as con:
        con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo) VALUES ('wamid.s', '5549', 'texto')")
    R.gravar(ligado, aviso(statuses=[status("wamid.s", "read"), status("wamid.s", "delivered")]))
    R.processar_pendentes(ligado, s, None, agora=QUINTA_14H)
    with conexao(ligado) as con:
        assert con.execute("SELECT status FROM atendimento.enviadas WHERE wamid = 'wamid.s'").fetchone()["status"] == "lida"


def test_o_processo_exposto_nao_serve_tela_nem_api(ligado):
    with TestClient(R.criar_app(ligado, saida=SaidaFalsa(), trabalhador=False)) as c:
        assert c.get("/").status_code == 404
        assert c.get("/api/eu").status_code == 404
        assert c.get("/saude").json()["responde"] is True
