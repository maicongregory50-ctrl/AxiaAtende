"""#1188: o porteiro dos avisos internos. Dentro das 24 h da pessoa o aviso sai como texto, de graca;
fora, fica guardado e sai UMA reabertura por numero ("Voce tem N aviso(s)... Ver"); o toque em Ver
solta os guardados na ordem; 7 dias sem toque = nao visto, que nao some. Chave desligada: como antes.
Meta falsa: nada sai."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import count

import pytest
from fastapi.testclient import TestClient

from backend import envio as envio_mod
from backend import migracoes, motor
from backend.banco import conexao
from backend.envio import Envio
from backend.main import criar_app
from tests.saida_falsa import SaidaFalsa
from tests.test_telas import ligado, tela  # noqa: F401 (fixtures: o login das telas)

AGORA = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
REP = "5549999110001"          # como o cadastro guarda: com o 9
REP_META = "554999110001"      # como a Meta manda: sem o 9
OUTRO = "5549999220002"
TEXTO_RECUSA = ("Aviso da sua carteira: o cliente Agro X (5475 · Chapecó) pediu para não receber as peças. "
                "Vale um contato direto: https://wa.me/5549888. Obrigado.")


_WAMIDS = count(1)


def saida():
    """Uma Meta falsa por volta, com wamids que nao se repetem entre elas (o `enviadas.wamid` e unico)."""
    s = SaidaFalsa()
    s._n = _WAMIDS
    return s


@pytest.fixture
def porteiro(cfg):
    return replace(cfg, responde=True, porteiro=True)


def avisar(cfg, para=REP, tipo="recusa", sobre="Agro X|5475 · Chapecó|https://wa.me/5549888", criado=AGORA):
    with conexao(cfg) as con:
        return con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre, criado_em)
                              VALUES (%s, 'Rep', %s, %s, %s) RETURNING id""", (tipo, para, sobre, criado)).fetchone()["id"]


def falou(cfg, quando, numero=REP_META, chave=None):
    """Uma mensagem DA PESSOA ao numero da empresa (qualquer tipo; aqui uma foto, sem texto)."""
    corpo = {"contacts": [{"wa_id": numero, "user_id": "BR.x"}],
             "msg": {"from": numero, "id": chave or "wamid.%s" % quando.timestamp(), "type": "image",
                     "image": {"id": "m1"}}}
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo, recebido_em, processado_em)
                       VALUES (%s, 'mensagem', %s, %s, %s)""", (corpo["msg"]["id"], json.dumps(corpo), quando, quando))


def avisos(cfg):
    with conexao(cfg) as con:
        return [dict(a) for a in con.execute("SELECT * FROM atendimento.avisos ORDER BY id").fetchall()]


def volta(cfg, saida, agora=AGORA):
    with conexao(cfg) as con:
        e = Envio()
        e._porteiro = cfg.porteiro
        e.mandar_avisos(con, saida, agora)


def toque_ver(cfg, saida, numero_carga=REP, de=REP_META, agora=AGORA):
    e = motor.Entrada(wamid="wamid.ver.%s" % agora.timestamp(), tipo="button",
                      pessoa=motor.Pessoa(bsuid="BR.x", wa_id=de, nome="Rep"), toque="reabrir:%s" % numero_carga)
    with conexao(cfg) as con:
        motor.tratar(con, saida, None, e, agora, envio=Envio())


# ── a migracao ────────────────────────────────────────────────────────────────

def test_o_modelo_de_reabertura_e_o_aprovado_pelo_dono(cfg):
    with conexao(cfg) as con:
        m = con.execute("SELECT * FROM atendimento.modelos WHERE uso = 'reabertura'").fetchone()
    assert (m["nome"], m["categoria"], m["botao"], m["variaveis"], m["cabecalho_imagem"]) == (
        "reabrir_avisos", "UTILITY", "ver", ["n_avisos"], False)
    assert m["texto"] == "Você tem {{1}} aviso(s) da Sementes Renascer. Toque em Ver para receber."


def test_a_volta_desfaz_e_a_ida_volta_a_aplicar(cfg):
    avisar(cfg)
    volta_sql = (migracoes.PASTA / "039_porteiro_dos_avisos_VOLTA.sql").read_text(encoding="utf-8")
    with conexao(cfg) as con:
        con.execute((migracoes.PASTA / "049_aviso_auditoria_estoque_VOLTA.sql").read_text(encoding="utf-8"))   # #350: a 049 reescreve os mesmos CHECKs
        con.execute((migracoes.PASTA / "045_informativo_so_ola_VOLTA.sql").read_text(encoding="utf-8").split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0])
        con.execute((migracoes.PASTA / "044_informativo_sem_link_VOLTA.sql").read_text(encoding="utf-8").split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0])
        con.execute((migracoes.PASTA / "043_informativo_ao_comprador_VOLTA.sql").read_text(encoding="utf-8").split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0])   # a 043 mexe nos mesmos CHECKs: a volta dela vem primeiro
        con.execute(volta_sql.split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0])
        assert not con.execute("SELECT 1 FROM atendimento.modelos WHERE uso = 'reabertura'").fetchone()
        assert not con.execute("SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'"
                               " AND table_name = 'avisos' AND column_name = 'guardado_em'").fetchone()
        assert con.execute("SELECT count(*) AS n FROM atendimento.avisos").fetchone()["n"] == 1   # nada apagado
    assert migracoes.aplicar(cfg) == ["039_porteiro_dos_avisos.sql", "043_informativo_ao_comprador.sql",
                                      "044_informativo_sem_link.sql", "045_informativo_so_ola.sql", "049_aviso_auditoria_estoque.sql"]
    with conexao(cfg) as con:
        assert con.execute("SELECT 1 FROM atendimento.modelos WHERE nome = 'reabrir_avisos'").fetchone()


# ── a janela ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ha, aberta", [(timedelta(hours=23), True), (timedelta(hours=25), False)])
def test_a_janela_conta_da_ultima_mensagem_da_pessoa(cfg, ha, aberta):
    falou(cfg, AGORA - ha)
    with conexao(cfg) as con:
        assert envio_mod.janela_aberta(con, REP, AGORA) is aberta


def test_sem_mensagem_nenhuma_a_janela_esta_fechada(cfg):
    falou(cfg, AGORA - timedelta(hours=1), numero="554999330003")   # outra pessoa
    with conexao(cfg) as con:
        assert envio_mod.janela_aberta(con, REP, AGORA) is False


def test_o_toque_de_botao_conta_como_mensagem(cfg):
    corpo = {"contacts": [], "msg": {"from": REP_META, "id": "wamid.b", "type": "button",
                                     "button": {"payload": "envio:1:quero"}}}
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo, recebido_em)
                       VALUES ('wamid.b', 'mensagem', %s, %s)""", (json.dumps(corpo), AGORA - timedelta(hours=2)))
        assert envio_mod.janela_aberta(con, REP, AGORA) is True


