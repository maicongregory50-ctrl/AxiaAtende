"""E1b do plano #950 (emenda do dono, 09/10/2026): a comunicacao direta so para quem ja aceitou, com
o botao Falar com meu atendimento (o nosso endereco, que abre o WhatsApp do responsavel); os modelos do cadastro; as imagens de cada revenda."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import recepcionista as R
from backend.banco import conexao
from backend.envio import Envio
from backend.main import criar_app
from tests.avisos_meta import aviso
from tests.saida_falsa import SaidaFalsa
from tests.test_envio import CHAVE, QUINTA_9H, cliente, destinatarios, pedido, pedir


@pytest.fixture
def ligado(cfg, tmp_path):
    return replace(cfg, responde=True, chave_pedido="chave-do-marketing", envios_pasta=tmp_path / "envios")


@pytest.fixture
def imagens(tmp_path):
    pasta = tmp_path / "marketing"
    pasta.mkdir()
    arquivos = []
    for nome in ("capa.jpg", "tela1.jpg", "tela2.jpg", "tela3.jpg", "agro_capa.jpg", "agro_1.jpg"):
        (pasta / nome).write_bytes(b"\xff\xd8\xff" + nome.encode())
        arquivos.append(str(pasta / nome))
    return arquivos


def direta(imagens, clientes, ref="dir-1"):
    return {"pedido_ref": ref, "tipo": "direta", "modelo": "epoca_de_plantio", "campanha": "Época do Trigo Mourisco",
            "peca": "Trigo Mourisco: a janela", "assunto": "plantio do Trigo Mourisco", "capa": imagens[0],
            "aprovado_por": "maicon", "aprovado_em": "2026-10-07T17:00:00-03:00", "clientes": clientes}


def test_direta_so_para_quem_ja_aceitou(ligado, imagens):
    c_aceite = dict(cliente(1, 30), aceite_cadastro=True)        # aceite no cadastro do #952
    c_sem = cliente(2, 20)                                        # nunca aceitou
    c_tocou = cliente(3, 10)                                      # aceitou num convite antes
    with conexao(ligado) as con:
        con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, tipo, wamid)
                       VALUES (%s, 'aceite', 'wamid.antes')""", ("55" + c_tocou["whatsapp"],))
    assert pedir(ligado, direta(imagens, [c_aceite, c_sem, c_tocou])).status_code == 200
    d = destinatarios(ligado)
    assert d[1]["situacao"] == "aguardando" and d[3]["situacao"] == "aguardando"
    assert d[2]["situacao"] == "sem_aceite"


def test_direta_vai_com_o_texto_e_o_botao_de_link_do_responsavel_e_sem_imagens_depois(ligado, imagens):
    pedir(ligado, direta(imagens, [dict(cliente(1, 30, nome="JOAO DA SILVA",
                                                resp=("Djeison de Oliveira", "5549999567572")), aceite_cadastro=True)]))
    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, QUINTA_9H)
    m = next(x for x in s.modelos if x["para"] != "5549999567572")
    assert m["nome"] == "epoca_de_plantio"
    assert m["corpo"] == ["Joao", "plantio do Trigo Mourisco", "Djeison de Oliveira"]
    assert m["botoes"] is None and m["imagem"] and m["url"].startswith("1-")
    assert destinatarios(ligado)[1]["imagens_total"] == 0
    copia = next(x for x in s.modelos if x["para"] == "5549999567572")      # a copia ao responsavel
    assert copia["corpo"][0] == "Djeison" and copia["url"].startswith("c1-")


