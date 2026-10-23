"""#1090 etapa 3, entrega 1: "Meus clientes" -- um cliente por vez, o consultor conta como foi, confere.

Spec: C:\\AxiaGestao\\docs\\specs\\2026-10-23-relacionamento-etapa3-visita-pelo-whatsapp.md (maquete).
Saida, IA e ERP falsos; banco de teste.
"""
import json
from datetime import timedelta

import pytest

from backend import clientes_do_dia as K
from backend import clientes_erp, erp
from backend.banco import conexao
from tests.avisos_meta import texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa
from tests.test_campo import AGORA, EQUIPE, canal, ligar, passo  # noqa: F401 -- `canal` e fixture

COOPERPASSO = {"posicao_fila": 1, "codigo": 4461, "nome": "COOPERPASSO", "cidade": "TANGARÁ", "uf": "SC",
               "faixa": "A+", "posicao": 4, "atraso_dias": 0, "ultimo_contato": None, "ultimo_meio": None,
               "meses_compra": ["jan", "fev"], "comprou": {"25-26": ["AVR PALHA", "AVEIA PRETA"]},
               "contato": {"nome": "Márcio Czernhak", "telefone": "(49) 98859-5737",
                           "link_whatsapp": "https://wa.me/5549988595737"},
               "campanha": None, "proximo_sugerido": "2026-10-27"}
PLANTAGRO = dict(COOPERPASSO, posicao_fila=2, codigo=4655, nome="PLANTAGRO", posicao=7,
                 contato={"nome": "Junior Picolo", "telefone": "(42) 99948-3552",
                          "link_whatsapp": "https://wa.me/5542999483552"})
LEITURA = {"meio": "ligacao", "quando": "2026-10-12", "ofereceu": False, "resposta": "interesse",
           "motivo_id": None, "interesse_texto": "+Palha e aveia para o inverno", "retomar_em": "2026-11-05",
           "pedido_numero": "", "anotacao": "terminando de plantar o verão"}


@pytest.fixture
def piloto(canal):
    ligar(canal)
    with conexao(canal) as con:
        # a 032 ja poe o dono pela linha dele em Destinos (o mesmo numero no banco de teste)
        con.execute("""INSERT INTO atendimento.clientes_consultores (wa_id, comercial_id, nome) VALUES (%s, 42, 'Maicon')
                       ON CONFLICT (wa_id) DO UPDATE SET comercial_id = 42, ativo = true""", (EQUIPE,))
        for f in (COOPERPASSO, PLANTAGRO):
            con.execute("INSERT INTO atendimento.clientes_fila (comercial_id, codigo, posicao, ficha) VALUES (42, %s, %s, %s)",
                        (f["codigo"], f["posicao_fila"], json.dumps(f)))
        con.execute("INSERT INTO atendimento.clientes_motivos (id, nome) VALUES (1, 'Preço'), (2, 'Já comprou')")
    return canal


def _rodar(cfg, s, ia, agora):
    with conexao(cfg) as con:
        return K.rodar(con, s, ia, agora)


def _registros(cfg):
    with conexao(cfg) as con:
        return [dict(r) for r in con.execute("SELECT * FROM atendimento.clientes_registros ORDER BY id").fetchall()]


def _abrir(cfg, s):
    passo(cfg, s, texto("w1", "bom dia", numero=EQUIPE))
    passo(cfg, s, toque("w2", "menu:interna.clientes", numero=EQUIPE), agora=AGORA + timedelta(seconds=10))


def test_o_menu_da_casa_mostra_meus_clientes_so_para_o_piloto(piloto):
    s = SaidaFalsa()
    passo(piloto, s, texto("w1", "bom dia", numero=EQUIPE))
    assert ("menu:interna.clientes", "📋 Meus clientes") in s.ultima[3]
    with conexao(piloto) as con:
        con.execute("UPDATE atendimento.clientes_consultores SET ativo = false")
    passo(piloto, s, texto("w2", "menu", numero=EQUIPE), agora=AGORA + timedelta(minutes=5))
    assert all(o[0] != "menu:interna.clientes" for o in s.ultima[3])


