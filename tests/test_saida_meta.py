"""A SaidaMeta monta, pelo PyWa 4.5.0, o pedido que a Cloud API espera, e nada sai da maquina: o
httpx.Client tem transporte falso. O token so vai no cabecalho."""
import json

import httpx
import pytest

from backend.saida import Opcao, SaidaMeta


@pytest.fixture
def meta():
    pedidos = []

    def responder(req: httpx.Request):
        pedidos.append(req)
        if req.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "midia.%d" % len(pedidos)})
        return httpx.Response(200, json={"messaging_product": "whatsapp",
                                         "contacts": [{"input": "5549999990000", "wa_id": "5549999990000"}],
                                         "messages": [{"id": "wamid.meta.%d" % len(pedidos)}]})

    sessao = httpx.Client(transport=httpx.MockTransport(responder))
    return SaidaMeta("725888737278277", "token-falso", sessao=sessao), pedidos


def _corpo(req):
    return json.loads(req.content)


def test_botoes_vao_como_interactive_button_com_os_ids(meta):
    s, pedidos = meta
    w = s.botoes("5549999990000", "Qual a sua área?", [Opcao("menu:a", "Produtor rural"), Opcao("menu:b", "Corretor")])
    req = pedidos[-1]
    assert w == "wamid.meta.1"
    assert req.url.path.endswith("/725888737278277/messages")
    assert req.headers["Authorization"] == "Bearer token-falso" and "token-falso" not in str(req.url)
    i = _corpo(req)["interactive"]
    assert i["type"] == "button"
    assert [(b["reply"]["id"], b["reply"]["title"]) for b in i["action"]["buttons"]] == [
        ("menu:a", "Produtor rural"), ("menu:b", "Corretor")]


def test_lista_vai_como_interactive_list(meta):
    s, pedidos = meta
    s.lista("5549999990000", "Escolha", "Ver opções",
            [Opcao("menu:comercial", "🛒 Comercial", "Cotar sementes"), Opcao("menu:fretes", "🚚 Fretes")])
    i = _corpo(pedidos[-1])["interactive"]
    assert i["type"] == "list" and i["action"]["button"] == "Ver opções"
    linhas = i["action"]["sections"][0]["rows"]
    assert linhas[0]["id"] == "menu:comercial" and linhas[0]["description"] == "Cotar sementes"


def test_texto_com_link_pede_a_previa(meta):
    s, pedidos = meta
    s.texto("5549999990000", "Fale com https://wa.me/5549991505565")
    b = _corpo(pedidos[-1])
    assert b["type"] == "text" and b["text"]["preview_url"] is True


def test_repr_nao_mostra_o_token(meta):
    assert "token" not in repr(meta[0]).lower() or "falso" not in repr(meta[0])


def test_mais_de_tres_botoes_e_recusado_antes_de_sair(meta):
    s, pedidos = meta
    with pytest.raises(ValueError):
        s.botoes("5549999990000", "x", [Opcao("a", "1"), Opcao("b", "2"), Opcao("c", "3"), Opcao("d", "4")])
    assert pedidos == []


def test_modelo_do_convite_sobe_a_capa_e_vai_com_corpo_e_botoes(meta, tmp_path):
    s, pedidos = meta
    capa = tmp_path / "capa.jpg"
    capa.write_bytes(b"\xff\xd8\xff falsa")
    s.modelo("5549999990000", "pecas_da_revenda", "pt_BR", ["Agro", "3"], imagem=str(capa),
             botoes=["envio:1:quero", "envio:1:nao_quero"])
    assert pedidos[0].url.path.endswith("/media")
    t = _corpo(pedidos[-1])
    assert t["type"] == "template" and t["template"]["name"] == "pecas_da_revenda"
    assert t["template"]["language"]["code"] == "pt_BR"
    comps = t["template"]["components"]
    assert comps[0]["type"] == "header" and comps[0]["parameters"][0]["type"] == "image"
    assert [p["text"] for p in comps[1]["parameters"]] == ["Agro", "3"]
    assert [c["parameters"][0]["payload"] for c in comps[2:]] == ["envio:1:quero", "envio:1:nao_quero"]


def test_nota_do_numero_e_so_leitura():
    pedidos = []

    def responder(req):
        pedidos.append(req)
        return httpx.Response(200, json={"id": "725888737278277", "display_phone_number": "+55 49 3664-0121",
                                         "verified_name": "Sementes Renascer", "quality_rating": "GREEN"})

    s = SaidaMeta("725888737278277", "token-falso", sessao=httpx.Client(transport=httpx.MockTransport(responder)))
    assert s.nota() == "GREEN"
    assert all(p.method == "GET" for p in pedidos)


def test_botao_de_link_do_responsavel(meta):
    s, pedidos = meta
    s.modelo("5549999990000", "epoca_de_plantio", "pt_BR", ["Joao", "plantio", "Djeison"], url="5549999567572")
    comps = _corpo(pedidos[-1])["template"]["components"]
    assert comps[-1] == {"type": "button", "sub_type": "url", "index": "0",
                         "parameters": [{"type": "text", "text": "5549999567572"}]}
