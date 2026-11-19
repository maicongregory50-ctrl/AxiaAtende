"""#1664: a resposta padrao ao produtor cooperante que responde a um aviso automatico do contrato (hoje, o termo de
reprovacao do #1542). Spec: docs/specs/2026-11-19-resposta-padrao-ao-aviso-de-contrato.md (D1 a D8).
Meta falsa: nada sai."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import cooperante, migracoes, motor, recepcionista as R
from backend.banco import conexao
from tests.avisos_meta import aviso, na_hora, texto
from tests.saida_falsa import SaidaFalsa

AGORA = datetime(2026, 11, 19, 12, 5, tzinfo=timezone.utc)   # 09:05 em Brasilia
PRODUTOR = "5514996033466"          # como o ERP guarda (com o 9)
PRODUTOR_META = "551496033466"      # como a Meta manda (sem o 9)
CONTATO = "5549991505565"           # o destino "Maicon Gregory" da semente (002)
PADRAO = "aviso de contrato: resposta padrao (termo %s)"


@pytest.fixture
def ligado(cfg):
    c = replace(cfg, responde=True)
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'cooperante.resposta_padrao'")
    return c


@pytest.fixture
def portao(monkeypatch):
    """O portao do cliente, trocado por um que so conta quem chegou a ele e para a corrente ali."""
    chamadas = []

    def falso(con, saida, ia, e, agora, envio, origem="mensagem"):
        chamadas.append(e.wamid)
        return True
    monkeypatch.setattr(motor, "portao_do_cliente", falso)
    return chamadas


def _termo(cfg, numero_termo="0001/2026", enviado=AGORA - timedelta(minutes=5), estado="enviada",
           para=PRODUTOR, envio_id=41):
    with conexao(cfg) as con:
        return con.execute("""INSERT INTO atendimento.termos_reprovacao
                                  (erp_envio_id, erp_termo_id, numero_termo, produtor_nome, para_whatsapp, estado,
                                   enviado_em, wamid)
                              VALUES (%s, 11, %s, 'ALFONSO ADRIANO SLEUTJES E OUTRA', %s, %s, %s, %s) RETURNING id""",
                           (envio_id, numero_termo, para, estado, enviado, "wamid.termo.%d" % envio_id)).fetchone()["id"]


def _janela_do_contato(cfg, quando=AGORA - timedelta(hours=1)):
    """O contato escreveu ao numero da empresa ha uma hora: a janela de 24 h dele esta aberta."""
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo, recebido_em, processado_em)
                       VALUES ('wamid.contato', 'mensagem', %s::jsonb, %s, %s)""",
                    ('{"msg": {"from": "554991505565", "timestamp": "%d"}}' % int(quando.timestamp()), quando, quando))


def _escrever(cfg, s, corpo="Quais são todos os meus lotes de centeio e aveia?", wamid="wamid.p1", agora=AGORA,
              numero=PRODUTOR_META, msg=None):
    m = msg or na_hora(texto(wamid, corpo, numero=numero), agora)
    R.gravar(cfg, aviso([m], numero=numero, bsuid="BR." + numero, nome="Alfonso"))
    R.processar_pendentes(cfg, s, None, agora=agora)


def _resumos(cfg, prefixo="aviso de contrato"):
    with conexao(cfg) as con:
        return [r["resumo"] for r in con.execute(
            "SELECT resumo FROM atendimento.enviadas WHERE resumo LIKE %s ORDER BY id", (prefixo + "%",))]


# ── passo 1: a migracao ─────────────────────────────────────────────────────────