# ── o texto livre ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tipo, sobre, comeca", [
    ("recusa", "Agro X|5475 · Chapecó|https://wa.me/5549888", "Aviso da sua carteira: o cliente Agro X"),
    ("sem_atendimento", "João (5549)|Comercial › SC|https://wa.me/5549", "Aviso do atendimento: João (5549)"),
    ("avaliacao_ruim", "João (5549)|Comercial › SC|https://wa.me/5549", None),
    ("endereco_fora", "atende.x|11/10 14:32", None),
    ("endereco_voltou", "atende.x|11/10 14:50|18 min", None),
    ("plano_sem_registro", "7|14/10/2026", "O plano de marketing está há 7 dias sem registro"),
    ("lote_do_representante", "Djeison|3 clientes seus|o Trigo", "Olá, Djeison. 3 clientes seus"),
])
def test_o_texto_livre_e_a_frase_do_modelo_sem_variavel_sobrando(cfg, tipo, sobre, comeca):
    avisar(cfg, tipo=tipo, sobre=sobre)
    with conexao(cfg) as con:
        a = con.execute("SELECT * FROM atendimento.avisos").fetchone()
        t = envio_mod.texto_do_aviso(con, a)
        m = envio_mod.modelo_do_uso(con, "aviso_" + tipo)
    assert "{{" not in t and t
    # a mesma frase do modelo: tirando as variaveis, todo o resto esta la
    for pedaco in [x for x in m["texto"].replace("}}", "{{").split("{{") if x and not x.isdigit()]:
        assert pedaco in t
    if comeca:
        assert t.startswith(comeca)


# ── o porteiro ────────────────────────────────────────────────────────────────

def test_chave_desligada_e_um_modelo_por_aviso_como_antes(cfg):
    avisar(cfg)
    avisar(cfg)
    falou(cfg, AGORA - timedelta(hours=1))   # mesmo com a janela aberta
    s = saida()
    volta(replace(cfg, porteiro=False), s)
    assert [m["nome"] for m in s.modelos] == ["aviso_recusa", "aviso_recusa"]
    assert not [x for x in s.enviadas if x[0] == "texto"]
    assert all(a["enviado_em"] == AGORA and a["como"] == "modelo" and a["guardado_em"] is None for a in avisos(cfg))


