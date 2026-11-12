"""#1434: o aviso de classe 1 do painel da casa vem de uma PASTA (a revisao do AxiaSecurity escreve) e vai
ao WhatsApp do dono pelo canal `painel_classe1` de `auditoria_erp.py`. Estes testes cobrem a migracao, o
canal por arquivo, a devolucao em arquivo e a independencia do ERP."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from backend import auditoria_erp, migracoes, painel_avisos
from backend.auditoria_erp import CANAIS
from backend.banco import conexao

TEXTO = "[CRÍTICO] axiaatende-recepcionista parado -- visto às 14:02 no painel. Feito até agora: reinício pela porta, não voltou. Chamado #1500."


@pytest.fixture
def painel(cfg, tmp_path):
    c = replace(cfg, painel_pedidos=tmp_path / "pedidos", painel_devolucao=tmp_path / "devolucao")
    c.painel_pedidos.mkdir()
    return c


def _pedir(cfg, pid, texto=TEXTO):
    (Path(cfg.painel_pedidos) / ("%d.json" % pid)).write_text(
        json.dumps({"id": pid, "texto": texto}, ensure_ascii=False), encoding="utf-8")


def _canal():
    return next(c for c in CANAIS if c.nome == "painel_classe1")


def _volta(cfg):
    return auditoria_erp.volta(cfg, canais=(_canal(),))


def _avisos(cfg):
    with conexao(cfg) as con:
        return [dict(a) for a in con.execute(
            "SELECT * FROM atendimento.avisos WHERE tipo = 'painel_classe1' ORDER BY id").fetchall()]


def _devolucao(cfg, pid):
    p = Path(cfg.painel_devolucao) / ("%d.json" % pid)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ── a migracao ────────────────────────────────────────────────────────────────

def test_a_migracao_poe_o_dono_e_o_modelo(cfg):
    with conexao(cfg) as con:
        nomes = [d["nome"] for d in auditoria_erp.destinos(con, "painel_para")]
        m = con.execute("SELECT * FROM atendimento.modelos WHERE uso = 'aviso_painel_classe1'").fetchone()
    assert nomes == ["Maicon Gregory"]
    assert m["nome"] == "aviso_painel" and m["categoria"] == "UTILITY" and m["variaveis"] == ["aviso1"]
    assert m["texto"] == "Aviso do painel da casa: {{1}} O detalhe está no painel."


def test_a_volta_da_063_desfaz_e_a_ida_refaz(painel):
    _pedir(painel, 1)
    _volta(painel)
    raiz = Path(migracoes.__file__).parent / "migracoes"
    with conexao(painel) as con:
        con.execute((raiz / "063_aviso_painel_VOLTA.sql").read_text(encoding="utf-8"))
        assert not con.execute("SELECT 1 FROM atendimento.ajustes WHERE chave = 'painel_para'").fetchone()
        con.execute((raiz / "063_aviso_painel.sql").read_text(encoding="utf-8"))
    assert _avisos(painel) == []


# ── o canal ───────────────────────────────────────────────────────────────────

def test_pedido_vira_um_aviso_para_o_dono_e_nao_repete(painel):
    _pedir(painel, 1)
    r = _volta(painel)
    assert r["canais"]["painel_classe1"]["novos"] == 1
    assert _volta(painel)["canais"]["painel_classe1"]["novos"] == 0
    a = _avisos(painel)
    assert len(a) == 1 and a[0]["sobre"] == TEXTO and a[0]["para_nome"] == "Maicon Gregory"
    assert _devolucao(painel, 1) is None   # ainda nao saiu: nada a devolver


def test_enviado_devolve_enviado_no_arquivo(painel):
    _pedir(painel, 2)
    _volta(painel)
    with conexao(painel) as con:
        con.execute("UPDATE atendimento.avisos SET enviado_em = now(), wamid = 'wamid.p' WHERE tipo = 'painel_classe1'")
    _volta(painel)
    d = _devolucao(painel, 2)
    assert d["estado"] == "ENVIADO" and d["wamid"] == "wamid.p" and d["id"] == 2
    assert not list(Path(painel.painel_devolucao).glob("*.tmp"))


def test_erro_devolve_falhou_com_o_motivo(painel):
    _pedir(painel, 3)
    _volta(painel)
    with conexao(painel) as con:
        con.execute("UPDATE atendimento.avisos SET erro = 'numero invalido' WHERE tipo = 'painel_classe1'")
    _volta(painel)
    d = _devolucao(painel, 3)
    assert d["estado"] == "FALHOU" and d["motivo"] == "numero invalido"


def test_pedido_ilegivel_e_pulado_e_o_bom_segue(painel):
    (Path(painel.painel_pedidos) / "9.json").write_text("{nao e json", encoding="utf-8")
    (Path(painel.painel_pedidos) / "8.json").write_text(json.dumps({"id": 8, "texto": ""}), encoding="utf-8")
    _pedir(painel, 4)
    assert _volta(painel)["canais"]["painel_classe1"]["novos"] == 1


def test_pasta_ausente_e_erro_do_canal_e_nao_para_os_outros(cfg, tmp_path):
    c = replace(cfg, painel_pedidos=tmp_path / "nao-existe", painel_devolucao=tmp_path / "dev")
    r = _volta(c)
    assert "nao existe" in r["canais"]["painel_classe1"]["erro"]


def test_sem_o_erp_o_painel_roda(painel):
    _pedir(painel, 5)
    r = auditoria_erp.volta(painel)   # cfg de teste: sem o segredo do ERP
    assert r["erro"] == "a ligação com o ERP não está ligada"
    assert r["canais"]["painel_classe1"]["novos"] == 1


def test_o_texto_do_aviso_e_o_do_modelo(painel):
    _pedir(painel, 6)
    _volta(painel)
    from backend.envio import texto_do_aviso
    with conexao(painel) as con:
        a = con.execute("SELECT * FROM atendimento.avisos WHERE tipo = 'painel_classe1'").fetchone()
        assert texto_do_aviso(con, a) == "Aviso do painel da casa: " + TEXTO + " O detalhe está no painel."


def test_devolver_cria_a_pasta(cfg, tmp_path):
    c = replace(cfg, painel_devolucao=tmp_path / "nova" / "pasta")
    painel_avisos.devolver(c, "", 11, "ENVIADO", wamid="w")
    assert json.loads((tmp_path / "nova" / "pasta" / "11.json").read_text(encoding="utf-8"))["estado"] == "ENVIADO"