def test_1_a_migracao_nasce_desligada_e_a_volta_desfaz(cfg):
    with conexao(cfg) as con:
        aj = {r["chave"]: r["valor"] for r in con.execute(
            "SELECT chave, valor FROM atendimento.ajustes WHERE chave LIKE 'cooperante.%'")}
        maicon = con.execute("SELECT id FROM atendimento.destinos WHERE nome = 'Maicon Gregory'").fetchone()["id"]
    assert aj["cooperante.resposta_padrao"] is False and aj["cooperante.dias"] == 7
    assert aj["cooperante.destino"] == maicon
    assert "{saudacao}, {nome}!" in aj["cooperante.texto"] and "{contato}" in aj["cooperante.texto"]
    volta = (migracoes.PASTA / "073_resposta_ao_cooperante_VOLTA.sql").read_text(encoding="utf-8")
    with conexao(cfg) as con:
        con.execute(volta)
        assert not con.execute("SELECT 1 FROM atendimento.ajustes WHERE chave LIKE 'cooperante.%'").fetchone()
        assert cooperante.ligado(con) is False
    assert migracoes.aplicar(cfg) == ["073_resposta_ao_cooperante.sql"]


def test_1_sem_o_destino_do_contato_a_migracao_falha_com_mensagem(cfg):
    import psycopg
    ida = (migracoes.PASTA / "073_resposta_ao_cooperante.sql").read_text(encoding="utf-8")
    with conexao(cfg) as con:
        con.execute((migracoes.PASTA / "073_resposta_ao_cooperante_VOLTA.sql").read_text(encoding="utf-8"))
        con.execute("UPDATE atendimento.destinos SET nome = 'Outro' WHERE nome = 'Maicon Gregory'")
        with pytest.raises(psycopg.errors.RaiseException, match="Maicon Gregory"):
            con.execute(ida)


# ── passo 2: o desvio ───────────────────────────────────────────────────────────

def test_2_com_aviso_recente_sai_o_texto_e_o_cartao_e_o_portao_nao_e_chamado(ligado, portao):
    _termo(ligado)
    s = SaidaFalsa()
    _escrever(ligado, s)
    para_ele = [x for x in s.enviadas if x[1] == PRODUTOR_META]
    assert [x[0] for x in para_ele] == ["texto", "contato"]
    assert para_ele[0][2] == (
        "Bom dia, Alfonso! Essa mensagem foi um envio automático do nosso sistema, que passou a informar os "
        "andamentos do seu contrato de multiplicação de sementes. Aos poucos todas as etapas vão chegar por "
        "aqui. Eu não tenho os detalhes do seu contrato; quem atende na empresa é o Maicon. Segue o contato dele.")
    assert para_ele[1][2] == "Maicon Gregory" and para_ele[1][3] == [CONTATO]
    assert portao == []
    assert _resumos(ligado)[:2] == [PADRAO % "0001/2026", "aviso de contrato: cartao (termo 0001/2026)"]


@pytest.mark.parametrize("hora_utc, saudacao", [(11, "Bom dia"), (16, "Boa tarde"), (22, "Boa noite"), (3, "Boa noite")])
def test_2_a_saudacao_pela_hora_de_brasilia(hora_utc, saudacao):
    assert cooperante.saudacao(AGORA.replace(hour=hora_utc)) == saudacao


def test_2_sem_aviso_tudo_como_hoje(ligado, portao):
    s = SaidaFalsa()
    _escrever(ligado, s)
    assert portao == ["wamid.p1"] and _resumos(ligado) == []


def test_2_aviso_de_mais_de_7_dias_tudo_como_hoje(ligado, portao):
    _termo(ligado, enviado=AGORA - timedelta(days=7, minutes=1))
    _escrever(ligado, SaidaFalsa())
    assert portao == ["wamid.p1"] and _resumos(ligado) == []


def test_2_aviso_que_falhou_nao_conta(ligado, portao):
    _termo(ligado, estado="falhou")
    _escrever(ligado, SaidaFalsa())
    assert portao == ["wamid.p1"] and _resumos(ligado) == []


def test_2_chave_desligada_tudo_como_hoje(cfg, portao):
    c = replace(cfg, responde=True)
    _termo(c)
    _escrever(c, SaidaFalsa())
    assert portao == ["wamid.p1"] and _resumos(c) == []