def test_dentro_da_janela_sai_texto_e_nenhum_modelo(porteiro):
    avisar(porteiro)
    avisar(porteiro)
    falou(porteiro, AGORA - timedelta(hours=3))
    s = saida()
    volta(porteiro, s)
    assert s.modelos == []
    assert [x[:3] for x in s.enviadas] == [("texto", REP, TEXTO_RECUSA)] * 2
    assert all(a["como"] == "texto" and a["enviado_em"] == AGORA for a in avisos(porteiro))


def test_fora_da_janela_dois_avisos_sao_uma_reabertura_com_dois(porteiro):
    avisar(porteiro)
    avisar(porteiro)
    s = saida()
    volta(porteiro, s)
    assert len(s.modelos) == 1
    m = s.modelos[0]
    assert (m["para"], m["nome"], m["corpo"], m["botoes"]) == (REP, "reabrir_avisos", ["2"], ["reabrir:%s" % REP])
    todos = avisos(porteiro)
    assert all(a["guardado_em"] == AGORA and a["enviado_em"] is None for a in todos)
    assert len({a["reabertura_id"] for a in todos}) == 1 and todos[0]["reabertura_id"] is not None
    # aviso novo com a reabertura pendente: so se soma, nao sai outra
    avisar(porteiro)
    s2 = saida()
    volta(porteiro, s2, AGORA + timedelta(hours=1))
    assert s2.enviadas == []
    assert avisos(porteiro)[2]["reabertura_id"] == todos[0]["reabertura_id"]


def test_cada_numero_tem_a_sua_reabertura(porteiro):
    avisar(porteiro)
    avisar(porteiro, para=OUTRO)
    s = saida()
    volta(porteiro, s)
    assert sorted(m["para"] for m in s.modelos) == sorted([OUTRO, REP])


def test_o_toque_em_ver_solta_os_guardados_na_ordem_e_o_segundo_nada(porteiro):
    sobres = ["A|1|x", "B|2|y", "C|3|z"]
    for i, sobre in enumerate(sobres):
        avisar(porteiro, sobre=sobre, criado=AGORA + timedelta(minutes=i))
    volta(porteiro, saida(), AGORA + timedelta(minutes=5))
    s = saida()
    toque_ver(porteiro, s, agora=AGORA + timedelta(hours=2))
    assert [x[0] for x in s.enviadas] == ["texto"] * 3 and s.modelos == []
    assert [x[2].split("cliente ")[1][0] for x in s.enviadas] == ["A", "B", "C"]
    assert all(a["como"] == "texto" for a in avisos(porteiro))
    s2 = saida()
    toque_ver(porteiro, s2, agora=AGORA + timedelta(hours=2, minutes=1))
    assert s2.enviadas == []


def test_o_toque_nao_abre_o_menu_e_de_outro_numero_e_ignorado(porteiro):
    avisar(porteiro)
    volta(porteiro, saida())
    s = saida()
    toque_ver(porteiro, s, de="554999330003", agora=AGORA + timedelta(hours=1))
    assert s.enviadas == []
    assert avisos(porteiro)[0]["guardado_em"] is not None and avisos(porteiro)[0]["enviado_em"] is None
    with conexao(porteiro) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"] == 0


def test_quem_escreve_sem_tocar_ver_recebe_os_guardados_na_volta(porteiro):
    avisar(porteiro)
    volta(porteiro, saida())
    falou(porteiro, AGORA + timedelta(hours=5))
    s = saida()
    volta(porteiro, s, AGORA + timedelta(hours=5, minutes=1))
    assert [x[0] for x in s.enviadas] == ["texto"] and avisos(porteiro)[0]["como"] == "texto"


def test_sete_dias_sem_toque_e_nao_visto_que_nao_some_nem_sai(porteiro):
    avisar(porteiro)
    s = saida()
    volta(porteiro, s)
    volta(porteiro, saida(), AGORA + timedelta(days=6, hours=23))
    assert avisos(porteiro)[0]["nao_visto_em"] is None
    volta(porteiro, saida(), AGORA + timedelta(days=7, minutes=1))
    a = avisos(porteiro)[0]
    assert a["nao_visto_em"] == AGORA + timedelta(days=7, minutes=1) and a["enviado_em"] is None
    # o toque tardio nao solta o nao visto; a chave desligada tambem nao o manda
    s2 = saida()
    toque_ver(porteiro, s2, agora=AGORA + timedelta(days=8))
    volta(replace(porteiro, porteiro=False), s2, AGORA + timedelta(days=8))
    assert s2.enviadas == [] and len(avisos(porteiro)) == 1
    # e o aviso seguinte abre uma reabertura nova
    avisar(porteiro, criado=AGORA + timedelta(days=9))
    s3 = saida()
    volta(porteiro, s3, AGORA + timedelta(days=9))
    assert [m["corpo"] for m in s3.modelos] == [["1"]]