def test_falar_com_meu_atendimento_anota_e_abre_o_whatsapp_do_responsavel(ligado, imagens):
    pedir(ligado, direta(imagens, [dict(cliente(1, 30, resp=("Djeison de Oliveira", "5549999567572")),
                                        aceite_cadastro=True)]))
    s, env = SaidaFalsa(), Envio(ler_nota=lambda: "GREEN")
    env.rotina(ligado, s, QUINTA_9H)
    m = next(x for x in s.modelos if x["para"] != "5549999567572")
    copia = next(x for x in s.modelos if x["para"] == "5549999567572")
    with TestClient(R.criar_app(ligado, saida=s, trabalhador=False)) as c:
        assert c.get("/falar/" + copia["url"], follow_redirects=False).headers["location"] == "https://wa.me/5549999567572"
        assert destinatarios(ligado)[1]["resposta"] is None             # o toque da copia nao conta
        r = c.get("/falar/" + m["url"], follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == "https://wa.me/5549999567572"
        assert destinatarios(ligado)[1]["resposta"] == "falar"
        forjado = m["url"].split("-")[0] + "-0000000000000000"
        assert c.get("/falar/" + forjado, follow_redirects=False).status_code == 404
        assert c.get("/falar/2-" + m["url"].split("-")[1], follow_redirects=False).status_code == 404


def test_modelo_que_nao_existe_ou_de_outro_uso_e_recusado(ligado, imagens):
    ruim = direta(imagens, [cliente(1, 10)])
    ruim["modelo"] = "pecas_da_revenda"                           # convite usado como direta
    assert pedir(ligado, ruim).status_code == 422
    ruim["modelo"] = "nao_existe"
    assert pedir(ligado, ruim).status_code == 422


def test_cada_revenda_recebe_as_suas_imagens(ligado, imagens):
    agro = dict(cliente(5475, 100, nome="Agro Real Agropecuarias"), capa=imagens[4], imagens=[imagens[5]])
    outro = cliente(4579, 50)
    pedir(ligado, pedido(imagens, [agro, outro]))
    s = SaidaFalsa()
    env = Envio(ler_nota=lambda: "GREEN")
    env.rotina(ligado, s, QUINTA_9H)
    convite_agro = next(x for x in s.modelos if x["para"] == destinatarios(ligado)[5475]["whatsapp"])
    assert "agro_capa" not in convite_agro["imagem"] and convite_agro["imagem"].endswith("capa.jpg")
    assert str(ligado.envios_pasta) in convite_agro["imagem"] and "5475" in convite_agro["imagem"]
    assert convite_agro["corpo"] == ["Agro", "1"]                 # 1 imagem: a da Agro Real
    numero = destinatarios(ligado)[5475]["whatsapp"]
    msg = {"from": numero, "id": "wamid.t", "timestamp": "1", "type": "button",
           "context": {"from": "554936640121", "id": "x"}, "button": {"payload": "envio:1:quero", "text": "Quero"}}
    R.gravar(ligado, aviso([msg], numero=numero, bsuid="BR.agro"))
    R.processar_pendentes(ligado, s, None, envio=env, agora=QUINTA_9H + timedelta(hours=1))
    imgs = [x for x in s.enviadas if x[0] == "imagem"]
    assert len(imgs) == 1 and "5475" in imgs[0][2]


def test_aviso_de_recusa_sai_pelo_modelo_do_cadastro(ligado, imagens):
    with conexao(ligado) as con:
        con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                       VALUES ('recusa', 'Maicon', '5549991505565', 'Cliente X|10 · Rio do Sul|https://wa.me/554799')""")
    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, QUINTA_9H)
    assert s.modelos[-1]["nome"] == "aviso_recusa"
    assert s.modelos[-1]["corpo"] == ["Cliente X", "10 · Rio do Sul", "https://wa.me/554799"]


def test_quem_recusou_no_cadastro_nao_recebe_nem_convite(ligado, imagens):
    pedir(ligado, pedido(imagens, [dict(cliente(1, 10), aceite_cadastro=False), cliente(2, 5)]))
    d = destinatarios(ligado)
    assert d[1]["situacao"] == "recusou_antes" and d[2]["situacao"] == "aguardando"


def test_modelos_e_aceites_para_a_ficha_do_marketing(ligado, imagens):
    with conexao(ligado) as con:
        con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, tipo, wamid) VALUES
                       ('5547999990001', 'aceite', 'w1'), ('5547999990002', 'aceite', 'w2'),
                       ('5547999990002', 'recusa', 'w3')""")
    with TestClient(criar_app(ligado)) as c:
        m = c.get("/pedido/modelos", headers=CHAVE).json()["modelos"]
        a = c.post("/pedido/aceites", json={"numeros": ["47 99999-0001", "5547999990002", "5547999990003"]},
                   headers=CHAVE).json()["aceites"]
        assert c.get("/pedido/modelos").status_code == 403
    assert {x["nome"] for x in m} >= {"pecas_da_revenda", "epoca_de_plantio"}
    assert a == {"5547999990001": "aceite", "5547999990002": "recusa"}
