"""#1589: a OlivIA na conversa de quem quer comprar -- as regras da venda, a ferramenta `passar_contato`
(o cartao do representante certo, sem o botao de confirmacao), a nota do perfil, a chave e o vigia.
Spec: docs/specs/2026-11-17-olivia-conversa-de-venda.md; plano, passo 5 (a) a (g)."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import olivia as O
from backend import recepcionista as R
from backend.banco import conexao
from tests.avisos_meta import aviso, texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa

AGORA = datetime(2026, 11, 17, 13, 0, tzinfo=timezone.utc)   # 10:00 em Brasilia, terca
DE_FORA = "5549988883333"
FOLHA = "comercial.produtor.sc"


@pytest.fixture
def venda(cfg, tmp_path):
    """A OlivIA ligada (OLIVIA_FALA) e a chave da venda ligada."""
    c = replace(cfg, responde=True, olivia_fala=True, campo_pasta=tmp_path / "campo")
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'olivia.conduz_venda'")
    return c


@pytest.fixture
def sem_venda(cfg, tmp_path):
    """OLIVIA_FALA ligada, a chave da venda como nasce (false)."""
    return replace(cfg, responde=True, olivia_fala=True, campo_pasta=tmp_path / "campo")


def passo(cfg, s, mensagem, ia=None, agora=AGORA, numero=DE_FORA, bsuid="BR.compra.1", nome="João da Silva"):
    R.gravar(cfg, aviso([mensagem], numero=numero, bsuid=bsuid, nome=nome))
    R.processar_pendentes(cfg, s, ia, agora=agora)
    with conexao(cfg) as con:
        erros = con.execute("SELECT erro FROM atendimento.eventos_meta WHERE erro <> ''").fetchall()
    assert not erros, erros


def ler(cfg, sql, *args):
    with conexao(cfg) as con:
        return con.execute(sql, args).fetchall()


def conversa(cfg):
    return ler(cfg, "SELECT * FROM atendimento.conversas ORDER BY id DESC LIMIT 1")[0]


def resumos(cfg):
    return [r["resumo"] for r in ler(cfg, "SELECT resumo FROM atendimento.enviadas ORDER BY id")]


# ── (a) as regras da venda so com a chave ───────────────────────────────────

def test_a_a_070_nasce_desligada_e_as_regras_so_entram_com_a_chave(sem_venda):
    with conexao(sem_venda) as con:
        assert O.conduz_venda(con) is False
        assert "QUEM QUER COMPRAR" not in O.instrucao(con)
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'olivia.conduz_venda'")
        i = O.instrucao(con)
        assert "QUEM QUER COMPRAR" in i and "passar_contato" in i and "NÃO diga que avisou" in i
        # dono, 18/11/2026 (Divino Green): recepciona e direciona -- "temos", oferece o representante,
        # pergunta so categoria e estado, apresenta quem atende antes do cartao
        assert "Posso indicar o representante comercial da sua região?" in i
        assert "Não pergunte a cidade exata, a quantidade nem a área" in i
        assert "nunca mande o cartão sem essa apresentação" in i
        assert "quanto ela precisa" not in i
        assert "só pergunta DEPOIS de a pessoa dizer que é do Paraná" in i   # dono, 19/11/2026
        # dono, 19/11/2026 (Sivan): quem vem do site quer semente; vaga nao e opcao de abertura
        assert "Venho pelo site" in i and "Nunca ofereça vaga de trabalho como opção" in i


# ── (b) o cartao do representante certo, sem o botao ────────────────────────

def test_b_produtor_de_sc_recebe_o_cartao_sem_o_botao_sim(venda):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Temos aveia sim, João! Quem atende produtor de Santa Catarina já te recebe.",
                    "ferramentas": [("passar_contato", {"chave": FOLHA})]},
                   {"texto": "Não devia sair: o cartão encerra a vez dela."}]
    passo(venda, s, texto("w1", "sou produtor de SC, vocês têm semente de aveia?", numero=DE_FORA), ia)
    with conexao(venda) as con:
        destino = con.execute("""SELECT d.nome, d.whatsapp FROM atendimento.menu m
                                   JOIN atendimento.destinos d ON d.id = m.destino_id WHERE m.chave = %s""",
                              (FOLHA,)).fetchone()
    tipos = [x[0] for x in s.enviadas]
    assert tipos == ["texto", "texto", "contato"]            # a fala dela, o texto do link e o cartao
    assert s.enviadas[0][2].startswith("Temos aveia sim")
    assert s.ultima[2] == destino["nome"] and s.ultima[3] == [destino["whatsapp"]]
    assert "botoes" not in tipos                             # sem o "Posso te passar para ...? [Sim]"
    c = conversa(venda)
    assert c["situacao"] == "com_link" and c["link_em"] is not None and c["pergunta_em"] is not None
    assert c["conduzida_por"] == "olivia" and c["destino_id"] is not None
    assert "link: %s" % FOLHA in resumos(venda)
    assert "passar_contato" in ia.chamadas[0]["ferramentas"]


# ── (c) a chave desligada ───────────────────────────────────────────────────

def test_c_desligada_a_ferramenta_nao_existe_e_os_botoes_sao_os_de_hoje(sem_venda):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("passar_contato", {"chave": FOLHA})]}, {"texto": "Vou te mostrar as opções."}]
    passo(sem_venda, s, texto("w1", "quero comprar semente", numero=DE_FORA), ia)
    assert "passar_contato" not in ia.chamadas[0]["ferramentas"]
    assert "não está disponível" in ia.chamadas[-1]["mensagens"][-1]["content"][0]["content"]
    assert "contato" not in [x[0] for x in s.enviadas] and conversa(sem_venda)["situacao"] != "com_link"
    assert ia.chamadas[0]["extra"] == ""                     # nem a nota do perfil


# ── (d) a lista e fechada ───────────────────────────────────────────────────

def test_d_so_folha_de_destino_do_comercial(venda):
    with conexao(venda) as con:
        f = [f for f in O.ferramentas(con, {"id": 0, "trabalhe": False}) if f["name"] == "passar_contato"][0]
        enum = f["input_schema"]["properties"]["chave"]["enum"]
        quem = con.execute("""SELECT d.nome FROM atendimento.menu m JOIN atendimento.destinos d
                                ON d.id = m.destino_id WHERE m.chave = %s""", (FOLHA,)).fetchone()["nome"]
        assert quem in f["description"]            # ela apresenta quem atende pelo nome (dono, 18/11/2026)
    assert FOLHA in enum and "comercial" not in enum and "fornecedores.ainda" not in enum and "trabalhe" not in enum
    assert all(x.startswith("comercial.") for x in enum)
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("passar_contato", {"chave": "fornecedores.ainda"})]},
                   {"texto": "De que estado você é?"}]
    passo(venda, s, texto("w1", "quero comprar semente", numero=DE_FORA), ia)
    assert "contato" not in [x[0] for x in s.enviadas]
    assert "não existe" in ia.chamadas[-1]["mensagens"][-1]["content"][0]["content"]
    assert s.ultima[2] == "De que estado você é?"


# ── (e) a nota do perfil ────────────────────────────────────────────────────

def test_e_o_nome_do_perfil_chega_como_nota_e_nao_sai_para_ninguem(venda):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Temos sim. Com quem eu falo?"}]
    passo(venda, s, texto("w1", "tem aveia?", numero=DE_FORA), ia, nome="🌾🚜")
    assert "NOME NO PERFIL DO WHATSAPP" in ia.chamadas[0]["extra"] and "🌾🚜" in ia.chamadas[0]["extra"]
    assert "NOME NO PERFIL" not in ia.chamadas[0]["sistema"]
    assert not [r for r in resumos(venda) if "NOME NO PERFIL" in r]
    assert not [r for r in resumos(venda) if r.startswith(O.FALA_TRAVOU)]   # a nota nao e a marca de "travou"


# ── (f) fora da conversa de vaga ────────────────────────────────────────────

def test_f_na_conversa_de_vaga_o_contato_do_comercial_nao_e_oferecido(venda):
    with conexao(venda) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'olivia.conduz_vaga'")
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Temos duas vagas. Qual te interessa?"}]
    passo(venda, s, toque("w1", "menu:trabalhe", numero=DE_FORA), ia)
    assert conversa(venda)["trabalhe"]
    ia.conversa = [{"texto": "Você tem currículo?"}]
    passo(venda, s, texto("w2", "empilhadeira", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=1))
    assert "passar_contato" not in ia.chamadas[-1]["ferramentas"]


# ── (g) o vigia ─────────────────────────────────────────────────────────────

def test_g_conversa_de_venda_com_o_cartao_entregue_termina_bem(venda):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Temos sim!", "ferramentas": [("passar_contato", {"chave": FOLHA})]}]
    passo(venda, s, texto("w1", "sou produtor de SC, tem aveia?", numero=DE_FORA), ia)
    with conexao(venda) as con:
        O.fechar_dia(con, AGORA + timedelta(hours=11))
    assert conversa(venda)["saida"] == "bem"


def test_saude_diz_a_chave_da_venda(venda):
    with conexao(venda) as con:
        assert O.conduz_venda(con) is True
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'olivia.conduz_venda'")
        assert O.conduz_venda(con) is False
