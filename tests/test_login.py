"""C2 do plano #950: o login das telas (copia do AxiaMarketing) entra, recusa e tranca."""
from fastapi.testclient import TestClient

from backend import seguranca
from backend.banco import conexao
from backend.main import CABECALHO_DA_TELA, criar_app

TELA = {CABECALHO_DA_TELA: "1"}


def _usuario(cfg, login="dono", senha="senha-de-teste-1"):
    with conexao(cfg) as con:
        con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash) VALUES (%s, %s, %s)",
                    (login, "Dono", seguranca.gerar_hash(senha)))


def test_entra_e_ve_quem_e(cfg):
    _usuario(cfg)
    with TestClient(criar_app(cfg)) as c:
        assert c.get("/api/eu").status_code == 401
        r = c.post("/api/entrar", json={"login": "Dono", "senha": "senha-de-teste-1"}, headers=TELA)
        assert r.status_code == 200
        assert c.get("/api/eu").json()["nome"] == "Dono"
        c.post("/api/sair", headers=TELA)
        assert c.get("/api/eu").status_code == 401


def test_senha_errada_recusa_e_cinco_trancam(cfg):
    _usuario(cfg, login="tranca")
    seguranca.limpar_erros("tranca")
    with TestClient(criar_app(cfg)) as c:
        for _ in range(5):
            r = c.post("/api/entrar", json={"login": "tranca", "senha": "errada-errada"}, headers=TELA)
            assert r.status_code == 401
        r = c.post("/api/entrar", json={"login": "tranca", "senha": "senha-de-teste-1"}, headers=TELA)
        assert r.status_code == 429
    seguranca.limpar_erros("tranca")


def test_pedido_sem_o_cabecalho_da_tela_e_recusado(cfg):
    _usuario(cfg)
    with TestClient(criar_app(cfg)) as c:
        r = c.post("/api/entrar", json={"login": "dono", "senha": "senha-de-teste-1"})
        assert r.status_code == 403


def test_saude_diz_que_nao_responde_ninguem(cfg):
    with TestClient(criar_app(cfg)) as c:
        s = c.get("/saude").json()
    assert s["de_pe"] is True and s["responde"] is False
    assert s["mudancas"] == ["001_casa_e_atendimento.sql", "002_menu_da_olivia.sql",
                            "003_modelos_e_comunicacao_direta.sql",
                            "004_modelo_nao_comeca_por_variavel.sql", "005_direta_por_toque.sql",
                            "006_agenda_do_cadastro.sql", "007_uma_pergunta_por_dia.sql",
                            "008_nota_em_tres_botoes.sql", "009_vigia_do_endereco.sql",
                            "010_canal_de_campo.sql", "011_frase_do_campo.sql", "012_palpite_fase.sql",
                            "013_atendente_de_campo.sql", "014_perguntas_feitas.sql",
                            "015_grupo_da_conversa.sql", "016_retomada.sql", "017_safra_dita.sql",
                            "018_menu_interno.sql"]
