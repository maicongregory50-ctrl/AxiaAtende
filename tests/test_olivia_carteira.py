"""#1754: a OlivIA atende o cliente da carteira na conversa do boletim -- o pedido com as culturas, o toque em
"Quero saber mais" (chave desligada, ligada, segundo toque, quem recusou), o texto em ate 7 dias, o modo
carteira dela (instrucao, ferramentas, filtro), o interesse e a ficha, a traducao ao ERP e o vigia.
Spec: docs/specs/2026-11-24-olivia-atende-a-carteira-no-boletim.md; plano, passos 6 a 12."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import eventos_erp, interesse
from backend import olivia as O
from backend import recepcionista as R
from backend.banco import conexao
from backend.envio import Envio
from tests.avisos_meta import aviso, texto
from tests.saida_falsa import IAFalsa, SaidaFalsa
from tests.test_envio import QUINTA_10H, cliente, destinatarios, pedir

REP = "5549999567572"
CULTURAS = ["Aveia preta", "Nabo forrageiro"]
PARCERIA_TEXTO = "A safra veio curta. A prioridade é a nossa carteira. Me diga quais culturas te interessam."
DEPOIS = QUINTA_10H + timedelta(hours=1)


def _parceria(pasta, situacao):
    arquivo = pasta / "parceria.md"
    arquivo.write_text("# Parceria\n\n**Situação:** %s\n\n<!-- texto -->\n%s\n<!-- /texto -->\n"
                       % (situacao, PARCERIA_TEXTO), encoding="utf-8")
    return arquivo


@pytest.fixture
def base(cfg, tmp_path, monkeypatch):
    """O recepcionista respondendo, a OlivIA falando (OLIVIA_FALA) e o texto da parceria APROVADO; a chave
    `olivia.atende_carteira` como nasce (desligada)."""
    monkeypatch.setattr(interesse, "PARCERIA", _parceria(tmp_path, "APROVADO"))
    return replace(cfg, responde=True, olivia_fala=True, chave_pedido="chave-do-marketing",
                   envios_pasta=tmp_path / "envios", campo_pasta=tmp_path / "campo")


@pytest.fixture
def ligada(base):
    with conexao(base) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'olivia.atende_carteira'")
    return base


@pytest.fixture
def imagens(tmp_path):
    pasta = tmp_path / "marketing"
    pasta.mkdir()
    arquivos = []
    for nome in ("chamada.jpg", "boletim1.jpg", "boletim2.jpg"):
        (pasta / nome).write_bytes(b"\xff\xd8\xff" + nome.encode())
        arquivos.append(str(pasta / nome))
    return arquivos


def boletim(imagens, culturas=CULTURAS, papel="comprador", nome="JOAO DA SILVA", resp=("Djeison de Oliveira", REP)):
    c = dict(cliente(1, 30, nome=nome, resp=resp), aceite_cadastro=True, papel=papel)
    d = {"pedido_ref": "bol-2", "tipo": "direta", "modelo": "boletim_quero_saber_mais", "campanha": "CAM-0010",
         "peca": "Boletim de safra nº 2", "assunto": "", "capa": imagens[0], "imagens": imagens[1:],
         "aprovado_por": "maicon", "aprovado_em": "2026-10-07T17:00:00-03:00", "clientes": [c]}
    if culturas is not None:
        d["culturas"] = culturas
    return d


def mandar(cfg, imagens, **k):
    assert pedir(cfg, boletim(imagens, **k)).status_code == 200
    s, env = SaidaFalsa(), Envio(ler_nota=lambda: "GREEN")
    env.rotina(cfg, s, QUINTA_10H)
    return s, env, destinatarios(cfg)[1]["whatsapp"]


def tocar(cfg, s, env, numero, acao="saber", agora=DEPOIS, wamid="wamid.toque"):
    msg = {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "button",
           "context": {"from": "554936640121", "id": "wamid.convite"},
           "button": {"payload": "envio:1:%s" % acao, "text": "Quero saber mais"}}
    R.gravar(cfg, aviso([msg], numero=numero, bsuid="BR." + numero))
    R.processar_pendentes(cfg, s, None, envio=env, agora=agora)


def escrever(cfg, s, env, numero, corpo, ia, agora=DEPOIS, wamid="wamid.texto"):
    R.gravar(cfg, aviso([texto(wamid, corpo, numero=numero)], numero=numero, bsuid="BR." + numero, nome="João"))
    R.processar_pendentes(cfg, s, ia, envio=env, agora=agora)
    erros = ler(cfg, "SELECT erro FROM atendimento.eventos_meta WHERE erro <> ''")
    assert not erros, erros


def ler(cfg, sql, *args):
    with conexao(cfg) as con:
        return con.execute(sql, args).fetchall()


def resumos(cfg):
    return [r["resumo"] for r in ler(cfg, "SELECT resumo FROM atendimento.enviadas ORDER BY id")]


def janela_do(cfg, numero, agora):
    """Abre a janela de 24 h de `numero`: uma mensagem dele, com a hora de `agora`, ja processada."""
    msg = {"from": numero, "id": "wamid.rep.%s" % agora.timestamp(), "timestamp": str(int(agora.timestamp())),
           "type": "text", "text": {"body": "bom dia"}}
    R.gravar(cfg, aviso([msg], numero=numero, bsuid="BR.rep"))
    with conexao(cfg) as con:
        con.execute("UPDATE atendimento.eventos_meta SET processado_em = recebido_em, recebido_em = %s "
                    "WHERE processado_em IS NULL", (agora,))


# ── passo 5 e 6: a migracao e o pedido ──────────────────────────────────────

def test_a_077_nasce_desligada_e_o_pedido_aceita_as_culturas_ou_nao(base, imagens):
    with conexao(base) as con:
        assert interesse.ligado(con) is False and interesse.atende(con) is False
    assert pedir(base, boletim(imagens, culturas=[" Aveia  preta", "aveia preta", "Nabo forrageiro"])).status_code == 200
    assert pedir(base, dict(boletim(imagens, culturas=None), pedido_ref="bol-3")).status_code == 200
    envios = ler(base, "SELECT pedido_ref, culturas FROM atendimento.envios ORDER BY id")
    assert [(e["pedido_ref"], e["culturas"]) for e in envios] == [("bol-2", ["Aveia preta", "Nabo forrageiro"]),
                                                                  ("bol-3", [])]
    assert pedir(base, dict(boletim(imagens, culturas=["x" * 41]), pedido_ref="bol-4")).status_code == 422


def test_o_boletim_sai_com_quero_saber_mais_e_a_recusa(base, imagens):
    s, _, numero = mandar(base, imagens)
    m = next(x for x in s.modelos if x["para"] == numero)
    assert m["nome"] == "boletim_quero_saber_mais" and m["corpo"] == ["Joao"] and m["imagem"]
    assert m["botoes"] == ["envio:1:saber", "envio:1:nao_quero"] and m["url"] is None


# ── passo 7: o toque ────────────────────────────────────────────────────────

def test_toque_com_a_chave_desligada_e_o_falar_de_hoje(base, imagens):
    s, env, numero = mandar(base, imagens)
    tocar(base, s, env, numero)
    assert s.ultima[0] == "texto" and "Djeison" in s.ultima[2] and "https://wa.me/%s" % REP in s.ultima[2]
    assert destinatarios(base)[1]["resposta"] == "falar"
    assert ler(base, "SELECT * FROM atendimento.interesses") == []


def test_toque_com_a_parceria_em_rascunho_e_como_a_chave_desligada(ligada, imagens, tmp_path, monkeypatch):
    monkeypatch.setattr(interesse, "PARCERIA", _parceria(tmp_path, "RASCUNHO — aguardando o dono"))
    s, env, numero = mandar(ligada, imagens)
    tocar(ligada, s, env, numero)
    assert destinatarios(ligada)[1]["resposta"] == "falar" and "Djeison" in s.ultima[2]


def test_toque_com_a_chave_ligada_e_a_saudacao_as_imagens_e_a_parceria_do_codigo(ligada, imagens):
    s, env, numero = mandar(ligada, imagens)
    antes = len(s.enviadas)
    tocar(ligada, s, env, numero)
    saiu = s.enviadas[antes:]
    assert [x[0] for x in saiu] == ["texto", "imagem", "imagem", "texto"]
    assert saiu[0][2] == "Olá, Joao! Aqui está o material completo do boletim."
    assert saiu[1][2].endswith("01.jpg") and saiu[2][2].endswith("02.jpg")
    assert saiu[3][2] == PARCERIA_TEXTO
    d = destinatarios(ligada)[1]
    assert d["resposta"] == "saber" and d["imagens_enviadas"] == 2 and d["imagens_total"] == 2
    i = ler(ligada, "SELECT * FROM atendimento.interesses")[0]
    assert (i["entrada"], i["papel"], i["culturas"], i["enviada_em"]) == ("toque", "comprador", [], None)
    c = ler(ligada, "SELECT * FROM atendimento.conversas WHERE id = %s", i["conversa_id"])[0]
    assert c["conduzida_por"] == "olivia" and c["situacao"] == "em_curso"
    assert not any(r.startswith("portao do cliente") for r in resumos(ligada))


def test_segundo_toque_nao_repete_o_bloco(ligada, imagens):
    s, env, numero = mandar(ligada, imagens)
    tocar(ligada, s, env, numero)
    antes = len(s.enviadas)
    tocar(ligada, s, env, numero, agora=DEPOIS + timedelta(minutes=5), wamid="wamid.toque2")
    assert [x[0] for x in s.enviadas[antes:]] == ["texto"] and s.ultima[2] == Envio.DE_NOVO
    assert len(ler(ligada, "SELECT * FROM atendimento.interesses")) == 1


def test_toque_de_quem_recusou_nao_faz_nada(ligada, imagens):
    s, env, numero = mandar(ligada, imagens)
    tocar(ligada, s, env, numero, acao="nao_quero")
    antes = len(s.enviadas)
    tocar(ligada, s, env, numero, agora=DEPOIS + timedelta(minutes=5), wamid="wamid.toque2")
    assert s.enviadas[antes:] == [] and destinatarios(ligada)[1]["resposta"] == "nao_quero"


# ── passo 8: o texto em 7 dias ──────────────────────────────────────────────

def test_texto_em_7_dias_vai_a_ela_no_modo_carteira(ligada, imagens):
    s, env, numero = mandar(ligada, imagens)
    ia = IAFalsa()
    ia.conversa = [{"texto": "Oi, João! Quer que eu mande o material completo do boletim?"}]
    escrever(ligada, s, env, numero, "Vi o boletim, como está a aveia?", ia, agora=QUINTA_10H + timedelta(days=6))
    vista = ia.chamadas[0]
    assert "CLIENTE DA CARTEIRA" in vista["sistema"] and "Joao" not in vista["sistema"]   # D4: nada do cliente no cache
    assert "Primeiro nome: Joao" in vista["extra"] and "Djeison" in vista["extra"] and PARCERIA_TEXTO in vista["extra"]
    assert "Aveia preta, Nabo forrageiro" in vista["extra"]
    assert set(vista["ferramentas"]) == {"mandar_material", "anotar_interesse", "passar_representante",
                                         "oferecer_opcao_da_carteira", "encerrar"}
    assert s.ultima[2].startswith("Oi, João!")
    d = destinatarios(ligada)[1]
    assert d["resposta"] == "saber" and d["resposta_texto"] == "Vi o boletim, como está a aveia?"
    assert ler(ligada, "SELECT entrada FROM atendimento.interesses")[0]["entrada"] == "texto"


@pytest.mark.parametrize("quando,chave", [(timedelta(days=8), True), (timedelta(days=1), False)])
def test_fora_dos_7_dias_ou_com_a_chave_desligada_e_o_portao(base, imagens, quando, chave):
    if chave:
        with conexao(base) as con:
            con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'olivia.atende_carteira'")
    s, env, numero = mandar(base, imagens)
    ia = IAFalsa()
    escrever(base, s, env, numero, "bom dia, quero falar do boleto", ia, agora=QUINTA_10H + quando)
    assert not getattr(ia, "chamadas", [])
    assert ler(base, "SELECT * FROM atendimento.interesses") == []
    assert any(r.startswith("portao do cliente") for r in resumos(base))


def test_a_ia_fora_no_texto_desfaz_a_conversa_e_cai_no_portao(ligada, imagens):
    s, env, numero = mandar(ligada, imagens)
    escrever(ligada, s, env, numero, "quero saber da aveia", IAFalsa(falha=True))
    assert ler(ligada, "SELECT * FROM atendimento.interesses") == []
    assert destinatarios(ligada)[1]["resposta"] != "saber"
    assert any(r.startswith("portao do cliente") for r in resumos(ligada))


# ── passo 9: o modo carteira ────────────────────────────────────────────────

def test_sem_culturas_no_pedido_anotar_interesse_nao_e_oferecida(ligada, imagens):
    s, env, numero = mandar(ligada, imagens, culturas=None)
    ia = IAFalsa()
    ia.conversa = [{"texto": "Oi! Posso te passar o contato de quem cuida de você."}]
    escrever(ligada, s, env, numero, "tenho interesse", ia)
    assert "anotar_interesse" not in ia.chamadas[0]["ferramentas"]
    assert "não anote interesse" in ia.chamadas[0]["extra"]


def test_ferramenta_fora_da_lista_e_recusada(ligada, imagens):
    s, env, numero = mandar(ligada, imagens)
    ia = IAFalsa()
    ia.conversa = [{"ferramentas": [("passar_contato", {"chave": "comercial.produtor.sc"})]}, {"texto": "Certo."}]
    escrever(ligada, s, env, numero, "quero comprar", ia)
    assert "não está disponível" in ia.chamadas[-1]["mensagens"][-1]["content"][0]["content"]
    assert "contato" not in [x[0] for x in s.enviadas]


def test_fala_com_valor_e_trocada_pelo_filtro(ligada, imagens):
    s, env, numero = mandar(ligada, imagens)
    ia = IAFalsa()
    ia.conversa = [{"texto": "A aveia está R$ 3,00 o quilo."}]
    escrever(ligada, s, env, numero, "quanto está a aveia?", ia)
    assert s.ultima[2] == O.FRASE_DA_CARTEIRA
    assert "olivia: recusada: valor" in resumos(ligada)


# ── passo 10: o interesse e a ficha ─────────────────────────────────────────

def _conversa_com_interesse(cfg, imagens, ia, janela_rep: bool, **k):
    s, env, numero = mandar(cfg, imagens, **k)
    if janela_rep:
        janela_do(cfg, REP, DEPOIS - timedelta(hours=1))
    ia.conversa = [{"texto": "Anotei!", "ferramentas": [("anotar_interesse", {"culturas": ["Aveia preta", "Soja"]})]},
                   {"texto": "Anotei a aveia preta, e o Djeison já sabe do seu interesse."}]
    escrever(cfg, s, env, numero, "me interessa aveia preta e soja", ia)
    return s, numero


def test_ficha_na_janela_vai_como_texto_ao_responsavel(ligada, imagens):
    ia = IAFalsa()
    s, numero = _conversa_com_interesse(ligada, imagens, ia, janela_rep=True)
    ficha = next(x for x in s.enviadas if x[1] == REP and x[0] == "texto")
    assert "*Interesse no boletim*" in ficha[2] and "Culturas: Aveia preta" in ficha[2]
    assert "Quem falou: comprador" in ficha[2] and "me interessa aveia preta e soja" in ficha[2]
    assert "https://wa.me/%s" % numero in ficha[2]
    i = ler(ligada, "SELECT * FROM atendimento.interesses")[0]
    assert i["culturas"] == ["Aveia preta"] and i["enviada_como"] == "texto" and i["erro"] == ""
    assert s.ultima[1] == numero and s.ultima[2].startswith("Anotei a aveia preta")   # a fala, depois da ficha
    assert "SAIU" in ia.chamadas[1]["mensagens"][-1]["content"][0]["content"]


def test_ficha_fora_da_janela_vai_pelo_olivia_resumo(ligada, imagens):
    ia = IAFalsa()
    s, _ = _conversa_com_interesse(ligada, imagens, ia, janela_rep=False)
    m = next(x for x in s.modelos if x["para"] == REP and x["nome"] == "olivia_resumo")
    assert "Interesse no boletim" in m["corpo"][0] and "\n" not in m["corpo"][0] and len(m["corpo"][0]) <= 900
    assert ler(ligada, "SELECT enviada_como FROM atendimento.interesses")[0]["enviada_como"] == "modelo"


def test_ficha_que_falha_troca_a_fala_e_guarda_o_erro(ligada, imagens):
    ia = IAFalsa()
    s, env, numero = mandar(ligada, imagens)
    s.modelo_falha = "131047"
    ia.conversa = [{"ferramentas": [("anotar_interesse", {"culturas": ["Nabo forrageiro"]})]},
                   {"texto": "Pronto, já avisei o Djeison do seu interesse."}]
    escrever(ligada, s, env, numero, "nabo", ia)
    i = ler(ligada, "SELECT * FROM atendimento.interesses")[0]
    assert i["enviada_em"] is None and "131047" in i["erro"]
    assert s.ultima[2] == O.SEM_FICHA_DA_CARTEIRA % "Djeison"
    assert O.RECUSADA_AVISO in resumos(ligada)


def test_responsavel_igual_a_quem_escreve_nao_recebe_ficha(ligada, imagens):
    ia = IAFalsa()
    numero_cliente = "55" + cliente(1, 30)["whatsapp"]
    s, env, numero = mandar(ligada, imagens, resp=("Joao", numero_cliente))
    ia.conversa = [{"ferramentas": [("anotar_interesse", {"culturas": ["Aveia preta"]})]}, {"texto": "Anotado."}]
    escrever(ligada, s, env, numero, "aveia", ia)
    i = ler(ligada, "SELECT * FROM atendimento.interesses")[0]
    assert i["enviada_em"] is None and "própria pessoa" in i["erro"]


def test_passar_representante_manda_a_ficha_e_a_linha_depois_da_fala(ligada, imagens):
    ia = IAFalsa()
    s, env, numero = mandar(ligada, imagens)
    janela_do(ligada, REP, DEPOIS - timedelta(hours=1))
    ia.conversa = [{"texto": "Claro! Quem cuida de você é o Djeison.", "ferramentas": [("passar_representante", {})]},
                   {}]
    escrever(ligada, s, env, numero, "quero falar com o vendedor", ia)
    para_ele = [x for x in s.enviadas if x[1] == numero]
    assert para_ele[-2][2] == "Claro! Quem cuida de você é o Djeison."
    assert "https://wa.me/%s" % REP in para_ele[-1][2]
    assert ler(ligada, "SELECT enviada_em FROM atendimento.interesses")[0]["enviada_em"] is not None
    assert "Culturas: não indicou" in next(x for x in s.enviadas if x[1] == REP)[2]


# ── passo 11: o ERP ─────────────────────────────────────────────────────────

def test_o_erp_recebe_falar_enquanto_corre_e_texto_com_o_interesse_depois(ligada, imagens):
    ia = IAFalsa()
    s, env, numero = mandar(ligada, imagens)
    tocar(ligada, s, env, numero)
    with conexao(ligada) as con:
        e = eventos_erp.montar(con, DEPOIS + timedelta(minutes=1))[0]
    assert (e["resposta"], e["resposta_texto"]) == ("falar", None)
    janela_do(ligada, REP, DEPOIS)
    ia.conversa = [{"ferramentas": [("anotar_interesse", {"culturas": ["Aveia preta", "Nabo forrageiro"]})]},
                   {"texto": "Anotado."}]
    escrever(ligada, s, env, numero, "aveia preta e nabo", ia, agora=DEPOIS + timedelta(minutes=2))
    with conexao(ligada) as con:
        e = eventos_erp.montar(con, DEPOIS + timedelta(minutes=3))[0]
    assert e["resposta"] == "texto"
    assert e["resposta_texto"].startswith("Quis saber mais. Interesse: Aveia preta, Nabo forrageiro.")
    assert "aveia preta e nabo" in e["resposta_texto"] and len(e["resposta_texto"]) <= 500
    with conexao(ligada) as con:   # nenhum valor novo sai cru
        assert all(x["resposta"] in (None, "quero", "nao_quero", "texto", "falar")
                   for x in eventos_erp.montar(con, DEPOIS + timedelta(minutes=3)))


def test_resposta_ao_erp_sem_cultura_e_quis_saber_mais_e_corta_em_500():
    agora = DEPOIS
    assert interesse.resposta_ao_erp({"conversa_aberta": False, "culturas": []}, agora) == ("texto", "Quis saber mais.")
    r = interesse.resposta_ao_erp({"conversa_aberta": True, "resposta_em": agora - timedelta(hours=25),
                                   "escreveu": "x" * 900}, agora)
    assert r[0] == "texto" and len(r[1]) == 500
    assert interesse.resposta_ao_erp({"conversa_aberta": True, "resposta_em": agora}, agora) == ("falar", None)


# ── passo 12: o vigia ───────────────────────────────────────────────────────

def test_o_vigia_conta_a_carteira_e_avisa_a_ficha_com_erro(ligada, imagens):
    ia = IAFalsa()
    s, env, numero = mandar(ligada, imagens)
    s.modelo_falha = "131047"
    ia.conversa = [{"ferramentas": [("anotar_interesse", {"culturas": ["Aveia preta"]})]}, {"texto": "Anotado."}]
    escrever(ligada, s, env, numero, "aveia", ia)
    with conexao(ligada) as con:
        n = O.fechar_dia(con, DEPOIS + timedelta(hours=2))
    assert n["carteira"] == {"conversas": 1, "interesses": 1, "fichas_com_erro": 1} and n["avisou"]
    texto_aviso = ler(ligada, "SELECT sobre FROM atendimento.avisos WHERE tipo = 'olivia_resumo'")[0]["sobre"]
    assert "carteira: 1 conversa, 1 com interesse, 1 ficha com erro" in texto_aviso


def test_parceria_le_so_o_aprovado_e_o_texto_entre_as_marcas(tmp_path):
    assert interesse.parceria(_parceria(tmp_path, "APROVADO")) == (True, PARCERIA_TEXTO)
    assert interesse.parceria(_parceria(tmp_path, "RASCUNHO — aguardando o dono")) == (False, PARCERIA_TEXTO)
    assert interesse.parceria(tmp_path / "nao-existe.md") == (False, "")
    aprovado, texto_real = interesse.parceria(interesse.Path(__file__).resolve().parent.parent / "docs" / "olivia"
                                              / "parceria-da-carteira.md")
    assert texto_real.startswith("A safra de sementes de cobertura")


def test_a_instrucao_responde_a_pergunta_da_ia_e_oferece_o_contato_uma_vez(ligada):
    """Prova do dono, 24/11/2026: "Falo com uma IA?" ficou sem resposta e o contato saiu sem pedido."""
    with conexao(ligada) as con:
        i = O.instrucao_da_carteira(con)
    assert "Sou a OlivIA, a assistente virtual da Renascer" in i and "Não use ferramenta nenhuma" in i
    assert "ofereça UMA vez" in i and "SÓ" in i


def test_cultura_fora_da_lista_vai_na_ficha_pelo_que_escreveu(ligada, imagens):
    """Prova do dono, 24/11/2026: pediu centeio (fora do boletim) e ouviu "nao consigo anotar"."""
    ia = IAFalsa()
    s, env, numero = mandar(ligada, imagens)
    janela_do(ligada, REP, DEPOIS - timedelta(hours=1))
    ia.conversa = [{"ferramentas": [("anotar_interesse", {"culturas": []})]},
                   {"texto": "Passei o seu pedido de centeio ao Djeison."}]
    escrever(ligada, s, env, numero, "quero centeio", ia)
    ficha = next(x for x in s.enviadas if x[1] == REP and x[0] == "texto")
    assert "Culturas: não indicou" in ficha[2] and "quero centeio" in ficha[2]
    i = ler(ligada, "SELECT * FROM atendimento.interesses")[0]
    assert i["culturas"] == [] and i["enviada_como"] == "texto"
    assert "SAIU" in ia.chamadas[1]["mensagens"][-1]["content"][0]["content"]
    with conexao(ligada) as con:
        assert "NÃO diga que não pode anotar" in O.instrucao_da_carteira(con)
