"""F1 do plano #950: as rotas das telas Recepcao, Envios e Destinos, com login."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import recepcionista as R
from backend import seguranca
from backend.banco import conexao
from backend.envio import Envio
from backend.main import CABECALHO_DA_TELA, criar_app
from backend.rotas_telas import _sem_nove, link_conversa, mascarar
from tests.avisos_meta import aviso, texto, toque
from tests.saida_falsa import SaidaFalsa
from tests.test_1192_janela import dia_util_10h
from tests.test_envio import cliente, pedido, pedir

AGORA = datetime.now(timezone.utc)


@pytest.fixture
def ligado(cfg, tmp_path):
    return replace(cfg, responde=True, chave_pedido="chave-do-marketing", envios_pasta=tmp_path / "envios")


@pytest.fixture
def tela(ligado):
    with conexao(ligado) as con:
        con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash) VALUES ('dono', 'Dono', %s)",
                    (seguranca.gerar_hash("senha-de-teste-1"),))
    seguranca.limpar_erros("dono")
    with TestClient(criar_app(ligado), headers={CABECALHO_DA_TELA: "1"}) as c:
        assert c.post("/api/entrar", json={"login": "dono", "senha": "senha-de-teste-1"}).status_code == 200
        yield c


def test_sem_login_nada(ligado):
    with TestClient(criar_app(ligado)) as c:
        for rota in ("/api/recepcao", "/api/envios", "/api/destinos"):
            assert c.get(rota).status_code == 401


def test_mascara_nunca_mostra_o_numero_inteiro():
    assert mascarar("5546999784298") == "+55 46 9…·4298"
    assert mascarar(None) == "sem número"


def test_link_da_conversa_usa_o_numero_da_meta_e_cala_quando_nao_ha():
    """#1025: o link da coluna QUEM."""
    # o wa_id como a Meta o entregou, sem acrescentar o nono digito do cadastro do ERP
    assert link_conversa("554699784298") == "https://web.whatsapp.com/send?phone=554699784298"
    assert link_conversa("5546999784298") == "https://web.whatsapp.com/send?phone=5546999784298"
    # o numero e opcional por desenho (regra 7: a conversa e chaveada pelo BSUID). Sem ele, SEM LINK
    # -- nunca um link morto. Hoje sao 0 linhas no banco, e e justamente por isso que o teste existe.
    assert link_conversa(None) is None
    assert link_conversa("") is None
    # o mesmo limiar da mascara: o que ela chama de "sem numero" nao vira link
    assert mascarar("55469") == "sem número" and link_conversa("55469") is None


def test_recepcao_conta_e_lista(ligado, tela):
    s = SaidaFalsa()
    R.gravar(ligado, aviso([toque("w1", "menu:fretes", lista=True)]))
    R.gravar(ligado, aviso([texto("w2", "oi")], numero="5549988887777", bsuid="BR.2"))
    R.processar_pendentes(ligado, s, None, agora=AGORA - timedelta(hours=1))
    R.rotina_do_minuto(ligado, s, agora=AGORA)          # a 2a parou no meio (sem toque ha 1 h)
    d = tela.get("/api/recepcao", params={"dias": 7}).json()
    assert d["cartoes"]["chegaram"] == 2 and d["cartoes"]["receberam_link"] == 1
    assert d["cartoes"]["pararam_no_meio"] == 1
    fretes = next(l for l in d["linhas"] if l["destino"])
    assert fretes["destino"] == "Benedito" and fretes["caminho"] == ["🚚 Fretes"] and "…" in fretes["numero"]
    # #1025: a linha leva o endereco pronto, e a tela so o desenha
    assert fretes["conversar"] == "https://web.whatsapp.com/send?phone=5549999990000"
    assert [l["estado"] for l in tela.get("/api/recepcao", params={"situacao": "parou"}).json()["linhas"]] == ["parou"]
    assert [m["chave"] for m in d["motivos"]][:2] == ["comercial", "fretes"]


