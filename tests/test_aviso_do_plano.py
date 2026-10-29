"""#926, o Controle do plano: o Marketing pede o aviso de "plano sem registro" ao dono pela porta do
pedido; ele entra na fila de avisos, sai na volta do envio com o modelo dele, e a situacao volta
pela mesma porta. Meta falsa: nada sai."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.banco import conexao
from backend.envio import Envio
from backend.main import criar_app
from tests.saida_falsa import SaidaFalsa

QUINTA_10H = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
CHAVE = {"X-Axiaatende-Chave": "chave-do-marketing"}
AVISO = {"tipo": "plano_sem_registro", "partes": ["7", "14/10/2026"]}


@pytest.fixture
def ligado(cfg, tmp_path):
    return replace(cfg, responde=True, chave_pedido="chave-do-marketing", envios_pasta=tmp_path / "envios")


def post(cfg, dados, cabecalho=CHAVE):
    with TestClient(criar_app(cfg)) as c:
        return c.post("/pedido/aviso", json=dados, headers=cabecalho)


def situacao(cfg, aviso_id, cabecalho=CHAVE):
    with TestClient(criar_app(cfg)) as c:
        return c.get("/pedido/aviso/%s" % aviso_id, headers=cabecalho)


def test_sem_a_chave_e_recusado(ligado):
    assert post(ligado, AVISO, cabecalho={}).status_code == 403
    assert post(ligado, AVISO, cabecalho={"X-Axiaatende-Chave": "outra"}).status_code == 403
    assert post(replace(ligado, chave_pedido=""), AVISO).status_code == 403
    assert situacao(ligado, 1, cabecalho={}).status_code == 403


def test_so_aceita_o_tipo_do_plano(ligado):
    assert post(ligado, dict(AVISO, tipo="recusa")).status_code == 422
    assert post(ligado, dict(AVISO, partes=[])).status_code == 422
    assert post(ligado, dict(AVISO, partes=["7|x", "14/10"])).status_code == 422


def test_o_aviso_vai_para_quem_recebe_o_nao_e_sai_com_o_modelo(ligado):
    r = post(ligado, AVISO)
    assert r.status_code == 200
    aviso_id = r.json()["aviso_id"]
    with conexao(ligado) as con:
        a = con.execute("SELECT * FROM atendimento.avisos WHERE id = %s", (aviso_id,)).fetchone()
        quem = con.execute("""SELECT d.nome, d.whatsapp FROM atendimento.destinos d, atendimento.ajustes j
                               WHERE j.chave = 'avisado_no_nao' AND d.id = (j.valor #>> '{}')::int""").fetchone()
    assert (a["tipo"], a["sobre"]) == ("plano_sem_registro", "7|14/10/2026")
    assert (a["para_nome"], a["para_whatsapp"]) == (quem["nome"], quem["whatsapp"])
    assert situacao(ligado, aviso_id).json()["situacao"] == "na_fila"

    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, QUINTA_10H)
    m = [x for x in s.modelos if x["nome"] == "aviso_plano_sem_registro"]
    assert len(m) == 1 and m[0]["para"] == quem["whatsapp"]
    assert m[0]["corpo"][:2] == ["7", "14/10/2026"]
    r = situacao(ligado, aviso_id).json()
    assert r["situacao"] == "enviado" and r["enviado_em"]


def test_sem_ninguem_configurado_para_receber_recusa(ligado):
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'null'::jsonb WHERE chave = 'avisado_no_nao'")
    r = post(ligado, AVISO)
    assert r.status_code == 422 and "ninguém" in r.json()["detail"]


def test_a_024_vai_volta_e_vai(ligado):
    from pathlib import Path
    pasta = Path(__file__).resolve().parents[1] / "backend" / "migracoes"
    volta = (pasta / "024_aviso_do_plano_VOLTA.sql").read_text(encoding="utf-8")
    volta = volta.replace("BEGIN;", "").replace("COMMIT;", "")
    with conexao(ligado) as con:
        con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                       VALUES ('plano_sem_registro', 'X', '5549991505565', '7|14/10')""")
        # a ordem das voltas e a inversa da das idas: a 039 (#1188), a 033 (#1142), a 032 (#1090) e a
        # 025 (#1098) mexem nos mesmos CHECKs
        volta_039 = (pasta / "039_porteiro_dos_avisos_VOLTA.sql").read_text(encoding="utf-8")
        con.execute(volta_039.replace("BEGIN;", "").replace("COMMIT;", ""))
        volta_033 = (pasta / "033_fila_por_numero_e_resumo_VOLTA.sql").read_text(encoding="utf-8")
        con.execute(volta_033.replace("BEGIN;", "").replace("COMMIT;", ""))
        volta_032 = (pasta / "032_clientes_do_dia_VOLTA.sql").read_text(encoding="utf-8")
        con.execute(volta_032.replace("BEGIN;", "").replace("COMMIT;", ""))
        volta_025 = (pasta / "025_trabalhe_conosco_VOLTA.sql").read_text(encoding="utf-8")
        con.execute(volta_025.replace("BEGIN;", "").replace("COMMIT;", ""))
        con.execute(volta)
        assert con.execute("SELECT count(*) AS n FROM atendimento.avisos WHERE tipo = 'plano_sem_registro'"
                           ).fetchone()["n"] == 0
        assert not con.execute("SELECT 1 FROM atendimento.modelos WHERE uso = 'aviso_plano_sem_registro'").fetchone()
        con.execute((pasta / "024_aviso_do_plano.sql").read_text(encoding="utf-8"))
        assert con.execute("SELECT 1 FROM atendimento.modelos WHERE uso = 'aviso_plano_sem_registro'").fetchone()


def test_situacao_de_outro_tipo_nao_aparece(ligado):
    with conexao(ligado) as con:
        outro = con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                               VALUES ('recusa', 'X', '5549991505565', 'a') RETURNING id""").fetchone()["id"]
    assert situacao(ligado, outro).status_code == 404
