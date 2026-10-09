"""#969, etapa 1: a agenda do cadastro e o reconhecimento de quem chama. So REGISTRA: o que a
pessoa recebe nao muda."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import agenda, erp
from backend import recepcionista as R
from backend.banco import conexao
from backend.main import CABECALHO_DA_TELA, criar_app
from backend import seguranca
from tests.avisos_meta import aviso, texto, toque
from tests.saida_falsa import SaidaFalsa

AGORA = datetime.now(timezone.utc)

LINHAS = [
    {"numero": "5549999990000", "codigo": 5475, "nome": "Agro Real Insumos", "papeis": ["cliente"],
     "contato_setor": "comercial", "contato_nome": "João"},
    {"numero": "5549991505565", "codigo": 12, "nome": "Maicon Gregory", "papeis": ["equipe", "representante"],
     "contato_setor": "comercial", "contato_nome": ""},
    {"numero": "5546988887777", "codigo": 801, "nome": "Um", "papeis": ["fornecedor"], "contato_setor": "", "contato_nome": ""},
    {"numero": "5546988887777", "codigo": 802, "nome": "Dois", "papeis": ["cliente"], "contato_setor": "", "contato_nome": ""},
]


@pytest.fixture
def ligado(cfg):
    return replace(cfg, responde=True, erp_segredo="segredo-de-teste")


def _carregar(cfg, linhas=LINHAS):
    return agenda.atualizar(cfg, buscar=lambda c: linhas, agora=AGORA)


def _ultima(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.conversas ORDER BY id DESC LIMIT 1").fetchone()


def test_sem_o_segredo_nem_tenta(cfg):
    chamado = []
    assert agenda.atualizar(cfg, buscar=lambda c: chamado.append(1) or LINHAS) == {"erro": "a leitura do cadastro não está ligada"}
    assert chamado == []


def test_a_leitura_troca_a_agenda_inteira(ligado):
    assert _carregar(ligado) == {"linhas": 4}
    assert _carregar(ligado, LINHAS[:1]) == {"linhas": 1}
    with conexao(ligado) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.agenda").fetchone()["n"] == 1
        assert agenda.ultima_leitura(con)["linhas"] == 1


def test_erp_fora_ou_agenda_vazia_mantem_a_de_ontem_e_anota_o_erro(ligado):
    _carregar(ligado)

    def fora(c):
        raise erp.ErpIndisponivel("o ERP não respondeu")
    assert agenda.atualizar(ligado, buscar=fora, agora=AGORA + timedelta(days=1)) == {"erro": "o ERP não respondeu"}
    assert agenda.atualizar(ligado, buscar=lambda c: [], agora=AGORA + timedelta(days=1, minutes=1))["erro"]
    with conexao(ligado) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.agenda").fetchone()["n"] == 4
        u = agenda.ultima_leitura(con)
    assert u["linhas"] == 4 and u["erro"] == "o ERP devolveu a agenda vazia"


def test_a_proxima_leitura_e_as_seis_da_manha():
    noite = datetime(2026, 10, 9, 23, 0, tzinfo=timezone.utc)        # 20:00 em Sao Paulo
    assert agenda.proxima_leitura(noite) == datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


def test_quem_chama_e_reconhecido_mesmo_sem_o_9_e_recebe_o_mesmo_menu(ligado):
    _carregar(ligado)
    s = SaidaFalsa()
    R.gravar(ligado, aviso([texto("w1", "oi")], numero="554991505565", bsuid="BR.maicon"))   # sem o 9
    R.processar_pendentes(ligado, s, None, agora=AGORA)
    c = _ultima(ligado)
    assert c["erp_cadastros"] == 1 and c["erp_codigo"] == 12 and c["erp_papeis"] == ["equipe", "representante"]
    assert s.ultima[0] == "lista" and s.ultima[2].startswith("Seja bem-vindo")   # nada muda para a pessoa


def test_fora_do_cadastro_e_numero_em_dois(ligado):
    _carregar(ligado)
    s = SaidaFalsa()
    R.gravar(ligado, aviso([texto("w1", "oi")], numero="5547900001111", bsuid="BR.novo"))
    R.processar_pendentes(ligado, s, None, agora=AGORA)
    assert _ultima(ligado)["erp_cadastros"] == 0
    R.gravar(ligado, aviso([texto("w2", "oi")], numero="5546988887777", bsuid="BR.dois"))
    R.processar_pendentes(ligado, s, None, agora=AGORA)
    c = _ultima(ligado)
    assert c["erp_cadastros"] == 2 and c["erp_codigo"] is None and c["erp_nome"] is None


def test_sem_agenda_nao_se_afirma_nada(ligado):
    s = SaidaFalsa()
    R.gravar(ligado, aviso([texto("w1", "oi")]))
    R.processar_pendentes(ligado, s, None, agora=AGORA)
    assert _ultima(ligado)["erp_cadastros"] is None and s.ultima[0] == "lista"


def test_a_recepcao_mostra_quem_e_conta_e_filtra(ligado):
    _carregar(ligado)
    s = SaidaFalsa()
    R.gravar(ligado, aviso([toque("w1", "menu:fretes", lista=True)]))                       # Agro Real
    R.gravar(ligado, aviso([texto("w2", "oi")], numero="5547900001111", bsuid="BR.novo"))   # fora
    R.processar_pendentes(ligado, s, None, agora=AGORA - timedelta(minutes=5))
    with conexao(ligado) as con:
        con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash) VALUES ('dono', 'Dono', %s)",
                    (seguranca.gerar_hash("senha-de-teste-1"),))
    seguranca.limpar_erros("dono")
    with TestClient(criar_app(replace(ligado, erp_segredo="")), headers={CABECALHO_DA_TELA: "1"}) as c:
        assert c.post("/api/entrar", json={"login": "dono", "senha": "senha-de-teste-1"}).status_code == 200
        d = c.get("/api/recepcao").json()
        assert d["cartoes"]["chegaram"] == 2 and d["cartoes"]["do_cadastro"] == 1
        agro = next(l for l in d["linhas"] if l["cadastro"])
        assert agro["cadastro"] == {"codigo": 5475, "nome": "Agro Real Insumos", "papeis": ["cliente"],
                                    "contato_setor": "comercial", "contato_nome": "João"}
        assert d["leitura"]["linhas"] == 4
        assert [l["cadastros"] for l in c.get("/api/recepcao", params={"quem": "fora"}).json()["linhas"]] == [0]
        assert len(c.get("/api/recepcao", params={"quem": "cadastro"}).json()["linhas"]) == 1
