"""#1223: o painel de custos -- o uso do Gemini que o Marketing empurra, a conferencia da Meta e a conta
por funcao. Nada sai da maquina: a Meta e falsa e o banco e o de teste."""
from dataclasses import replace

from fastapi.testclient import TestClient

from backend.banco import conexao
from backend.main import criar_app

CHAVE = {"X-Axiaatende-Chave": "chave-do-marketing"}
LOTE = {"usos": [{"id": 7, "em": "2026-10-31T10:00:00-03:00", "funcao": "edicao", "modelo": "gemini-3.8-flash-image",
                  "entrada": 1290, "saida": 1300},
                 {"id": 8, "em": "2026-10-31T10:05:00-03:00", "funcao": "olhar_foto", "modelo": "gemini-3.8-flash",
                  "entrada": 900, "saida": 40}]}


def _com_chave(cfg):
    return replace(cfg, chave_pedido="chave-do-marketing")


def test_uso_do_gemini_sem_a_chave_e_recusado(cfg):
    with TestClient(criar_app(_com_chave(cfg))) as c:
        assert c.post("/pedido/uso-ia", json=LOTE).status_code == 403
        assert c.post("/pedido/uso-ia", json=LOTE, headers={"X-Axiaatende-Chave": "outra"}).status_code == 403
    with TestClient(criar_app(cfg)) as c:   # sem chave configurada, recusa tudo
        assert c.post("/pedido/uso-ia", json=LOTE, headers=CHAVE).status_code == 403


def test_o_mesmo_lote_duas_vezes_vira_uma_linha_por_chamada(cfg):
    with TestClient(criar_app(_com_chave(cfg))) as c:
        for _ in range(2):
            r = c.post("/pedido/uso-ia", json=LOTE, headers=CHAVE)
            assert r.status_code == 200 and r.json() == {"aceitos": [7, 8]}
    with conexao(cfg) as con:
        linhas = con.execute("SELECT origem, id_origem, servico, funcao FROM atendimento.uso_ia ORDER BY id_origem").fetchall()
    assert [(l["origem"], l["id_origem"], l["servico"], l["funcao"]) for l in linhas] == [
        ("axiamarketing", 7, "gemini", "edicao"), ("axiamarketing", 8, "gemini", "olhar_foto")]


# ── a conferencia diaria da Meta ────────────────────────────────────────────────────────────────
from datetime import date, datetime, timezone   # noqa: E402

import httpx   # noqa: E402

from backend import custos_meta   # noqa: E402

HOJE = date(2026, 11, 1)
MOMENTO = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)   # 09:00 no servidor


def _meta(status, corpo, pedidos=None):
    def responder(req):
        if pedidos is not None:
            pedidos.append(req)
        return httpx.Response(status, json=corpo)
    return httpx.Client(base_url="https://graph.facebook.com/v23.0", transport=httpx.MockTransport(responder))


