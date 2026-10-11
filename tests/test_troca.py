"""A ferramenta da troca: --ver so le; --assinar so assina este app. Nada de registro, PIN ou override."""
from dataclasses import replace
from pathlib import Path

import httpx

from backend import troca


def cliente_falso(pedidos):
    def responder(req):
        pedidos.append(req)
        return httpx.Response(200, json={"success": True, "data": []})
    return httpx.Client(base_url="https://graph.facebook.com/v23.0", transport=httpx.MockTransport(responder))


def test_ver_so_le(cfg):
    pedidos = []
    troca.ver(replace(cfg, meta_token="t"), http=cliente_falso(pedidos))
    assert [p.method for p in pedidos] == ["GET", "GET"]
    assert pedidos[0].url.path.endswith("/1442233593867052/subscribed_apps")


def test_ver_app_so_le_e_a_chave_vai_no_cabecalho(cfg):
    pedidos = []

    def responder(req):
        pedidos.append(req)
        return httpx.Response(200, json={"id": "77", "name": "AxiaAtende", "data": []})
    http = httpx.Client(base_url="https://graph.facebook.com/v23.0", transport=httpx.MockTransport(responder))
    r = troca.ver_app(replace(cfg, meta_token="t", meta_app_secret="s3gr3d0"), http=http)
    assert [(p.method, p.url.path.split("/")[-1]) for p in pedidos] == [("GET", "app"), ("GET", "subscriptions")]
    assert pedidos[1].headers["Authorization"] == "Bearer 77|s3gr3d0"
    assert "s3gr3d0" not in str(pedidos[1].url) and "s3gr3d0" not in str(r)


def test_assinar_so_assina_a_conta(cfg):
    pedidos = []
    troca.assinar(replace(cfg, meta_token="t"), http=cliente_falso(pedidos))
    assert [(p.method, p.url.path.split("/")[-1]) for p in pedidos] == [("POST", "subscribed_apps")]


def test_nenhum_caminho_perigoso_no_codigo():
    src = Path(troca.__file__).read_text(encoding="utf-8").split('"""', 2)[2]   # o codigo, sem a docstring
    for perigoso in ("/register", "/deregister", "override_callback_uri", "two_step", "pin"):
        assert perigoso not in src, perigoso
