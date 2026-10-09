"""Fase E do plano #950: o pedido do Marketing, o convite em degraus, o aceite com as imagens na
janela, a recusa com aviso ao responsavel, e o resumo do KR2. Meta falsa: nada sai."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import recepcionista as R
from backend.banco import conexao
from backend.envio import Envio
from backend.main import criar_app
from tests.avisos_meta import aviso, status, texto
from tests.saida_falsa import SaidaFalsa

QUINTA_9H = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)   # 09:00 em Sao Paulo
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
    return {"pedido_ref": ref, "campanha": "Bom te ver de novo", "peca": peca, "capa": imagens[0],
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


def test_lote_de_20_por_dia_so_com_nota_verde_e_copia_ao_responsavel(ligado, imagens):
    pedir(ligado, pedido(imagens, [cliente(i, 1000 - i) for i in range(1, 46)]))
    s = SaidaFalsa()
    env = Envio(ler_nota=lambda: "GREEN")
    env.rotina(ligado, s, QUINTA_9H)
    convites = [x for x in s.enviadas if x[0] == "modelo" and x[1] != "5549991505565"]
    copias = [x for x in s.enviadas if x[0] == "modelo" and x[1] == "5549991505565"]
    assert len(convites) == 20 and len(copias) == 1
    d = destinatarios(ligado)
    assert {k for k, v in d.items() if v["situacao"] == "convidado"} == set(range(1, 21))   # o Top 20
    env.rotina(ligado, s, QUINTA_9H + timedelta(hours=3))
    assert len([x for x in s.enviadas if x[0] == "modelo"]) == 21                          # nada a mais no dia
    env.rotina(ligado, s, QUINTA_9H + timedelta(days=1))
    d = destinatarios(ligado)
    assert sum(1 for v in d.values() if v["situacao"] == "convidado") == 40
    assert d[21]["lote"] == 2 and len([x for x in s.enviadas if x[1] == "5549991505565"]) == 1   # copia so uma vez


@pytest.mark.parametrize("nota, parado", [("YELLOW", True), ("RED", True), (None, False)])
def test_sem_nota_verde_nada_sai_e_amarela_ou_vermelha_param(ligado, imagens, nota, parado):
    pedir(ligado, pedido(imagens, [cliente(1, 10)]))
    s = SaidaFalsa()
    Envio(ler_nota=(lambda: nota) if nota else None).rotina(ligado, s, QUINTA_9H)
    assert s.enviadas == []
    with conexao(ligado) as con:
        assert (con.execute("SELECT situacao FROM atendimento.envios").fetchone()["situacao"] == "parado_nota") is parado


def _convidar(ligado, imagens, clientes):
    pedir(ligado, pedido(imagens, clientes))
    s = SaidaFalsa()
    env = Envio(ler_nota=lambda: "GREEN")
    env.rotina(ligado, s, QUINTA_9H)
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
    _tocar(ligado, s, env, numero, "quero", QUINTA_9H + timedelta(hours=1))
    assert [x[0] for x in s.enviadas[-3:]] == ["imagem", "imagem", "imagem"]
    d = destinatarios(ligado)[1]
    assert d["resposta"] == "quero" and d["imagens_enviadas"] == 3
    with conexao(ligado) as con:
        c = con.execute("SELECT tipo, wamid FROM atendimento.consentimentos").fetchone()
        avisos = con.execute("SELECT count(*) AS n FROM atendimento.avisos").fetchone()["n"]
    assert c["tipo"] == "aceite" and c["wamid"] == "wamid.toque" and avisos == 0   # quero nao avisa ninguem
    _tocar(ligado, s, env, numero, "quero", QUINTA_9H + timedelta(hours=2), wamid="wamid.toque2")
    assert len([x for x in s.enviadas if x[0] == "imagem"]) == 3                      # segundo toque nao repete


def test_nao_quero_tira_da_lista_e_avisa_o_responsavel(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10, resp=("Djeison de Oliveira", "5549999567572"))])
    numero = destinatarios(ligado)[1]["whatsapp"]
    _tocar(ligado, s, env, numero, "nao_quero", QUINTA_9H + timedelta(hours=1))
    assert s.ultima[0] == "texto" and "não vai mais receber" in s.ultima[2]
    env.rotina(ligado, s, QUINTA_9H + timedelta(hours=1, minutes=1))
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
                       imagens_enviadas = 1""", (QUINTA_9H,))
    env.rotina(ligado, s, QUINTA_9H + timedelta(hours=25))
    assert [x for x in s.enviadas if x[0] == "imagem"] == []


def test_numero_que_nao_e_whatsapp_nao_e_tentado_de_novo(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 10)])
    d = destinatarios(ligado)[1]
    falha = status(d["convite_wamid"], "failed", numero=d["whatsapp"])
    falha["errors"] = [{"code": 131026, "title": "Message undeliverable"}]
    R.gravar(ligado, aviso(statuses=[falha]))
    R.processar_pendentes(ligado, s, None, envio=env, agora=QUINTA_9H)
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
    R.processar_pendentes(ligado, s, None, envio=env, agora=QUINTA_9H + timedelta(hours=1))
    d = destinatarios(ligado)[1]
    assert d["entregue_em"] and d["lido_em"]
    assert d["resposta"] == "texto" and d["resposta_texto"] == "tem aveia branca?"
    assert s.ultima[0] == "lista"                       # e a OlivIA atende quem escreveu


def test_resumo_do_kr2(ligado, imagens):
    s, env = _convidar(ligado, imagens, [cliente(1, 30), cliente(2, 20), cliente(3, 10)])
    d = destinatarios(ligado)
    _tocar(ligado, s, env, d[1]["whatsapp"], "quero", QUINTA_9H + timedelta(hours=1), wamid="w1")
    _tocar(ligado, s, env, d[2]["whatsapp"], "nao_quero", QUINTA_9H + timedelta(hours=1), wamid="w2")
    with TestClient(criar_app(ligado)) as c:
        r = c.get("/pedido/resumo", params={"desde": "2026-10-01T00:00:00-03:00", "ate": "2026-11-01T00:00:00-03:00"},
                  headers=CHAVE).json()
    assert r == {"convidados": 3, "responderam": 2, "aceitaram": 1, "recusaram": 1}
