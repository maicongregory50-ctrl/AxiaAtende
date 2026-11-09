"""#1337: o aviso de API externa recusando (#1280 no ERP) vai ao WhatsApp do dono pelo mesmo caminho da
auditoria de estoque -- `auditoria_erp.py` em canais. Os testes do #350 (test_auditoria_erp.py) seguem
intactos; estes cobrem o canal novo, a separacao entre canais e os dois clientes de `erp.py`."""
import io
import json
import urllib.error
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend import auditoria_erp, erp, migracoes
from backend.auditoria_erp import Canal
from backend.banco import conexao
from backend.envio import Envio
from tests.saida_falsa import SaidaFalsa
from tests.test_1188_porteiro import falou

AGORA = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
TEXTO = "a SEFAZ (NF-e) recusou 3 vezes seguidas: Rejeição 999. Chamado #1400."
PENDENTE = {"id": 7, "partes": [TEXTO]}


@pytest.fixture
def ligado(cfg):
    return replace(cfg, erp_segredo="segredo-de-teste", erp_agente="ATENDIMENTO", porteiro=True, responde=True)


class ErpFalso:
    def __init__(self, pendentes=(), fora=None):
        self.pendentes, self.fora, self.estados = list(pendentes), fora, []

    def ir(self, cfg):
        if self.fora:
            raise erp.ErpIndisponivel(self.fora)
        return {"pendentes": self.pendentes, "token": "t"}

    def devolver(self, cfg, token, aviso_id, estado, motivo="", wamid=""):
        self.estados.append((aviso_id, estado, motivo, wamid))


def _canais(integ, audit=None):
    audit = audit or ErpFalso()
    return (Canal("auditoria_estoque", audit.ir, audit.devolver, "auditoria_estoque_para"),
            Canal("integracao_recusada", integ.ir, integ.devolver, "integracoes_para"))


def _volta(cfg, integ, audit=None):
    return auditoria_erp.volta(cfg, canais=_canais(integ, audit))


def _avisos(cfg, tipo="integracao_recusada"):
    with conexao(cfg) as con:
        return [dict(a) for a in con.execute(
            "SELECT * FROM atendimento.avisos WHERE tipo = %s ORDER BY id", (tipo,)).fetchall()]


# ── a migracao ────────────────────────────────────────────────────────────────

def test_a_migracao_poe_so_o_dono_e_o_modelo(cfg):
    with conexao(cfg) as con:
        nomes = [d["nome"] for d in auditoria_erp.destinos(con, "integracoes_para")]
        m = con.execute("SELECT * FROM atendimento.modelos WHERE uso = 'aviso_integracao_recusada'").fetchone()
    assert nomes == ["Maicon Gregory"]
    assert m["nome"] == "aviso_integracao" and m["categoria"] == "UTILITY"
    assert m["variaveis"] == ["aviso1"] and m["texto"] == "Aviso do AxiaGestão: {{1}}"


def test_a_volta_da_060_desfaz_e_a_ida_refaz(ligado):
    _volta(ligado, ErpFalso([PENDENTE]))
    raiz = Path(migracoes.__file__).parent / "migracoes"
    with conexao(ligado) as con:
        con.execute((raiz / "060_aviso_integracao_VOLTA.sql").read_text(encoding="utf-8"))
        assert not con.execute("SELECT 1 FROM atendimento.ajustes WHERE chave = 'integracoes_para'").fetchone()
        assert not con.execute("""SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                                   AND table_name = 'avisos_auditoria_erp' AND column_name = 'canal'""").fetchone()
        con.execute((raiz / "060_aviso_integracao.sql").read_text(encoding="utf-8"))
    assert _avisos(ligado) == []


# ── o canal ───────────────────────────────────────────────────────────────────

def test_pendente_vira_um_aviso_por_destino_com_o_texto(ligado):
    e = ErpFalso([PENDENTE])
    r = _volta(ligado, e)
    assert r["canais"]["integracao_recusada"]["novos"] == 1
    assert _volta(ligado, e)["canais"]["integracao_recusada"]["novos"] == 0
    a = _avisos(ligado)
    assert len(a) == 1 and a[0]["sobre"] == TEXTO and a[0]["para_nome"] == "Maicon Gregory"
    assert e.estados == []