def test_um_contato_por_numero_com_a_ultima_mensagem_em_qualquer_sentido(ligado, tela):
    """#1249 (dono, 04/11): "cada numero que entra gera UMA linha, atualizada com a data e hora da ultima
    mensagem, recebida ou enviada; fica tudo num historico so". O DJ (logo + foto, sem conversa) e o
    Benedito ("Bom dia" + chamados) aparecem; quem chamou pelo menu continua aparecendo, uma linha por
    numero mesmo com dois atendimentos; a janela abre pelo numero, de dentro ou de fora da casa."""
    with conexao(ligado) as con:
        con.execute("""INSERT INTO atendimento.agenda (numero, codigo, nome, papeis, contato_setor, contato_nome)
                       VALUES ('5549999570001', 4445, 'DJ AGRO', ARRAY['representante','cliente'], '', '')""")
        con.execute("INSERT INTO atendimento.agenda_leitura (linhas) VALUES (1)")
        con.execute("""INSERT INTO atendimento.logos_de_cliente (bsuid, wa_id, wamid, nome_arquivo, pergunta_pendente)
                       VALUES ('BR.dj', '554999570001', 'wamid.logo', 'logo.pdf', 'erp_codigo')""")
    foto = {"from": "554999570001", "id": "wamid.f1", "type": "image", "image": {"id": "m1"}}
    doc = {"from": "554999570001", "id": "wamid.d1", "type": "document",
           "document": {"id": "m2", "mime_type": "application/pdf", "filename": "logo.pdf"}}
    R.gravar(ligado, aviso([foto, doc], numero="554999570001", bsuid="BR.dj"))
    s = SaidaFalsa()
    R.gravar(ligado, aviso([toque("w1", "menu:fretes", lista=True)]))                       # 5549999990000, 1o atendimento
    R.processar_pendentes(ligado, s, None, agora=AGORA - timedelta(hours=2))
    R.gravar(ligado, aviso([toque("w2", "menu:comercial", lista=True)]))                   # o mesmo numero, 2o atendimento
    R.processar_pendentes(ligado, s, None, agora=AGORA - timedelta(hours=1))
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.eventos_meta SET processado_em = now() WHERE processado_em IS NULL")
    d = tela.get("/api/recepcao", params={"dias": 7}).json()
    chaves = [_sem_nove(l["pessoa"]) for l in d["linhas"]]   # o numero de teste vem com o 9
    assert chaves.count("554999570001") == 1 and chaves.count("554999990000") == 1       # uma linha por numero
    dj = next(l for l in d["linhas"] if l["pessoa"] == "554999570001")
    assert dj["cadastro"]["nome"] == "DJ AGRO" and dj["estado"] == "equipe" and dj["interno"] is True
    assert dj["pendente"] == "logo sem cliente" and dj["recebidas"] == 2   # a pergunta da logo saiu: enviadas >= 1
    menu = next(l for l in d["linhas"] if _sem_nove(l["pessoa"]) == "554999990000")
    assert menu["caminho"] == ["🛒 Comercial"] and menu["recebidas"] == 2 and menu["enviadas"] >= 2   # o ultimo atendimento
    assert menu["quando"] >= menu["enviada_em"] and menu["quando"] >= menu["recebida_em"]
    assert d["cartoes"]["contatos"] == 2 and d["cartoes"]["equipe"] == 1 and d["cartoes"]["chegaram"] == 2
    assert [l["pessoa"] for l in tela.get("/api/recepcao", params={"situacao": "equipe"}).json()["linhas"]] == ["554999570001"]
    assert tela.get("/api/recepcao", params={"quem": "fora"}).json()["cartoes"]["equipe"] == 0
    j = tela.get("/api/recepcao/pessoa/554999570001").json()
    assert j["pessoa"]["nome"] == "DJ AGRO" and j["pessoa"]["codigo"] == 4445 and len(j["itens"]) >= 2
    fora = tela.get("/api/recepcao/pessoa/5549999990000").json()                              # de fora: tambem abre
    assert fora["pessoa"]["codigo"] is None and len(fora["itens"]) >= 4
    # dono, 04/11: o robo (so mensagem sem tipo, sem atendimento) nao e contato
    robo = {"from": "5511933157031", "id": "wamid.r1", "type": "unsupported", "errors": [{"code": 131051}]}
    R.gravar(ligado, aviso([robo], numero="5511933157031", bsuid="BR.robo"))
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.eventos_meta SET processado_em = now() WHERE processado_em IS NULL")
    assert "5511933157031" not in [l["pessoa"] for l in tela.get("/api/recepcao", params={"dias": 7}).json()["linhas"]]


