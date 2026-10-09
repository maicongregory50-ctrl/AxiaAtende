"""Os modelos do cadastro indo para a Meta: so cria o que falta, nunca edita nem apaga."""
from dataclasses import replace

import httpx
import pytest

from backend import modelos_meta


def cliente_falso(pedidos, ja_tem=()):
    def responder(req):
        pedidos.append(req)
        caminho = req.url.path
        if req.method == "GET" and caminho.endswith("/message_templates"):
            return httpx.Response(200, json={"data": [{"name": n, "language": "pt_BR", "status": "APPROVED"}
                                                      for n in ja_tem]})
        if caminho.endswith("/app"):
            return httpx.Response(200, json={"id": "999"})
        if caminho.endswith("/999/uploads"):
            return httpx.Response(200, json={"id": "upload:abc"})
        if caminho.endswith("/upload:abc"):
            return httpx.Response(200, json={"h": "4::exemplo"})
        return httpx.Response(200, json={"id": "1", "status": "PENDING", "category": "MARKETING"})
    return httpx.Client(base_url="https://graph.facebook.com/v23.0", transport=httpx.MockTransport(responder))


def test_o_cadastro_vira_a_forma_da_meta(cfg):
    por_nome = {m["nome"]: m for m in modelos_meta.cadastro(cfg)}
    convite = modelos_meta.componentes(por_nome["pecas_da_revenda"], "4::h")
    assert convite[0] == {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["4::h"]}}
    assert convite[1]["example"]["body_text"] == [["João", "6"]]
    assert [b["text"] for b in convite[2]["buttons"]] == ["Quero receber", "Não quero receber"]
    direta = modelos_meta.componentes(por_nome["epoca_de_plantio"], "4::h")
    assert direta[1]["text"].startswith("Olá, {{1}}!")       # a 004: nao comeca por variavel
    assert direta[2]["buttons"][0]["url"] == "https://wa.me/{{1}}"
    aviso = modelos_meta.componentes(por_nome["aviso_recusa"])
    assert [c["type"] for c in aviso] == ["BODY"] and len(aviso[0]["example"]["body_text"][0]) == 3


def test_corpo_que_comeca_por_variavel_e_recusado_antes_de_ir(cfg):
    m = dict(modelos_meta.cadastro(cfg)[0], texto="{{1}}, oi", cabecalho_imagem=False)
    with pytest.raises(ValueError):
        modelos_meta.componentes(m)


def test_propor_so_cria_o_que_falta_e_nunca_edita(cfg, tmp_path):
    imagem = tmp_path / "capa.jpg"
    imagem.write_bytes(b"\xff\xd8\xff")
    pedidos = []
    feitos = modelos_meta.propor(replace(cfg, meta_token="t"), imagem,
                                 http=cliente_falso(pedidos, ja_tem=["aviso_recusa"]))
    assert sorted(f["nome"] for f in feitos) == ["aviso_sem_atendimento", "epoca_de_plantio", "pecas_da_revenda"]
    criados = [p for p in pedidos if p.method == "POST" and p.url.path.endswith("/message_templates")]
    assert len(criados) == 3
    assert all(p.method in ("GET", "POST") for p in pedidos)      # nada de DELETE
    assert not any("/register" in p.url.path or "/deregister" in p.url.path for p in pedidos)


def test_propor_com_imagem_no_cabecalho_exige_o_exemplo(cfg):
    with pytest.raises(SystemExit):
        modelos_meta.propor(replace(cfg, meta_token="t"), None, http=cliente_falso([]))