def _ts(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def _com_token(cfg):
    return replace(cfg, meta_token="falso")


def _conferencia(cfg):
    with conexao(cfg) as con:
        return ({r["dia"]: r["situacao"] for r in con.execute("SELECT * FROM atendimento.meta_conferencia")},
                {(r["dia"], r["categoria"]): (r["volume"], float(r["custo"]), r["moeda"])
                 for r in con.execute("SELECT * FROM atendimento.meta_cobrado")})


def test_a_leitura_boa_grava_o_cobrado_dos_tres_dias(cfg):
    pedidos = []
    corpo = {"currency": "USD", "pricing_analytics": {"data": [{"data_points": [
        {"start": _ts(date(2026, 10, 30)), "end": 0, "pricing_category": "MARKETING", "volume": 40, "cost": 2.5},
        {"start": _ts(date(2026, 10, 31)), "end": 0, "pricing_category": "UTILITY", "volume": 3, "cost": 0.02}]}]}}
    with conexao(cfg) as con:
        assert custos_meta.conferir(_com_token(cfg), con, MOMENTO, http=_meta(200, corpo, pedidos)) == "ok"
    sit, cobrado = _conferencia(cfg)
    assert sit == {date(2026, 10, 29): "ok", date(2026, 10, 30): "ok", date(2026, 10, 31): "ok"}
    assert cobrado == {(date(2026, 10, 30), "marketing"): (40, 2.5, "USD"),
                       (date(2026, 10, 31), "utility"): (3, 0.02, "USD")}
    assert pedidos[0].method == "GET" and "pricing_analytics" in str(pedidos[0].url)
    with conexao(cfg) as con:   # uma vez por dia: a segunda volta do minuto nao pergunta de novo
        assert custos_meta.conferir(_com_token(cfg), con, MOMENTO, http=_meta(500, {})) is None


def test_permissao_negada_e_sem_acesso_e_nunca_zero(cfg):
    with conexao(cfg) as con:
        sit = custos_meta.conferir(_com_token(cfg), con, MOMENTO, http=_meta(
            400, {"error": {"code": 200, "message": "Requires whatsapp_business_management permission"}}))
    assert sit == "sem_acesso"
    situacoes, cobrado = _conferencia(cfg)
    assert set(situacoes.values()) == {"sem_acesso"} and cobrado == {}


def test_forma_inesperada_e_erro_com_detalhe(cfg):
    with conexao(cfg) as con:
        assert custos_meta.conferir(_com_token(cfg), con, MOMENTO, http=_meta(200, {"id": "1"})) == "erro"
        d = con.execute("SELECT detalhe FROM atendimento.meta_conferencia LIMIT 1").fetchone()["detalhe"]
    assert "forma inesperada" in d


def test_desligada_antes_das_seis_ou_sem_token_nao_pergunta(cfg):
    cedo = datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)   # 04:00 no servidor
    with conexao(cfg) as con:
        assert custos_meta.conferir(_com_token(cfg), con, cedo, http=_meta(500, {})) is None
        assert custos_meta.conferir(cfg, con, MOMENTO, http=_meta(500, {})) is None   # sem token
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'custos.conferir_meta'")
        assert custos_meta.conferir(_com_token(cfg), con, MOMENTO, http=_meta(500, {})) is None


# ── a tela: por funcao, "sem preco" nunca e zero, e so para quem esta na lista ──────────────────
import json   # noqa: E402

from backend import seguranca   # noqa: E402
from backend.main import CABECALHO_DA_TELA   # noqa: E402


def _status_pago(wamid, categoria, quando="2026-10-20 10:00-03"):
    return (wamid + ":sent", "status", None,
            json.dumps({"id": wamid, "status": "sent", "pricing": {"billable": True, "pricing_model": "PMP",
                                                                    "category": categoria, "type": "regular"}}), quando)


