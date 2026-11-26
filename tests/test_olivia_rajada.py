"""#1929: a OlivIA espera a rajada, nao repete o botao e nao conversa com link solto.
Plano: docs/specs/2026-11-26-olivia-rajada-botao-repetido-e-link-solto-plano.md."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import olivia as O
from backend import recepcionista as R
from backend.banco import conexao
from tests.avisos_meta import aviso, texto
from tests.saida_falsa import IAFalsa, SaidaFalsa

AGORA = datetime(2026, 11, 17, 13, 0, tzinfo=timezone.utc)   # no passado: a espera nao vale (so a vez cedida)
DE_FORA = "5549988884444"
BSUID = "BR.rajada.1"


@pytest.fixture
def ligada(cfg, tmp_path):
    R._ADIADOS.clear()
    yield replace(cfg, responde=True, olivia_fala=True, campo_pasta=tmp_path / "campo")
    R._ADIADOS.clear()


def chegar(cfg, *mensagens):
    R.gravar(cfg, aviso(list(mensagens), numero=DE_FORA, bsuid=BSUID, nome="Marcos"))


def rodar(cfg, s, ia, agora=AGORA):
    R.processar_pendentes(cfg, s, ia, agora=agora)
    with conexao(cfg) as con:
        erros = con.execute("SELECT erro FROM atendimento.eventos_meta WHERE erro <> ''").fetchall()
    assert not erros, erros


def ler(cfg, sql, *args):
    with conexao(cfg) as con:
        return con.execute(sql, args).fetchall()


def falas(cfg):
    return [r["resumo"] for r in ler(cfg, "SELECT resumo FROM atendimento.enviadas ORDER BY id")
            if r["resumo"].startswith(O.FALA)]


def pendentes(cfg):
    return ler(cfg, "SELECT count(*) AS n FROM atendimento.eventos_meta WHERE processado_em IS NULL")[0]["n"]


# ── a rajada ────────────────────────────────────────────────────────────────

def test_duas_mensagens_na_fila_ganham_uma_resposta_que_le_as_duas(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Boa tarde! Em que posso ajudar?"}, {"texto": "Não devia sair."}]
    chegar(ligada, texto("r1", "Olá!", numero=DE_FORA), texto("r2", "Boa tarde", numero=DE_FORA))
    rodar(ligada, s, ia)
    assert len(falas(ligada)) == 1 and len(ia.chamadas) == 1 and pendentes(ligada) == 0
    visto = ia.chamadas[0]["mensagens"][-1]["content"]
    assert "Olá!" in visto and "Boa tarde" in visto


def test_a_espera_adia_o_texto_e_depois_ele_e_respondido(ligada):
    with conexao(ligada) as con:   # o conftest poe 0; sem o ajuste vale o padrao do codigo
        con.execute("DELETE FROM atendimento.ajustes WHERE chave = %s", (O.AJUSTE_ESPERA,))
        assert O.espera_da_rajada(con) == O.ESPERA_RAJADA
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Bom dia! Em que posso ajudar?"}]
    chegar(ligada, texto("r1", "Bom dia", numero=DE_FORA))
    agora = datetime.now(timezone.utc)
    rodar(ligada, s, ia, agora=agora)
    assert not s.enviadas and pendentes(ligada) == 1 and len(R._ADIADOS) == 1   # adiado: nada saiu, nada gravado
    assert not ler(ligada, "SELECT 1 FROM atendimento.conversas")
    rodar(ligada, s, ia, agora=agora)
    assert not s.enviadas                                                       # ainda na espera: fica fora da fila
    R._ADIADOS.clear()                                                          # a espera venceu
    rodar(ligada, s, ia, agora=agora + timedelta(seconds=O.ESPERA_RAJADA + 5))
    assert len(falas(ligada)) == 1 and pendentes(ligada) == 0


def test_a_espera_em_zero_responde_na_hora(ligada):
    with conexao(ligada) as con:
        con.execute("""INSERT INTO atendimento.ajustes (chave, valor) VALUES (%s, '0'::jsonb)
                       ON CONFLICT (chave) DO UPDATE SET valor = excluded.valor""", (O.AJUSTE_ESPERA,))
        assert O.espera_da_rajada(con) == 0
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Bom dia! Em que posso ajudar?"}]
    chegar(ligada, texto("r1", "Bom dia", numero=DE_FORA))
    rodar(ligada, s, ia, agora=datetime.now(timezone.utc))
    assert len(falas(ligada)) == 1 and not R._ADIADOS


# ── o botao repetido ────────────────────────────────────────────────────────

def test_a_mesma_opcao_sem_toque_nao_sai_de_novo(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    oferta = ("oferecer_opcao_do_menu", {"chave": "financeiro.pagamentos"})
    ia.conversa = [{"texto": "Quem cuida disso é o Financeiro.", "ferramentas": [oferta]}]
    chegar(ligada, texto("b1", "quero saber de um pagamento", numero=DE_FORA))
    rodar(ligada, s, ia)
    assert [t for t, *_ in s.enviadas] == ["texto", "botoes"]
    ia.conversa = [{"ferramentas": [oferta]}, {"texto": "É só tocar em Sim nos botões acima."}]
    chegar(ligada, texto("b2", "boa tarde", numero=DE_FORA))
    rodar(ligada, s, ia)
    assert [t for t, *_ in s.enviadas].count("botoes") == 1
    assert "JÁ estão na tela" in ia.chamadas[-1]["mensagens"][-1]["content"][0]["content"]
    assert s.ultima[2] == "É só tocar em Sim nos botões acima."


# ── o link solto ────────────────────────────────────────────────────────────

def test_link_solto_ganha_a_linha_fixa_uma_vez_sem_modelo(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Não devia sair."}]
    chegar(ligada, texto("l1", "https://cacaushow-giftbasket.com/ycfwyE0Dce5/sDCUj78", numero=DE_FORA))
    rodar(ligada, s, ia)
    assert [(t, c) for t, _, c, _ in s.enviadas] == [("texto", O.TEXTO_LINK_SOLTO)]
    assert not getattr(ia, "chamadas", []) and not ler(ligada, "SELECT 1 FROM atendimento.conversas")
    chegar(ligada, texto("l2", "https://dollarama-gifts.com/ycfwz0eWIiP/XWZo4V5", numero=DE_FORA))
    rodar(ligada, s, ia)
    assert len(s.enviadas) == 1 and not getattr(ia, "chamadas", []) and pendentes(ligada) == 0


def test_link_no_meio_de_uma_conversa_vai_ao_modelo(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Qual semente você procura?"}]
    chegar(ligada, texto("l1", "quero comprar semente", numero=DE_FORA))
    rodar(ligada, s, ia)
    ia.conversa = [{"texto": "Links não são tratados neste canal. Quer falar com alguém da empresa?"}]
    chegar(ligada, texto("l2", "https://exemplo.com.br/pedido/123", numero=DE_FORA))
    rodar(ligada, s, ia)
    assert len(ia.chamadas) == 2 and O.TEXTO_LINK_SOLTO not in [c for _, _, c, _ in s.enviadas]


def test_so_link_e_so_link():
    class E:
        def __init__(self, t):
            self.texto = t
    assert O._so_link(E("https://a.com/x")) and O._so_link(E(" www.a.com/x \nhttps://b.com "))
    assert not O._so_link(E("segue a ordem https://a.com/x")) and not O._so_link(E("bom dia")) and not O._so_link(E(None))


# ── a propaganda de quem ja tem o contato (dono, 26/11/2026) ────────────────

PROPAGANDA = ("Bom dia, tudo bem? Sua colheitadeira precisa estar 100% pronta para o campo! Que tal fazer aquela "
              "revisão preventiva com urgência para evitar surpresas? A LOJA DE PEÇAS distribui direto das maiores "
              "fabricantes do país com preço de atacado e entrega rápida para você não perder tempo! Vantagens de "
              "hoje: peças de alta qualidade, frete grátis e atendimento especializado. Envie a lista de peças.")


def ja_tem_o_contato(cfg):
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo)
                       VALUES ('wamid.antigo', %s, 'texto', 'link: fornecedores.ainda')""", (DE_FORA,))


