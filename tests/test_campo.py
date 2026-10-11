"""#970: o canal de campo. A foto ou o video de equipe/representante reconhecidos, com a chave ligada,
e baixado e guardado; a OlivIA responde "Recebi" na hora e faz a rodada de perguntas no laco do
minuto, com o palpite do marketing se ele chegou em 2 min (emenda de 11/10); o marketing busca pelas
rotas /campo/* com a chave do pedido; os avisos a quem mandou so dentro das 24 h."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import agenda, campo, recepcionista as R
from backend.banco import conexao
from backend.main import criar_app
from tests.avisos_meta import aviso, texto, toque
from tests.saida_falsa import SaidaFalsa

EQUIPE = "5549991505565"      # Maicon, equipe + representante (agenda de teste)
CLIENTE = "5549999990000"     # Agro Real, cliente
AGORA = datetime(2026, 10, 12, 13, 0, tzinfo=timezone.utc)   # 10:00 em Sao Paulo, segunda
MIN = timedelta(minutes=1)
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
    return c


def ligar(cfg, valor=True):
    with conexao(cfg) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = 'campo.ligado'", ("true" if valor else "false",))


def passo(cfg, s, mensagem, agora=AGORA, numero=EQUIPE, bsuid="BR.equipe"):
    R.gravar(cfg, aviso([mensagem], numero=numero, bsuid=bsuid))
    R.processar_pendentes(cfg, s, None, agora=agora)


def minuto(cfg, s, agora):
    R.rotina_do_minuto(cfg, s, agora=agora)


def material(cfg):
    with conexao(cfg) as con:
        return [dict(r) for r in con.execute("SELECT * FROM atendimento.material_de_campo ORDER BY id").fetchall()]


def palpite(cfg, item_id, bastidor, produto, agora):
    with conexao(cfg) as con:
        campo.palpite(con, item_id, bastidor, produto, agora)


def test_com_a_chave_desligada_a_foto_da_equipe_segue_como_hoje(canal):
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "Colheita do centeio"))
    assert material(canal) == []
    assert s.enviadas and s.enviadas[0][0] in ("texto", "lista", "botoes")   # o menu, como sempre


def test_foto_com_legenda_e_baixada_e_a_rodada_sai_com_o_palpite(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "Colheita do centeio"))
    m = material(canal)
    assert len(m) == 1 and m[0]["legenda"] == "Colheita do centeio" and m[0]["erp_papel"] == "equipe"
    assert m[0]["arquivo"] == "2026-10-12/wamid.f1.jpg" and (canal.campo_pasta / m[0]["arquivo"]).read_bytes().startswith(b"MIDIA:")
    assert [x[2] for x in s.enviadas] == [campo.RECEBI]   # so o "Recebi": a rodada e do laco
    with conexao(canal) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"] == 0   # sem atendimento
        assert [i["id"] for i in campo.novos(con)] == [m[0]["id"]]   # o marketing vai olhar a foto
    minuto(canal, s, AGORA + 30 * timedelta(seconds=1))
    assert len(s.enviadas) == 1   # sem palpite e antes de 2 min: espera
    palpite(canal, m[0]["id"], "colheita", "CENTEIO IPR 89", AGORA + MIN)
    minuto(canal, s, AGORA + MIN)
    assert [(x[0], x[2]) for x in s.enviadas[1:]] == [("texto", "Parece colheita de centeio ipr 89. É isso?"),
                                                      ("botoes", campo.PERGUNTA_DATA)]
    assert s.enviadas[2][3] == [("campo:hoje:sim", "Sim"), ("campo:hoje:outra", "Outra data")]
    assert material(canal)[0]["pergunta_pendente"] == "data"
    with conexao(canal) as con:
        assert campo.novos(con) == [] and campo.pendentes(con, AGORA + 2 * MIN) == []   # perguntado, sem resposta: espera
    passo(canal, s, toque("wamid.t1", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 2 * MIN)
    m = material(canal)[0]
    assert m["data_dita"] == date(2026, 10, 12) and m["data_presumida"] is False and m["pergunta_pendente"] is None
    assert s.ultima[2] == campo.ANOTADO
    with conexao(canal) as con:
        p = campo.pendentes(con, AGORA + 3 * MIN)
    assert len(p) == 1 and p[0]["palpite"] == {"bastidor": "colheita", "produto": "CENTEIO IPR 89"} and p[0]["falta"] == []


def test_sem_legenda_e_sem_palpite_a_rodada_sai_aos_dois_minutos(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"))
    minuto(canal, s, AGORA + MIN)
    assert [x[2] for x in s.enviadas] == [campo.RECEBI]
    minuto(canal, s, AGORA + 3 * MIN)
    assert s.ultima[2] == campo.PERGUNTA_LEGENDA and material(canal)[0]["pergunta_pendente"] == "legenda"
    minuto(canal, s, AGORA + 4 * MIN)
    assert len(s.enviadas) == 2   # a rodada nao se repete
    passo(canal, s, texto("wamid.t1", "Vistoria da aveia no campo do Jair", numero=EQUIPE), agora=AGORA + 5 * MIN)
    m = material(canal)[0]
    assert m["legenda"] == "Vistoria da aveia no campo do Jair" and m["pergunta_pendente"] == "data"
    assert s.ultima[2] == campo.PERGUNTA_DATA
    passo(canal, s, toque("wamid.t2", "campo:hoje:outra", numero=EQUIPE), agora=AGORA + 6 * MIN)
    assert s.ultima[2] == campo.PERGUNTA_QUAL_DIA and material(canal)[0]["pergunta_pendente"] == "qual_dia"
    passo(canal, s, texto("wamid.t3", "09/10", numero=EQUIPE), agora=AGORA + 7 * MIN)
    m = material(canal)[0]
    assert m["data_dita"] == date(2026, 10, 9) and m["data_presumida"] is False and m["pergunta_pendente"] is None


def test_a_frase_mandada_logo_depois_da_foto_e_a_legenda_e_nao_abre_o_menu(canal):
    """Primeiro caso com o dono (11/10/2026): foto sem legenda e, em seguida, a frase em mensagem
    separada. Antes, o texto caia no atendimento e vinha o menu junto com o 'Recebi'."""
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"))
    passo(canal, s, texto("wamid.t1", "Vistoria da aveia", numero=EQUIPE), agora=AGORA + timedelta(seconds=20))
    assert [x[2] for x in s.enviadas] == [campo.RECEBI]   # nada de menu
    with conexao(canal) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"] == 0
    assert material(canal)[0]["legenda"] == "Vistoria da aveia"
    passo(canal, s, texto("wamid.t2", "campo do Jair", numero=EQUIPE), agora=AGORA + timedelta(seconds=40))
    assert material(canal)[0]["legenda"] == "Vistoria da aveia · campo do Jair" and len(s.enviadas) == 1
    minuto(canal, s, AGORA + 3 * MIN)
    assert [x[2] for x in s.enviadas[1:]] == [campo.PERGUNTA_DATA]   # a legenda ja esta: so a data
    # depois da rodada respondida, texto solto volta a ser atendimento normal (depois dos 10 min)
    passo(canal, s, toque("wamid.t3", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 4 * MIN)
    passo(canal, s, texto("wamid.t4", "preciso falar com o comercial", numero=EQUIPE), agora=AGORA + 15 * MIN)
    with conexao(canal) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"] == 1


def test_varias_fotos_em_minutos_sao_uma_rodada_e_a_resposta_vale_para_todas(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"))
    passo(canal, s, foto("wamid.f2"), agora=AGORA + MIN)
    passo(canal, s, foto("wamid.f3", tipo="video"), agora=AGORA + 2 * MIN)
    for m in material(canal):   # o marketing devolve o palpite de CADA foto (o lote do dono, 11/10)
        palpite(canal, m["id"], "beneficiamento", None, AGORA + MIN)
    minuto(canal, s, AGORA + 3 * MIN)
    minuto(canal, s, AGORA + 5 * MIN)
    assert [x[2] for x in s.enviadas] == [campo.RECEBI, "Parece beneficiamento. É isso? " + campo.PERGUNTA_LEGENDA]
    assert [m["tipo"] for m in material(canal)] == ["foto", "foto", "video"]
    assert all(m["perguntas_em"] is not None for m in material(canal))   # a rodada e do grupo
    passo(canal, s, texto("wamid.t1", "Beneficiamento na UBS", numero=EQUIPE), agora=AGORA + 6 * MIN)
    passo(canal, s, toque("wamid.t2", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 7 * MIN)
    for m in material(canal):
        assert m["legenda"] == "Beneficiamento na UBS" and m["data_dita"] == date(2026, 10, 12)
    # uma foto 20 minutos depois e outro grupo: nova rodada
    passo(canal, s, foto("wamid.f4", "Carga saindo"), agora=AGORA + 25 * MIN)
    minuto(canal, s, AGORA + 28 * MIN)
    assert s.ultima[2] == campo.PERGUNTA_DATA and material(canal)[-1]["legenda"] == "Carga saindo"


def test_cliente_com_foto_segue_para_o_menu_e_quem_nao_responde_nao_e_cobrado(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.c1", "oi", numero=CLIENTE), numero=CLIENTE, bsuid="BR.cliente")
    assert material(canal) == []
    with conexao(canal) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"] == 1
    # a equipe manda e some: a rodada sai aos 2 min, e 10 min depois dela o material esta pronto, com "falta"
    passo(canal, s, foto("wamid.f1"))
    minuto(canal, s, AGORA + 3 * MIN)
    with conexao(canal) as con:
        assert campo.pendentes(con, AGORA + 8 * MIN) == []
        prontos = campo.pendentes(con, AGORA + 14 * MIN)
    assert len(prontos) == 1 and prontos[0]["falta"] == ["legenda", "data"] and prontos[0]["data"] == "2026-10-12"


def test_quando_a_meta_nao_entrega_a_midia_a_linha_diz_o_erro_e_nada_quebra(canal):
    ligar(canal)
    s = SaidaFalsa()
    s.baixar_falha = True
    passo(canal, s, foto("wamid.f1", "x"))
    m = material(canal)[0]
    assert m["arquivo"] is None and "nao entregou" in m["erro"]
    with conexao(canal) as con:
        assert campo.pendentes(con, AGORA + timedelta(hours=1)) == []   # sem arquivo, nao se oferece
        assert campo.novos(con) == []


def test_ler_data():
    assert campo.ler_data("hoje", AGORA) == date(2026, 10, 12)
    assert campo.ler_data("ontem", AGORA) == date(2026, 10, 11)
    assert campo.ler_data("09/10", AGORA) == date(2026, 10, 9)
    assert campo.ler_data("foi dia 9/10/2026", AGORA) == date(2026, 10, 9)
    assert campo.ler_data("2026-10-08", AGORA) == date(2026, 10, 8)
    assert campo.ler_data("30/12", AGORA) == date(2025, 12, 30)   # um mes a frente sem ano: foi no ano passado
    assert campo.ler_data("nao sei", AGORA) is None and campo.ler_data("31/02", AGORA) is None


def _api(cfg):
    return TestClient(criar_app(cfg)), {"X-Axiaatende-Chave": "chave-de-teste"}


def test_as_rotas_do_marketing_so_com_a_chave(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "Colheita do centeio"))
    api, chave = _api(canal)
    assert api.get("/campo/pendentes").status_code == 403
    assert api.get("/campo/pendentes", headers={"X-Axiaatende-Chave": "errada"}).status_code == 403
    novos = api.get("/campo/novos", headers=chave).json()
    assert novos["ligado"] is True and len(novos["itens"]) == 1 and novos["itens"][0]["palpite"] is None
    item = novos["itens"][0]
    assert api.post("/campo/%d/palpite" % item["id"], json={"bastidor": "colheita", "produto": "CENTEIO IPR 89"}, headers=chave).status_code == 200
    minuto(canal, s, AGORA + MIN)
    passo(canal, s, toque("wamid.t1", "campo:hoje:sim", numero=EQUIPE), agora=AGORA + 2 * MIN)
    r = api.get("/campo/pendentes", headers=chave).json()
    assert r["ligado"] is True and len(r["itens"]) == 1
    item = r["itens"][0]
    assert item["contato"] == {"codigo": 12, "papel": "equipe", "nome": "Maicon Gregory"}
    assert item["legenda"] == "Colheita do centeio" and item["data"] == "2026-10-12" and item["falta"] == []
    assert item["palpite"] == {"bastidor": "colheita", "produto": "CENTEIO IPR 89"}
    arq = api.get("/campo/%d/arquivo" % item["id"], headers=chave)
    assert arq.status_code == 200 and arq.content.startswith(b"MIDIA:")
    assert api.post("/campo/%d/buscado" % item["id"], json={"lote": "2026-10-12-campo-maicon", "linha": 0}, headers=chave).json()["lote"] == "2026-10-12-campo-maicon"
    assert api.get("/campo/pendentes", headers=chave).json()["itens"] == []   # ja levado
    assert api.post("/campo/%d/catalogado" % item["id"], json={"atv": "atv-0700"}, headers=chave).json()["atv"] == "ATV-0700"
    assert api.post("/campo/%d/foi-ao-ar" % item["id"], json={"peca": "ao-vivo-2026-10-12-colheita"}, headers=chave).status_code == 200
    assert api.post("/campo/999/catalogado", json={"atv": "ATV-1"}, headers=chave).status_code == 404
    med = api.get("/campo/medidas", headers=chave).json()
    assert (med["recebidos"], med["buscados"], med["catalogados"], med["ligado"]) == (1, 1, 1, True)
    assert api.get("/campo/qualquer").status_code in (403, 404, 422)   # a tela nao serve /campo/


def test_buscado_sem_resposta_presume_a_data_do_envio(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1"))
    minuto(canal, s, AGORA + 3 * MIN)
    with conexao(canal) as con:
        x = campo.buscado(con, material(canal)[0]["id"], "lote-x", 0, AGORA + 14 * MIN)
    assert x["data"] == "2026-10-12" and x["data_presumida"] is True and x["falta"] == ["legenda", "data"]
    assert material(canal)[0]["pergunta_pendente"] is None


def test_os_avisos_saem_so_dentro_da_janela_e_uma_vez(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, foto("wamid.f1", "Colheita"))
    item = material(canal)[0]["id"]
    with conexao(canal) as con:
        campo.catalogado(con, item, "ATV-0700", AGORA + timedelta(hours=2))
    s2 = SaidaFalsa()
    minuto(canal, s2, AGORA + timedelta(hours=3))
    avisos = [x[2] for x in s2.enviadas if x[2] == campo.AVISO_CATALOGO]
    assert avisos == [campo.AVISO_CATALOGO] and s2.enviadas[-1][1] == EQUIPE
    minuto(canal, s2, AGORA + timedelta(hours=4))
    assert [x[2] for x in s2.enviadas].count(campo.AVISO_CATALOGO) == 1   # nunca duas vezes
    m = material(canal)[0]
    assert m["aviso_catalogo"] == "enviado" and m["aviso_catalogo_em"] is not None
    # o Stories so no dia seguinte: passou a janela da ultima mensagem dela; fica anotado, nada sai
    with conexao(canal) as con:
        campo.foi_ao_ar(con, item, "ao-vivo-x", AGORA + timedelta(hours=30))
    n = len(s2.enviadas)
    minuto(canal, s2, AGORA + timedelta(hours=30, minutes=1))
    assert len(s2.enviadas) == n and material(canal)[0]["aviso_ar"] == "fora_da_janela"