def _povoar(cfg):
    with conexao(cfg) as con:
        for linha in (_status_pago("w.modelo", "marketing"), _status_pago("w.aviso", "utility"),
                      _status_pago("w.resumo", "marketing"), _status_pago("w.nada", "marketing"),
                      _status_pago("w.setembro", "marketing", "2026-09-30 10:00-03")):
            con.execute("INSERT INTO atendimento.eventos_meta (chave_meta, tipo, bsuid, corpo, recebido_em)"
                        " VALUES (%s, %s, %s, %s, %s)", linha)
        # gratis: nao entra
        con.execute("INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo, recebido_em) VALUES"
                    " ('w.free:sent', 'status', %s, '2026-10-20 10:00-03')",
                    (json.dumps({"id": "w.free", "status": "sent", "pricing": {"billable": False, "category": "service"}}),))
        con.execute("INSERT INTO atendimento.enviadas_texto (wamid, tipo, modelo) VALUES ('w.modelo', 'modelo', 'pecas_da_revenda')")
        con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES ('w.resumo', '5549', 'modelo', 'direta Boletim de safra')")
        con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre, wamid)
                       VALUES ('recusa', 'X', '5549991505565', 't', 'w.aviso')""")
        con.execute("INSERT INTO atendimento.uso_ia (em, origem, servico, funcao, modelo, entrada, saida) VALUES"
                    " ('2026-10-20 10:00-03', 'axiaatende', 'claude', 'triagem', 'claude-haiku-5-5', 1000000, 100000)")
        con.execute("INSERT INTO atendimento.uso_ia (em, origem, id_origem, servico, funcao, modelo, entrada, saida) VALUES"
                    " ('2026-10-20 10:00-03', 'axiamarketing', 1, 'gemini', 'edicao', 'gemini-x', 10, 10)")
        con.execute("INSERT INTO atendimento.precos (servico, item, vale_desde, por_mensagem) VALUES ('meta', 'marketing', '2026-10-01', 0.0625)")
        con.execute("INSERT INTO atendimento.meta_conferencia (dia, situacao) VALUES ('2026-10-20', 'ok'), ('2026-10-21', 'sem_acesso')")
        con.execute("INSERT INTO atendimento.meta_cobrado (dia, categoria, volume, custo, moeda) VALUES ('2026-10-20', 'marketing', 3, 0.19, 'USD')")
        con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash) VALUES ('maicon', 'Maicon', %s), ('fran', 'Fran', %s)",
                    (seguranca.gerar_hash("senha-de-teste-1"), seguranca.gerar_hash("senha-de-teste-1")))
    seguranca.limpar_erros("maicon")
    seguranca.limpar_erros("fran")


def _tela(cfg, login):
    c = TestClient(criar_app(replace(cfg, erp_segredo="", custos_logins=("maicon",))), headers={CABECALHO_DA_TELA: "1"})
    c.__enter__()
    assert c.post("/api/entrar", json={"login": login, "senha": "senha-de-teste-1"}).status_code == 200
    return c


def test_so_quem_esta_na_lista_ve(cfg):
    _povoar(cfg)
    c = _tela(cfg, "fran")
    try:
        assert c.get("/api/custos/permitido").json() == {"permitido": False}
        assert c.get("/api/custos?mes=2026-10").status_code == 403
        assert c.post("/api/custos/precos", json={"servico": "meta", "item": "utility", "vale_desde": "2026-10-01",
                                                   "por_mensagem": 0.01}).status_code == 403
    finally:
        c.__exit__(None, None, None)


def test_a_conta_por_funcao_com_sem_preco_e_sem_funcao(cfg):
    _povoar(cfg)
    c = _tela(cfg, "maicon")
    try:
        assert c.get("/api/custos/permitido").json() == {"permitido": True}
        d = c.get("/api/custos?mes=2026-10").json()
    finally:
        c.__exit__(None, None, None)
    meta = {(l["funcao"], l["fonte"]): l for l in d["linhas"] if l["servico"] == "meta"}
    assert set(meta) == {("convite", "registro"), ("aviso_recusa", "registro"), ("direta", "resumo"),
                         ("sem_funcao", "nenhum")}                       # setembro e gratis ficam de fora
    assert meta[("convite", "registro")]["valor"] == 0.0625 and meta[("convite", "registro")]["sem_preco"] == 0
    assert meta[("aviso_recusa", "registro")]["sem_preco"] == 1 and meta[("aviso_recusa", "registro")]["valor"] == 0
    claude = next(l for l in d["linhas"] if l["servico"] == "claude")
    assert claude["funcao"] == "triagem" and abs(claude["valor"] - 0.15) < 1e-9     # 1M x 0,10 + 0,1M x 0,50
    gemini = next(l for l in d["linhas"] if l["servico"] == "gemini")
    assert gemini["sem_preco"] == 1 and gemini["valor"] == 0
    dias = {x["dia"]: x for x in d["meta_dias"]}
    assert dias["2026-10-20"]["quantidade"] == 4 and abs(dias["2026-10-20"]["calculado"] - 0.1875) < 1e-9
    assert dias["2026-10-20"]["sem_preco"] == 1 and dias["2026-10-20"]["cobrado"] == 0.19
    assert dias["2026-10-21"]["situacao"] == "sem_acesso" and dias["2026-10-21"]["cobrado"] is None


def test_preco_novo_e_linha_nova_e_a_mesma_data_e_recusada(cfg):
    _povoar(cfg)
    c = _tela(cfg, "maicon")
    try:
        p = {"servico": "meta", "item": "utility", "vale_desde": "2026-10-01", "por_mensagem": 0.0068}
        assert c.post("/api/custos/precos", json=p).status_code == 200
        assert c.post("/api/custos/precos", json=p).status_code == 409
        assert c.post("/api/custos/precos", json={"servico": "gemini", "item": "gemini-x",
                                                   "vale_desde": "2026-10-01", "por_milhao_entrada": 0.3}).status_code == 422
        d = c.get("/api/custos/precos").json()
        assert "utility" in d["itens"]["meta"] and d["itens"]["gemini"] == ["gemini-x"]
        aviso = next(l for l in c.get("/api/custos?mes=2026-10").json()["linhas"] if l["funcao"] == "aviso_recusa")
        assert aviso["sem_preco"] == 0 and aviso["valor"] == 0.0068
    finally:
        c.__exit__(None, None, None)
