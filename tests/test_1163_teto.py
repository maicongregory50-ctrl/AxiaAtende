"""#1163: o teto de duas mensagens por mes ao comprador (o #1103, spec de 26/10, linha 27).

O que se segura: decidido no laco do lote, na hora de sair; conta convite e peca do mes do
calendario em Sao Paulo; a terceira no mes fica `teto_do_mes` e o comprador volta a receber no mes
seguinte; o tecnico e o contato sem papel nao sao segurados; a rota da previa diz quantas cada numero
recebeu no mes. Meta falsa: nada sai.
"""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.banco import conexao
from backend.envio import Envio
from backend.main import criar_app
from tests.saida_falsa import SaidaFalsa
from tests.test_1192_janela import dia_util_10h
from tests.test_envio import CHAVE, cliente, ligado, imagens, pedido, pedir  # noqa: F401 (fixtures)

DIA_5 = datetime(2026, 11, 5, 13, 0, tzinfo=timezone.utc)      # quinta, 10:00 em Sao Paulo (#1192: dentro da janela)


def _situacao(cfg, ref, codigo):
    with conexao(cfg) as con:
        return con.execute(
            "SELECT d.situacao FROM atendimento.envio_destinatarios d JOIN atendimento.envios e"
            " ON e.id = d.envio_id WHERE e.pedido_ref = %s AND d.erp_codigo = %s", (ref, codigo)).fetchone()["situacao"]


def _com_papel(codigo, papel, whatsapp):
    c = cliente(codigo, 1000, whatsapp=whatsapp)
    c["papel"] = papel
    return c


def test_a_terceira_do_mes_fica_no_teto_e_o_mes_seguinte_recebe(ligado, imagens):
    env, s = Envio(ler_nota=lambda: "GREEN"), SaidaFalsa()
    gente = [_com_papel(1, "comprador", "47991110001"), _com_papel(2, "tecnico", "47991110002"),
             _com_papel(3, None, "47991110003")]
    # #1192: so dia util -- quinta, sexta e a segunda seguinte
    for n, dia in ((1, DIA_5), (2, DIA_5 + timedelta(days=1)), (3, DIA_5 + timedelta(days=4))):
        assert pedir(ligado, pedido(imagens, gente, ref="pub-%d" % n, peca="Peca %d" % n)).status_code == 200
        env.rotina(ligado, s, dia)
    assert [_situacao(ligado, "pub-%d" % n, 1) for n in (1, 2, 3)] == ["convidado", "convidado", "teto_do_mes"]
    assert _situacao(ligado, "pub-3", 2) == "convidado"           # o tecnico nao e segurado
    assert _situacao(ligado, "pub-3", 3) == "convidado"           # nem o contato sem papel
    # 1o de dezembro (terca), 10:00 em Sao Paulo: mes novo, o comprador recebe de novo
    assert pedir(ligado, pedido(imagens, gente, ref="pub-4", peca="Peca 4")).status_code == 200
    env.rotina(ligado, s, datetime(2026, 12, 1, 13, 0, tzinfo=timezone.utc))
    assert _situacao(ligado, "pub-4", 1) == "convidado"


def test_a_virada_do_mes_e_a_de_sao_paulo(ligado, imagens):
    """30/11 23:30 em Sao Paulo ja e 01/12 em UTC: ainda e novembro, e conta no teto de novembro. Desde
    o #1192 nenhum lote sai as 23:30 (a janela fecha as 17h): a conta do mes se confere direto."""
    env, s = Envio(ler_nota=lambda: "GREEN"), SaidaFalsa()
    gente = [_com_papel(1, "comprador", "47991110001")]
    for n, quando in ((1, DIA_5), (2, DIA_5 + timedelta(days=1))):
        pedir(ligado, pedido(imagens, gente, ref="pub-%d" % n, peca="Peca %d" % n))
        env.rotina(ligado, s, quando)
    with conexao(ligado) as con:
        numero = con.execute("SELECT whatsapp FROM atendimento.envio_destinatarios LIMIT 1").fetchone()["whatsapp"]
        assert Envio.recebidas_no_mes(con, numero, datetime(2026, 12, 1, 2, 30, tzinfo=timezone.utc)) == 2
        assert Envio.recebidas_no_mes(con, numero, datetime(2026, 12, 1, 13, 0, tzinfo=timezone.utc)) == 0