def test_reabertura_recusada_pela_meta_deixa_o_erro_e_nao_guarda(porteiro):
    avisar(porteiro)
    s = saida()
    s.modelo_falha = "(#132001) Template name does not exist in the translation"
    volta(porteiro, s)
    a = avisos(porteiro)[0]
    assert "132001" in a["erro"] and a["guardado_em"] is None and a["enviado_em"] is None


def test_desligar_a_chave_manda_os_guardados_pelo_modelo_do_tipo(porteiro):
    """O ROLLBACK da spec: o porteiro desligado nao guarda, e o que estava guardado sai como antes."""
    avisar(porteiro)
    volta(porteiro, saida())
    s = saida()
    volta(replace(porteiro, porteiro=False), s, AGORA + timedelta(hours=1))
    assert [m["nome"] for m in s.modelos] == ["aviso_recusa"] and avisos(porteiro)[0]["como"] == "modelo"


# ── a tela Envios e a rota do marketing ───────────────────────────────────────

def test_a_tela_envios_mostra_cada_estado_do_aviso(ligado, tela):
    agora = datetime.now(timezone.utc)   # a tela olha os ultimos 30 dias do relogio de verdade
    ligado_p = replace(ligado, porteiro=True)
    modelo_id = avisar(ligado_p, para="5549999660006", criado=agora)
    volta(replace(ligado_p, porteiro=False), saida(), agora)   # antes: desligada, ela manda os guardados
    nao_visto_id = avisar(ligado_p, para="5549999550005", criado=agora)
    volta(ligado_p, saida(), agora - timedelta(days=8))       # a reabertura de oito dias atras
    volta(ligado_p, saida(), agora)                           # ... sem toque: nao visto
    texto_id = avisar(ligado_p, para=OUTRO, criado=agora)
    falou(ligado_p, agora - timedelta(hours=1), numero="554999220002")
    guardado_id = avisar(ligado_p, criado=agora)
    volta(ligado_p, saida(), agora)
    erro_id = avisar(ligado_p, para="5549999440004", tipo="sem_atendimento", sobre="a|b|c", criado=agora)
    recusa = saida()
    recusa.modelo_falha = "(#132001) Template name does not exist in the translation"
    volta(ligado_p, recusa, agora)
    por_id = {a["id"]: a for a in tela.get("/api/envios").json()["avisos"]}
    assert {i: por_id[i]["estado"] for i in (texto_id, guardado_id, erro_id, nao_visto_id, modelo_id)} == {
        texto_id: "texto", guardado_id: "guardado", erro_id: "erro", nao_visto_id: "nao_visto",
        modelo_id: "modelo"}
    assert por_id[guardado_id]["para"] == "Rep" and REP not in por_id[guardado_id]["numero"]   # mascarado
    assert "132001" in por_id[erro_id]["erro"]


def test_a_rota_do_marketing_continua_na_fila_e_diz_guardado(porteiro):
    ligado = replace(porteiro, chave_pedido="chave-do-marketing")
    with conexao(ligado) as con:
        quem = con.execute("""SELECT d.whatsapp FROM atendimento.destinos d, atendimento.ajustes j
                               WHERE j.chave = 'avisado_no_nao' AND d.id = (j.valor #>> '{}')::int""").fetchone()
    aviso_id = avisar(ligado, para=quem["whatsapp"], tipo="plano_sem_registro", sobre="7|14/10/2026")
    volta(ligado, saida())
    with TestClient(criar_app(ligado)) as c:
        r = c.get("/pedido/aviso/%d" % aviso_id, headers={"X-Axiaatende-Chave": "chave-do-marketing"}).json()
    assert r["situacao"] == "na_fila" and r["guardado"] is True and r["nao_visto"] is False


# ── a chave ───────────────────────────────────────────────────────────────────

def test_a_chave_nasce_desligada_e_so_on_liga(monkeypatch):
    from backend.config import carregar
    monkeypatch.delenv("AXIAATENDE_PORTEIRO", raising=False)
    assert carregar("teste").porteiro is False
    for valor, ligado in (("on", True), ("ON", True), ("off", False), ("true", False), ("", False)):
        monkeypatch.setenv("AXIAATENDE_PORTEIRO", valor)
        assert carregar("teste").porteiro is ligado
