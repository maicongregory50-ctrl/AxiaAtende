"""Fase E do plano #950: o pedido do Marketing, o convite em degraus, o aceite com as imagens na
janela, a recusa com aviso ao responsavel, e o resumo do KR2. Meta falsa: nada sai."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import motor, recepcionista as R
from backend.banco import conexao
from backend.envio import Envio
from backend.main import criar_app
from tests.avisos_meta import aviso, status, texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa

QUINTA_10H = datetime(2026, 10, 8, 13, 0, tzinfo=timezone.utc)   # 10:00 em Sao Paulo, dentro da janela (#1192)
CHAVE = {"X-Axiaatende-Chave": "chave-do-marketing"}


@pytest.fixture
def ligado(cfg, tmp_path):
    return replace(cfg, responde=True, chave_pedido="chave-do-marketing", envios_pasta=tmp_path / "envios")


@pytest.fixture
def imagens(tmp_path):
    pasta = tmp_path / "marketing"
    pasta.mkdir()
    arquivos = []
    for nome in ("capa.jpg", "tela1.jpg", "tela2.jpg", "tela3.jpg"):
        (pasta / nome).write_bytes(b"\xff\xd8\xff" + nome.encode())
        arquivos.append(str(pasta / nome))
    return arquivos


def cliente(codigo, fat, whatsapp="", resp=("Maicon Gregory", "5549991505565"), nome=None):
    return {"erp_codigo": codigo, "nome": nome or "Cliente %d" % codigo, "cidade": "Rio do Sul", "uf": "SC",
            "whatsapp": whatsapp or "4799%07d" % codigo, "faturamento": fat,
            "responsavel_nome": resp[0], "responsavel_whatsapp": resp[1], "sugestao_vendedor": "MAICON"}


def pedido(imagens, clientes, ref="pub-1", peca="Trigo Mourisco IPR 92"):
    return {"pedido_ref": ref, "modelo": "pecas_da_revenda", "campanha": "Bom te ver de novo", "peca": peca, "capa": imagens[0],
            "imagens": imagens[1:], "aprovado_por": "maicon", "aprovado_em": "2026-10-07T17:00:00-03:00",
            "clientes": clientes}


def pedir(cfg, dados, cabecalho=CHAVE):
    with TestClient(criar_app(cfg)) as c:
        return c.post("/pedido/envio", json=dados, headers=cabecalho)


def destinatarios(cfg):
    with conexao(cfg) as con:
        return {d["erp_codigo"]: d for d in con.execute("SELECT * FROM atendimento.envio_destinatarios ORDER BY posicao")}


def test_pedido_sem_a_chave_e_recusado(ligado, imagens):
    assert pedir(ligado, pedido(imagens, [cliente(1, 10)]), cabecalho={}).status_code == 403
    assert pedir(ligado, pedido(imagens, [cliente(1, 10)]), cabecalho={"X-Axiaatende-Chave": "outra"}).status_code == 403
    assert pedir(replace(ligado, chave_pedido=""), pedido(imagens, [cliente(1, 10)])).status_code == 403


def test_pedido_classifica_cada_cliente_e_copia_as_imagens(ligado, imagens):
    r = pedir(ligado, pedido(imagens, [
        cliente(1, 500), cliente(2, 900), cliente(3, 100, whatsapp="4732221111"),       # fixo: sem celular
        cliente(4, 300, resp=("", "")),                                                  # canal vazio
    ]))
    assert r.status_code == 200
    d = destinatarios(ligado)
    assert d[2]["posicao"] == 1 and d[1]["posicao"] == 2                                 # por faturamento
    assert d[3]["situacao"] == "sem_whatsapp" and d[4]["situacao"] == "sem_responsavel"
    assert d[4]["sugestao_vendedor"] == "MAICON"
    with conexao(ligado) as con:
        e = con.execute("SELECT capa, imagens FROM atendimento.envios").fetchone()
    assert e["capa"].startswith(str(ligado.envios_pasta)) and len(e["imagens"]) == 3
    assert pedir(ligado, pedido(imagens, [cliente(1, 500)])).json()["envio_id"] == r.json()["envio_id"]  # repetido


def test_lote_de_20_por_dia_so_com_nota_verde_e_nada_ao_responsavel(ligado, imagens):
    """#1142: a COPIA de cada convite ao responsavel ACABOU (dono, 26/10/2026). Aqui o responsavel e
    o dono (`cliente()` o poe como padrao), e o resumo do lote nunca vai a ele -- o que vai, e so a
    representante e corretor, esta em test_1142_fila_por_numero.py."""
    pedir(ligado, pedido(imagens, [cliente(i, 1000 - i) for i in range(1, 46)]))
    s = SaidaFalsa()
    env = Envio(ler_nota=lambda: "GREEN")
    env.rotina(ligado, s, QUINTA_10H)
    convites = [x for x in s.enviadas if x[0] == "modelo" and x[1] != "5549991505565"]
    ao_responsavel = [x for x in s.enviadas if x[0] == "modelo" and x[1] == "5549991505565"]
    assert len(convites) == 20 and ao_responsavel == []
    d = destinatarios(ligado)
    assert {k for k, v in d.items() if v["situacao"] == "convidado"} == set(range(1, 21))   # o Top 20
    env.rotina(ligado, s, QUINTA_10H + timedelta(hours=3))
    assert len([x for x in s.enviadas if x[0] == "modelo"]) == 20                          # nada a mais no dia
    env.rotina(ligado, s, QUINTA_10H + timedelta(days=1))
    d = destinatarios(ligado)
    assert sum(1 for v in d.values() if v["situacao"] == "convidado") == 40
    assert d[21]["lote"] == 2 and [x for x in s.enviadas if x[1] == "5549991505565"] == []


@pytest.mark.parametrize("nota, parado", [("YELLOW", True), ("RED", True), (None, False)])
def test_sem_nota_verde_nada_sai_e_amarela_ou_vermelha_param(ligado, imagens, nota, parado):
    pedir(ligado, pedido(imagens, [cliente(1, 10)]))
    s = SaidaFalsa()
    Envio(ler_nota=(lambda: nota) if nota else None).rotina(ligado, s, QUINTA_10H)
    assert s.enviadas == []
    with conexao(ligado) as con:
        assert (con.execute("SELECT situacao FROM atendimento.envios").fetchone()["situacao"] == "parado_nota") is parado


def _convidar(ligado, imagens, clientes):
    pedir(ligado, pedido(imagens, clientes))
    s = SaidaFalsa()
    env = Envio(ler_nota=lambda: "GREEN")
    env.rotina(ligado, s, QUINTA_10H)
    return s, env


def _tocar(ligado, s, env, numero, acao, agora, wamid="wamid.toque"):
    msg = {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "button",
           "context": {"from": "554936640121", "id": "wamid.convite"},
           "button": {"payload": "envio:1:%s" % acao, "text": acao}}
    R.gravar(ligado, aviso([msg], numero=numero, bsuid="BR." + numero))
    R.processar_pendentes(ligado, s, None, envio=env, agora=agora)


def test_quero_receber_grava_o_aceite_e_manda_as_imagens(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    numero = destinatarios(ligado)[1]["whatsapp"]
    _tocar(ligado, s, env, numero, "quero", QUINTA_10H + timedelta(hours=1))
    assert [x[0] for x in s.enviadas[-3:]] == ["imagem", "imagem", "imagem"]
    d = destinatarios(ligado)[1]
    assert d["resposta"] == "quero" and d["imagens_enviadas"] == 3
    with conexao(ligado) as con:
        c = con.execute("SELECT tipo, wamid FROM atendimento.consentimentos").fetchone()
        avisos = con.execute("SELECT count(*) AS n FROM atendimento.avisos").fetchone()["n"]
    assert c["tipo"] == "aceite" and c["wamid"] == "wamid.toque" and avisos == 0   # quero nao avisa ninguem
    _tocar(ligado, s, env, numero, "quero", QUINTA_10H + timedelta(hours=2), wamid="wamid.toque2")
    assert len([x for x in s.enviadas if x[0] == "imagem"]) == 3                      # segundo toque nao repete


def test_nao_quero_tira_da_lista_e_avisa_o_responsavel(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10, resp=("Djeison de Oliveira", "5549999567572"))])
    numero = destinatarios(ligado)[1]["whatsapp"]
    _tocar(ligado, s, env, numero, "nao_quero", QUINTA_10H + timedelta(hours=1))
    assert s.ultima[0] == "texto" and "não vai mais receber" in s.ultima[2]
    env.rotina(ligado, s, QUINTA_10H + timedelta(hours=1, minutes=1))
    aviso_enviado = s.ultima
    assert aviso_enviado[0] == "modelo" and aviso_enviado[1] == "5549999567572" and aviso_enviado[2] == "aviso_recusa"
    assert aviso_enviado[3][0] == "Cliente 1" and aviso_enviado[3][2] == "https://wa.me/%s" % numero
    # num envio novo, quem recusou nao entra
    pedir(ligado, pedido(imagens, [cliente(1, 10)], ref="pub-2", peca="Guandu"))
    with conexao(ligado) as con:
        assert con.execute("""SELECT situacao FROM atendimento.envio_destinatarios
                               WHERE envio_id = 2""").fetchone()["situacao"] == "recusou_antes"


def test_imagens_fora_da_janela_de_24h_nao_saem(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    with conexao(ligado) as con:
        con.execute("""UPDATE atendimento.envio_destinatarios SET resposta = 'quero', resposta_em = %s,
                       imagens_enviadas = 1""", (QUINTA_10H,))
    env.rotina(ligado, s, QUINTA_10H + timedelta(hours=25))
    assert [x for x in s.enviadas if x[0] == "imagem"] == []


def test_numero_que_nao_e_whatsapp_nao_e_tentado_de_novo(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    d = destinatarios(ligado)[1]
    falha = status(d["convite_wamid"], "failed", numero=d["whatsapp"])
    falha["errors"] = [{"code": 131026, "title": "Message undeliverable"}]
    R.gravar(ligado, aviso(statuses=[falha]))
    R.processar_pendentes(ligado, s, None, envio=env, agora=QUINTA_10H)
    assert destinatarios(ligado)[1]["situacao"] == "nao_e_whatsapp"
    pedir(ligado, pedido(imagens, [cliente(1, 10)], ref="pub-2", peca="Guandu"))
    with conexao(ligado) as con:
        assert con.execute("SELECT situacao FROM atendimento.envio_destinatarios WHERE envio_id = 2").fetchone()["situacao"] == "nao_e_whatsapp"


def test_entregue_e_lido_e_o_texto_de_quem_escreveu(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    d = destinatarios(ligado)[1]
    R.gravar(ligado, aviso(statuses=[status(d["convite_wamid"], "delivered", numero=d["whatsapp"]),
                                     status(d["convite_wamid"], "read", numero=d["whatsapp"])]))
    R.gravar(ligado, aviso([texto("wamid.t", "tem aveia branca?", numero=d["whatsapp"])],
                           numero=d["whatsapp"], bsuid="BR.x"))
    R.processar_pendentes(ligado, s, None, envio=env, agora=QUINTA_10H + timedelta(hours=1))
    d = destinatarios(ligado)[1]
    assert d["entregue_em"] and d["lido_em"]
    assert d["resposta"] == "texto" and d["resposta_texto"] == "tem aveia branca?"
    # #1189: o cliente convidado vai ao representante dele, nao a OlivIA (antes: a lista do menu)
    assert s.ultima[0] == "lista" and "https://wa.me/5549991505565" in s.ultima[2]


def _escreve(ligado, s, env, numero, frase, agora, wamid, ia=None):
    R.gravar(ligado, aviso([texto(wamid, frase, numero=numero)], numero=numero, bsuid="BR." + numero))
    R.processar_pendentes(ligado, s, ia, envio=env, agora=agora)


def _toca(ligado, s, env, numero, opcao, agora, wamid, lista=True):
    R.gravar(ligado, aviso([toque(wamid, opcao, numero=numero, lista=lista)], numero=numero, bsuid="BR." + numero))
    R.processar_pendentes(ligado, s, None, envio=env, agora=agora)


def test_1189_o_portao_manda_ao_representante_e_ao_menu_da_carteira_uma_vez_por_dia(ligado, imagens):
    """Dono, 28/10/2026: "nao podemos ligar no fluxo geral". O cliente da carteira recebe o contato do
    representante e, para outro assunto, o menu dele -- uma vez por dia: do outro lado pode estar a
    resposta automatica do WhatsApp Business do cliente."""
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    numero = destinatarios(ligado)[1]["whatsapp"]

    def portoes():
        return [x for x in s.enviadas if x[1] == numero and "Obrigado pela mensagem" in x[2]]

    _escreve(ligado, s, env, numero, "bom dia, tudo bem?", QUINTA_10H + timedelta(hours=1), "wamid.a")
    assert len(portoes()) == 1
    tipo, _, msg, opcoes = portoes()[0]
    assert tipo == "lista" and "Maicon" in msg and "https://wa.me/5549991505565" in msg
    assert [o for o, _ in opcoes] == ["menu:carteira.financeiro", "menu:carteira.carga",
                                      "menu:carteira.qualidade", "menu:carteira.empresa"]
    assert destinatarios(ligado)[1]["resposta_texto"] == "bom dia, tudo bem?"   # anotado na tela Envios
    # sem tocar, a segunda mensagem do mesmo dia sem assunto (a resposta automatica) nao recebe nada
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.conversas SET situacao = 'parou_no_meio'")
    n = len(s.enviadas)
    _escreve(ligado, s, env, numero, "Em breve retornaremos", QUINTA_10H + timedelta(hours=2), "wamid.b")
    assert len(s.enviadas) == n, s.enviadas[n:]
    # no dia seguinte, de novo uma
    _escreve(ligado, s, env, numero, "bom dia", QUINTA_10H + timedelta(days=1), "wamid.c")
    assert len(portoes()) == 2


def test_1189_o_toque_no_boleto_leva_a_fran_e_o_da_empresa_ao_dono(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    numero = destinatarios(ligado)[1]["whatsapp"]
    _escreve(ligado, s, env, numero, "oi", QUINTA_10H + timedelta(hours=1), "wamid.a")
    _toca(ligado, s, env, numero, "menu:carteira.financeiro", QUINTA_10H + timedelta(hours=1, minutes=1), "wamid.t1")
    assert s.ultima[0] == "contato" and s.ultima[2] == "Fran"
    _escreve(ligado, s, env, numero, "empresa", QUINTA_10H + timedelta(days=1), "wamid.b")
    assert s.ultima[0] == "contato" and s.ultima[2] == "Maicon Gregory"   # a palavra da opcao: direto
    assert "Obrigado pela mensagem" in s.enviadas[-3][2]                  # a linha do dia antes do contato


def test_1189_o_texto_com_assunto_a_olivia_propoe_so_as_opcoes_da_carteira(ligado, imagens):
    """"OlivIA precisa entender o tipo de atendimento": o texto vai a IA SO com as quatro opcoes, e
    a reclamacao longa tambem (casar_opcao nao chama a IA acima de 80 letras)."""
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    numero = destinatarios(ligado)[1]["whatsapp"]
    ia = IAFalsa(resposta="carteira.empresa")
    frase = ("a semente que chegou semana passada veio com muita impureza, estou muito chateado com "
             "isso e quero uma solucao")
    _escreve(ligado, s, env, numero, frase, QUINTA_10H + timedelta(hours=1), "wamid.a", ia=ia)
    assert ia.opcoes == [["carteira.financeiro", "carteira.carga", "carteira.qualidade", "carteira.empresa"]]
    tipo, _, msg, opcoes = s.ultima
    assert tipo == "botoes" and "https://wa.me/5549991505565" in msg and "Falar com a empresa" not in msg
    assert opcoes[0][0] == "ia:sim:carteira.empresa"
    # "Ver todas as opcoes" volta ao menu da carteira, nao ao menu geral
    _toca(ligado, s, env, numero, "ia:menu", QUINTA_10H + timedelta(hours=1, minutes=1), "wamid.t", lista=False)
    assert s.ultima[0] == "lista" and s.ultima[3][0][0] == "menu:carteira.financeiro"


def test_1189_quem_nao_esta_em_envio_segue_o_fluxo_geral(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    _escreve(ligado, s, env, "5547988887777", "quero comprar semente", QUINTA_10H + timedelta(hours=1), "wamid.z")
    assert s.ultima[0] == "lista" and "menu:carteira.financeiro" not in [o for o, _ in s.ultima[3]]


def test_1189_o_portao_desligado_e_o_comportamento_de_antes(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'portao.ligado'")
    numero = destinatarios(ligado)[1]["whatsapp"]
    _escreve(ligado, s, env, numero, "tem aveia branca?", QUINTA_10H + timedelta(hours=1), "wamid.d")
    assert s.ultima[0] == "lista" and "Obrigado pela mensagem" not in s.ultima[2]


def test_resumo_do_kr2(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 30), cliente(2, 20), cliente(3, 10)])
    d = destinatarios(ligado)
    _tocar(ligado, s, env, d[1]["whatsapp"], "quero", QUINTA_10H + timedelta(hours=1), wamid="w1")
    _tocar(ligado, s, env, d[2]["whatsapp"], "nao_quero", QUINTA_10H + timedelta(hours=1), wamid="w2")
    with TestClient(criar_app(ligado)) as c:
        r = c.get("/pedido/resumo", params={"desde": "2026-10-01T00:00:00-03:00", "ate": "2026-11-01T00:00:00-03:00"},
                  headers=CHAVE).json()
    assert r == {"convidados": 3, "responderam": 2, "aceitaram": 1, "recusaram": 1}


def test_1189_o_portao_retroativo_acha_quem_escreveu_e_manda_uma_vez(ligado, imagens):
    """Dono, 29/10/2026: o portao para os clientes que escreveram antes de ele existir."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "portao_retroativo", Path(__file__).resolve().parent.parent / "scripts" / "portao_retroativo.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    s, env = _convidar(ligado, imagens, [cliente(1, 10), cliente(2, 5)])
    numero = destinatarios(ligado)[1]["whatsapp"]
    R.gravar(ligado, aviso([texto("wamid.r", "voces tem azevem?", numero=numero)], numero=numero, bsuid="BR." + numero))
    agora = datetime.now(timezone.utc)
    with conexao(ligado) as con:   # escreveu antes do portao: o evento ja processado, sem resposta
        con.execute("UPDATE atendimento.eventos_meta SET processado_em = now(), recebido_em = now() - interval '2 hours'")
        lista = m.quem_escreveu(con, env, agora)
        assert [d["erp_codigo"] for _, _, d in lista] == [1]
        assert motor.portao_do_cliente(con, s, None, lista[0][1], agora, env)
        assert s.ultima[0] == "lista" and "https://wa.me/5549991505565" in s.ultima[2]