def test_envios_lista_detalhe_e_religar(ligado, tela, tmp_path):
    pasta = tmp_path / "mk"
    pasta.mkdir()
    imgs = []
    for n in ("capa.jpg", "t1.jpg"):
        (pasta / n).write_bytes(b"\xff\xd8\xff")
        imgs.append(str(pasta / n))
    pedir(ligado, pedido(imgs, [cliente(1, 10), cliente(2, 5, resp=("", ""))]))
    Envio(ler_nota=lambda: "YELLOW").rotina(ligado, SaidaFalsa(), dia_util_10h())   # #1192: dentro da janela
    lista = tela.get("/api/envios").json()
    assert lista["envios"][0]["situacao"] == "parado_nota" and lista["nota"]["nota"] == "YELLOW"
    d = tela.get("/api/envios/1").json()
    assert d["cartoes"]["sem_responsavel"] == 1 and d["cartoes"]["aguardando"] == 1
    assert {l["situacao"] for l in d["linhas"]} == {"aguardando", "sem_responsavel"}
    assert tela.post("/api/envios/1/religar").status_code == 200
    assert tela.post("/api/envios/1/religar").status_code == 422
    assert tela.get("/api/envios/99").status_code == 404


def test_1169_suspender_religar_e_segurar_tudo_pela_tela(ligado, tela, tmp_path):
    pasta = tmp_path / "mk1169"
    pasta.mkdir()
    imgs = []
    for n in ("capa.jpg", "t1.jpg"):
        (pasta / n).write_bytes(bytes([0xFF, 0xD8, 0xFF]))
        imgs.append(str(pasta / n))
    pedir(ligado, pedido(imgs, [cliente(1, 10)]))
    assert tela.post("/api/envios/1/suspender").status_code == 200
    e = tela.get("/api/envios").json()["envios"][0]
    assert e["situacao"] == "suspenso" and e["suspenso_por"] and e["suspenso_em"]
    assert tela.post("/api/envios/1/suspender").status_code == 422                 # ja esta suspenso
    r = tela.put("/api/ajustes/segurar-envio", json={"ligado": True}).json()
    assert r["ligado"] is True and r["por"] and r["em"]
    assert tela.get("/api/envios").json()["segurado"]["ligado"] is True
    assert "SEGURADO" in tela.post("/api/envios/1/religar").json()["detail"]      # com a trava, nao religa
    assert tela.put("/api/ajustes/segurar-envio", json={"ligado": False}).json()["ligado"] is False
    assert tela.post("/api/envios/1/religar").status_code == 200
    assert tela.get("/api/envios").json()["envios"][0]["situacao"] == "ativo"
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.envios SET situacao = 'concluido'")
    assert tela.post("/api/envios/1/suspender").status_code == 422                 # concluido nao se suspende
    assert tela.post("/api/envios/1/religar").status_code == 422


