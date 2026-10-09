"""D3 do plano #950: a IA so devolve uma chave da lista; qualquer outra coisa vira None (o menu).
A Anthropic e falsa: nenhum pedido sai da maquina e nada e cobrado."""
from types import SimpleNamespace

import pytest

from backend import ia as IAmod
from backend.banco import conexao
from backend.motor import folhas_e_menus

OPCOES = [{"chave": "fretes", "rotulo": "🚚 Fretes", "descricao": "Cotações de frete", "caminho": ["🚚 Fretes"]},
          {"chave": "financeiro.boleto", "rotulo": "🧾 2ª via do Boleto", "descricao": "",
           "caminho": ["🧾 Financeiro", "🧾 2ª via do Boleto"]}]


class ClienteFalso:
    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.pedidos = resposta, erro, []
        self.messages = self

    def create(self, **kw):
        self.pedidos.append(kw)
        if self.erro:
            raise self.erro
        return self.resposta


def resposta(texto, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=texto)])


def test_devolve_a_chave_e_o_pedido_e_o_combinado():
    c = ClienteFalso(resposta('{"chave": "financeiro.boleto"}'))
    assert IAmod.IA(cliente=c).classificar("segunda via do boleto por favor", OPCOES) == "financeiro.boleto"
    p = c.pedidos[0]
    assert p["model"] == "claude-haiku-5-5" and p["thinking"] == {"type": "disabled"}
    assert p["output_config"]["effort"] == "low"
    assert p["output_config"]["format"]["schema"]["properties"]["chave"]["enum"] == ["fretes", "financeiro.boleto", "nenhuma"]
    assert "tools" not in p and "<mensagem>" in p["messages"][0]["content"]


@pytest.mark.parametrize("r", [
    resposta('{"chave": "nenhuma"}'),
    resposta('{"chave": "link.do.golpe"}'),
    resposta("isto nao e json"),
    resposta('{"chave": "fretes"}', stop="refusal"),
    resposta('{"chave": "fretes"}', stop="max_tokens"),
    SimpleNamespace(stop_reason="end_turn", content=[]),
])
def test_qualquer_coisa_fora_da_lista_vira_none(r):
    assert IAmod.IA(cliente=ClienteFalso(r)).classificar("oi", OPCOES) is None


def test_erro_ou_tempo_esgotado_vira_none():
    assert IAmod.IA(cliente=ClienteFalso(erro=TimeoutError())).classificar("oi", OPCOES) is None


def test_texto_vazio_nem_pergunta():
    c = ClienteFalso(resposta('{"chave": "fretes"}'))
    assert IAmod.IA(cliente=c).classificar("   ", OPCOES) is None and c.pedidos == []


def test_repr_sem_chave():
    assert "sk-" not in repr(IAmod.IA(cliente=ClienteFalso()))


def test_as_opcoes_do_menu_de_hoje_cabem_na_lista(cfg):
    with conexao(cfg) as con:
        ops = folhas_e_menus(con)
    chaves = {o["chave"] for o in ops}
    assert {"fretes", "qualidade", "financeiro.boleto", "comercial.produtor.pr.cascavel"} <= chaves
    assert "raiz" not in chaves and "encerrar" not in chaves
