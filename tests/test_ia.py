"""D3 do plano #950: a IA so devolve uma chave da lista; qualquer outra coisa vira None (o menu).
A Anthropic e falsa: nenhum pedido sai da maquina e nada e cobrado."""
import json
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


# ── #1027 (15/10/2026): a direcao do pedido ──────────────────────────────────────────────────
# A Yasmin, da World Rafia, escreveu "posso te fazer uma cotacao para apresentar nossos precos" e
# foi classificada como `comercial` -- o caminho de quem quer COMPRAR. A causa era o cadastro: a
# unica opcao cujo texto continha "cotar" era `comercial` ("Cotar sementes").

def test_a_instrucao_diz_que_a_direcao_do_pedido_importa():
    i = IAmod.INSTRUCOES.lower()
    assert "direção do pedido" in i and "fornecedores, não comercial" in i
    assert "cotação" in i          # a palavra que aparece nos dois lados, dita como tal


def test_as_opcoes_de_fornecedores_dizem_vender_e_as_de_comercial_dizem_comprar(cfg):
    """O INSUMO da IA, que e o que esta etapa muda. Sem estas palavras na lista, nenhuma instrucao
    salva: a IA so ve `chave: caminho (descricao)`."""
    with conexao(cfg) as con:
        por_chave = {o["chave"]: o for o in folhas_e_menus(con)}
    lista = IAmod._lista(list(por_chave.values())).lower()
    assert "vender à renascer" in lista or "vender para a renascer" in lista
    assert "comprar" in lista
    # e a armadilha saiu: "cotar sementes" nao e mais a unica mencao a cotacao
    assert "cotar sementes" not in lista
    assert "cotação de venda" in lista


def test_nenhuma_descricao_passa_do_limite_da_coluna(cfg):
    """72 e o CHECK `menu_descricao`, e tambem o que a linha de lista do WhatsApp suporta."""
    with conexao(cfg) as con:
        ops = folhas_e_menus(con)
    longas = [(o["chave"], len(o["descricao"])) for o in ops if len(o["descricao"] or "") > 72]
    assert longas == []


# ── #1048: o enum e a prosa do campo vem do CADASTRO ─────────────────────────────────────────

def test_a_prosa_do_campo_e_montada_do_cadastro():
    """Antes, acrescentar uma categoria exigia editar este texto, o enum, e mais quatro lugares --
    e esquecer um deles nao dava erro: dava silencio."""
    lista = [{"chave": "estoque", "rotulo": "Estoque / armazém",
              "descricao": "semente guardada, armazém, pálete"},
             {"chave": "colheita", "rotulo": "Colheita", "descricao": "colheitadeira"}]
    prosa = IAmod.IA.instrucoes_campo(lista)
    assert "estoque = semente guardada, armazém, pálete" in prosa
    assert "colheita = colheitadeira" in prosa
    assert "beneficiamento" not in prosa      # o que nao esta no cadastro nao entra na prosa


def test_o_enum_do_campo_tem_as_chaves_do_cadastro():
    """O enum CONTINUA FECHADO: muda de onde a lista vem, nao que exista uma."""
    c = ClienteFalso(resposta(json.dumps({"bastidor": "estoque", "produto": "nenhum", "fase": "nenhuma"})))
    lista = [{"chave": "estoque", "rotulo": "Estoque", "descricao": "armazém"},
             {"chave": "manejo", "rotulo": "Manejo", "descricao": "rolo-faca"}]
    r = IAmod.IA(cliente=c).ler_campo("foto do armazém", ["CENTEIO IPR 89"], lista)
    assert r["bastidor"] == "estoque"
    enum = c.pedidos[-1]["output_config"]["format"]["schema"]["properties"]["bastidor"]["enum"]
    assert enum == ["estoque", "manejo", "nenhum"]


def test_sem_cadastro_o_campo_cai_nas_cinco_originais():
    c = ClienteFalso(resposta(json.dumps({"bastidor": "colheita", "produto": "nenhum", "fase": "nenhuma"})))
    IAmod.IA(cliente=c).ler_campo("colheita", [])
    enum = c.pedidos[-1]["output_config"]["format"]["schema"]["properties"]["bastidor"]["enum"]
    assert enum == ["campo-de-sementes", "colheita", "beneficiamento", "controle-de-qualidade",
                    "entrega", "nenhum"]


# ── #1098: a pre-triagem do curriculo ────────────────────────────────────────

VAGA = {"titulo": "Vaga Comercial", "requisitos": ["Agronomia com pós", "2 anos com sementes",
                                                    "Vivência comercial", "Morar em Maravilha"]}


