"""#1238, passos 3 a 7: o roteador com contexto por contato. O retrato dos cinco fios, o texto levado ao fio
certo, a duvida por botao, o "nenhum" que devolve a corrente, a correcao escrita e a carencia.
Meta, IA e ERP falsos; banco de teste."""
import json
import re
from datetime import timedelta

import pytest

from backend import pendencias, pendencias_erp, roteador
from backend.banco import conexao
from tests.avisos_meta import texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa
from tests.test_campo import AGORA, EQUIPE, canal, foto, ligar, passo  # noqa: F401 -- `canal` e fixture

BSUID = "BR.equipe"
MIN = timedelta(minutes=1)
PLANTAGRO = {"codigo": 4655, "nome": "PLANTAGRO", "cidade": "TANGARÁ", "uf": "SC", "faixa": "A", "contato": {}}


class Aponta(IAFalsa):
    """A OlivIA falsa que aponta o assunto PELO ROTULO (o numero muda com a ordem do retrato)."""

    def __init__(self, *respostas):
        super().__init__()
        self.fila = list(respostas)

    def rotear(self, retrato):
        self.retratos = getattr(self, "retratos", []) + [retrato]
        r = dict(self.fila.pop(0)) if self.fila else {"destino": "nenhum"}
        numeros = dict((rot, n) for n, rot in re.findall(r"^(\d+)\. (.*?) — ", retrato["texto"], re.M))
        for campo_ in ("destino", "destino_certo"):
            alvo = r.get(campo_)
            if alvo and alvo not in ("nenhum", "correcao"):
                r[campo_] = next((n for rot, n in numeros.items() if rot.startswith(alvo)), "nenhum")
        return {"destino": r.get("destino", "nenhum"), "confianca": r.get("confianca", "alta"),
                "sinal": r.get("sinal", "nomeado"), "destino_certo": r.get("destino_certo", "nenhum")}


@pytest.fixture
def casa(canal):
    ligar(canal)
    with conexao(canal) as con:
        for chave, valor in (("pendencias.ligado", "true"), ("pendencias.juntar_minutos", "0"),
                             ("roteador.ligado", "true")):
            con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = %s", (valor, chave))
    return canal


def chamado(cfg, n=1222, evento=1, quando=AGORA - 30 * MIN, titulo="Chamado no WhatsApp"):
    with conexao(cfg) as con:
        pendencias_erp.receber(con, [{"evento_id": evento, "demanda_id": n, "titulo": titulo, "numero": EQUIPE,
                                      "classe": "pergunta", "texto": "Ficou claro o passo 3?"}], quando)
        con.execute("""UPDATE atendimento.pendencias_mensagens SET estado = 'enviada', wamid = %s, enviada_em = %s
                        WHERE origem_evento_id = %s""", ("wamid.pend.%d" % evento, quando, evento))
        return con.execute("SELECT id FROM atendimento.pendencias WHERE referencia = %s", (str(n),)).fetchone()["id"]


def foto_aberta(cfg, s, quando=AGORA - 10 * MIN, wamid="wf1"):
    passo(cfg, s, foto(wamid), agora=quando)
    with conexao(cfg) as con:
        return con.execute("SELECT grupo_id FROM atendimento.material_de_campo WHERE wamid = %s", (wamid,)).fetchone()["grupo_id"]


def logo_esperando(cfg, quando=AGORA - 20 * MIN):
    with conexao(cfg) as con:
        return con.execute("""INSERT INTO atendimento.logos_de_cliente (bsuid, wa_id, wamid, nome_arquivo, formato,
                                  pergunta_pendente, recebida_em) VALUES (%s, %s, 'wl1', 'logo.pdf', 'pdf', 'erp_codigo', %s)
                              RETURNING id""", (BSUID, EQUIPE, quando)).fetchone()["id"]