def _volta():
    from backend import migracoes
    sql = (migracoes.PASTA / "034_teto_do_comprador_VOLTA.sql").read_text(encoding="utf-8")
    return sql.split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0]


def test_a_034_vai_volta_e_vai(cfg):
    from backend import migracoes
    with conexao(cfg) as con:
        con.execute(_volta())
        check = con.execute("SELECT pg_get_constraintdef(oid) AS d FROM pg_constraint"
                            " WHERE conname = 'envio_dest_situacao'").fetchone()["d"]
        assert "teto_do_mes" not in check
    assert migracoes.aplicar(cfg) == ["034_teto_do_comprador.sql"]


def test_a_volta_recusa_com_o_numero_quando_ha_segurado(ligado, imagens):
    import pytest
    pedir(ligado, pedido(imagens, [_com_papel(1, "comprador", "47991110001")], ref="pub-1"))
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.envio_destinatarios SET situacao = 'teto_do_mes'")
        with pytest.raises(Exception, match="1 destinatario"):
            con.execute(_volta())


def test_a_rota_da_previa(ligado, imagens):
    env, s = Envio(ler_nota=lambda: "GREEN"), SaidaFalsa()
    pedir(ligado, pedido(imagens, [_com_papel(1, "comprador", "47991110001")], ref="pub-1"))
    env.rotina(ligado, s, dia_util_10h())   # #1192: dentro da janela, no mes corrente
    with TestClient(criar_app(ligado)) as c:
        assert c.post("/pedido/teto", json={"numeros": ["5547991110001"]}).status_code == 403
        r = c.post("/pedido/teto", json={"numeros": ["5547991110001", "5547999999999"]}, headers=CHAVE)
    assert r.status_code == 200, r.text
    assert r.json() == {"teto": 2, "no_mes": {"5547991110001": 1, "5547999999999": 0}}


# ── #1175: a peca a mais (dono, 27/10/2026: "precisa permitir") ─────────────────────────────────

def test_a_peca_a_mais_passa_do_teto_e_a_comum_continua_segurada(ligado, imagens):
    env, s = Envio(ler_nota=lambda: "GREEN"), SaidaFalsa()
    gente = [_com_papel(1, "comprador", "47991110001")]
    for n, dia in ((1, DIA_5), (2, DIA_5 + timedelta(days=1))):
        pedir(ligado, pedido(imagens, gente, ref="pub-%d" % n, peca="Peca %d" % n))
        env.rotina(ligado, s, dia)
    a_mais = dict(pedido(imagens, gente, ref="pub-3", peca="Peca 3"), passa_do_teto=True)
    assert pedir(ligado, a_mais).status_code == 200
    pedir(ligado, pedido(imagens, gente, ref="pub-4", peca="Peca 4"))
    env.rotina(ligado, s, DIA_5 + timedelta(days=4))   # #1192: a segunda seguinte, dia util
    assert _situacao(ligado, "pub-3", 1) == "convidado"           # o dono mandou alem do teto
    assert _situacao(ligado, "pub-4", 1) == "teto_do_mes"         # a comum continua segurada
    with conexao(ligado) as con:
        marcas = {r["pedido_ref"]: r["passa_do_teto"] for r in con.execute(
            "SELECT pedido_ref, passa_do_teto FROM atendimento.envios").fetchall()}
    assert marcas == {"pub-1": False, "pub-2": False, "pub-3": True, "pub-4": False}