def test_propaganda_de_quem_ja_tem_o_contato_nao_e_respondida(ligada):
    assert len(PROPAGANDA) >= O.PROPAGANDA_DE
    ja_tem_o_contato(ligada)
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Não devia sair."}]
    chegar(ligada, texto("p1", PROPAGANDA, numero=DE_FORA))
    rodar(ligada, s, ia)
    assert not s.enviadas and not getattr(ia, "chamadas", []) and pendentes(ligada) == 0
    assert not ler(ligada, "SELECT 1 FROM atendimento.conversas")


def test_a_primeira_propaganda_e_a_mensagem_curta_de_quem_ja_tem_o_contato_seguem_ao_modelo(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Ofertas são com o setor de Fornecedores."}]
    chegar(ligada, texto("p1", PROPAGANDA, numero=DE_FORA))
    rodar(ligada, s, ia)
    assert len(ia.chamadas) == 1                      # a primeira vez, como sempre
    with conexao(ligada) as con:                      # a conversa fecha, e ele ja tem o contato
        con.execute("UPDATE atendimento.conversas SET situacao = 'com_link'")
    ja_tem_o_contato(ligada)
    ia.conversa = [{"texto": "Quem cuida de pagamento é o Financeiro."}]
    chegar(ligada, texto("p2", "boa tarde, queria falar de um pagamento", numero=DE_FORA))
    rodar(ligada, s, ia)
    assert len(ia.chamadas) == 2                      # mensagem curta: pode ser gente