def cliente_aberto(cfg, quando=AGORA - 40 * MIN):
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.clientes_consultores (wa_id, comercial_id, nome) VALUES (%s, 42, 'Maicon')
                       ON CONFLICT (wa_id) DO UPDATE SET comercial_id = 42, ativo = true""", (EQUIPE,))
        return con.execute("""INSERT INTO atendimento.clientes_registros (wa_id, para, comercial_id, codigo, ficha, criado_em)
                              VALUES (%s, %s, 42, 4655, %s, %s) RETURNING id""",
                           (EQUIPE, EQUIPE, json.dumps(PLANTAGRO), quando)).fetchone()["id"]


def curriculo(cfg, quando=AGORA - 50 * MIN):
    with conexao(cfg) as con:
        return con.execute("""INSERT INTO atendimento.candidaturas (fran_para, nome_perfil, feedback, feedback_em,
                                  espera_comentario, apagar_em) VALUES (%s, 'Joana', 'errada', %s, true, %s) RETURNING id""",
                           (EQUIPE, quando, AGORA + timedelta(days=365))).fetchone()["id"]


def escreve(cfg, s, ia, corpo, agora=AGORA, wamid=None):
    passo(cfg, s, texto(wamid or "wt.%s" % agora.timestamp(), corpo, numero=EQUIPE), agora=agora, ia=ia)


def toca(cfg, s, ia, id_opcao, agora=AGORA + MIN):
    passo(cfg, s, toque("wq.%s" % id_opcao, id_opcao, numero=EQUIPE), agora=agora, ia=ia)


def linhas(cfg):
    with conexao(cfg) as con:
        return [dict(r) for r in con.execute("SELECT * FROM atendimento.roteador ORDER BY id").fetchall()]


def entrou(cfg):
    with conexao(cfg) as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM atendimento.pendencias_mensagens WHERE sentido = 'entrou' ORDER BY id").fetchall()]


def grupo(cfg, gid):
    with conexao(cfg) as con:
        return dict(con.execute("SELECT * FROM atendimento.material_de_campo WHERE id = %s", (gid,)).fetchone())


# ── passo 3: o retrato ─────────────────────────────────────────────────────────────────────────────────

def test_o_retrato_tem_os_cinco_fios_com_trecho_e_tempo(casa):
    s = SaidaFalsa()
    chamado(casa)
    gid = foto_aberta(casa, s)
    logo_esperando(casa)
    cliente_aberto(casa)
    curriculo(casa)
    with conexao(casa) as con:
        a = roteador.assuntos_abertos(con, EQUIPE, BSUID, AGORA)
    assert [x.fio for x in a] == ["foto", "logo", "chamado", "cliente", "curriculo"]   # do mais recente
    assert a[0].chave == "foto:%d" % gid and a[0].rotulo.startswith("Foto de ") and a[0].ha_segundos == 600
    assert "esperando a legenda" in a[0].ultimo_trecho or "perguntamos" in a[0].ultimo_trecho
    assert a[2].rotulo == "Chamado 1222 · Chamado no WhatsApp" and "Ficou claro o passo 3?" in a[2].ultimo_trecho
    assert a[3].rotulo.startswith("Cliente PLANTAGRO") and a[4].rotulo == "Currículo de Joana"


def test_o_retrato_monta_os_tres_blocos_e_o_historico_para_em_20(casa):
    s = SaidaFalsa()
    chamado(casa)
    for i in range(25):
        passo(casa, s, texto("wh%d" % i, "linha %d" % i, numero=EQUIPE), agora=AGORA - timedelta(hours=2) + i * MIN)
    with conexao(casa) as con:
        hist = roteador.historico(con, EQUIPE, AGORA)
        from backend import motor
        e = motor.Entrada(wamid="wnovo", pessoa=motor.Pessoa(BSUID, EQUIPE, "Maicon"), texto="ok recebi")
        r = roteador.montar_retrato(con, e, roteador.assuntos_abertos(con, EQUIPE, BSUID, AGORA), AGORA)
    assert len(hist) == 20 and hist[-1][1:] == ("ela", "linha 24") and hist[0][2] == "linha 5"
    assert r["numeros"] == ["1"] and r["pode_corrigir"] is False
    t = r["texto"]
    assert "ASSUNTOS ABERTOS" in t and "1. Chamado 1222" in t and "AS ÚLTIMAS 24 H" in t
    assert "<mensagem>\nok recebi\n</mensagem>" in t and "depois da última mensagem nossa" in t


# ── passo 4: o destino no fio, a duvida, o nenhum ────────────────────────────────────────────────────

def test_o_texto_vai_ao_chamado_com_a_carencia(casa):
    s = SaidaFalsa()
    chamado(casa)
    cliente_aberto(casa)
    ia = Aponta({"destino": "Chamado 1222", "sinal": "proximidade"})
    escreve(casa, s, ia, "Ok, recebi")
    m = entrou(casa)
    assert len(m) == 1 and m[0]["texto"] == "Ok, recebi" and m[0]["estado"] == "a_entregar"
    assert m[0]["entregar_apos"] == AGORA + timedelta(minutes=3)
    assert s.ultima[2] == "Anotado no chamado 1222. ✓"
    r = linhas(casa)[-1]
    assert r["aplicado"] and r["sinal"] == "proximidade" and r["destino"].startswith("chamado:")
    with conexao(casa) as con:   # o cliente aberto nao recebeu nada
        assert con.execute("SELECT textos FROM atendimento.clientes_registros").fetchone()["textos"] == ""


def test_o_texto_vai_a_foto_aberta_ha_mais_de_2_min(casa):
    s = SaidaFalsa()
    chamado(casa)
    gid = foto_aberta(casa, s)
    escreve(casa, s, Aponta({"destino": "Foto"}), "centeio florindo na área 3")
    assert "centeio florindo" in grupo(casa, gid)["legenda"]
    assert entrou(casa) == []


def test_o_texto_vai_a_logo_ao_cliente_e_ao_curriculo(casa):
    s = SaidaFalsa()
    lid = logo_esperando(casa)
    rid = cliente_aberto(casa)
    cid = curriculo(casa)
    escreve(casa, s, Aponta({"destino": "Logo"}), "Plantagro", agora=AGORA)
    escreve(casa, s, Aponta({"destino": "Cliente PLANTAGRO"}), "liguei, quer preço do +Palha", agora=AGORA + MIN)
    escreve(casa, s, Aponta({"destino": "Currículo"}), "ela não viu a cidade", agora=AGORA + 2 * MIN)
    with conexao(casa) as con:
        assert con.execute("SELECT cliente_dito FROM atendimento.logos_de_cliente WHERE id = %s", (lid,)).fetchone()["cliente_dito"] == "Plantagro"
        assert "quer preço" in con.execute("SELECT textos FROM atendimento.clientes_registros WHERE id = %s", (rid,)).fetchone()["textos"]
        c = con.execute("SELECT * FROM atendimento.candidaturas WHERE id = %s", (cid,)).fetchone()
        assert c["feedback_texto"] == "ela não viu a cidade" and not c["espera_comentario"]
    assert [r["aplicado"] for r in linhas(casa)] == [True, True, True]


def test_na_duvida_os_botoes_e_o_sim_entra_sem_carencia(casa):
    s = SaidaFalsa()
    chamado(casa)
    cliente_aberto(casa)
    ia = Aponta({"destino": "Chamado 1222", "confianca": "baixa"})
    escreve(casa, s, ia, "blz, legal.")
    assert s.ultima[0] == "botoes" and s.ultima[2] == "É sobre Chamado 1222 · Chamado no WhatsApp?"
    rid = linhas(casa)[-1]["id"]
    assert [o[0] for o in s.ultima[3]] == ["rot:sim:%d" % rid, "rot:lista:%d" % rid, "rot:outro:%d" % rid]
    assert entrou(casa) == []
    toca(casa, s, ia, "rot:sim:%d" % rid)
    m = entrou(casa)
    assert m[0]["texto"] == "blz, legal." and m[0]["entregar_apos"] is None
    assert linhas(casa)[-1]["sinal"] == "botao"


def test_nenhum_com_dois_assuntos_manda_a_lista_e_outro_assunto_devolve_a_corrente(casa):
    s = SaidaFalsa()
    chamado(casa)
    gid = foto_aberta(casa, s)
    ia = Aponta({"destino": "nenhum", "sinal": "nenhum"})
    escreve(casa, s, ia, "a reunião é às 15h")
    assert s.ultima[0] == "lista"
    rid = linhas(casa)[-1]["id"]
    assert ("rot:outro:%d" % rid, "Outro assunto") in s.ultima[3]
    toca(casa, s, ia, "rot:outro:%d" % rid)
    # a corrente de sempre: com a foto aberta, o texto solto e a legenda dela
    assert "a reunião é às 15h" in grupo(casa, gid)["legenda"]
    assert entrou(casa) == []


def test_a_lista_escolhe_o_assunto(casa):
    s = SaidaFalsa()
    pid = chamado(casa)
    foto_aberta(casa, s)
    ia = Aponta({"destino": "nenhum", "sinal": "nenhum"})
    escreve(casa, s, ia, "pode fechar")
    rid = linhas(casa)[-1]["id"]
    toca(casa, s, ia, "rot:para:%d:chamado:%d" % (rid, pid))
    assert entrou(casa)[0]["texto"] == "pode fechar" and linhas(casa)[-1]["aplicado"]


def test_nenhum_com_um_assunto_segue_a_corrente(casa):
    s = SaidaFalsa()
    chamado(casa)
    ia = Aponta({"destino": "nenhum", "sinal": "nenhum"})
    escreve(casa, s, ia, "vou almoçar")
    r = linhas(casa)[-1]
    assert r["destino"] is None and not r["aplicado"]
    assert s.ultima[2].startswith("É sobre o Chamado 1222")   # a oferta de hoje, sem mudar


def test_sem_assunto_aberto_nem_pergunta_a_olivia(casa):
    s, ia = SaidaFalsa(), Aponta()
    escreve(casa, s, ia, "vou almoçar")
    assert getattr(ia, "retratos", []) == [] and linhas(casa) == []


# ── passo 5: a correcao escrita ──────────────────────────────────────────────────────────────────────

def test_a_correcao_tira_do_chamado_na_carencia_e_leva_a_foto(casa):
    s = SaidaFalsa()
    pid = chamado(casa)
    gid = foto_aberta(casa, s)
    ia = Aponta({"destino": "Chamado 1222"},
                {"destino": "correcao", "sinal": "correcao", "destino_certo": "Foto"})
    escreve(casa, s, ia, "trigo na Linha Bonita")
    escreve(casa, s, ia, "não, era sobre a foto", agora=AGORA + MIN)
    assert ia.retratos[1]["pode_corrigir"] is True
    m = entrou(casa)
    assert m[0]["estado"] == "descartada"
    with conexao(casa) as con:
        assert con.execute("SELECT espera FROM atendimento.pendencias WHERE id = %s", (pid,)).fetchone()["espera"] == "resposta"
    assert "trigo na Linha Bonita" in grupo(casa, gid)["legenda"]
    a, b = linhas(casa)
    assert a["corrigido_em"] is not None and b["sinal"] == "correcao" and b["destino"] == "foto:%d" % gid
    assert any(x[2].startswith("Certo, tirei de Chamado 1222") for x in s.enviadas)


def test_a_correcao_do_que_ja_foi_ao_erp_vira_segundo_comentario(casa):
    s = SaidaFalsa()
    chamado(casa)
    cliente_aberto(casa)
    ia = Aponta({"destino": "Chamado 1222"}, {"destino": "correcao", "sinal": "correcao", "destino_certo": "Cliente"})
    escreve(casa, s, ia, "quer preço")
    with conexao(casa) as con:
        con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'entregue' WHERE sentido = 'entrou'")
    escreve(casa, s, ia, "isso era do cliente", agora=AGORA + 2 * MIN)
    m = entrou(casa)
    assert [x["estado"] for x in m] == ["entregue", "a_entregar"] and m[1]["texto"] == roteador.NAO_ERA
    with conexao(casa) as con:
        assert "quer preço" in con.execute("SELECT textos FROM atendimento.clientes_registros").fetchone()["textos"]


def test_a_correcao_devolve_a_legenda_da_foto_o_cliente_e_a_logo(casa):
    s = SaidaFalsa()
    gid = foto_aberta(casa, s)
    rid = cliente_aberto(casa)
    lid = logo_esperando(casa)
    ia = Aponta({"destino": "Foto"}, {"destino": "correcao", "sinal": "correcao", "destino_certo": "Cliente"},
                {"destino": "correcao", "sinal": "correcao", "destino_certo": "Logo"},
                {"destino": "correcao", "sinal": "correcao"})
    escreve(casa, s, ia, "Plantagro")
    assert grupo(casa, gid)["legenda"] == "Plantagro"
    escreve(casa, s, ia, "era do cliente", agora=AGORA + MIN)
    assert grupo(casa, gid)["legenda"] == ""
    escreve(casa, s, ia, "não, da logo", agora=AGORA + 2 * MIN)
    with conexao(casa) as con:
        assert con.execute("SELECT textos FROM atendimento.clientes_registros WHERE id = %s", (rid,)).fetchone()["textos"] == ""
        assert con.execute("SELECT cliente_dito FROM atendimento.logos_de_cliente WHERE id = %s", (lid,)).fetchone()["cliente_dito"] == "Plantagro"
    escreve(casa, s, ia, "esquece, não era da logo", agora=AGORA + 3 * MIN)
    with conexao(casa) as con:
        l = con.execute("SELECT * FROM atendimento.logos_de_cliente WHERE id = %s", (lid,)).fetchone()
    assert l["cliente_dito"] == "" and l["pergunta_pendente"] == "erp_codigo"


def test_correcao_sem_encaminhamento_recente_vira_nenhum(casa):
    s = SaidaFalsa()
    chamado(casa)
    cliente_aberto(casa)
    ia = Aponta({"destino": "Chamado 1222"}, {"destino": "correcao", "sinal": "correcao"})
    escreve(casa, s, ia, "ok")
    escreve(casa, s, ia, "não era isso", agora=AGORA + 11 * MIN)
    assert ia.retratos[1]["pode_corrigir"] is False
    r = linhas(casa)[-1]
    assert r["sinal"] == "nenhum" and r["destino"] is None and linhas(casa)[0]["corrigido_em"] is None


# ── passo 6: o degrau no motor ───────────────────────────────────────────────────────────────────────

def test_ponta_a_ponta_a_plantagro_quer_preco(casa):
    s = SaidaFalsa()
    chamado(casa)
    gid = foto_aberta(casa, s)
    rid = cliente_aberto(casa)
    ia = Aponta({"destino": "Cliente PLANTAGRO", "sinal": "nomeado"})
    escreve(casa, s, ia, "a Plantagro quer preço")
    with conexao(casa) as con:
        assert con.execute("SELECT textos FROM atendimento.clientes_registros WHERE id = %s", (rid,)).fetchone()["textos"] == "a Plantagro quer preço"
    assert grupo(casa, gid)["legenda"] == "" and entrou(casa) == []
    assert [r["sinal"] for r in linhas(casa)] == ["nomeado"]
    assert len(ia.retratos[0]["numeros"]) == 3


def test_foto_de_ate_2_min_vence_sem_perguntar_a_olivia(casa):
    s = SaidaFalsa()
    chamado(casa)
    gid = foto_aberta(casa, s, quando=AGORA - timedelta(seconds=26))
    ia = Aponta({"destino": "Chamado 1222"})
    escreve(casa, s, ia, "colheita do centeio")
    assert "colheita do centeio" in grupo(casa, gid)["legenda"] and entrou(casa) == []
    assert getattr(ia, "retratos", []) == []
    r = linhas(casa)[-1]
    assert r["sinal"] == "proximidade" and r["aplicado"]


def test_chave_desligada_nada_muda_de_caminho(casa):
    with conexao(casa) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'roteador.ligado'")
    s = SaidaFalsa()
    chamado(casa)
    ia = Aponta({"destino": "Chamado 1222"})
    escreve(casa, s, ia, "Ok, recebi")
    assert getattr(ia, "retratos", []) == [] and linhas(casa) == []
    assert s.ultima[2].startswith("É sobre o Chamado 1222")


def test_citacao_nao_passa_pelo_roteador(casa):
    s = SaidaFalsa()
    chamado(casa)
    ia = Aponta({"destino": "nenhum"})
    m = dict(texto("wc1", "sim, ficou", numero=EQUIPE), context={"from": "554936640121", "id": "wamid.pend.1"})
    passo(casa, s, m, ia=ia)
    assert getattr(ia, "retratos", []) == [] and entrou(casa)[0]["entregar_apos"] is None


# ── passo 7: a carencia nas telas ────────────────────────────────────────────────────────────────────

class Erp:
    def __init__(self):
        self.respostas = []

    def trazer(self, cfg, depois):
        return {"linhas": [], "cursor": 100, "token": "t"}

    def estado(self, cfg, token, ids):
        return []

    def responder(self, cfg, token, demanda_id, numero, texto):
        self.respostas.append(texto)

    def validar(self, *a):
        pass


def test_a_volta_das_telas_espera_a_carencia(casa):
    from dataclasses import replace
    cfg = replace(casa, erp_segredo="segredo-de-teste")
    pid = chamado(casa)
    s = SaidaFalsa()
    with conexao(casa) as con:
        p = pendencias.pendencia(con, pid, EQUIPE)
        pendencias.anotar_resposta(con, s, EQUIPE, p, "com carencia", AGORA, entregar_apos=AGORA + 3 * MIN)
        pendencias.anotar_resposta(con, s, EQUIPE, p, "por citacao", AGORA)
    e = Erp()
    for agora in (AGORA, AGORA + MIN):
        pendencias_erp.volta(cfg, trazer=e.trazer, estado=e.estado, responder=e.responder, validar=e.validar, agora=agora)
    assert e.respostas == ["por citacao"]
    pendencias_erp.volta(cfg, trazer=e.trazer, estado=e.estado, responder=e.responder, validar=e.validar,
                         agora=AGORA + 3 * MIN)
    assert e.respostas == ["por citacao", "com carencia"]
