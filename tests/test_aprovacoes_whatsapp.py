"""#1276: o aviso de aprovação no WhatsApp. O ERP manda o ESTADO (os pedidos que esperam aprovação), as
TELAS gravam uma pendência informativa por pedido × etapa × número, o RECEPCIONISTA manda só com a janela
aberta -- nunca o modelo pago -- juntando os pedidos da pessoa numa mensagem só. Meta e ERP falsos."""
from dataclasses import replace
from datetime import timedelta

import pytest

from backend import pendencias, pendencias_erp
from backend.banco import conexao
from tests.test_pendencias import AGORA, FRAN, FRAN_META, chega, falou, mandar, mensagens, saida

VENDA = {"referencia": "venda:548:comercial", "tipo": "venda", "pedido_id": 548, "numero": "PED-2026-0487",
         "etapa": "comercial", "contraparte": "SILVIO CESAR LORENSI", "valor_total": 55800.0, "condicao": "30 DIAS",
         "filial": "FILIAL FREDERICO — FREDERICO WESTPHALEN/RS", "usuario_id": 1, "numero_whatsapp": FRAN}
COMPRA = dict(VENDA, referencia="compra:25:comercial", tipo="compra", pedido_id=25, numero="PEDC-2026-023",
              contraparte="ROBERTO VASCONCELOS BOEMO", condicao=None)


class ErpFalso:
    def __init__(self, linhas=()):
        self.linhas, self.pedidos = list(linhas), 0

    def trazer(self, cfg):
        self.pedidos += 1
        return list(self.linhas)


@pytest.fixture
def ligado(cfg):
    c = replace(cfg, erp_segredo="segredo-de-teste", porteiro=True, responde=True)
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'pendencias.ligado'")
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'pendencias.aprovacao.ligado'")
        con.execute("UPDATE atendimento.ajustes SET valor = '0'::jsonb WHERE chave = 'pendencias.juntar_minutos'")
    return c


def volta(cfg, e, agora=AGORA):
    return pendencias_erp.volta_aprovacoes(cfg, trazer=e.trazer, agora=agora)


def test_nasce_desligado_e_desligado_nem_pergunta_ao_erp(cfg):
    c = replace(cfg, erp_segredo="segredo-de-teste")
    e = ErpFalso([VENDA])
    assert volta(c, e) == {"desligado": True} and e.pedidos == 0


def test_dentro_da_janela_sai_uma_mensagem_com_os_dois_pedidos(ligado):
    falou(ligado, AGORA - timedelta(hours=1))
    assert volta(ligado, ErpFalso([VENDA, COMPRA]))["novas"] == 2
    s = mandar(ligado)
    assert s.modelos == [] and len(s.enviadas) == 1
    tipo, para, texto, _ = s.enviadas[0]
    assert tipo == "texto" and para == FRAN
    assert texto.startswith("*Aprovação esperando você*\n")
    assert "Venda PED-2026-0487 · SILVIO CESAR LORENSI · R$ 55.800,00 · 30 DIAS · Frederico" in texto
    assert "Compra PEDC-2026-023 · ROBERTO VASCONCELOS BOEMO · R$ 55.800,00 · Frederico" in texto
    assert "Abra *Aprovações* no app do celular." in texto and texto.endswith("_Só aviso, não precisa responder._")
    assert {m["estado"] for m in mensagens(ligado)} == {"enviada"}


def test_fora_da_janela_espera_calado_e_nunca_chama_o_modelo(ligado):
    volta(ligado, ErpFalso([VENDA]))
    s = mandar(ligado)
    assert s.enviadas == [] and s.modelos == []
    assert [m["estado"] for m in mensagens(ligado)] == ["esperando"]
    falou(ligado, AGORA + timedelta(minutes=5))           # a pessoa escreveu: a janela abriu
    s = mandar(ligado, AGORA + timedelta(minutes=6))
    assert len(s.enviadas) == 1 and s.modelos == []


def test_decidido_antes_de_sair_nao_sai(ligado):
    e = ErpFalso([VENDA])
    volta(ligado, e)
    e.linhas = []                                        # aprovado pelo celular antes da janela abrir
    assert volta(ligado, e)["fechadas"] == 1
    falou(ligado, AGORA + timedelta(minutes=5))
    assert mandar(ligado, AGORA + timedelta(minutes=6)).enviadas == []
    (m,) = mensagens(ligado)
    assert m["estado"] == "descartada" and m["erro"] == "decidido antes de sair"


def test_a_mesma_lista_nao_avisa_duas_vezes(ligado):
    e = ErpFalso([VENDA])
    volta(ligado, e)
    assert volta(ligado, e)["novas"] == 0
    assert len(mensagens(ligado)) == 1


def test_recusado_e_mandado_de_novo_e_aviso_novo(ligado):
    e = ErpFalso([VENDA])
    volta(ligado, e)
    e.linhas = []
    volta(ligado, e)
    e.linhas = [VENDA]                                   # corrigido e de volta à comercial
    assert volta(ligado, e)["novas"] == 1
    with conexao(ligado) as con:
        refs = sorted(r["referencia"] for r in con.execute(
            "SELECT referencia FROM atendimento.pendencias WHERE tipo = 'aprovacao'").fetchall())
    assert refs[0] == "venda:548:comercial" and refs[1].startswith("venda:548:comercial~")


def test_aviso_nao_entra_na_escolha_da_olivia(ligado):
    volta(ligado, ErpFalso([VENDA]))
    with conexao(ligado) as con:
        assert pendencias._pendencias_da_pessoa(con, FRAN_META) == []


def test_responder_o_aviso_ensina_que_ele_nao_aprova(ligado):
    falou(ligado, AGORA - timedelta(hours=1))
    volta(ligado, ErpFalso([VENDA]))
    mandar(ligado)
    (m,) = mensagens(ligado, "saiu")
    s = saida()
    chega(ligado, s, texto="aprovado", contexto=m["wamid"])
    assert [t for _k, _p, t, _o in s.enviadas] == [pendencias.SO_AVISO_APROVACAO]
