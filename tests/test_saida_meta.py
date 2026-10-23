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


def test_baixar_pede_a_url_da_midia_e_grava_o_arquivo(tmp_path):
    """#970: a midia que a pessoa mandou e baixada com o mesmo token: primeiro a URL (vale 5 min),
    depois o arquivo, gravado onde o canal de campo pediu."""
    pedidos = []

    def responder(req: httpx.Request):
        pedidos.append(req)
        if req.url.path.endswith("/midia-1"):
            return httpx.Response(200, json={"url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=1",
                                             "mime_type": "image/jpeg", "sha256": "x", "file_size": 5, "id": "midia-1",
                                             "messaging_product": "whatsapp"})
        if "lookaside" in str(req.url):
            return httpx.Response(200, content=b"JPEG!", headers={"Content-Type": "image/jpeg"})
        return httpx.Response(404)

    s = SaidaMeta("725888737278277", "token-falso", sessao=httpx.Client(transport=httpx.MockTransport(responder)))
    destino = tmp_path / "campo" / "2026-10-12" / "wamid.1.jpg"
    assert s.baixar("midia-1", destino) == str(destino)
    assert destino.read_bytes() == b"JPEG!"
    assert all(r.headers.get("Authorization") == "Bearer token-falso" for r in pedidos)


def test_contato_vai_como_cartao_com_o_whatsapp_de_quem_atende(meta):
    s, pedidos = meta
    s.contato("5549999990000", "Willian Souza", "5546999784298")
    c = _corpo(pedidos[-1])
    assert c["type"] == "contacts"
    cartao = c["contacts"][0]
    assert cartao["name"]["formatted_name"] == "Willian Souza" and cartao["name"]["first_name"] == "Willian"
    assert cartao["phones"][0]["phone"] == "+5546999784298"
    assert cartao["phones"][0]["wa_id"] == "554699784298"          # o id do WhatsApp: sem o 9
    assert cartao["org"]["company"] == "Sementes Renascer"


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


def test_curriculo_vai_como_documento_com_os_botoes_da_triagem(meta):
    """#1098: dentro da janela da Fran, o PDF sobe e vai com a triagem na legenda e os 3 botoes."""
    s, pedidos = meta
    w = s.documento("5549999990000", b"%PDF-1.4 joao", "Curriculo - Joao.pdf", "Novo currículo",
                    [Opcao("vaga:certa:7", "Triagem certa"), Opcao("vaga:errada:7", "Triagem errada")])
    assert w.startswith("wamid.meta.")
    subida = [p for p in pedidos if p.url.path.endswith("/media")]
    assert subida, "o PDF sobe antes de ir"
    corpo = _corpo(pedidos[-1])
    i = corpo["interactive"]
    assert i["type"] == "button" and i["header"]["type"] == "document"
    assert i["header"]["document"]["filename"] == "Curriculo - Joao.pdf"
    assert i["body"]["text"] == "Novo currículo"
    assert [b["reply"]["id"] for b in i["action"]["buttons"]] == ["vaga:certa:7", "vaga:errada:7"]


def test_modelo_da_fran_leva_o_pdf_e_o_link_depois_das_respostas(meta):
    """#1098: cabecalho de documento; o botao de link fica no indice 2, depois das duas respostas."""
    s, pedidos = meta
    s.modelo("5549999990000", "curriculo_para_fran", "pt_BR", ["Vaga Comercial"] * 8,
             botoes=["vaga:certa:7", "vaga:errada:7"], url="v7-0a1b2c3d4e5f6a7b",
             documento=(b"%PDF-1.4", "Curriculo.pdf"))
    comps = _corpo(pedidos[-1])["template"]["components"]
    assert comps[0]["type"] == "header"
    assert comps[0]["parameters"][0]["type"] == "document"
    assert comps[0]["parameters"][0]["document"]["filename"] == "Curriculo.pdf"
    assert [c.get("index") for c in comps if c["type"] == "button"] == ["0", "1", "2"]
    assert comps[-1] == {"type": "button", "sub_type": "url", "index": "2",
                         "parameters": [{"type": "text", "text": "v7-0a1b2c3d4e5f6a7b"}]}


def test_link_vai_como_cta_url_e_recusa_rotulo_longo(meta):
    """#1090 etapa 3: a ficha do cliente com o botao "Chamar ... no WhatsApp" (wa.me)."""
    s, pedidos = meta
    s.link("5549999990000", "Cliente 1 de 43", "Chamar Márcio", "https://wa.me/5549988595737")
    i = _corpo(pedidos[-1])["interactive"]
    assert i["type"] == "cta_url"
    assert i["action"]["parameters"] == {"display_text": "Chamar Márcio", "url": "https://wa.me/5549988595737"}
    with pytest.raises(ValueError):
        s.link("5549999990000", "x", "Chamar Márcio no WhatsApp", "https://wa.me/1")
