"""#970: o canal de campo com o ATENDENTE DE OBJETIVO (decisao 14 do dono, 12/10/2026). A foto ou o
video de equipe/representante reconhecidos, com a chave ligada, e baixado e guardado; a OlivIA
responde "Recebi", le a frase com a IA de texto e pergunta SO o que falta (bastidor, produto, fase,
data), no maximo tres perguntas de classificacao; a foto entra no catalogo na hora e a classificacao
e aplicada quando fecha; quem nao responde e lembrado uma vez (2 h) e depois o grupo fecha com o que
tem. O marketing busca pelas rotas /campo/* com a chave do pedido; os avisos so dentro das 24 h."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import agenda, campo, recepcionista as R
from backend.banco import conexao
from backend.main import criar_app
from tests.avisos_meta import aviso, texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa

EQUIPE = "5549991505565"      # Maicon, equipe + representante (agenda de teste)
CLIENTE = "5549999990000"     # Agro Real, cliente
AGORA = datetime(2026, 10, 12, 13, 0, tzinfo=timezone.utc)   # 10:00 em Sao Paulo, segunda
MIN = timedelta(minutes=1)
H = timedelta(hours=1)
PRODUTOS = ["CENTEIO IPR 89", "AVEIA PRETA IAPAR61", "AVEIA PRETA EMBRAPA 139", "TREMOCO BRANCO"]
LINHAS = [
    {"numero": CLIENTE, "codigo": 5475, "nome": "Agro Real Insumos", "papeis": ["cliente"], "contato_setor": "", "contato_nome": ""},
    {"numero": EQUIPE, "codigo": 12, "nome": "Maicon Gregory", "papeis": ["equipe", "representante"], "contato_setor": "", "contato_nome": ""},
]


def foto(wamid, legenda="", numero=EQUIPE, tipo="image"):
    m = {"from": numero, "id": wamid, "timestamp": "1760040000", "type": tipo,
         tipo: {"id": "midia-" + wamid, "mime_type": "image/jpeg" if tipo == "image" else "video/mp4", "sha256": "x"}}
    if legenda:
        m[tipo]["caption"] = legenda
    return m


@pytest.fixture
def canal(cfg, tmp_path):
    c = replace(cfg, responde=True, campo_pasta=tmp_path / "campo", chave_pedido="chave-de-teste",
                erp_segredo="segredo-de-teste")   # a agenda so carrega com a leitura do ERP ligada
    agenda.atualizar(c, buscar=lambda x: LINHAS, agora=AGORA)
    with conexao(c) as con:
        campo.guardar_produtos(con, PRODUTOS)
    return c


def ligar(cfg, valor=True):
    with conexao(cfg) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = 'campo.ligado'", ("true" if valor else "false",))


def passo(cfg, s, mensagem, agora=AGORA, numero=EQUIPE, bsuid="BR.equipe", ia=None):
    R.gravar(cfg, aviso([mensagem], numero=numero, bsuid=bsuid))
    R.processar_pendentes(cfg, s, ia, agora=agora, campo=campo.Campo(cfg.campo_pasta, ia))


def minuto(cfg, s, agora, ia=None):
    R.rotina_do_minuto(cfg, s, agora=agora, ia=ia)


def material(cfg):
    with conexao(cfg) as con:
        return [dict(r) for r in con.execute("SELECT * FROM atendimento.material_de_campo ORDER BY id").fetchall()]


def palpite(cfg, item_id, bastidor, produto, agora, fase=None):
    with conexao(cfg) as con:
        campo.palpite(con, item_id, bastidor, produto, agora, fase)


def conversas(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"]


def textos(s):
    return [x[2] for x in s.enviadas]


def test_com_a_chave_desligada_a_foto_da_equipe_segue_como_hoje(canal):
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "Colheita do centeio"))
    assert material(canal) == []
    assert [(x[0], x[2]) for x in s.enviadas] == [("texto", R.motor.NAO_ENTENDO)]   # sem canal: a linha curta


def test_a_frase_lida_pela_ia_fecha_tudo_e_so_a_data_e_perguntada(canal):
    """Frase completa ("colheita do centeio IPR 89 no campo do Jair"): a IA le bastidor e produto; o
    atendente pergunta so a data; a foto ja esta no catalogo (pendente na hora) e a classificacao
    chega por `classificados` quando fecha."""
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "colheita", "produto": "CENTEIO IPR 89", "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "Colheita do centeio IPR 89 no campo do Jair"), ia=ia)
    m = material(canal)[0]
    assert textos(s) == [campo.RECEBI] and ia.frases == ["Colheita do centeio IPR 89 no campo do Jair"]
    assert (m["classe_bastidor"], m["classe_produto"], m["classe_fase"], m["lida_em"] is not None) == ("colheita", "CENTEIO IPR 89", None, True)
    assert conversas(canal) == 0
    with conexao(canal) as con:
        assert campo.pendentes(con, AGORA) == []   # entra no catalogo quando a conversa fecha (decisao 15)
        assert campo.classificados(con) == []
    minuto(canal, s, AGORA + MIN, ia=ia)   # sem palpite e antes de 2 min: espera
    assert len(s.enviadas) == 1
    minuto(canal, s, AGORA + 3 * MIN, ia=ia)
    assert [(x[0], x[2]) for x in s.enviadas[1:]] == [("botoes", campo.PERGUNTA_DATA)]   # bastidor e produto ja estao
    assert material(canal)[0]["pergunta_n"] == 0   # a data nao conta no limite
    # o texto que nao e data, com a data em aberto, complementa a legenda em silencio (14:34 de 12/10)
    passo(canal, s, texto("wamid.t0", "Foto da safra 2025", numero=EQUIPE), agora=AGORA + 4 * MIN, ia=ia)
    assert len(s.enviadas) == 2 and material(canal)[0]["legenda"].endswith(" · Foto da safra 2025")
    assert material(canal)[0]["pergunta_pendente"] == "data" and conversas(canal) == 0
    passo(canal, s, toque("wamid.t1", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 4 * MIN, ia=ia)
    m = material(canal)[0]
    assert m["data_dita"] == date(2026, 10, 12) and m["fechado_em"] is not None and s.ultima[2] == campo.ANOTADO
    with conexao(canal) as con:
        p = campo.pendentes(con, AGORA + 4 * MIN)
        assert [x["id"] for x in p] == [m["id"]] and p[0]["fechado"] is True   # agora sim
        assert p[0]["classe"] == {"bastidor": "colheita", "produto": "CENTEIO IPR 89", "fase": None}
        campo.buscado(con, m["id"], "lote", 0, AGORA + 5 * MIN)
        assert campo.classificados(con) == []          # sem ATV ainda, nada a aplicar
        campo.catalogado(con, m["id"], "ATV-0700", AGORA + 2 * MIN)
        cl = campo.classificados(con)
        assert len(cl) == 1 and cl[0]["classe"]["bastidor"] == "colheita" and cl[0]["atv"] == "ATV-0700"
        campo.classe_aplicada(con, m["id"], AGORA + 5 * MIN)
        assert campo.classificados(con) == []


def test_sem_frase_pergunta_o_que_falta_em_texto_e_a_ia_encaixa(canal):
    """Sem frase e sem palpite: pergunta o que e (texto); a resposta e lida; depois o produto (texto,
    casado com a lista) e a fase (texto, lido pela IA). As listas sao do agente (decisao 15)."""
    ligar(canal)
    ia = IAFalsa(campo=[{"bastidor": "campo-de-sementes", "produto": None, "fase": None},
                        {"bastidor": None, "produto": None, "fase": "flor"}])
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"), ia=ia)
    minuto(canal, s, AGORA + 3 * MIN, ia=ia)
    assert textos(s) == [campo.RECEBI, campo.PERGUNTA_LEGENDA] and material(canal)[0]["pergunta_n"] == 1
    passo(canal, s, texto("wamid.t1", "vistoria no campo do Jair", numero=EQUIPE), agora=AGORA + 4 * MIN, ia=ia)
    m = material(canal)[0]
    assert m["classe_bastidor"] == "campo-de-sementes" and m["legenda"] == "vistoria no campo do Jair"
    assert s.ultima[2] == campo.PERGUNTA_PRODUTO and m["pergunta_n"] == 2
    passo(canal, s, texto("wamid.t2", "aveia preta iapar61", numero=EQUIPE), agora=AGORA + 5 * MIN, ia=ia)
    m = material(canal)[0]
    assert m["classe_produto"] == "AVEIA PRETA IAPAR61" and s.ultima[0] == "texto" and s.ultima[2] == campo.PERGUNTA_FASE
    assert m["pergunta_n"] == 3 and all(x[0] != "lista" for x in s.enviadas)   # nenhuma lista para a pessoa
    passo(canal, s, texto("wamid.t3", "tá florindo", numero=EQUIPE), agora=AGORA + 6 * MIN, ia=ia)
    m = material(canal)[0]
    assert m["classe_fase"] == "flor" and s.ultima[2] == campo.PERGUNTA_DATA   # a data nao conta no limite
    assert ia.frases == ["vistoria no campo do Jair", "tá florindo"]
    passo(canal, s, toque("wamid.t4", "campo:hoje:outra", numero=EQUIPE), agora=AGORA + 7 * MIN, ia=ia)
    assert s.ultima[2] == campo.PERGUNTA_QUAL_DIA
    passo(canal, s, texto("wamid.t5", "09/10", numero=EQUIPE), agora=AGORA + 8 * MIN, ia=ia)
    m = material(canal)[0]
    assert m["data_dita"] == date(2026, 10, 9) and m["fechado_em"] is not None and m["desistiu_em"] is None
    assert sorted(m["perguntas_feitas"]) == ["data", "fase", "legenda", "produto", "qual_dia"]


def test_o_limite_de_tres_perguntas_deixa_o_resto_a_classificar(canal):
    """A resposta que a IA nao encaixa fica na legenda e a pergunta nao se repete; no limite de tres,
    so a data sai e o grupo fecha com o que tem."""
    ligar(canal)
    ia = IAFalsa(campo=[None, {"bastidor": "colheita", "produto": None, "fase": None}])
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"), ia=ia)
    minuto(canal, s, AGORA + 3 * MIN, ia=ia)                       # 1: o que e
    passo(canal, s, texto("wamid.t1", "coisa do dia", numero=EQUIPE), agora=AGORA + 4 * MIN, ia=ia)
    assert s.ultima[0] == "texto" and s.ultima[2] == campo.PERGUNTA_BASTIDOR   # 2: nao encaixou: pergunta aberta
    passo(canal, s, texto("wamid.t2", "colhendo no Jair", numero=EQUIPE), agora=AGORA + 5 * MIN, ia=ia)
    assert s.ultima[2] == campo.PERGUNTA_PRODUTO                   # 3: o produto
    passo(canal, s, texto("wamid.t3", "nao sei", numero=EQUIPE), agora=AGORA + 6 * MIN, ia=ia)
    assert campo.NAO_ACHEI_PRODUTO in textos(s) and s.ultima[2] == campo.PERGUNTA_DATA   # estourou: so a data
    m = material(canal)[0]
    assert (m["classe_bastidor"], m["classe_produto"], m["pergunta_n"]) == ("colheita", None, 3)
    assert m["legenda"] == "coisa do dia · colhendo no Jair"


def test_o_que_a_ia_nao_encaixa_fica_na_legenda_e_a_pergunta_nao_se_repete(canal):
    """O manejo do cliente, que nao esta na lista: duas respostas sem encaixe, nenhuma pergunta
    repetida, e o grupo fecha a classificar com o texto como legenda (para o dono)."""
    ligar(canal)
    ia = IAFalsa(campo=None)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"), ia=ia)
    minuto(canal, s, AGORA + 3 * MIN, ia=ia)
    passo(canal, s, texto("wamid.t1", "cliente fazendo o manejo do azevem", numero=EQUIPE), agora=AGORA + 4 * MIN, ia=ia)
    assert s.ultima[2] == campo.PERGUNTA_BASTIDOR
    passo(canal, s, texto("wamid.t2", "e a dessecacao antes do plantio", numero=EQUIPE), agora=AGORA + 5 * MIN, ia=ia)
    assert s.ultima[2] == campo.PERGUNTA_DATA   # nao repete; nao ha produto a perguntar sem bastidor
    passo(canal, s, toque("wamid.t3", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 6 * MIN, ia=ia)
    m = material(canal)[0]
    assert m["fechado_em"] is not None and m["classe_bastidor"] is None and m["pergunta_n"] == 2
    assert m["legenda"] == "cliente fazendo o manejo do azevem · e a dessecacao antes do plantio"
    with conexao(canal) as con:
        assert campo.pendentes(con, AGORA + 6 * MIN)[0]["falta"] == ["bastidor"]


def test_o_palpite_de_imagem_molda_a_pergunta_do_bastidor(canal):
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "beneficiamento", "produto": None, "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"), ia=ia)
    palpite(canal, material(canal)[0]["id"], "entrega", None, AGORA + MIN)
    minuto(canal, s, AGORA + MIN, ia=ia)   # com o palpite nao espera os 2 min
    assert s.ultima[0] == "botoes" and s.ultima[2] == "Parece entrega / carregamento. É isso?"
    assert s.ultima[3] == [("campo:bastidor:entrega", "Sim"), ("campo:bastidor:outra", "Outra coisa")]
    passo(canal, s, toque("wamid.t1", "campo:bastidor:outra", numero=EQUIPE), agora=AGORA + 2 * MIN, ia=ia)
    assert s.ultima[0] == "texto" and s.ultima[2] == campo.PERGUNTA_LEGENDA   # o palpite errou: pergunta aberta
    passo(canal, s, texto("wamid.t2", "beneficiamento na UBS", numero=EQUIPE), agora=AGORA + 3 * MIN, ia=ia)
    m = material(canal)[0]
    assert m["classe_bastidor"] == "beneficiamento" and s.ultima[2] == campo.PERGUNTA_DATA   # institucional: sem produto
    assert m["legenda"] == "beneficiamento na UBS" and m["pergunta_n"] == 2


def test_uma_conversa_aberta_por_pessoa_a_foto_de_depois_entra_nela_e_a_lembranca_e_uma_so(canal):
    """12/10/2026, 14:25: cinco lembrancas de uma vez, uma por grupo de 10 min. Agora a foto que chega
    com pergunta pendente entra na mesma conversa, mesmo 20 min depois, e a lembranca e uma so."""
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "entrega", "produto": None, "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"), ia=ia)
    minuto(canal, s, AGORA + 3 * MIN, ia=ia)
    assert textos(s) == [campo.RECEBI, campo.PERGUNTA_LEGENDA]
    passo(canal, s, foto("wamid.f2"), agora=AGORA + 20 * MIN, ia=ia)    # 20 min depois, sem resposta
    passo(canal, s, foto("wamid.f3"), agora=AGORA + 50 * MIN, ia=ia)
    assert len(s.enviadas) == 2   # nem "Recebi" de novo, nem pergunta nova: a conversa e a mesma
    assert len({m["grupo_id"] for m in material(canal)}) == 1
    minuto(canal, s, AGORA + 2 * H + 4 * MIN, ia=ia)
    assert textos(s)[2:] == [campo.RETOMANDO + campo.PERGUNTA_LEGENDA]   # uma lembranca, nao tres
    minuto(canal, s, AGORA + 2 * H + 5 * MIN, ia=ia)
    assert len(s.enviadas) == 3
    passo(canal, s, texto("wamid.t1", "carregamento pra Agro Real", numero=EQUIPE), agora=AGORA + 2 * H + 6 * MIN, ia=ia)
    assert s.ultima[2] == campo.PERGUNTA_DATA and all(m["classe_bastidor"] == "entrega" for m in material(canal))
    passo(canal, s, toque("wamid.t2", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 2 * H + 7 * MIN, ia=ia)
    assert all(m["fechado_em"] is not None for m in material(canal))
    with conexao(canal) as con:
        assert len(campo.pendentes(con, AGORA + 3 * H)) == 3   # as tres entram juntas, classificadas


def test_quem_nao_responde_e_lembrado_uma_vez_e_depois_o_grupo_fecha_com_o_que_tem(canal):
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "entrega", "produto": None, "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "carregamento pra Agro Real"), ia=ia)
    minuto(canal, s, AGORA + 3 * MIN, ia=ia)
    assert s.ultima[2] == campo.PERGUNTA_DATA
    minuto(canal, s, AGORA + H, ia=ia)
    assert len(s.enviadas) == 2   # ainda nao e hora de lembrar
    minuto(canal, s, AGORA + 2 * H + 4 * MIN, ia=ia)
    assert s.ultima[2] == campo.RETOMANDO + campo.PERGUNTA_DATA and material(canal)[0]["retomada"] is True
    minuto(canal, s, AGORA + 3 * H, ia=ia)
    assert len(s.enviadas) == 3   # uma retomada so
    minuto(canal, s, AGORA + 4 * H + 5 * MIN, ia=ia)
    m = material(canal)[0]
    assert m["desistiu_em"] is not None and m["fechado_em"] is not None and len(s.enviadas) == 3
    assert m["data_dita"] == date(2026, 10, 12) and m["data_presumida"] is True and m["classe_bastidor"] == "entrega"
    with conexao(canal) as con:
        campo.catalogado(con, m["id"], "ATV-0701", AGORA + 5 * H)
        assert campo.classificados(con)[0]["desistiu"] is True


def test_varias_fotos_sao_um_grupo_e_a_frase_antes_da_foto_e_a_legenda(canal):
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "beneficiamento", "produto": None, "fase": None})
    s = SaidaFalsa()
    passo(canal, s, texto("wamid.t0", "Beneficiamento na UBS", numero=EQUIPE), ia=ia)   # a frase antes
    assert textos(s) == [campo.ANOTADO_FRASE] and conversas(canal) == 0
    passo(canal, s, foto("wamid.f1"), agora=AGORA + MIN, ia=ia)
    passo(canal, s, foto("wamid.f2"), agora=AGORA + 2 * MIN, ia=ia)
    passo(canal, s, foto("wamid.f3", tipo="video"), agora=AGORA + 3 * MIN, ia=ia)
    assert textos(s) == [campo.ANOTADO_FRASE, campo.RECEBI]   # um Recebi por grupo
    for m in material(canal):
        assert m["legenda"] == "Beneficiamento na UBS" and m["classe_bastidor"] == "beneficiamento"
    minuto(canal, s, AGORA + 4 * MIN, ia=ia)
    minuto(canal, s, AGORA + 6 * MIN, ia=ia)
    assert textos(s)[2:] == [campo.PERGUNTA_DATA]   # uma rodada, uma pergunta
    passo(canal, s, toque("wamid.t1", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 7 * MIN, ia=ia)
    for m in material(canal):
        assert m["data_dita"] == date(2026, 10, 12) and m["fechado_em"] is not None
    # uma foto 20 minutos depois e outro grupo: nova conversa
    passo(canal, s, foto("wamid.f4", "Carga saindo"), agora=AGORA + 25 * MIN, ia=ia)
    assert s.ultima[2] == campo.RECEBI and material(canal)[-1]["fechado_em"] is None


def test_colaborador_so_recebe_o_menu_se_pedir(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, texto("wamid.t0", "preciso falar com o comercial", numero=EQUIPE))
    assert textos(s) == [campo.ANOTADO_FRASE] and conversas(canal) == 0
    passo(canal, s, texto("wamid.t1", "outra frase", numero=EQUIPE), agora=AGORA + 30 * MIN)
    assert len(s.enviadas) == 1   # a segunda, em silencio
    passo(canal, s, texto("wamid.t2", "menu", numero=EQUIPE), agora=AGORA + 31 * MIN)
    assert conversas(canal) == 1
    ligar(canal, False)
    s2 = SaidaFalsa()
    passo(canal, s2, texto("wamid.t3", "qualquer coisa", numero=EQUIPE), agora=AGORA + 40 * MIN)
    assert s2.enviadas and s2.enviadas[-1][2] != campo.ANOTADO_FRASE   # canal desligado: como qualquer um


def test_cliente_com_foto_recebe_a_linha_curta_e_interno_com_figurinha_fica_em_silencio(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.c1", "oi", numero=CLIENTE), numero=CLIENTE, bsuid="BR.cliente")
    assert material(canal) == [] and s.ultima[2] == R.motor.NAO_ENTENDO and conversas(canal) == 0
    figurinha = {"from": EQUIPE, "id": "wamid.s1", "timestamp": "1760040000", "type": "sticker",
                 "sticker": {"id": "stk-1", "mime_type": "image/webp"}}
    passo(canal, s, figurinha)
    assert len(s.enviadas) == 1


def test_quando_a_meta_nao_entrega_a_midia_a_linha_diz_o_erro_e_nada_quebra(canal):
    ligar(canal)
    s = SaidaFalsa()
    s.baixar_falha = True
    passo(canal, s, foto("wamid.f1", "x"))
    m = material(canal)[0]
    assert m["arquivo"] is None and "nao entregou" in m["erro"]
    with conexao(canal) as con:
        assert campo.pendentes(con, AGORA + H) == [] and campo.novos(con) == []   # sem arquivo, nao se oferece


def test_casar_produto_e_ler_data():
    assert campo.casar_produto("aveia preta iapar61", PRODUTOS) == "AVEIA PRETA IAPAR61"
    assert campo.casar_produto("é a aveia preta IAPAR 61 do Jair", PRODUTOS) is None   # "IAPAR 61" com espaco nao casa: a IA le
    assert campo.casar_produto("centeio ipr 89", PRODUTOS) == "CENTEIO IPR 89"
    assert campo.casar_produto("tremoço branco", PRODUTOS) == "TREMOCO BRANCO"
    assert campo.casar_produto("soja", PRODUTOS) is None and campo.casar_produto("", PRODUTOS) is None
    assert campo.ler_data("hoje", AGORA) == date(2026, 10, 12)
    assert campo.ler_data("ontem", AGORA) == date(2026, 10, 11)
    assert campo.ler_data("09/10", AGORA) == date(2026, 10, 9)
    assert campo.ler_data("foi dia 9/10/2026", AGORA) == date(2026, 10, 9)
    assert campo.ler_data("2026-10-08", AGORA) == date(2026, 10, 8)
    assert campo.ler_data("30/12", AGORA) == date(2025, 12, 30)
    assert campo.ler_data("nao sei", AGORA) is None and campo.ler_data("31/02", AGORA) is None


def _api(cfg):
    return TestClient(criar_app(cfg)), {"X-Axiaatende-Chave": "chave-de-teste"}


def test_as_rotas_do_marketing_so_com_a_chave(canal):
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "colheita", "produto": "CENTEIO IPR 89", "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "Colheita do centeio"), ia=ia)
    api, chave = _api(canal)
    assert api.get("/campo/pendentes").status_code == 403
    assert api.get("/campo/pendentes", headers={"X-Axiaatende-Chave": "errada"}).status_code == 403
    assert api.post("/campo/portfolio", json={"produtos": PRODUTOS + ["GUANDU"]}, headers=chave).json() == {"produtos": 5}
    assert api.get("/campo/novos", headers=chave).json()["ligado"] is True   # a rota (a janela de 1 dia e do relogio real)
    with conexao(canal) as con:
        novos = campo.novos(con, AGORA + MIN)
    assert len(novos) == 1 and novos[0]["palpite"] is None
    item = novos[0]
    assert api.post("/campo/%d/palpite" % item["id"], json={"bastidor": "colheita", "produto": "CENTEIO IPR 89", "fase": "pre-colheita"}, headers=chave).status_code == 200
    assert api.get("/campo/pendentes", headers=chave).json() == {"ligado": True, "itens": []}   # a conversa ainda nao fechou
    minuto(canal, s, AGORA + MIN, ia=ia)
    passo(canal, s, toque("wamid.t1", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 2 * MIN, ia=ia)
    r = api.get("/campo/pendentes", headers=chave).json()
    assert r["ligado"] is True and len(r["itens"]) == 1   # fechou: entra
    item = r["itens"][0]
    assert item["contato"] == {"codigo": 12, "papel": "equipe", "nome": "Maicon Gregory"}
    assert item["classe"] == {"bastidor": "colheita", "produto": "CENTEIO IPR 89", "fase": None} and item["fechado"] is True
    assert item["palpite"] == {"bastidor": "colheita", "produto": "CENTEIO IPR 89", "fase": "pre-colheita"}
    arq = api.get("/campo/%d/arquivo" % item["id"], headers=chave)
    assert arq.status_code == 200 and arq.content.startswith(b"MIDIA:")
    assert api.post("/campo/%d/buscado" % item["id"], json={"lote": "2026-10-12-campo-maicon", "linha": 0}, headers=chave).json()["lote"] == "2026-10-12-campo-maicon"
    assert api.get("/campo/pendentes", headers=chave).json()["itens"] == []   # ja levado
    assert api.get("/campo/classificados", headers=chave).json()["itens"] == []   # sem ATV ainda
    assert api.post("/campo/%d/catalogado" % item["id"], json={"atv": "atv-0700"}, headers=chave).json()["atv"] == "ATV-0700"
    cl = api.get("/campo/classificados", headers=chave).json()["itens"]
    assert [c["id"] for c in cl] == [item["id"]] and cl[0]["data"] == "2026-10-12"
    assert api.post("/campo/%d/classe-aplicada" % item["id"], headers=chave).status_code == 200
    assert api.get("/campo/classificados", headers=chave).json()["itens"] == []
    assert api.post("/campo/%d/foi-ao-ar" % item["id"], json={"peca": "ao-vivo-2026-10-12-colheita"}, headers=chave).status_code == 200
    assert api.post("/campo/999/catalogado", json={"atv": "ATV-1"}, headers=chave).status_code == 404
    med = api.get("/campo/medidas", headers=chave).json()
    assert (med["recebidos"], med["buscados"], med["catalogados"], med["classificados"], med["ligado"]) == (1, 1, 1, 1, True)
    assert api.get("/campo/qualquer").status_code in (403, 404, 422)   # a tela nao serve /campo/


def test_os_avisos_saem_so_dentro_da_janela_e_uma_vez_por_grupo(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "Colheita"))
    passo(canal, s, foto("wamid.f2", "Colheita"), agora=AGORA + MIN)
    ids = [m["id"] for m in material(canal)]
    with conexao(canal) as con:
        for i, item in enumerate(ids):
            campo.catalogado(con, item, "ATV-070%d" % i, AGORA + 2 * H)
    s2 = SaidaFalsa()
    minuto(canal, s2, AGORA + 3 * H)
    assert textos(s2).count(campo.AVISO_CATALOGO) == 1 and s2.enviadas[-1][1] == EQUIPE   # um aviso por grupo
    minuto(canal, s2, AGORA + 4 * H)
    assert textos(s2).count(campo.AVISO_CATALOGO) == 1
    assert all(m["aviso_catalogo"] == "enviado" for m in material(canal))
    with conexao(canal) as con:
        campo.foi_ao_ar(con, ids[0], "ao-vivo-x", AGORA + 40 * H)
        # a janela conta da ultima mensagem DELA (eventos_meta.recebido_em, que o banco carimba com o
        # relogio real): fixa em AGORA para o teste nao depender do dia em que roda
        con.execute("UPDATE atendimento.eventos_meta SET recebido_em = %s", (AGORA,))
    n = len(s2.enviadas)
    minuto(canal, s2, AGORA + 40 * H + MIN)
    assert len(s2.enviadas) == n and material(canal)[0]["aviso_ar"] == "fora_da_janela"
