"""#1207: o status do dia. O Marketing pede pela porta do pedido (/pedido/aviso) as artes do Stories
com a legenda; o porteiro as manda ao dono como IMAGENS, sem texto nenhum, so a ultima com a legenda
(dono, 30/10/2026: "vir somente a legenda da ultima foto, sem mais nenhum texto adicional"). Fora da
janela, a mesma reabertura dos avisos (#1188); o Ver solta as imagens. Meta falsa: nada sai."""
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import migracoes
from backend.banco import conexao
from backend.main import criar_app
from tests.test_1188_porteiro import AGORA, avisos, falou, saida, toque_ver, volta

CHAVE = {"X-Axiaatende-Chave": "chave-do-marketing"}
LEGENDA = "Cobertura de verão: a linha tem uma para cada janela.\n\nPergunte à sua revenda."


class SaidaComLegenda:
    """A saida falsa do #1188, guardando tambem a legenda de cada imagem."""

    def __init__(self):
        self.s = saida()
        self.legendas = []

    def __getattr__(self, nome):
        return getattr(self.s, nome)

    def imagem(self, para, arquivo, legenda=""):
        self.legendas.append(legenda)
        return self.s.imagem(para, arquivo, legenda)


@pytest.fixture
def ligado(cfg, tmp_path):
    return replace(cfg, responde=True, porteiro=True, chave_pedido="chave-do-marketing",
                   envios_pasta=tmp_path / "envios")


@pytest.fixture
def artes(tmp_path):
    feitas = []
    for i in range(1, 5):
        p = tmp_path / "marketing" / ("vertical-%d.jpeg" % i)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"JPEG %d" % i)
        feitas.append(str(p))
    return feitas


def pedir(cfg, artes, legenda=LEGENDA, cabecalho=CHAVE, **mais):
    with TestClient(criar_app(cfg)) as c:
        return c.post("/pedido/aviso", headers=cabecalho,
                      json=dict(tipo="status_do_dia", imagens=artes, legenda=legenda, ref="PUB-0294", **mais))


def dono(cfg):
    with conexao(cfg) as con:
        return con.execute("""SELECT d.nome, d.whatsapp FROM atendimento.destinos d, atendimento.ajustes j
                               WHERE j.chave = 'status_do_dia_para' AND d.id = (j.valor #>> '{}')::int""").fetchone()


def sem_o_nove(numero):
    return numero[:4] + numero[5:] if len(numero) == 13 else numero


# ── a migracao ────────────────────────────────────────────────────────────────

def test_quem_recebe_nasce_o_mesmo_do_aviso_do_plano(ligado):
    with conexao(ligado) as con:
        j = {r["chave"]: r["valor"] for r in con.execute(
            "SELECT chave, valor FROM atendimento.ajustes WHERE chave IN ('status_do_dia_para', 'avisado_no_nao')")}
    assert j["status_do_dia_para"] == j["avisado_no_nao"]


def test_a_volta_desfaz_e_a_ida_volta_a_aplicar(ligado, artes):
    assert pedir(ligado, artes).status_code == 200
    raiz = Path(migracoes.__file__).parent / "migracoes"
    with conexao(ligado) as con:
        con.execute((raiz / "048_status_do_dia_VOLTA.sql").read_text(encoding="utf-8"))
        assert not con.execute("SELECT 1 FROM atendimento.ajustes WHERE chave = 'status_do_dia_para'").fetchone()
        assert not con.execute("""SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                                   AND table_name = 'avisos' AND column_name = 'imagens'""").fetchone()
        con.execute((raiz / "048_status_do_dia.sql").read_text(encoding="utf-8"))
    assert dono(ligado)


# ── o pedido ──────────────────────────────────────────────────────────────────

def test_sem_a_chave_e_recusado(ligado, artes):
    assert pedir(ligado, artes, cabecalho={}).status_code == 403


def test_sem_imagem_ou_com_onze_e_recusado(ligado, artes):
    assert pedir(ligado, []).status_code == 422
    assert pedir(ligado, (artes * 3)[:11]).status_code == 422
    assert pedir(ligado, artes + ["C:/nao/existe.png"]).status_code == 422


