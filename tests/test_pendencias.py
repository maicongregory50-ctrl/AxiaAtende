"""#1222: o chamado no WhatsApp. O ERP manda o que chega ao autor (as TELAS gravam), o recepcionista
manda pela Meta (juncao, janela, reabertura) e le a resposta (citada, toque, OlivIA); as TELAS levam a
resposta ao ERP. Meta e ERP falsos."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import count

import pytest

from backend import erp, migracoes, motor, pendencias, pendencias_erp
from backend.banco import conexao
from backend.envio import Envio
from tests.saida_falsa import IAFalsa, SaidaFalsa

AGORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
FRAN = "5549999330003"          # como o ERP guarda: com o 9
FRAN_META = "554999330003"      # como a Meta manda: sem o 9
_WAMIDS = count(1)


def saida():
    s = SaidaFalsa()
    s._n = _WAMIDS
    return s


@pytest.fixture
def ligado(cfg):
    c = replace(cfg, erp_segredo="segredo-de-teste", porteiro=True, responde=True)
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'pendencias.ligado'")
        con.execute("UPDATE atendimento.ajustes SET valor = '0'::jsonb WHERE chave = 'pendencias.juntar_minutos'")
    return c


def linha(evento, classe, texto="Fran, a lista sai sem saldo?", demanda=350, titulo="Auditoria de estoque"):
    return {"evento_id": evento, "demanda_id": demanda, "titulo": titulo, "numero": FRAN, "classe": classe,
            "texto": texto, "criado_em": AGORA.isoformat()}


class ErpFalso:
    def __init__(self, linhas=(), cursor=100):
        self.linhas, self.cursor = list(linhas), cursor
        self.respostas, self.validacoes, self.pedidos = [], [], []
        self.recusar = False
        self.demandas = []

    def trazer(self, cfg, depois):
        self.pedidos.append(depois)
        linhas, self.linhas = (self.linhas, []) if depois is not None else ([], self.linhas)
        return {"linhas": linhas, "cursor": self.cursor, "token": "t"}

    def estado(self, cfg, token, ids):
        return self.demandas

    def responder(self, cfg, token, demanda_id, numero, texto):
        if self.recusar:
            raise erp.ErpRecusou("Este número não é o WhatsApp de quem abriu o chamado.")
        self.respostas.append((demanda_id, numero, texto))

    def validar(self, cfg, token, demanda_id, numero, resultado, motivo):
        self.validacoes.append((demanda_id, numero, resultado, motivo))


def volta(cfg, e, agora=AGORA):
    return pendencias_erp.volta(cfg, trazer=e.trazer, estado=e.estado, responder=e.responder,
                                validar=e.validar, agora=agora)


def receber(cfg, linhas):
    """Liga o cursor e traz as linhas: a primeira volta so guarda o cursor."""
    e = ErpFalso(linhas)
    volta(cfg, e)
    volta(cfg, e)
    return e


def falou(cfg, quando, numero=FRAN_META):
    corpo = {"contacts": [{"wa_id": numero, "user_id": "BR.f"}],
             "msg": {"from": numero, "id": "wamid.f.%s" % quando.timestamp(), "type": "text", "text": {"body": "oi"}}}
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo, recebido_em, processado_em)
                       VALUES (%s, 'mensagem', %s, %s, %s)""", (corpo["msg"]["id"], json.dumps(corpo), quando, quando))


def mandar(cfg, agora=AGORA):
    s = saida()
    with conexao(cfg) as con:
        pendencias.mandar(con, s, agora)
    return s


def chega(cfg, s, texto=None, toque=None, contexto=None, ia=None):
    e = motor.Entrada(wamid="wamid.in.%d" % next(_WAMIDS), tipo="interactive" if toque else "text",
                      pessoa=motor.Pessoa(bsuid="BR.f", wa_id=FRAN_META, nome="Fran"),
                      texto=texto, toque=toque, contexto=contexto)
    with conexao(cfg) as con:
        motor.tratar(con, s, ia, e, AGORA, Envio(), None)


def mensagens(cfg, sentido=None):
    with conexao(cfg) as con:
        return [dict(m) for m in con.execute(
            "SELECT * FROM atendimento.pendencias_mensagens WHERE sentido = coalesce(%s, sentido) ORDER BY id",
            (sentido,)).fetchall()]


def pendencia(cfg):
    with conexao(cfg) as con:
        return dict(con.execute("SELECT * FROM atendimento.pendencias ORDER BY id LIMIT 1").fetchone())


# ── a migracao e a chave ─────────────────────────────────────────────────────

def test_nasce_desligado_e_desligado_nada_anda(cfg):
    c = replace(cfg, erp_segredo="segredo-de-teste")
    with conexao(c) as con:
        assert pendencias.ligado(con) is False
    e = ErpFalso([linha(101, "pergunta")])
    assert volta(c, e) == {"desligado": True} and e.pedidos == []