def test_2_o_toque_ciente_continua_no_termo(ligado, portao):
    termo_id = _termo(ligado)
    s = SaidaFalsa()
    msg = {"from": PRODUTOR_META, "id": "wamid.toque", "timestamp": str(int(AGORA.timestamp())), "type": "button",
           "context": {"from": "554936640121", "id": "wamid.termo.41"},
           "button": {"payload": "termo:ciente:%d" % termo_id, "text": "Recebi e estou ciente"}}
    _escrever(ligado, s, msg=msg)
    with conexao(ligado) as con:
        assert con.execute("SELECT ciencia_em FROM atendimento.termos_reprovacao WHERE id = %s",
                           (termo_id,)).fetchone()["ciencia_em"]
    assert _resumos(ligado) == [] and portao == []
    assert any(x[0] == "texto" and "0001/2026" in x[2] for x in s.enviadas)   # a confirmacao do termo


def test_2_toque_de_menu_segue_o_menu(ligado, portao):
    _termo(ligado)
    s = SaidaFalsa()
    msg = {"from": PRODUTOR_META, "id": "wamid.menu", "timestamp": str(int(AGORA.timestamp())), "type": "interactive",
           "context": {"from": "554936640121", "id": "wamid.nosso"},
           "interactive": {"type": "button_reply", "button_reply": {"id": "menu:qualidade", "title": "Qualidade"}}}
    _escrever(ligado, s, msg=msg)
    assert _resumos(ligado) == []


def test_2_erro_no_desvio_segue_o_caminho_de_hoje(ligado, portao, monkeypatch):
    _termo(ligado)

    def quebra(*a, **k):
        raise RuntimeError("banco fora")
    monkeypatch.setattr(cooperante, "aviso_de_contrato_recente", quebra)
    _escrever(ligado, SaidaFalsa())
    assert portao == ["wamid.p1"]


# ── passo 3: o aviso ao contato ─────────────────────────────────────────────────

def test_3_janela_aberta_o_contato_recebe_o_texto_com_o_link(ligado, portao):
    _termo(ligado)
    _janela_do_contato(ligado)
    s = SaidaFalsa()
    _escrever(ligado, s)
    (rep,) = [x for x in s.enviadas if x[1] == CONTATO]
    assert rep[0] == "texto"
    assert rep[2].startswith("*Cooperante respondeu ao aviso*")
    assert "Alfonso Adriano Sleutjes E Outra" in rep[2] and "termo de reprovação 0001/2026" in rep[2]
    assert "Quais são todos os meus lotes de centeio e aveia?" in rep[2]
    assert "https://wa.me/%s" % PRODUTOR_META in rep[2]
    assert _resumos(ligado)[-1] == "aviso de contrato: repasse ao contato (termo 0001/2026)"


def test_3_janela_fechada_o_contato_recebe_o_modelo_numa_linha(ligado, portao):
    _termo(ligado)
    s = SaidaFalsa()
    _escrever(ligado, s)
    (m,) = [x for x in s.modelos if x["para"] == CONTATO]
    assert m["nome"] == "olivia_resumo"
    (linha,) = m["corpo"]
    assert linha.startswith("cooperante respondeu ao aviso do contrato: Alfonso")
    assert "\n" not in linha and "  " not in linha and linha.endswith("telefone +55 14 9603-3466.")


def test_3_saida_que_falha_no_repasse_nao_segura_a_resposta(ligado, portao):
    _termo(ligado)
    s = SaidaFalsa()
    s.modelo_falha = "131047 fora da janela"
    _escrever(ligado, s)
    assert [x[0] for x in s.enviadas if x[1] == PRODUTOR_META] == ["texto", "contato"]
    assert portao == []
    assert "aviso de contrato: repasse ao contato (termo 0001/2026)" not in _resumos(ligado)