def test_o_caminho_da_maquete(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.visita = dict(LEITURA)
    _abrir(piloto, s)
    ficha, conte = s.enviadas[-2], s.enviadas[-1]
    assert ficha[0] == "link" and "*Cliente 1 de 2*" in ficha[2] and "COOPERPASSO" in ficha[2]
    assert ficha[3] == [("Chamar Márcio", "https://wa.me/5549988595737")]
    assert conte[2] == K.ME_CONTE and [o[1] for o in conte[3]] == ["⏭ Depois", "🛑 Parar por hoje"]

    t = AGORA + timedelta(minutes=2)
    passo(piloto, s, texto("w3", "liguei pro Márcio, vão querer +Palha e aveia, passo lá dia 5", numero=EQUIPE), agora=t)
    assert s.ultima[2] == K.RECEBI
    assert _rodar(piloto, s, ia, t + timedelta(seconds=10)) == 0       # ainda pode estar escrevendo
    assert _rodar(piloto, s, ia, t + timedelta(seconds=31)) == 1
    cartao = s.ultima
    assert cartao[0] == "botoes" and "resposta: *Mostrou interesse*" in cartao[2] and "*05/11*" in cartao[2]
    assert [o[1] for o in cartao[3]] == ["✅ Confere", "✏️ Corrigir"]
    rid = _registros(piloto)[0]["id"]

    passo(piloto, s, toque("w4", "cli:confere:%d" % rid, numero=EQUIPE), agora=t + timedelta(minutes=1))
    assert s.ultima[2] == K.ANOTADO and _registros(piloto)[0]["estado"] == "confirmado"

    enviados = []
    r = clientes_erp.enviar_registros(piloto, gravar=lambda cfg, corpo: enviados.append(corpo) or {"id": 777})
    assert r == {"gravados": 1, "recusados": 0}
    c = enviados[0]
    assert (c["stakeholder_id"], c["comercial_id"], c["ref_externa"]) == (4461, 42, "atende-cli:%d" % rid)
    assert (c["meio"], c["resposta"], c["retomar_em"], c["ofereceu"]) == ("ligacao", "interesse", "2026-11-05", False)

    _rodar(piloto, s, ia, t + timedelta(minutes=2))
    textos = [e[2] for e in s.enviadas[-3:]]
    assert textos[0].startswith(K.GRAVADO) and "PLANTAGRO" in textos[1] and "*Cliente 2 de 2*" in textos[1]


def test_o_que_falta_e_perguntado_por_botao_uma_coisa_por_vez(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.visita = dict(LEITURA, meio=None, resposta=None)
    _abrir(piloto, s)
    t = AGORA + timedelta(minutes=2)
    passo(piloto, s, texto("w3", "falei com ele", numero=EQUIPE), agora=t)
    _rodar(piloto, s, ia, t + timedelta(seconds=31))
    rid = _registros(piloto)[0]["id"]
    assert s.ultima[0] == "botoes" and [o[0] for o in s.ultima[3]] == [
        "cli:meio:%d:visita" % rid, "cli:meio:%d:ligacao" % rid, "cli:meio:%d:whatsapp" % rid]
    passo(piloto, s, toque("w4", "cli:meio:%d:visita" % rid, numero=EQUIPE), agora=t + timedelta(minutes=1))
    assert s.ultima[0] == "lista" and "cli:resp:%d:conversou" % rid in [o[0] for o in s.ultima[3]]
    passo(piloto, s, toque("w5", "cli:resp:%d:conversou" % rid, lista=True, numero=EQUIPE), agora=t + timedelta(minutes=2))
    assert "Confere?" in s.ultima[2] and "Visita" in s.ultima[2] and "(sugerido)" not in s.ultima[2]


def test_sem_proximo_dito_vem_o_sugerido(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.visita = dict(LEITURA, retomar_em="")
    _abrir(piloto, s)
    t = AGORA + timedelta(minutes=2)
    passo(piloto, s, texto("w3", "liguei, conversamos", numero=EQUIPE), agora=t)
    _rodar(piloto, s, ia, t + timedelta(seconds=31))
    assert "*27/10* (sugerido)" in s.ultima[2]


def test_recusa_pede_o_motivo_da_lista(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.visita = dict(LEITURA, resposta="nao_atendeu")
    with conexao(piloto) as con:   # com campanha aberta, a resposta da oferta
        f = dict(COOPERPASSO, campanha={"codigo": "CAM-0008", "nome": "Inverno", "versao": "recompra"})
        con.execute("UPDATE atendimento.clientes_fila SET ficha = %s WHERE codigo = 4461", (json.dumps(f),))
    ia.visita = dict(LEITURA, ofereceu=True, resposta="recusou")
    _abrir(piloto, s)
    assert "campanha *Inverno* · *recompra*" in s.enviadas[-2][2]
    t = AGORA + timedelta(minutes=2)
    passo(piloto, s, texto("w3", "ofereci o inverno, não quer", numero=EQUIPE), agora=t)
    _rodar(piloto, s, ia, t + timedelta(seconds=31))
    rid = _registros(piloto)[0]["id"]
    assert s.ultima[0] == "lista" and s.ultima[3][0] == ("cli:motivo:%d:1" % rid, "Preço")
    passo(piloto, s, toque("w4", "cli:motivo:%d:1" % rid, lista=True, numero=EQUIPE), agora=t + timedelta(minutes=1))
    assert "motivo: Preço" in s.ultima[2] and "ofereceu *Inverno*: sim" in s.ultima[2]


def test_depois_manda_o_proximo_e_o_cliente_volta_amanha(piloto):
    s = SaidaFalsa()
    _abrir(piloto, s)
    rid = _registros(piloto)[0]["id"]
    passo(piloto, s, toque("w3", "cli:depois:%d" % rid, numero=EQUIPE), agora=AGORA + timedelta(minutes=1))
    assert "PLANTAGRO" in s.enviadas[-2][2]
    amanha = AGORA + timedelta(days=1)
    passo(piloto, s, texto("w4", "bom dia", numero=EQUIPE), agora=amanha)
    passo(piloto, s, toque("w5", "menu:interna.clientes", numero=EQUIPE), agora=amanha + timedelta(seconds=10))
    # o PLANTAGRO ficou aberto ha menos de 24 h: ele vem de novo, e nao um terceiro
    assert "PLANTAGRO" in s.enviadas[-2][2]
    rid2 = _registros(piloto)[1]["id"]
    passo(piloto, s, toque("w6", "cli:depois:%d" % rid2, numero=EQUIPE), agora=amanha + timedelta(minutes=1))
    # e o COOPERPASSO, deixado para depois ontem, volta hoje
    assert "COOPERPASSO" in s.enviadas[-2][2]
    assert [r["estado"] for r in _registros(piloto)] == ["depois", "depois", "aberto"]


def test_texto_de_interno_sem_cliente_aberto_continua_no_canal_de_campo(piloto):
    s = SaidaFalsa()
    passo(piloto, s, texto("w1", "colheita do centeio no Jair", numero=EQUIPE))
    with conexao(piloto) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.campo_frases").fetchone()["n"] == 1
    assert _registros(piloto) == []


def test_parar_por_hoje_e_o_texto_seguinte_vai_ao_canal_de_campo(piloto):
    s = SaidaFalsa()
    _abrir(piloto, s)
    rid = _registros(piloto)[0]["id"]
    passo(piloto, s, toque("w3", "cli:parar:%d" % rid, numero=EQUIPE), agora=AGORA + timedelta(minutes=1))
    assert s.ultima[2] == K.ATE_LOGO
    passo(piloto, s, texto("w4", "foto da colheita", numero=EQUIPE), agora=AGORA + timedelta(minutes=2))
    assert _registros(piloto)[0]["textos"] == ""


def test_o_erp_recusa_e_a_frase_volta_ao_consultor(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.visita = dict(LEITURA)
    _abrir(piloto, s)
    t = AGORA + timedelta(minutes=2)
    passo(piloto, s, texto("w3", "liguei", numero=EQUIPE), agora=t)
    _rodar(piloto, s, ia, t + timedelta(seconds=31))
    rid = _registros(piloto)[0]["id"]
    passo(piloto, s, toque("w4", "cli:confere:%d" % rid, numero=EQUIPE), agora=t + timedelta(minutes=1))

    def recusa(cfg, corpo):
        raise erp.ErpRecusou("Não achei esse pedido para este cliente.")
    assert clientes_erp.enviar_registros(piloto, gravar=recusa) == {"gravados": 0, "recusados": 1}
    _rodar(piloto, s, ia, t + timedelta(minutes=2))
    assert "Não achei esse pedido" in s.ultima[2]
    r = _registros(piloto)[0]
    assert r["estado"] == "aberto" and r["textos"] == "" and r["avisado"]


def test_erp_fora_do_ar_deixa_confirmado(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.visita = dict(LEITURA)
    _abrir(piloto, s)
    t = AGORA + timedelta(minutes=2)
    passo(piloto, s, texto("w3", "liguei", numero=EQUIPE), agora=t)
    _rodar(piloto, s, ia, t + timedelta(seconds=31))
    rid = _registros(piloto)[0]["id"]
    passo(piloto, s, toque("w4", "cli:confere:%d" % rid, numero=EQUIPE), agora=t + timedelta(minutes=1))

    def fora(cfg, corpo):
        raise erp.ErpIndisponivel("o ERP não respondeu")
    assert "erro" in clientes_erp.enviar_registros(piloto, gravar=fora)
    assert _registros(piloto)[0]["estado"] == "confirmado"


def test_sem_ia_pergunta_tudo_por_botao(piloto):
    s = SaidaFalsa()
    _abrir(piloto, s)
    t = AGORA + timedelta(minutes=2)
    passo(piloto, s, texto("w3", "liguei", numero=EQUIPE), agora=t)
    _rodar(piloto, s, None, t + timedelta(seconds=31))
    assert s.ultima[0] == "botoes" and s.ultima[3][0][1] == "🚗 Visita"


def test_copiar_filas_troca_a_copia_e_os_motivos(piloto):
    lidos = []

    def ler(cfg, comercial, limite):
        lidos.append(comercial)
        return {"itens": [dict(PLANTAGRO, posicao_fila=1)], "motivos": [{"id": 9, "nome": "Preço", "pede_texto": False}]}
    assert clientes_erp.copiar_filas(piloto, ler=ler) == {42: 1}
    with conexao(piloto) as con:
        fila = con.execute("SELECT codigo FROM atendimento.clientes_fila").fetchall()
        motivos = con.execute("SELECT id FROM atendimento.clientes_motivos").fetchall()
    assert [f["codigo"] for f in fila] == [4655] and [m["id"] for m in motivos] == [9] and lidos == [42]


def test_quem_nao_esta_no_piloto_recebe_a_frase(piloto):
    with conexao(piloto) as con:
        con.execute("DELETE FROM atendimento.clientes_consultores")
    s = SaidaFalsa()
    _abrir(piloto, s)
    assert s.ultima[2] == K.SEM_LIBERACAO


def test_o_rotulo_do_link_cabe_em_20(piloto):
    f = dict(COOPERPASSO, contato={"nome": "Maximilianoaugusto da Silva", "link_whatsapp": "https://wa.me/1"})
    assert K._rotulo_link(f) == "Chamar no WhatsApp"