def test_a_volta_da_052_desfaz_e_a_ida_reaplica(cfg):
    with conexao(cfg) as con:
        con.execute((migracoes.PASTA / "052_pendencias_VOLTA.sql").read_text(encoding="utf-8"))
        assert con.execute("SELECT to_regclass('atendimento.pendencias') AS t").fetchone()["t"] is None
    assert migracoes.aplicar(cfg) == ["052_pendencias.sql"]


# ── do ERP para a fila ───────────────────────────────────────────────────────

def test_a_primeira_volta_so_guarda_o_cursor(ligado):
    e = ErpFalso([linha(101, "pergunta")])
    assert volta(ligado, e)["novas"] == 0
    assert e.pedidos == [None] and mensagens(ligado) == []
    volta(ligado, e)
    assert e.pedidos == [None, 100]


def test_pergunta_e_entrega_esperam_e_informativo_nao(ligado):
    receber(ligado, [linha(101, "informativo", "Começamos hoje.")])
    assert pendencia(ligado)["espera"] is None
    e = ErpFalso([linha(102, "pergunta"), linha(102, "pergunta")])   # repetido: o UNIQUE segura
    e.linhas = [linha(102, "pergunta")]
    volta(ligado, e)
    volta(ligado, ErpFalso([linha(102, "pergunta")]))
    p = pendencia(ligado)
    assert p["espera"] == "resposta" and p["espera_evento"] == 102
    assert [m["origem_evento_id"] for m in mensagens(ligado)] == [101, 102]


# ── o envio ──────────────────────────────────────────────────────────────────

def test_dentro_da_janela_sai_um_texto_com_os_blocos_e_a_entrega_ganha_botoes(ligado):
    receber(ligado, [linha(101, "pergunta"),
                     linha(102, "entrega", "Já está no ar.", demanda=1214, titulo="Ficha do cliente")])
    falou(ligado, AGORA - timedelta(hours=1))
    s = mandar(ligado)
    tipo, para, texto, _ = s.enviadas[0]
    assert tipo == "texto" and para == FRAN
    assert "*Chamado 350 · Auditoria de estoque*" in texto and "deslize esta mensagem" in texto
    assert "*Chamado 1214 · Ficha do cliente*" in texto
    assert s.enviadas[1][0] == "botoes" and [t for _, t in s.enviadas[1][3]] == ["Ficou bom", "Não ficou bom"]
    assert {m["estado"] for m in mensagens(ligado)} == {"enviada"}


def test_a_juncao_espera_a_rajada_acabar(ligado):
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = '10'::jsonb WHERE chave = 'pendencias.juntar_minutos'")
    receber(ligado, [linha(101, "informativo", "Está no ar.")])
    falou(ligado, AGORA)
    assert mandar(ligado).enviadas == []                                  # chegou agora: espera
    assert len(mandar(ligado, AGORA + timedelta(minutes=11)).enviadas) == 1


def test_fora_da_janela_o_informativo_espera_calado(ligado):
    receber(ligado, [linha(101, "informativo", "A auditoria está no ar.")])
    assert mandar(ligado).enviadas == []
    falou(ligado, AGORA + timedelta(hours=1))                              # a Fran escreveu na terca
    s = mandar(ligado, AGORA + timedelta(hours=1))
    assert s.enviadas[0][0] == "texto" and "Só aviso" in s.enviadas[0][2]


def test_fora_da_janela_a_pergunta_leva_uma_reabertura_so(ligado):
    receber(ligado, [linha(101, "pergunta")])
    s = mandar(ligado)
    assert [x[0] for x in s.enviadas] == ["modelo"] and s.modelos[0]["botoes"] == ["reabrir:%s" % FRAN]
    assert mensagens(ligado)[0]["estado"] == "guardada"
    receber(ligado, [linha(102, "pergunta", "E o lote?")])
    assert mandar(ligado).enviadas == []                                    # ja ha reabertura sem toque


def test_o_ver_da_reabertura_solta_na_hora(ligado):
    receber(ligado, [linha(101, "pergunta")])
    mandar(ligado)
    falou(ligado, AGORA)
    s = saida()
    chega(ligado, s, toque="reabrir:%s" % FRAN)
    assert any(x[0] == "texto" and "Chamado 350" in x[2] for x in s.enviadas)


# ── a volta ──────────────────────────────────────────────────────────────────

def _enviada(cfg, linhas):
    receber(cfg, linhas)
    falou(cfg, AGORA - timedelta(hours=1))
    s = mandar(cfg)
    return s.enviadas, mensagens(cfg, "saiu")[0]["wamid"]


def test_resposta_citada_vai_ao_chamado_e_ao_erp(ligado):
    _, w = _enviada(ligado, [linha(101, "pergunta")])
    s = saida()
    chega(ligado, s, texto="Sim, sem saldo", contexto=w)
    assert s.enviadas[-1][2] == "Anotado no chamado 350. ✓"
    assert pendencia(ligado)["espera"] is None
    e = ErpFalso()
    volta(ligado, e)
    assert e.respostas == [(350, FRAN, "Sim, sem saldo")]
    assert mensagens(ligado, "entrou")[0]["estado"] == "entregue"


