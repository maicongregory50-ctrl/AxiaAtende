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
    botao = direta[2]["buttons"][0]
    assert botao["type"] == "URL" and botao["url"].endswith("/falar/{{1}}") and "wa.me" not in botao["url"]
    aviso = modelos_meta.componentes(por_nome["aviso_recusa"])
    assert [c["type"] for c in aviso] == ["BODY"] and len(aviso[0]["example"]["body_text"][0]) == 3


def test_corpo_que_comeca_por_variavel_e_recusado_antes_de_ir(cfg):
    m = dict(modelos_meta.cadastro(cfg)[0], texto="{{1}}, oi", cabecalho_imagem=False)
    with pytest.raises(ValueError):
        modelos_meta.componentes(m)


def test_propor_so_cria_o_que_falta_e_nunca_edita(cfg, tmp_path):
    imagem = tmp_path / "capa.jpg"
    imagem.write_bytes(b"\xff\xd8\xff")
    pdf = tmp_path / "exemplo.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    pedidos = []
    feitos = modelos_meta.propor(replace(cfg, meta_token="t"), imagem,
                                 http=cliente_falso(pedidos, ja_tem=["aviso_recusa"]), documento=pdf)
    assert sorted(f["nome"] for f in feitos) == ["abertura_do_canal", "aviso_avaliacao_ruim", "aviso_endereco_fora",
                                                 "aviso_endereco_voltou", "aviso_lote_do_representante",
                                                 "aviso_plano_sem_registro",
                                                 "aviso_sem_atendimento", "curriculo_para_fran",
                                                 "epoca_de_plantio", "informativo_ao_comprador",
                                                 "pecas_da_revenda", "reabrir_avisos"]
    criados = [p for p in pedidos if p.method == "POST" and p.url.path.endswith("/message_templates")]
    assert len(criados) == 12   # #1182: + abertura_do_canal; #1188: + reabrir_avisos; 043: + informativo
    import json
    reabrir = next(json.loads(p.content) for p in criados if json.loads(p.content)["name"] == "reabrir_avisos")
    assert reabrir["category"] == "UTILITY"
    assert reabrir["components"] == [
        {"type": "BODY", "text": "Você tem {{1}} aviso(s) da Sementes Renascer. Toque em Ver para receber.",
         "example": {"body_text": [["3"]]}},
        {"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": "Ver"}]}]
    assert all(p.method in ("GET", "POST") for p in pedidos)      # nada de DELETE
    assert not any("/register" in p.url.path or "/deregister" in p.url.path for p in pedidos)


def test_propor_com_imagem_no_cabecalho_exige_o_exemplo(cfg):
    with pytest.raises(SystemExit):
        modelos_meta.propor(replace(cfg, meta_token="t"), None, http=cliente_falso([]))


def test_o_modelo_da_fran_leva_o_pdf_e_os_tres_botoes(cfg):
    """#1098: PDF no cabecalho, corpo sem variavel no comeco nem no fim, 2 respostas + 1 link."""
    m = {x["nome"]: x for x in modelos_meta.cadastro(cfg)}["curriculo_para_fran"]
    assert m["categoria"] == "UTILITY"
    c = modelos_meta.componentes(m, None, "4::pdf")
    assert c[0] == {"type": "HEADER", "format": "DOCUMENT", "example": {"header_handle": ["4::pdf"]}}
    assert c[1]["text"].startswith("Novo currículo") and c[1]["text"].endswith("acertou?")
    assert len(c[1]["example"]["body_text"][0]) == 8
    assert all("\n" not in v for v in c[1]["example"]["body_text"][0])   # a Meta recusa quebra em variavel
    botoes = c[2]["buttons"]
    assert [b["type"] for b in botoes] == ["QUICK_REPLY", "QUICK_REPLY", "URL"]
    assert botoes[2]["url"].endswith("/falar/{{1}}") and "wa.me" not in botoes[2]["url"]
    with pytest.raises(ValueError):
        modelos_meta.componentes(m)                       # sem o exemplo de PDF, nao vai


def test_propor_o_modelo_com_pdf_exige_o_exemplo(cfg, tmp_path):
    imagem = tmp_path / "capa.jpg"
    imagem.write_bytes(b"\xff\xd8\xff")
    with pytest.raises(SystemExit):
        modelos_meta.propor(replace(cfg, meta_token="t"), imagem, http=cliente_falso([]))
