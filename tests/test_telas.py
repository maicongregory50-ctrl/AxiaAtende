"""F1 do plano #950: as rotas das telas Recepcao, Envios e Destinos, com login."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import recepcionista as R
from backend import seguranca
from backend.banco import conexao
from backend.envio import Envio
from backend.main import CABECALHO_DA_TELA, criar_app
from backend.rotas_telas import mascarar
from tests.avisos_meta import aviso, texto, toque
from tests.saida_falsa import SaidaFalsa
from tests.test_envio import cliente, pedido, pedir

AGORA = datetime.now(timezone.utc)


@pytest.fixture
def ligado(cfg, tmp_path):
    return replace(cfg, responde=True, chave_pedido="chave-do-marketing", envios_pasta=tmp_path / "envios")


@pytest.fixture
def tela(ligado):
    with conexao(ligado) as con:
        con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash) VALUES ('dono', 'Dono', %s)",
                    (seguranca.gerar_hash("senha-de-teste-1"),))
    seguranca.limpar_erros("dono")
    with TestClient(criar_app(ligado), headers={CABECALHO_DA_TELA: "1"}) as c:
        assert c.post("/api/entrar", json={"login": "dono", "senha": "senha-de-teste-1"}).status_code == 200
        yield c


def test_sem_login_nada(ligado):
    with TestClient(criar_app(ligado)) as c:
        for rota in ("/api/recepcao", "/api/envios", "/api/destinos"):
            assert c.get(rota).status_code == 401


def test_mascara_nunca_mostra_o_numero_inteiro():
    assert mascarar("5546999784298") == "+55 46 9…·4298"
    assert mascarar(None) == "sem número"


def test_recepcao_conta_e_lista(ligado, tela):
    s = SaidaFalsa()
    R.gravar(ligado, aviso([toque("w1", "menu:fretes", lista=True)]))
    R.gravar(ligado, aviso([texto("w2", "oi")], numero="5549988887777", bsuid="BR.2"))
    R.processar_pendentes(ligado, s, None, agora=AGORA - timedelta(hours=1))
    R.rotina_do_minuto(ligado, s, agora=AGORA)          # a 2a parou no meio (sem toque ha 1 h)
    d = tela.get("/api/recepcao", params={"dias": 7}).json()
    assert d["cartoes"]["chegaram"] == 2 and d["cartoes"]["receberam_link"] == 1
    assert d["cartoes"]["pararam_no_meio"] == 1
    fretes = next(l for l in d["linhas"] if l["destino"])
    assert fretes["destino"] == "Benedito" and fretes["caminho"] == ["🚚 Fretes"] and "…" in fretes["numero"]
    assert [l["estado"] for l in tela.get("/api/recepcao", params={"situacao": "parou"}).json()["linhas"]] == ["parou"]
    assert [m["chave"] for m in d["motivos"]][:2] == ["comercial", "fretes"]


def test_envios_lista_detalhe_e_religar(ligado, tela, tmp_path):
    pasta = tmp_path / "mk"
    pasta.mkdir()
    imgs = []
    for n in ("capa.jpg", "t1.jpg"):
        (pasta / n).write_bytes(b"\xff\xd8\xff")
        imgs.append(str(pasta / n))
    pedir(ligado, pedido(imgs, [cliente(1, 10), cliente(2, 5, resp=("", ""))]))
    Envio(ler_nota=lambda: "YELLOW").rotina(ligado, SaidaFalsa(), AGORA)
    lista = tela.get("/api/envios").json()
    assert lista["envios"][0]["situacao"] == "parado_nota" and lista["nota"]["nota"] == "YELLOW"
    d = tela.get("/api/envios/1").json()
    assert d["cartoes"]["sem_responsavel"] == 1 and d["cartoes"]["aguardando"] == 1
    assert {l["situacao"] for l in d["linhas"]} == {"aguardando", "sem_responsavel"}
    assert tela.post("/api/envios/1/religar").status_code == 200
    assert tela.post("/api/envios/1/religar").status_code == 422
    assert tela.get("/api/envios/99").status_code == 404


def test_destinos_trocar_numero_ligar_opcao_e_horario(ligado, tela):
    d = tela.get("/api/destinos").json()
    cascavel = next(o for o in d["opcoes"] if o["chave"] == "comercial.produtor.pr.cascavel")
    assert cascavel["caminho"] == ["🛒 Comercial", "Produtor rural", "PR", "Cascavel"]
    assert cascavel["perguntas"][1] == "Qual a sua área de atuação?"
    willian = next(x for x in d["destinos"] if x["nome"] == "Willian Souza")
    assert tela.put("/api/destinos/%d" % willian["id"], json={"nome": "Willian Souza", "whatsapp": "46 99999-1234"}).json()["whatsapp"] == "5546999991234"
    assert tela.put("/api/destinos/%d" % willian["id"], json={"nome": "W", "whatsapp": "123"}).status_code == 422
    novo = tela.post("/api/destinos", json={"nome": "Rep Oeste", "whatsapp": "(46) 98888-7777"}).json()
    assert tela.put("/api/opcoes/%d" % cascavel["id"], json={"destino_id": novo["id"]}).status_code == 200
    s = SaidaFalsa()
    R.gravar(ligado, aviso([toque("w9", "menu:comercial.produtor.pr.cascavel")]))
    R.processar_pendentes(ligado, s, None, agora=datetime(2026, 10, 8, 17, 0, tzinfo=timezone.utc))
    assert s.ultima[2] == "Rep Oeste" and s.ultima[3] == ["5546988887777"]   # vale para a proxima pessoa
    h = {"dias": [1, 2, 3, 4, 5, 6], "faixas": [["08:00", "12:00"]]}
    assert tela.put("/api/ajustes/horario", json=h).json() == h
    assert tela.put("/api/ajustes/horario", json={"dias": [9], "faixas": [["8", "x"]]}).status_code == 422
    assert tela.put("/api/ajustes/avisado", json={"destino_id": novo["id"]}).status_code == 200