def test_resposta_a_informativo_e_descartada_com_uma_linha_so(ligado):
    _, w = _enviada(ligado, [linha(101, "informativo", "Está no ar.")])
    s = saida()
    chega(ligado, s, texto="obrigada", contexto=w)
    chega(ligado, s, texto="valeu", contexto=w)
    assert [x[2] for x in s.enviadas] == [pendencias.SO_AVISO]
    assert {m["estado"] for m in mensagens(ligado, "entrou")} == {"descartada"}


def test_ficou_bom_e_nao_ficou_bom(ligado):
    receber(ligado, [linha(101, "entrega", "No ar.")])
    falou(ligado, AGORA - timedelta(hours=1))
    mandar(ligado)
    pid = pendencia(ligado)["id"]
    s = saida()
    chega(ligado, s, toque="pend:nao:%d" % pid)
    assert s.enviadas[-1][2] == pendencias.QUAL_FALHOU
    chega(ligado, s, texto="O QR não aparece no PDF")
    assert "voltou para ajuste" in s.enviadas[-1][2]
    chega(ligado, s, toque="pend:ok:%d" % pid)                             # repetido: ja respondida
    assert "já foi respondida" in s.enviadas[-1][2]
    e = ErpFalso()
    volta(ligado, e)
    assert e.validacoes == [(350, FRAN, "nao_ficou_bom", "O QR não aparece no PDF")]


def test_toque_de_outro_numero_nao_mexe(ligado):
    receber(ligado, [linha(101, "entrega", "No ar.")])
    pid = pendencia(ligado)["id"]
    s = saida()
    e = motor.Entrada(wamid="wamid.x", tipo="interactive", toque="pend:ok:%d" % pid,
                      pessoa=motor.Pessoa(bsuid="BR.o", wa_id="554988887777", nome="Outro"))
    with conexao(ligado) as con:
        motor.tratar(con, s, None, e, AGORA, Envio(), None)
    assert pendencia(ligado)["espera"] == "validacao" and mensagens(ligado, "entrou") == []


def test_sem_citar_a_olivia_propoe_e_a_pessoa_confirma(ligado):
    _enviada(ligado, [linha(101, "pergunta")])
    pid = pendencia(ligado)["id"]
    ia = IAFalsa()
    ia.pendencia = pid
    s = saida()
    chega(ligado, s, texto="a lista sai sem saldo sim", ia=ia)
    tipo, _, texto, botoes = s.enviadas[-1]
    assert tipo == "botoes" and texto == "É sobre o Chamado 350 · Auditoria de estoque?"
    assert [t for _, t in botoes] == ["Sim", "Outro chamado", "Outro assunto"]
    chega(ligado, s, toque=botoes[0][0])
    assert s.enviadas[-1][2] == "Anotado no chamado 350. ✓"
    assert [m["estado"] for m in mensagens(ligado, "entrou")] == ["descartada", "a_entregar"]


def test_nenhuma_segue_a_corrente_de_sempre(ligado):
    _enviada(ligado, [linha(101, "pergunta")])
    ia = IAFalsa()                       # pendencia = None: "nenhuma"
    ia.resposta = None
    s = saida()
    chega(ligado, s, texto="preciso de um boleto", ia=ia)
    assert ia.pendencias_vistas and mensagens(ligado, "entrou") == []
    assert not any("É sobre" in x[2] for x in s.enviadas)               # seguiu o caminho de hoje


def test_bom_dia_com_mensagem_esperando_nao_leva_o_menu(ligado):
    with conexao(ligado) as con:
        con.execute("INSERT INTO atendimento.destinos (nome, whatsapp) VALUES ('Fran', %s)", (FRAN,))
    receber(ligado, [linha(101, "informativo", "A auditoria está no ar.")])
    s = saida()
    falou(ligado, AGORA)
    chega(ligado, s, texto="Bom dia")
    assert len(s.enviadas) == 1 and "Chamado 350" in s.enviadas[0][2]


def test_o_erp_recusando_a_mensagem_fica_com_o_erro(ligado):
    _, w = _enviada(ligado, [linha(101, "pergunta")])
    chega(ligado, saida(), texto="sim", contexto=w)
    e = ErpFalso()
    e.recusar = True
    volta(ligado, e)
    m = mensagens(ligado, "entrou")[0]
    assert m["estado"] == "erro" and "não é o WhatsApp" in m["erro"]


def test_a_entrega_validada_na_caixa_deixa_de_esperar(ligado):
    receber(ligado, [linha(101, "entrega", "No ar.")])
    e = ErpFalso()
    e.demandas = [{"id": 350, "no": 7, "na_entrega": False, "ultima_do_autor": None}]
    assert volta(ligado, e)["fechadas"] == 1
    assert pendencia(ligado)["espera"] is None