def test_enviado_devolve_enviado_com_o_wamid(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    with conexao(ligado) as con:
        con.execute("""UPDATE atendimento.avisos SET enviado_em = %s, wamid = 'wamid.i'
                        WHERE tipo = 'integracao_recusada'""", (AGORA,))
    _volta(ligado, e)
    _volta(ligado, e)
    assert e.estados == [(7, "ENVIADO", "", "wamid.i")]


def test_erro_em_todos_devolve_falhou(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.avisos SET erro = 'numero invalido' WHERE tipo = 'integracao_recusada'")
    _volta(ligado, e)
    assert e.estados == [(7, "FALHOU", "numero invalido", "")]


def test_sem_destino_falha_com_a_frase_do_ajuste(ligado):
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = '[]'::jsonb WHERE chave = 'integracoes_para'")
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    assert e.estados == [(7, "FALHOU", "Ninguém configurado para receber o aviso (ajuste integracoes_para).", "")]


def test_o_mesmo_id_nos_dois_canais_nao_colide(ligado):
    audit = ErpFalso([{"id": 7, "partes": ["Matriz", "29/10/2026"]}])
    integ = ErpFalso([PENDENTE])
    r = _volta(ligado, integ, audit)
    assert r["canais"]["auditoria_estoque"]["novos"] == 1 and r["canais"]["integracao_recusada"]["novos"] == 1
    assert len(_avisos(ligado)) == 1 and len(_avisos(ligado, "auditoria_estoque")) == 2
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.avisos SET enviado_em = %s, wamid = 'w' WHERE tipo = 'integracao_recusada'",
                    (AGORA,))
    _volta(ligado, integ, audit)
    assert integ.estados == [(7, "ENVIADO", "", "w")] and audit.estados == []


def test_canal_fora_do_ar_nao_para_o_outro(ligado):
    integ = ErpFalso([PENDENTE])
    r = _volta(ligado, integ, ErpFalso(fora="o ERP não respondeu"))
    assert r["canais"]["auditoria_estoque"] == {"erro": "o ERP não respondeu"}
    assert r["canais"]["integracao_recusada"]["novos"] == 1


def test_a_volta_padrao_tem_os_dois_canais(ligado, monkeypatch):
    assert [c.nome for c in auditoria_erp.CANAIS] == ["auditoria_estoque", "integracao_recusada"]
    assert auditoria_erp.CANAIS[1].ir is erp.integracoes_pendentes
    assert auditoria_erp.CANAIS[1].devolver is erp.estado_do_aviso_integracao


# ── a saida, pelo porteiro ────────────────────────────────────────────────────

def _dono(cfg):
    with conexao(cfg) as con:
        return auditoria_erp.destinos(con, "integracoes_para")[0]["whatsapp"]


def test_dentro_da_janela_sai_o_texto(ligado):
    _volta(ligado, ErpFalso([PENDENTE]))
    falou(ligado, AGORA - timedelta(hours=2), numero=_dono(ligado))
    s = SaidaFalsa()
    with conexao(ligado) as con:
        en = Envio()
        en._porteiro = True
        en.mandar_avisos(con, s, AGORA)
    assert s.modelos == []
    assert [x[0] for x in s.enviadas] == ["texto"] and s.enviadas[0][2] == "Aviso do AxiaGestão: " + TEXTO
    assert _avisos(ligado)[0]["enviado_em"] == AGORA


def test_fora_da_janela_sai_a_reabertura_e_guarda(ligado):
    _volta(ligado, ErpFalso([PENDENTE]))
    s = SaidaFalsa()
    with conexao(ligado) as con:
        en = Envio()
        en._porteiro = True
        en.mandar_avisos(con, s, AGORA)
    assert [m["nome"] for m in s.modelos] == ["reabrir_avisos"]
    a = _avisos(ligado)[0]
    assert a["guardado_em"] == AGORA and a["enviado_em"] is None


# ── os dois clientes de erp.py ────────────────────────────────────────────────

class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def rede(monkeypatch):
    """`urlopen` falso: guarda o pedido e responde o que o teste mandar (corpo ou codigo de erro)."""
    estado = {"pedidos": [], "resposta": {}}

    def urlopen(pedido, timeout=None):
        estado["pedidos"].append(pedido)
        r = estado["resposta"]
        if isinstance(r, int):
            raise urllib.error.HTTPError(pedido.full_url, r, "x", {}, io.BytesIO(b"{}"))
        return _Resp(json.dumps(r).encode())

    monkeypatch.setattr(erp, "_token", lambda cfg: "t")
    monkeypatch.setattr(erp.urllib.request, "urlopen", urlopen)
    return estado


def test_cliente_traz_os_pendentes_no_formato_do_canal(ligado, rede):
    rede["resposta"] = {"tipo": "integracao_recusada",
                        "avisos": [{"id": 3, "fonte": "sefaz", "texto": TEXTO, "criado_em": "2026-11-09T10:00:00"}]}
    r = erp.integracoes_pendentes(ligado)
    assert r == {"pendentes": [{"id": 3, "partes": [TEXTO]}], "token": "t"}
    assert rede["pedidos"][0].full_url.endswith("/atendimento/integracoes-avisos")


def test_cliente_sem_permissao_cita_a_atividade(ligado, rede):
    rede["resposta"] = 403
    with pytest.raises(erp.ErpIndisponivel, match="AUD.AVISO"):
        erp.integracoes_pendentes(ligado)


def test_devolver_e_patch_e_409_nao_e_erro(ligado, rede):
    rede["resposta"] = {"ok": True}
    erp.estado_do_aviso_integracao(ligado, "t", 3, "ENVIADO", wamid="wamid.x")
    p = rede["pedidos"][0]
    assert p.get_method() == "PATCH" and p.full_url.endswith("/atendimento/integracoes-avisos/3")
    assert json.loads(p.data) == {"estado": "ENVIADO", "motivo": None, "ref_externa": "wamid.x"}
    rede["resposta"] = 409
    erp.estado_do_aviso_integracao(ligado, "t", 3, "ENVIADO")      # ja respondido: silencio
    rede["resposta"] = 403
    with pytest.raises(erp.ErpIndisponivel, match="AUD.AVISO"):
        erp.estado_do_aviso_integracao(ligado, "t", 3, "FALHOU", motivo="x")
