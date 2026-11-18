"""#1542 (etapa 3): o termo de reprovacao do ERP ao WhatsApp Legal do produtor. As telas trazem o pedido com o
PDF e devolvem estado e ciencia; o recepcionista manda o MODELO (so com a chave) e recebe o toque.
Meta falsa e ERP falso: nada sai."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from backend import erp, recepcionista as R, termo_erp
from backend.banco import conexao
from tests.avisos_meta import aviso, status
from tests.saida_falsa import SaidaFalsa

AGORA = datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc)
PRODUTOR = "5514996033466"
PENDENTE = {"id": 41, "termo_id": 11, "destino": PRODUTOR, "numero_termo": "0001/2026", "valor_total": "2970.00",
            "data_vencimento": "2026-12-02", "produtor_nome": "ALFONSO ADRIANO SLEUTJES E OUTRA",
            "lotes": "A206201-01", "arquivo": "TERMO_REPROVACAO_0001-2026.pdf"}


@pytest.fixture
def ligado(cfg, tmp_path):
    return replace(cfg, erp_segredo="segredo-de-teste", envios_pasta=tmp_path / "envios", responde=True,
                   termo_reprovacao_ativo=True)


class ErpFalso:
    def __init__(self, pendentes=(), recusa_ciencia=None, fora=False):
        self.pendentes, self.recusa_ciencia, self.fora = list(pendentes), recusa_ciencia, fora
        self.estados, self.ciencias = [], []

    def ir(self, cfg):
        if self.fora:
            raise erp.ErpIndisponivel("o ERP não respondeu")
        return {"pendentes": self.pendentes, "token": "t"}

    def pdf(self, cfg, token, termo_id):
        return b"%PDF-1.4 termo"

    def estado(self, cfg, token, envio_id, estado, motivo="", wamid=""):
        if self.fora:
            raise erp.ErpIndisponivel("o ERP não respondeu")
        self.estados.append((envio_id, estado, motivo, wamid))

    def ciencia(self, cfg, token, envio_id, numero, quando, wamid=""):
        if self.recusa_ciencia:
            raise erp.ErpRecusou(self.recusa_ciencia)
        self.ciencias.append((envio_id, numero, quando, wamid))
        return {"ciencia_no_termo": True}


def _volta(cfg, e):
    return termo_erp.volta(cfg, ir=e.ir, pdf=e.pdf, estado=e.estado, ciencia=e.ciencia)


def _linha(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.termos_reprovacao ORDER BY id DESC LIMIT 1").fetchone()


def _mandar(cfg, saida, ativo=True):
    with conexao(cfg) as con:
        return termo_erp.mandar(con, saida, ativo, AGORA)


def _toque(cfg, saida, payload, numero=PRODUTOR, wamid="wamid.toque"):
    msg = {"from": numero, "id": wamid, "timestamp": str(int(AGORA.timestamp())), "type": "button",
           "context": {"from": "554936640121", "id": "wamid.termo"},
           "button": {"payload": payload, "text": "Recebi e estou ciente"}}
    R.gravar(cfg, aviso([msg], numero=numero, bsuid="BR." + numero))
    R.processar_pendentes(cfg, saida, None, agora=AGORA)


def test_sem_o_segredo_nem_tenta(cfg):
    assert termo_erp.volta(cfg) == {"erro": "a ligação com o ERP não está ligada"}


def test_o_pedido_vem_com_o_pdf_e_o_modelo_sai_com_o_documento_e_a_carga(ligado):
    e = ErpFalso([PENDENTE])
    assert _volta(ligado, e)["novos"] == 1
    assert _volta(ligado, e)["novos"] == 0          # repetido nao entra de novo
    s = SaidaFalsa()
    assert _mandar(ligado, s) == 1
    (m,) = s.modelos
    linha = _linha(ligado)
    assert (m["para"], m["nome"]) == (PRODUTOR, "termo_reprovacao_lote")
    assert m["corpo"] == ["ALFONSO ADRIANO SLEUTJES E OUTRA", "0001/2026", "A206201-01", "2.970,00", "02/12/2026"]
    assert m["botoes"] == ["termo:ciente:%d" % linha["id"]]
    assert m["documento"] == (b"%PDF-1.4 termo", "TERMO_REPROVACAO_0001-2026.pdf")
    assert (linha["estado"], bool(linha["wamid"])) == ("enviada", True)
    _volta(ligado, e)
    assert e.estados == [(41, "ENVIADO", "", linha["wamid"])]
    _volta(ligado, e)
    assert len(e.estados) == 1                       # o mesmo estado nao vai duas vezes


def test_chave_desligada_nada_sai(ligado):
    _volta(ligado, ErpFalso([PENDENTE]))
    s = SaidaFalsa()
    assert _mandar(ligado, s, ativo=False) == 0 and not s.modelos
    assert _linha(ligado)["estado"] == "a_enviar"


def test_fora_das_9h_as_17h_espera_e_sai_na_janela(ligado):
    _volta(ligado, ErpFalso([PENDENTE]))
    s = SaidaFalsa()
    for hora_utc in (11, 20, 2):                     # 08h, 17h e 23h em Brasilia
        with conexao(ligado) as con:
            assert termo_erp.mandar(con, s, True, AGORA.replace(hour=hora_utc)) == 0
    assert not s.modelos and _linha(ligado)["estado"] == "a_enviar"
    with conexao(ligado) as con:
        assert termo_erp.mandar(con, s, True, AGORA.replace(hour=12)) == 1   # 09h em Brasilia
    assert _linha(ligado)["estado"] == "enviada"


def test_termo_estornado_antes_de_sair_nao_sai(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    assert _linha(ligado)["estado"] == "a_enviar"
    e.pendentes = []                                 # estornado no ERP: some da lista
    _volta(ligado, e)
    assert _linha(ligado) is None
    s = SaidaFalsa()
    assert _mandar(ligado, s) == 0 and not s.modelos


def test_o_que_ja_saiu_nao_some_quando_o_erp_tira_da_lista(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    _mandar(ligado, SaidaFalsa())
    e.pendentes = []
    _volta(ligado, e)
    assert _linha(ligado)["estado"] == "enviada"


def test_falha_da_meta_vira_falhou_e_volta_ao_erp(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    s = SaidaFalsa()
    s.modelo_falha = "131026 Message undeliverable"
    _mandar(ligado, s)
    assert _linha(ligado)["estado"] == "falhou"
    _volta(ligado, e)
    assert e.estados[0][1] == "FALHOU" and "131026" in e.estados[0][2]


def test_os_avisos_da_meta_avancam_e_nao_voltam(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    s = SaidaFalsa()
    _mandar(ligado, s)
    w = _linha(ligado)["wamid"]
    R.gravar(ligado, aviso(statuses=[status(w, "read", PRODUTOR)]))
    R.gravar(ligado, aviso(statuses=[status(w, "delivered", PRODUTOR)]))
    R.processar_pendentes(ligado, s, None, agora=AGORA)
    assert _linha(ligado)["estado"] == "lida"
    _volta(ligado, e)
    assert e.estados[-1][1] == "LIDO"


def test_o_toque_do_numero_certo_vira_ciencia_e_tem_resposta(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    s = SaidaFalsa()
    _mandar(ligado, s)
    linha = _linha(ligado)
    _toque(ligado, s, "termo:ciente:%d" % linha["id"])
    linha = _linha(ligado)
    assert linha["ciencia_em"] and linha["ciencia_numero"] == PRODUTOR and linha["ciencia_wamid"] == "wamid.toque"
    assert any(x[0] == "texto" and "0001/2026" in x[2] for x in s.enviadas)
    _volta(ligado, e)
    assert e.ciencias and e.ciencias[0][:2] == (41, PRODUTOR)
    assert _linha(ligado)["ciencia_devolvida_em"]


def test_o_toque_de_outro_numero_o_erp_recusa_e_nao_se_tenta_de_novo(ligado):
    e = ErpFalso([PENDENTE], recusa_ciencia="O número que tocou não é o do pedido: não vale como ciência.")
    _volta(ligado, e)
    s = SaidaFalsa()
    _mandar(ligado, s)
    _toque(ligado, s, "termo:ciente:%d" % _linha(ligado)["id"], numero="5549999990000")
    _volta(ligado, e)
    linha = _linha(ligado)
    assert linha["ciencia_recusada"].startswith("O número que tocou") and linha["ciencia_devolvida_em"] is None
    e.recusa_ciencia = None
    _volta(ligado, e)
    assert not e.ciencias                            # recusada fica recusada


def test_erp_fora_do_ar_o_estado_espera_a_volta_seguinte(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    s = SaidaFalsa()
    _mandar(ligado, s)
    e.fora = True
    assert "erro" in _volta(ligado, e)
    e.fora = False
    _volta(ligado, e)
    assert [x[1] for x in e.estados] == ["ENVIADO"]