def test_destinos_trocar_numero_ligar_opcao_e_horario(ligado, tela):
    d = tela.get("/api/destinos").json()
    cascavel = next(o for o in d["opcoes"] if o["chave"] == "comercial.produtor.pr.cascavel")
    assert cascavel["caminho"] == ["🛒 Comercial", "Produtor rural", "PR", "Cascavel"]
    assert cascavel["perguntas"][1] == "Qual a sua área de atuação?"
    willian = next(x for x in d["destinos"] if x["nome"] == "Willian Souza")
    assert tela.put("/api/destinos/%d" % willian["id"], json={"nome": "Willian Souza", "whatsapp": "46 99999-1234"}).json()["whatsapp"] == "5546999991234"
    assert tela.put("/api/destinos/%d" % willian["id"], json={"nome": "W", "whatsapp": "123"}).status_code == 422
    novo = tela.post("/api/destinos", json={"nome": "Rep Oeste", "whatsapp": "(46) 98888-7777"}).json()
    assert tela.put("/api/opcoes/%d" % cascavel["id"], json={"destino_id": novo["id"]}).status_code == 200
    s = SaidaFalsa()
    R.gravar(ligado, aviso([toque("w9", "menu:comercial.produtor.pr.cascavel")]))
    R.processar_pendentes(ligado, s, None, agora=datetime(2026, 10, 8, 17, 0, tzinfo=timezone.utc))
    assert s.ultima[2] == "Rep Oeste" and s.ultima[3] == ["5546988887777"]   # vale para a proxima pessoa
    h = {"dias": [1, 2, 3, 4, 5, 6], "faixas": [["08:00", "12:00"]]}
    assert tela.put("/api/ajustes/horario", json=h).json() == h
    assert tela.put("/api/ajustes/horario", json={"dias": [9], "faixas": [["8", "x"]]}).status_code == 422
    assert tela.put("/api/ajustes/avisado", json={"destino_id": novo["id"]}).status_code == 200
    # #970: a chave do canal de campo nasce desligada e liga pela tela
    assert tela.get("/api/destinos").json()["campo_ligado"] is False
    assert tela.put("/api/ajustes/campo", json={"ligado": True}).json() == {"campo_ligado": True}
    assert tela.get("/api/destinos").json()["campo_ligado"] is True


def test_1204_a_conversa_do_portao_retroativo_nao_e_chegada(ligado, tela):
    """29/10 09:28: o script abriu a da COPERMAP, e a Recepcao a mostrava como "so chegou / parou no meio"."""
    with conexao(ligado) as con:
        con.execute("""INSERT INTO atendimento.conversas (bsuid, wa_id, situacao, origem, iniciada_em)
                       VALUES ('BR.1', '554988116066', 'parou_no_meio', 'portao_retroativo', now() - interval '1 hour'),
                              ('BR.2', '5549988887777', 'parou_no_meio', 'mensagem', now() - interval '2 hours')""")
    # dono, 30/10: a que nos abrimos nem aparece -- nem na lista, nem nos cartoes
    d = tela.get("/api/recepcao", params={"dias": 7}).json()
    assert d["cartoes"]["chegaram"] == 1 and d["cartoes"]["pararam_no_meio"] == 1
    assert [(l["numero"][-4:], l["estado"]) for l in d["linhas"]] == [("7777", "parou")]


