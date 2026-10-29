"""#1128: o pedido de CT-e da Logistica do ERP. As telas contam a janela ao ERP, enfileiram o pedido com a
ficha e devolvem o estado; o recepcionista manda o PDF SO com a janela de 24 h aberta (sem modelo)."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import erp, logistica_erp
from backend.banco import conexao
from tests.saida_falsa import SaidaFalsa

AGORA = datetime.now(timezone.utc)
BENEDITO = "5549999190249"          # como o cadastro guarda (com o 9)
BENEDITO_META = "554999190249"      # como a Meta manda (sem o 9)
PENDENTE = {"id": 7, "frete_id": 3, "numero": "FRT-2026-0003",
            "texto": "Solicitação de CT-e FRT-2026-0003 · Saída: Cunha Porã/SC → Uberlândia/MG. Ficha em anexo.",
            "arquivo": "ficha-FRT-2026-0003.pdf"}


@pytest.fixture
def ligado(cfg, tmp_path):
    c = replace(cfg, erp_segredo="segredo-de-teste", envios_pasta=tmp_path / "envios")
    with conexao(c) as con:
        con.execute("INSERT INTO atendimento.destinos (nome, whatsapp, ativo) VALUES ('Logistica', %s, true)", (BENEDITO,))
    return c


def _falou(cfg, quando):
    corpo = {"contacts": [], "msg": {"from": BENEDITO_META, "id": "wamid.l", "type": "text", "text": {"body": "oi"}}}
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo, recebido_em)
                       VALUES ('wamid.l', 'mensagem', %s, %s)""", (json.dumps(corpo), quando))


class ErpFalso:
    def __init__(self, pendentes=()):
        self.pendentes = list(pendentes)
        self.janelas, self.estados = [], []

    def ir(self, cfg, janela):
        self.janelas.append(janela)
        return {"pendentes": self.pendentes, "token": "t"}

    def ficha(self, cfg, token, frete_id):
        return b"%PDF-1.4 ficha"

    def devolver(self, cfg, token, pedido_id, estado, motivo="", wamid=""):
        self.estados.append((pedido_id, estado, motivo, wamid))


def _volta(cfg, e):
    return logistica_erp.volta(cfg, ir=e.ir, ficha=e.ficha, devolver=e.devolver)


def test_sem_o_segredo_nem_tenta(cfg):
    assert logistica_erp.volta(cfg) == {"erro": "a ligação com o ERP não está ligada"}


def test_o_destino_acha_sem_acento_e_a_janela_vai_ao_erp(ligado):
    _falou(ligado, AGORA - timedelta(hours=2))
    e = ErpFalso()
    _volta(ligado, e)
    j = e.janelas[0]
    assert j["destino"] == "Logistica"
    assert datetime.fromisoformat(j["aberta_ate"]) > AGORA + timedelta(hours=21)


def test_sem_recado_a_janela_vai_vazia(ligado):
    e = ErpFalso()
    _volta(ligado, e)
    assert e.janelas[0]["aberta_ate"] is None


def test_janela_aberta_o_pdf_sai_e_o_estado_volta(ligado):
    _falou(ligado, AGORA - timedelta(hours=1))
    e = ErpFalso([PENDENTE])
    assert _volta(ligado, e)["novos"] == 1
    saida = SaidaFalsa()
    with conexao(ligado) as con:
        assert logistica_erp.mandar(con, saida, AGORA) == 1
    tipo, para, legenda, _ = saida.enviadas[0]
    assert (tipo, para) == ("documento", BENEDITO) and legenda == PENDENTE["texto"]
    assert saida.documentos[0][1] == b"%PDF-1.4 ficha" and saida.documentos[0][2] == "ficha-FRT-2026-0003.pdf"
    e.pendentes = [PENDENTE]          # o ERP ainda lista ate receber o estado: nao duplica
    _volta(ligado, e)
    assert e.estados == [(7, "ENVIADO", "", "wamid.saida.1")]
    with conexao(ligado) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.pedidos_cte").fetchone()["n"] == 1


def test_janela_fechada_nao_sai_e_volta_falhou_com_a_frase(ligado):
    _falou(ligado, AGORA - timedelta(hours=30))
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    saida = SaidaFalsa()
    with conexao(ligado) as con:
        assert logistica_erp.mandar(con, saida, AGORA) == 0
    assert saida.enviadas == []
    _volta(ligado, e)
    assert e.estados == [(7, "FALHOU", "Você precisa abrir a janela no WhatsApp.", "")]


def test_sem_logistica_vai_ao_destino_do_item_fretes_do_menu(cfg, tmp_path):
    c = replace(cfg, erp_segredo="s", envios_pasta=tmp_path / "envios")
    with conexao(c) as con:
        esperado = con.execute("""SELECT d.nome FROM atendimento.menu m JOIN atendimento.destinos d ON d.id = m.destino_id
                                   WHERE m.chave = 'fretes'""").fetchone()["nome"]
    e = ErpFalso()
    _volta(c, e)
    assert e.janelas[0]["destino"] == esperado


def test_logistica_no_meio_do_nome_tambem_serve(cfg, tmp_path):
    c = replace(cfg, erp_segredo="s", envios_pasta=tmp_path / "envios")
    with conexao(c) as con:
        con.execute("INSERT INTO atendimento.destinos (nome, whatsapp, ativo) VALUES ('Benedito - Logística', %s, true)", (BENEDITO,))
    e = ErpFalso()
    _volta(c, e)
    assert e.janelas[0]["destino"] == "Benedito - Logística"


def test_sem_destino_volta_falhou_dizendo_o_que_falta(cfg, tmp_path):
    c = replace(cfg, erp_segredo="s", envios_pasta=tmp_path / "envios")
    with conexao(c) as con:
        con.execute("UPDATE atendimento.destinos SET ativo = false")
    e = ErpFalso([PENDENTE])
    _volta(c, e)
    _volta(c, e)
    assert e.estados[0][1] == "FALHOU" and "Destinos" in e.estados[0][2]


def test_erp_fora_vira_erro_e_nada_e_gravado(ligado):
    def fora(cfg, janela):
        raise erp.ErpIndisponivel("o ERP não respondeu")
    assert logistica_erp.volta(ligado, ir=fora) == {"erro": "o ERP não respondeu"}
    with conexao(ligado) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.pedidos_cte").fetchone()["n"] == 0