def test_o_pedido_copia_as_imagens_na_ordem_e_vai_para_o_dono(ligado, artes):
    r = pedir(ligado, artes)
    assert r.status_code == 200
    a = [x for x in avisos(ligado) if x["id"] == r.json()["aviso_id"]][0]
    quem = dono(ligado)
    assert (a["tipo"], a["para_whatsapp"], a["legenda"]) == ("status_do_dia", quem["whatsapp"], LEGENDA)
    assert [Path(p).read_bytes() for p in a["imagens"]] == [b"JPEG 1", b"JPEG 2", b"JPEG 3", b"JPEG 4"]
    assert all(str(ligado.envios_pasta) in p for p in a["imagens"])
    assert "PUB-0294" in a["sobre"]


# ── o porteiro ────────────────────────────────────────────────────────────────

def test_dentro_da_janela_saem_so_as_imagens_e_a_legenda_na_ultima(ligado, artes):
    aviso_id = pedir(ligado, artes).json()["aviso_id"]
    numero = dono(ligado)["whatsapp"]
    falou(ligado, AGORA - timedelta(hours=2), numero=sem_o_nove(numero))
    s = SaidaComLegenda()
    volta(ligado, s)
    assert [e[0] for e in s.enviadas] == ["imagem"] * 4         # nenhum texto, nenhum modelo
    assert s.modelos == []
    assert s.legendas == ["", "", "", LEGENDA]                  # com as quebras de linha
    a = [x for x in avisos(ligado) if x["id"] == aviso_id][0]
    assert a["enviado_em"] and a["como"] == "texto" and a["erro"] == ""
    with TestClient(criar_app(ligado)) as c:
        r = c.get("/pedido/aviso/%d" % aviso_id, headers=CHAVE).json()
    assert r["situacao"] == "enviado"


def test_legenda_maior_que_a_da_imagem_vai_num_texto_depois(ligado, artes):
    longa = "x" * 1500
    pedir(ligado, artes[:2], legenda=longa)
    falou(ligado, AGORA - timedelta(hours=1), numero=sem_o_nove(dono(ligado)["whatsapp"]))
    s = SaidaComLegenda()
    volta(ligado, s)
    assert [e[0] for e in s.enviadas] == ["imagem", "imagem", "texto"]
    assert s.legendas == ["", ""] and s.enviadas[-1][2] == longa


def test_fora_da_janela_uma_reabertura_e_o_ver_solta_as_imagens(ligado, artes):
    aviso_id = pedir(ligado, artes).json()["aviso_id"]
    numero = dono(ligado)["whatsapp"]
    s = SaidaComLegenda()
    volta(ligado, s)
    assert len(s.modelos) == 1 and [e[0] for e in s.enviadas] == ["modelo"]   # so a reabertura
    a = [x for x in avisos(ligado) if x["id"] == aviso_id][0]
    assert a["guardado_em"] and not a["enviado_em"]
    toque_ver(ligado, s, numero_carga=numero, de=sem_o_nove(numero), agora=AGORA + timedelta(minutes=5))
    assert [e[0] for e in s.enviadas] == ["modelo"] + ["imagem"] * 4
    assert s.legendas[-1] == LEGENDA


def test_sem_porteiro_e_janela_fechada_fica_o_erro_e_nada_sai(ligado, artes):
    desligado = replace(ligado, porteiro=False)
    aviso_id = pedir(desligado, artes).json()["aviso_id"]
    s = SaidaComLegenda()
    volta(desligado, s)
    assert s.enviadas == [] and s.modelos == []
    a = [x for x in avisos(ligado) if x["id"] == aviso_id][0]
    assert "janela" in a["erro"]


def test_sem_porteiro_e_janela_aberta_saem_as_imagens(ligado, artes):
    desligado = replace(ligado, porteiro=False)
    pedir(desligado, artes)
    falou(desligado, AGORA - timedelta(hours=3), numero=sem_o_nove(dono(desligado)["whatsapp"]))
    s = SaidaComLegenda()
    volta(desligado, s)
    assert [e[0] for e in s.enviadas] == ["imagem"] * 4 and s.legendas[-1] == LEGENDA


def test_o_aviso_do_plano_continua_exigindo_as_partes(ligado):
    with TestClient(criar_app(ligado)) as c:
        r = c.post("/pedido/aviso", headers=CHAVE, json={"tipo": "plano_sem_registro", "partes": []})
    assert r.status_code == 422