def test_1205_a_janela_le_a_pessoa_inteira_com_o_atendimento_em_destaque(ligado, tela):
    import json
    with conexao(ligado) as con:
        ids = [r["id"] for r in con.execute(
            """INSERT INTO atendimento.conversas (bsuid, wa_id, nome_perfil, iniciada_em, situacao) VALUES
                 ('BR.c', '554988116066', 'Alex Sandro Compras Copermap', now() - interval '2 hours', 'parou_no_meio'),
                 ('BR.c', '554988116066', 'Alex Sandro Compras Copermap', now() - interval '1 hour', 'em_curso')
               RETURNING id""").fetchall()]
        con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo, status, enviada_em)
                       VALUES ('wamid.m1', '554988116066', 'lista', 'menu principal', 'lida', now() - interval '90 minutes')""")
    R.gravar(ligado, aviso([texto("wamid.e1", "Como posso lhe ajudar?", numero="554988116066")],
                           numero="554988116066", bsuid="BR.c"))
    with conexao(ligado) as con:   # a mensagem que ABRIU o 2o atendimento: chegou 1 s antes de ele nascer
        assert con.execute("""UPDATE atendimento.eventos_meta e SET processado_em = c.iniciada_em,
                                     recebido_em = c.iniciada_em - interval '1 second'
                                FROM atendimento.conversas c WHERE c.id = %s AND e.chave_meta = 'wamid.e1'""",
                           (ids[1],)).rowcount == 1
    d = tela.get("/api/recepcao/conversa/%d" % ids[1]).json()
    assert d["pessoa"]["nome"] == "Alex Sandro Compras Copermap" and "…" in d["pessoa"]["numero"]
    assert [(i["lado"], i["texto"], i["resumo"], i["destaque"]) for i in d["itens"]] == [
        ("marco", "atendimento", False, False),
        ("nos", "menu principal", True, False),
        ("marco", "atendimento", False, True),
        ("cliente", "Como posso lhe ajudar?", False, True)]
    assert tela.get("/api/recepcao/conversa/999999").status_code == 404
    registro = [json.loads(l) for l in (ligado.logs / "telas" / "leituras.jsonl").read_text(encoding="utf-8").splitlines()]
    assert registro[-1]["quem"] == "dono" and registro[-1]["conversa"] == ids[1] and registro[-1]["itens"] == 4
    with TestClient(criar_app(ligado)) as sem_login:
        assert sem_login.get("/api/recepcao/conversa/%d" % ids[1]).status_code == 401


def test_recepcao_conversa_de_vaga_nao_e_parou_no_meio(ligado, tela):
    """#1098: quem chegou pelo anuncio e nao mandou o PDF termina "sem curriculo", fora das paradas."""
    # #1474: a 062 fechou a Comercial; este teste nasceu com ela como a unica aberta (o anuncio
    # 120249624037810192 e dela). O mesmo estado da fixture `so_a_comercial` de test_vaga.py.
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.vagas SET aberta = (id = 1), fechada_em = CASE WHEN id = 1 THEN NULL ELSE now() END")
    s = SaidaFalsa()
    m = texto("w1", "Olá! Posso ter mais informações sobre isso?", numero="5549988887777")
    m["referral"] = {"source_type": "ad", "source_id": "120249624037810192"}
    R.gravar(ligado, aviso([m], numero="5549988887777", bsuid="BR.2"))
    R.processar_pendentes(ligado, s, None, agora=AGORA - timedelta(hours=1))
    R.rotina_do_minuto(ligado, s, agora=AGORA)
    d = tela.get("/api/recepcao", params={"dias": 7}).json()
    assert d["cartoes"]["pararam_no_meio"] == 0
    assert [l["estado"] for l in d["linhas"]] == ["sem_curriculo"]


def test_destinos_mostra_a_vaga_fecha_e_desliga_a_triagem(ligado, tela):
    # #1474: a 062 fechou a Comercial; este teste nasceu com ela como a unica aberta (o anuncio
    # 120249624037810192 e dela). O mesmo estado da fixture `so_a_comercial` de test_vaga.py.
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.vagas SET aberta = (id = 1), fechada_em = CASE WHEN id = 1 THEN NULL ELSE now() END")
    d = tela.get("/api/destinos").json()
    trabalhe = next(o for o in d["opcoes"] if o["chave"] == "trabalhe")   # a Fran continua trocavel
    assert trabalhe["destino_id"]
    assert tela.put("/api/opcoes/%d" % trabalhe["id"], json={"destino_id": trabalhe["destino_id"]}).json() == {"ok": True}
    v = d["vagas"][0]
    assert v["titulo"] == "Vaga Comercial" and v["aberta"] and v["triagem_ligada"] and v["curriculos"] == 0
    assert tela.put("/api/vagas/%d/triagem" % v["id"], json={"ligada": False}).json() == {"triagem_ligada": False}
    assert tela.post("/api/vagas/%d/fechar" % v["id"]).status_code == 200
    assert tela.post("/api/vagas/%d/fechar" % v["id"]).status_code == 422   # ja fechada
    # #1474: com as tres vagas na tabela, a primeira da lista depois de fechar nao e mais a Comercial
    # (a ordem e aberta primeiro, depois a mais nova): procura-se pelo id.
    v = next(x for x in tela.get("/api/destinos").json()["vagas"] if x["id"] == v["id"])
    assert not v["aberta"] and not v["triagem_ligada"] and v["fechada_em"]