def test_3_audio_conta_como_mensagem_e_vai_o_tipo(ligado, portao):
    _termo(ligado)
    _janela_do_contato(ligado)
    s = SaidaFalsa()
    msg = {"from": PRODUTOR_META, "id": "wamid.audio", "timestamp": str(int(AGORA.timestamp())), "type": "audio",
           "audio": {"id": "midia.1", "mime_type": "audio/ogg"}}
    _escrever(ligado, s, msg=msg)
    assert [x[0] for x in s.enviadas if x[1] == PRODUTOR_META] == ["texto", "contato"]
    (rep,) = [x for x in s.enviadas if x[1] == CONTATO]
    assert "Escreveu: (mandou um áudio)" in rep[2]


# ── passo 4: uma vez por aviso ──────────────────────────────────────────────────

def test_4_tres_mensagens_uma_resposta_padrao_duas_linhas_curtas_tres_repasses(ligado, portao):
    _termo(ligado)
    _janela_do_contato(ligado)
    s = SaidaFalsa()
    for i in range(3):
        _escrever(ligado, s, corpo="mensagem %d" % i, wamid="wamid.p%d" % i, agora=AGORA + timedelta(minutes=i))
    para_ele = [x for x in s.enviadas if x[1] == PRODUTOR_META]
    assert [x[0] for x in para_ele] == ["texto", "contato", "texto", "texto"]
    assert para_ele[2][2] == para_ele[3][2] == (
        "Alfonso, o Maicon já foi avisado da sua mensagem; o contato dele está logo acima.")
    assert len([x for x in s.enviadas if x[1] == CONTATO]) == 3
    assert _resumos(ligado).count(PADRAO % "0001/2026") == 1
    assert portao == []


def test_4_um_aviso_novo_reinicia_a_contagem(ligado, portao):
    _termo(ligado)
    s = SaidaFalsa()
    _escrever(ligado, s, wamid="wamid.p1")
    _termo(ligado, numero_termo="0002/2026", envio_id=42, enviado=AGORA + timedelta(hours=1))
    _escrever(ligado, s, wamid="wamid.p2", agora=AGORA + timedelta(hours=2))
    assert _resumos(ligado, "aviso de contrato: resposta padrao") == [PADRAO % "0001/2026", PADRAO % "0002/2026"]


# ── passo 5: o script e a saude ─────────────────────────────────────────────────

def test_5_o_script_liga_desliga_mostra_e_recusa_sem_o_ajuste(cfg, capsys):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "script_cooperante", Path(__file__).resolve().parent.parent / "scripts" / "cooperante.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    with conexao(cfg) as con:
        assert script.rodar(con, "ligar") == 0 and cooperante.ligado(con)
        assert "LIGADA" in capsys.readouterr().out
        assert script.rodar(con, "desligar") == 0 and not cooperante.ligado(con)
        assert script.rodar(con, "mostrar") == 0
        out = capsys.readouterr().out
        assert "desligada" in out and "7 dias" in out and "Maicon Gregory" in out and "{saudacao}" in out
        assert script.rodar(con, "outro") == 2
        con.execute("DELETE FROM atendimento.ajustes WHERE chave LIKE 'cooperante.%'")
        assert script.rodar(con, "ligar") == 1 and script.rodar(con, "mostrar") == 1
        assert "RECUSADO" in capsys.readouterr().out


def test_5_a_saude_diz_a_chave(ligado):
    from fastapi.testclient import TestClient
    with TestClient(R.criar_app(ligado, saida=SaidaFalsa(), trabalhador=False)) as t:
        assert t.get("/saude").json()["cooperante_resposta"] == "ligada"
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'cooperante.resposta_padrao'")
    with TestClient(R.criar_app(ligado, saida=SaidaFalsa(), trabalhador=False)) as t:
        assert t.get("/saude").json()["cooperante_resposta"] == "desligada"