def test_1197_quem_ganhou_responsavel_volta_a_fila_do_envio(ligado, imagens, tmp_path):
    """Dono, 29/10/2026: a DISAM ficou "sem responsavel" no envio (a CERES sem WhatsApp); corrigido o
    ERP, ela volta a fila do MESMO envio, na posicao dela -- e quem recusou antes continua fora."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "religar", Path(__file__).resolve().parent.parent / "scripts" / "religar_sem_responsavel.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    pedir(ligado, pedido(imagens, [cliente(1, 900, resp=("", "")), cliente(2, 500, resp=("", "")), cliente(3, 100)]))
    with conexao(ligado) as con:
        con.execute("INSERT INTO atendimento.consentimentos (whatsapp, tipo, wamid) VALUES (%s, 'recusa', 'wamid.teste')",
                    (destinatarios(ligado)[2]["whatsapp"],))
    csv_ = tmp_path / "resp.csv"
    csv_.write_text("erp_codigo,responsavel_nome,responsavel_whatsapp,responsavel_canal\n"
                    "1,CERES REPRESENTACOES,5542999990000,representante\n"
                    "2,CERES REPRESENTACOES,5542999990000,representante\n", encoding="utf-8")
    novos = m.ler(str(csv_))
    with conexao(ligado) as con:
        assert all(not x[4].startswith("volta") or x[1] == 1 for x in m.religar(con, novos, gravar=False))
    assert destinatarios(ligado)[1]["situacao"] == "sem_responsavel"     # o ensaio nao grava
    with conexao(ligado) as con:
        m.religar(con, novos, gravar=True)
    d = destinatarios(ligado)
    assert d[1]["situacao"] == "aguardando" and d[1]["responsavel_whatsapp"] == "5542999990000"
    assert d[2]["situacao"] == "sem_responsavel"                         # recusou antes: fora
    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, QUINTA_10H + timedelta(hours=1))
    assert destinatarios(ligado)[1]["convite_em"] is not None            # sai no proximo lote