def test_triar_manda_o_pdf_e_o_esquema_e_le_um_por_requisito():
    c = ClienteFalso(resposta(json.dumps({"requisitos": [
        {"situacao": "consta", "fonte": "Agronomia UFSC"}, {"situacao": "nao_consta", "fonte": ""},
        {"situacao": "consta", "fonte": "revenda"}, {"situacao": "nao", "fonte": "Cascavel, PR"}],
        "resumo": "perfil comercial", "legivel": True})))
    t = IAmod.IA(cliente=c).triar(b"%PDF-1.4", VAGA)
    assert [r["situacao"] for r in t["requisitos"]] == ["consta", "nao_consta", "consta", "nao"]
    assert t["legivel"] is True and t["resumo"] == "perfil comercial"
    p = c.pedidos[0]
    assert p["model"] == "claude-haiku-5-5" and "tools" not in p
    doc = p["messages"][0]["content"][0]
    assert doc["type"] == "document" and doc["source"]["media_type"] == "application/pdf"
    assert "AUSÊNCIA NUNCA É" in p["system"] and "religião" in p["system"] and "Morar em Maravilha" in p["system"]


def test_triar_completa_o_que_faltou_com_nao_consta_e_nunca_com_nao():
    c = ClienteFalso(resposta(json.dumps({"requisitos": [{"situacao": "talvez", "fonte": "x\ny"}],
                                          "resumo": "a\nb", "legivel": True})))
    t = IAmod.IA(cliente=c).triar(b"%PDF", VAGA)
    assert [r["situacao"] for r in t["requisitos"]] == ["nao_consta"] * 4
    assert "\n" not in t["requisitos"][0]["fonte"] and "\n" not in t["resumo"]   # variavel de uma linha


@pytest.mark.parametrize("r", [resposta("nao e json"), resposta("{}", stop="refusal"), None])
def test_triar_sem_resposta_boa_devolve_none(r):
    c = ClienteFalso(r, erro=TimeoutError("demorou") if r is None else None)
    assert IAmod.IA(cliente=c).triar(b"%PDF", VAGA) is None


def test_triar_sem_pdf_nem_pergunta():
    c = ClienteFalso(resposta("{}"))
    assert IAmod.IA(cliente=c).triar(b"", VAGA) is None and not c.pedidos


# ── #1090 etapa 3: a leitura do registro de visita ─────────────────────────────────────────────

def test_ler_visita_preenche_so_de_dentro_das_listas():
    from datetime import date
    motivos = [{"id": 3, "nome": "Preço"}]
    c = ClienteFalso(resposta(json.dumps({
        "meio": "ligacao", "quando": "2026-10-23", "ofereceu": "nao", "resposta": "interesse", "motivo": "nenhum",
        "interesse": "+Palha no inverno", "retomar": "2026-11-05", "pedido": "", "anotacao": "plantando o verão"})))
    r = IAmod.IA(cliente=c).ler_visita("liguei pro Márcio...", {"nome": "COOPERPASSO", "campanha": None},
                                       motivos, date(2026, 10, 23))
    assert r == {"meio": "ligacao", "quando": "2026-10-23", "ofereceu": False, "resposta": "interesse",
                 "motivo_id": None, "interesse_texto": "+Palha no inverno", "retomar_em": "2026-11-05",
                 "pedido_numero": "", "anotacao": "plantando o verão"}
    p = c.pedidos[0]
    props = p["output_config"]["format"]["schema"]["properties"]
    assert props["motivo"]["enum"] == ["Preço", "nenhum"] and "nenhum" in props["meio"]["enum"]
    assert "tools" not in p and "<texto>" in p["messages"][0]["content"] and "2026-10-23" in p["system"]
    assert "cortesia" in p["system"]


def test_ler_visita_com_campanha_motivo_pelo_nome_e_falha_vira_none():
    from datetime import date
    motivos = [{"id": 3, "nome": "Preço"}]
    c = ClienteFalso(resposta(json.dumps({
        "meio": "visita", "quando": "", "ofereceu": "sim", "resposta": "recusou", "motivo": "Preço",
        "interesse": "", "retomar": "", "pedido": "", "anotacao": ""})))
    ficha = {"nome": "X", "campanha": {"nome": "Inverno"}}
    r = IAmod.IA(cliente=c).ler_visita("ofereci, achou caro", ficha, motivos, date(2026, 10, 23))
    assert r["ofereceu"] is True and r["motivo_id"] == 3 and "Inverno" in c.pedidos[0]["system"]
    assert IAmod.IA(cliente=ClienteFalso(erro=TimeoutError())).ler_visita("x", ficha, motivos, date(2026, 10, 23)) is None
    assert IAmod.IA(cliente=ClienteFalso(resposta("nao e json"))).ler_visita("x", ficha, motivos, date(2026, 10, 23)) is None
