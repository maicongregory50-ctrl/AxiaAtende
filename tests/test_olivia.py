"""#1520: a OlivIA anonima fala. Os casos de 12/11/2026 (Deivid, Leomar, Joao Ficagna), o filtro de saida,
o gatilho de erro repetido, quem NAO passa por ela, a chave desligada, o vigia e a API fora."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import olivia as O
from backend import recepcionista as R
from backend import vaga as V
from backend.banco import conexao
from tests.avisos_meta import aviso, texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa

AGORA = datetime(2026, 11, 13, 13, 0, tzinfo=timezone.utc)   # 10:00 em Brasilia, sexta
DE_FORA = "5549988881111"


@pytest.fixture
def ligada(cfg, tmp_path):
    return replace(cfg, responde=True, olivia_fala=True, campo_pasta=tmp_path / "campo")


@pytest.fixture
def desligada(cfg, tmp_path):
    return replace(cfg, responde=True, campo_pasta=tmp_path / "campo")


def passo(cfg, s, mensagem, ia=None, agora=AGORA, numero=DE_FORA, bsuid="BR.fora.1", nome="Deivid Betancourt",
          envio=None):
    R.gravar(cfg, aviso([mensagem], numero=numero, bsuid=bsuid, nome=nome))
    R.processar_pendentes(cfg, s, ia, envio=envio, agora=agora)
    with conexao(cfg) as con:
        erros = con.execute("SELECT erro FROM atendimento.eventos_meta WHERE erro <> ''").fetchall()
    assert not erros, erros


def foto(wamid, numero=DE_FORA, media="mid-foto", legenda=""):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "image",
            "image": {"id": media, "mime_type": "image/jpeg", "caption": legenda}}


def doc(wamid, numero=DE_FORA, media="mid-pdf", nome="Curriculo Leomar.pdf", mime="application/pdf"):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "document",
            "document": {"id": media, "mime_type": mime, "filename": nome}}


def enviadas(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.enviadas ORDER BY id").fetchall()


def conversa(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.conversas ORDER BY id DESC LIMIT 1").fetchone()


def candidaturas(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.candidaturas ORDER BY id").fetchall()


def fran(cfg):
    with conexao(cfg) as con:
        return V.quem_atende(con)["whatsapp"]


# ── (a) Deivid: espanhol, "Era outro assunto", a foto do curriculo ──────────

def test_a_deivid_em_espanhol_manda_a_foto_e_ela_vira_curriculo_sem_triagem(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "¡Hola, Deivid! Sí, estamos contratando. ¿Puedes enviarme tu currículum?"}]
    passo(ligada, s, texto("w1", "Hola, quiero más información sobre el trabajo", numero=DE_FORA), ia=ia)
    assert s.ultima[0] == "texto" and s.ultima[2].startswith("¡Hola, Deivid!")
    assert conversa(ligada)["conduzida_por"] == "olivia"
    # a foto: ela le, encaminha ao banco (sem vaga dita) e responde em espanhol
    ia.conversa = [{"ferramentas": [("ler_arquivo_recebido", {})]},
                   {"ferramentas": [("encaminhar_curriculo", {"vaga_id": None})]},
                   {"texto": "¡Recibido! El equipo lo va a analizar."}]
    passo(ligada, s, foto("w2"), ia=ia)
    assert ia.arquivos_lidos == ["image/jpeg"]
    c = candidaturas(ligada)
    assert len(c) == 1 and c[0]["tipo_arquivo"] == "imagem" and c[0]["vaga_id"] is None
    assert c[0]["triagem_erro"] == V.SEM_TRIAGEM_FOTO and c[0]["triagem_em"] is not None
    assert s.ultima[2] == "¡Recibido! El equipo lo va a analizar."
    # a Fran recebe a IMAGEM, com legenda e so o "Conversar" (sem os botoes da triagem)
    with conexao(ligada) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, bsuid, corpo, recebido_em, processado_em)
                       VALUES ('fran-escreveu', 'mensagem', 'BR.fran', %s, %s, %s)""",
                    ('{"msg": {"from": "%s", "type": "text"}}' % fran(ligada), AGORA, AGORA))
        assert V.mandar_a_fran(con, s, IAFalsa(), "segredo", AGORA + timedelta(minutes=1)) == 1
    tipo, para, _, opcoes = s.ultima
    assert tipo == "imagem" and para == fran(ligada) and [o[1] for o in opcoes] == ["Conversar"]
    assert s.legendas[-1].startswith("Currículo em foto (sem pré-triagem)")


def test_a_foto_fora_da_janela_da_fran_vai_no_modelo_como_pdf(ligada):
    s = SaidaFalsa()
    s.baixar = lambda media_id, destino: (__import__("pathlib").Path(destino).write_bytes(JPEG), str(destino))[1]
    ia = IAFalsa()
    ia.conversa = [{"ferramentas": [("encaminhar_curriculo", {"vaga_id": 2})]}, {"texto": "Recebi!"}]
    passo(ligada, s, foto("w1"), ia=ia)
    with conexao(ligada) as con:
        assert V.mandar_a_fran(con, s, IAFalsa(), "segredo", AGORA + timedelta(minutes=1)) == 1
    m = s.modelos[-1]
    assert m["documento"][1] == "curriculo-foto.pdf" and m["documento"][0].startswith(b"%PDF-1.4")
    assert JPEG in m["documento"][0]


JPEG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffc0001108000a001403012200021101031101ffd9")


# ── (b) Leomar: apresentacao e o PDF fora do fluxo, duas vezes ───────────────

def test_b_leomar_pdf_fora_do_fluxo_vira_uma_candidatura_so(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá, Leomar! Pode mandar o currículo por aqui."}]
    passo(ligada, s, texto("w1", "Boa tarde, me chamo Leomar, quero a vaga de auxiliar de produção"),
          ia=ia, nome="Leomar Puntel")
    for w in ("w2", "w3"):   # o mesmo PDF, duas vezes
        ia.conversa = [{"ferramentas": [("encaminhar_curriculo", {"vaga_id": 2})]},
                       {"texto": "Recebi o seu currículo."}]
        passo(ligada, s, doc(w), ia=ia, nome="Leomar Puntel")
    c = candidaturas(ligada)
    assert len(c) == 1 and c[0]["tipo_arquivo"] == "pdf" and c[0]["vaga_id"] == 2
    assert "auxiliar de produção" in c[0]["texto"]
    # a segunda vez a ferramenta disse que ja estava com a equipe
    resultado = ia.chamadas[-1]["mensagens"][-1]["content"][0]["content"]
    assert "já tinha sido recebido" in resultado


# ── (c) Joao Ficagna: o e-mail que ela nao inventa ──────────────────────────

def test_c_pedido_de_email_vira_a_opcao_do_setor_e_o_email_inventado_e_recusado(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Claro! O e-mail é financeiro@renascer.com.br",
                    "ferramentas": [("oferecer_opcao_do_menu", {"chave": "financeiro.pagamentos"})]},
                   {}]
    passo(ligada, s, texto("w1", "podem me passar um e-mail do financeiro?"), ia=ia, nome="João Ficagna")
    (t1, _, corpo1, _), (t2, _, corpo2, opcoes) = s.enviadas[-2:]
    assert corpo1 == O.FRASE_APROVADA                                    # a frase com @ nao saiu
    assert t2 == "botoes" and [o[0] for o in opcoes] == ["ia:sim:financeiro.pagamentos", "ia:menu"]
    resumos = [e["resumo"] for e in enviadas(ligada)]
    assert "olivia: recusada: e-mail" in resumos
    assert any(r.startswith("olivia: ferramenta oferecer_opcao_do_menu: financeiro.pagamentos") for r in resumos)
    # o toque no "Sim" e o caminho de hoje: o link sai da tela Destinos
    passo(ligada, s, toque("w2", "ia:sim:financeiro.pagamentos"), ia=ia, nome="João Ficagna")
    assert s.ultima[0] == "contato" and conversa(ligada)["situacao"] == "com_link"


def test_c_oferecer_um_no_com_opcoes_manda_a_pergunta_dele(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Você é produtor ou revenda?", "ferramentas": [("oferecer_opcao_do_menu", {"chave": "comercial"})]}]
    passo(ligada, s, texto("w1", "quero comprar semente de aveia"), ia=ia)
    assert s.ultima[0] == "botoes" and all(o[0].startswith("menu:comercial.") for o in s.ultima[3])


# ── (d) o filtro de saida ───────────────────────────────────────────────────

@pytest.mark.parametrize("frase,motivo", [
    ("O salário é R$ 2.000", "valor"), ("Ligue no (49) 3664-0121", "numero"), ("Veja www.renascer.com.br", "link"),
    ("Mande para rh@renascer.com.br", "e-mail"), ("O contrato é de experiência", "palavra: contrato"),
    ("Nosso prazo de resposta é curto", "palavra: prazo de resposta"), ("A remuneração é boa", "palavra: remuneracao"),
])
def test_d_o_filtro_recusa(frase, motivo):
    assert O.frase_permitida(frase) == (False, motivo)


@pytest.mark.parametrize("frase", ["Olá! Como posso ajudar?", "A vaga abriu em 13/11/2026.", "Temos 3 vagas."])
def test_d_o_filtro_deixa_passar(frase):
    assert O.frase_permitida(frase) == (True, "")


def test_d_frase_com_valor_vira_a_aprovada_e_grava_recusada(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "O salário é R$ 2.000 por mês."}]
    passo(ligada, s, texto("w1", "quanto paga a vaga?"), ia=ia)
    assert s.ultima[2] == O.FRASE_APROVADA
    assert [e["resumo"] for e in enviadas(ligada)][-1] == "olivia: recusada: valor"


# ── (e) travou ──────────────────────────────────────────────────────────────

def test_e_a_mesma_mensagem_duas_vezes_marca_e_na_segunda_travada_vai_ao_menu(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Me conte mais."}]
    passo(ligada, s, texto("w1", "preciso de ajuda"), ia=ia)
    assert ia.chamadas[-1]["extra"] == ""
    ia.conversa = [{"texto": "Pode me dizer o assunto?"}]
    passo(ligada, s, texto("w2", "preciso de ajuda"), ia=ia, agora=AGORA + timedelta(minutes=1))
    assert ia.chamadas[-1]["extra"] == O.TRAVOU_MARCA                    # 1a vez: a marca
    n = len(ia.chamadas)
    passo(ligada, s, texto("w3", "não é isso"), ia=ia, agora=AGORA + timedelta(minutes=2))
    assert len(ia.chamadas) == n                                         # 2a vez: sem IA, o menu
    assert s.ultima[0] == "lista" and conversa(ligada)["conduzida_por"] == "menu"
    # e a proxima mensagem cai no caminho de hoje (a IA de classificar, nao a de conversar)
    ia.resposta = None
    passo(ligada, s, texto("w4", "quero falar com alguém"), ia=ia, agora=AGORA + timedelta(minutes=3))
    assert len(ia.chamadas) == n and ia.perguntas[-1] == "quero falar com alguém"


def test_e_tres_falas_sem_avanco_tambem_travam(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    for i in range(3):
        ia.conversa = [{"texto": "Resposta %d." % i}]
        passo(ligada, s, texto("w%d" % i, "pergunta %d" % i), ia=ia, agora=AGORA + timedelta(minutes=i))
    ia.conversa = [{"texto": "Vamos por partes."}]
    passo(ligada, s, texto("w9", "outra pergunta"), ia=ia, agora=AGORA + timedelta(minutes=5))
    assert ia.chamadas[-1]["extra"] == O.TRAVOU_MARCA


# ── (f) quem NAO passa por ela ──────────────────────────────────────────────

def test_f_interno_nao_passa_pela_olivia(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    passo(ligada, s, texto("w1", "quero saber do pedido"), ia=ia, numero=fran(ligada), bsuid="BR.fran", nome="Fran")
    assert not getattr(ia, "chamadas", [])


def test_f_consultor_do_piloto_nao_passa_pela_olivia(ligada):
    with conexao(ligada) as con:
        con.execute("INSERT INTO atendimento.clientes_consultores (wa_id, comercial_id, nome) VALUES (%s, 42, 'X')",
                    (DE_FORA,))
    with conexao(ligada) as con:
        assert not O.e_de_fora(con, _entrada(DE_FORA), AGORA)


class _EnvioFalso:
    def convidado_recente(self, con, wa_id, agora):
        return {"erp_codigo": 1} if wa_id == DE_FORA else None


def _entrada(numero):
    from backend.motor import Entrada, Pessoa
    return Entrada(wamid="x", pessoa=Pessoa(bsuid="BR.x", wa_id=numero, nome=""), texto="oi")


def test_f_cliente_da_carteira_nao_passa_pela_olivia(ligada):
    with conexao(ligada) as con:
        assert not O.e_de_fora(con, _entrada(DE_FORA), AGORA, _EnvioFalso())
        assert O.e_de_fora(con, _entrada("5549900000000"), AGORA, _EnvioFalso())


def test_f_o_casamento_exato_do_no_atual_continua_sem_ia(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    passo(ligada, s, toque("w1", "menu:comercial.produtor", numero=DE_FORA), ia=ia)
    passo(ligada, s, texto("w2", "Sc"), ia=ia)
    assert not getattr(ia, "chamadas", []) and s.ultima[0] == "contato"


# ── (g) a chave desligada ───────────────────────────────────────────────────

def test_g_desligada_o_texto_solto_e_a_proposta_de_hoje(desligada):
    s = SaidaFalsa()
    ia = IAFalsa(resposta="fretes")
    passo(desligada, s, texto("w1", "quero cotar um frete"), ia=ia)
    assert s.ultima[0] == "botoes" and "Entendi que você quer" in s.ultima[2]
    assert not getattr(ia, "chamadas", []) and conversa(desligada)["conduzida_por"] == "menu"


def test_g_desligada_o_pdf_de_fora_ainda_ouve_o_nao_abro_arquivo(desligada):
    s = SaidaFalsa()
    passo(desligada, s, doc("w1"), ia=IAFalsa())
    assert "não consigo abrir arquivo" in s.ultima[2]


def test_g_desligada_a_foto_na_conversa_da_vaga_entra_como_curriculo(desligada):
    s = SaidaFalsa()
    passo(desligada, s, toque("w1", "menu:trabalhe", numero=DE_FORA))
    passo(desligada, s, toque("w2", "vaga:escolher:2", numero=DE_FORA))
    passo(desligada, s, foto("w3"))
    c = candidaturas(desligada)
    assert len(c) == 1 and c[0]["tipo_arquivo"] == "imagem" and c[0]["vaga_id"] == 2
    assert s.ultima[2].startswith("Recebemos o seu currículo")


# ── (h) o vigia ─────────────────────────────────────────────────────────────

def _conversa_da_olivia(cfg, s, ia, wamid, numero, bsuid, frase="Olá!"):
    ia.conversa = [{"texto": frase}]
    passo(cfg, s, texto(wamid, "oi, tudo bem?", numero=numero), ia=ia, numero=numero, bsuid=bsuid)


def test_h_dia_limpo_nao_avisa_e_marca_bem(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("encerrar", {})]}]
    passo(ligada, s, texto("w1", "obrigado pela informação, era só isso mesmo"), ia=ia)
    with conexao(ligada) as con:
        n = O.fechar_dia(con, AGORA + timedelta(hours=12, minutes=40))
        assert n["bem"] == 1 and not n["avisou"]
        assert not con.execute("SELECT 1 FROM atendimento.avisos WHERE tipo = 'olivia_resumo'").fetchone()
    assert conversa(ligada)["saida"] == "bem"


def test_h_sem_saida_e_recusada_avisam_o_dono_uma_vez_por_dia(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    _conversa_da_olivia(ligada, s, ia, "w1", DE_FORA, "BR.a")
    _conversa_da_olivia(ligada, s, ia, "w2", "5549977776666", "BR.b", frase="Ligue 49 3664-0121")
    noite = AGORA + timedelta(hours=13, minutes=40)   # 23:40 em Brasilia
    with conexao(ligada) as con:
        assert O.hora_do_vigia(con, noite) and not O.hora_do_vigia(con, AGORA)
        n = O.fechar_dia(con, noite)
        assert n["avisou"] and len(n["sem_saida"]) == 2 and n["n_recusadas"] == 1
        a = con.execute("SELECT * FROM atendimento.avisos WHERE tipo = 'olivia_resumo'").fetchone()
        assert a["sobre"].startswith("Hoje a OlivIA falou em 2 conversas: 0 terminaram bem, 2 sem saída")
        assert "1 frase recusada" in a["sobre"]
        assert not O.hora_do_vigia(con, noite + timedelta(minutes=5))      # uma vez por dia
    m = __import__("backend.modelos_meta", fromlist=["x"])
    with conexao(ligada) as con:
        modelo = dict(con.execute("SELECT * FROM atendimento.modelos WHERE nome = 'olivia_resumo'").fetchone())
    assert m.componentes(modelo)[0]["example"]["body_text"][0][0].startswith("Hoje")


# ── (i) a API fora ──────────────────────────────────────────────────────────

def test_i_api_fora_devolve_o_caminho_de_hoje_sem_conversa_dela(ligada):
    s = SaidaFalsa()
    ia = IAFalsa(resposta="fretes")
    ia.conversar = lambda *a, **k: None
    passo(ligada, s, texto("w1", "quero cotar um frete"), ia=ia)
    assert s.ultima[0] == "botoes" and "Entendi que você quer" in s.ultima[2]
    c = conversa(ligada)
    assert c["conduzida_por"] == "menu"
    with conexao(ligada) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.conversas").fetchone()["n"] == 1


def test_i_erro_no_meio_depois_de_falar_nao_responde_duas_vezes(ligada):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá!", "ferramentas": [("ver_vagas", {})]}]
    original = O._executar

    def quebra(*a, **k):
        raise RuntimeError("banco caiu")
    O._executar = quebra
    try:
        passo(ligada, s, texto("w1", "tem vaga?"), ia=ia)
    finally:
        O._executar = original
    assert [x[2] for x in s.enviadas] == ["Olá!"]


# ── a base e a instrucao ────────────────────────────────────────────────────

def test_a_base_e_relida_quando_muda(tmp_path):
    b = tmp_path / "base.md"
    b.write_text("primeira", encoding="utf-8")
    assert O.base(b) == "primeira"
    import os
    b.write_text("segunda", encoding="utf-8")
    os.utime(b, (b.stat().st_atime, b.stat().st_mtime + 10))
    assert O.base(b) == "segunda"
    assert O.base(tmp_path / "nao-existe.md") == ""


def test_a_instrucao_tem_o_menu_as_vagas_e_as_cinco_ferramentas(ligada):
    with conexao(ligada) as con:
        sistema = O.instrucao(con)
        nomes = [f["name"] for f in O.ferramentas(con)]
    assert "financeiro.boleto" in sistema and "vaga_id 2: Vaga Auxiliar de produção" in sistema
    assert "raiz_interna" not in sistema and "interna." not in sistema    # a arvore da casa nao entra
    assert nomes == list(O.FERRAMENTAS_NOMES)


def test_saude_diz_se_a_olivia_esta_ligada(ligada, desligada):
    from fastapi.testclient import TestClient
    for c, esperado in ((ligada, "ligada"), (desligada, "desligada")):
        with TestClient(R.criar_app(c, saida=SaidaFalsa(), trabalhador=False)) as t:
            assert t.get("/saude").json()["olivia"] == esperado


# ── a tela Recepcao: a marca e o filtro (passo 8) ────────────────────────────

def test_a_recepcao_marca_olivia_falou_e_filtra_sem_saida(ligada):
    from fastapi.testclient import TestClient
    from backend import seguranca
    from backend.main import CABECALHO_DA_TELA, criar_app
    s, ia = SaidaFalsa(), IAFalsa()
    _conversa_da_olivia(ligada, s, ia, "w1", DE_FORA, "BR.a")
    passo(ligada, s, texto("w2", "oi", numero="5549977776666"), ia=IAFalsa(resposta=None), numero="5549977776666",
          bsuid="BR.b")
    with conexao(ligada) as con:
        con.execute("UPDATE atendimento.conversas SET iniciada_em = now(), ultimo_toque_em = now() - interval '1 hour'")
        O.fechar_dia(con, datetime.now(timezone.utc))
        con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash) VALUES ('dono', 'Dono', %s)",
                    (seguranca.gerar_hash("senha-de-teste-1"),))
    seguranca.limpar_erros("dono")
    with TestClient(criar_app(ligada), headers={CABECALHO_DA_TELA: "1"}) as t:
        assert t.post("/api/entrar", json={"login": "dono", "senha": "senha-de-teste-1"}).status_code == 200
        d = t.get("/api/recepcao", params={"dias": 7}).json()
        assert d["cartoes"]["olivia_falou"] == 1 and d["cartoes"]["olivia_sem_saida"] == 1
        assert sorted((l["olivia"], l["saida"]) for l in d["linhas"]) == [(False, None), (True, "sem_saida")]
        so = t.get("/api/recepcao", params={"dias": 7, "situacao": "sem_saida"}).json()["linhas"]
        assert [l["olivia"] for l in so] == [True]


# ── etapa B: o audio de quem e de fora (D10, 16/11/2026) ─────────────────────

from backend import audio as A                       # noqa: E402
from backend.motor import NAO_ABRO_ARQUIVO           # noqa: E402


def audio_msg(wamid, numero=DE_FORA):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "audio",
            "audio": {"id": "midia-" + wamid, "mime_type": "audio/ogg; codecs=opus", "voice": True}}


class Ouvido:
    """O transcritor falso: `texto` (ou uma excecao em `falha`), e a lingua pedida em cada audio."""
    modelo = "falso"

    def __init__(self, texto="queria ver se tem vaga pra empilhadeira", duracao=9.0, falha=None):
        self.texto, self.duracao, self.falha, self.ouvidos = texto, duracao, falha, []

    def __call__(self, caminho, maximo, lingua="pt"):
        self.ouvidos.append((caminho.name, lingua))
        if self.falha:
            raise self.falha
        if self.duracao > maximo:
            return None, self.duracao
        return self.texto, self.duracao


def chaves_do_audio(cfg, de_fora=True, transcrever=True, por_dia=None):
    with conexao(cfg) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = 'audio.transcrever'",
                    ("true" if transcrever else "false",))
        con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = 'audio.de_fora'",
                    ("true" if de_fora else "false",))
        if por_dia is not None:
            con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = 'audio.de_fora_por_dia'",
                        (str(por_dia),))


def linhas_de_audio(cfg):
    with conexao(cfg) as con:
        return [dict(r) for r in con.execute("SELECT * FROM atendimento.audios ORDER BY id").fetchall()]


@pytest.fixture
def com_modelo():
    antes = A.estado["modelo_presente"]
    A.estado["modelo_presente"] = None
    yield
    A.estado["modelo_presente"] = antes


def test_b_a_gabriel_fala_e_a_olivia_responde_ao_que_ele_falou(ligada, com_modelo):
    chaves_do_audio(ligada)
    s, ia = SaidaFalsa(), IAFalsa()
    passo(ligada, s, audio_msg("wa1"), ia=ia, nome="Gabriel")
    assert s.enviadas == [] and not getattr(ia, "chamadas", [])           # nada na hora
    a = linhas_de_audio(ligada)
    assert len(a) == 1 and a[0]["de_fora"] and a[0]["arquivo"]
    ouvido = Ouvido()
    assert A.transcrever_um(ligada, ouvido)
    assert ouvido.ouvidos[0][1] is None                                   # lingua detectada
    ia.conversa = [{"texto": "Temos sim, a de operador de empilhadeira. Pode mandar o currículo por aqui."}]
    R.processar_pendentes(ligada, s, ia, agora=AGORA)
    assert s.ultima[2].startswith("Temos sim")
    assert ia.chamadas[-1]["mensagens"][-1]["content"] == "(áudio) queria ver se tem vaga pra empilhadeira"
    assert "(áudio) é a transcrição" in ia.chamadas[-1]["sistema"]


@pytest.mark.parametrize("caso", ["de_fora_desligada", "olivia_desligada", "sem_modelo", "transcricao_desligada"])
def test_b_b_chave_desligada_e_a_linha_fixa_de_hoje(cfg, tmp_path, com_modelo, caso):
    c = replace(cfg, responde=True, olivia_fala=caso != "olivia_desligada", campo_pasta=tmp_path / "campo")
    chaves_do_audio(c, de_fora=caso != "de_fora_desligada", transcrever=caso != "transcricao_desligada")
    if caso == "sem_modelo":
        A.estado["modelo_presente"] = False
    s = SaidaFalsa()
    passo(c, s, audio_msg("wa1"), ia=IAFalsa())
    assert s.ultima[2] == NAO_ABRO_ARQUIVO and linhas_de_audio(c) == []


@pytest.mark.parametrize("ouvido", [Ouvido(falha=RuntimeError("audio corrompido")), Ouvido(duracao=999),
                                    Ouvido(texto="")])
def test_b_c_nao_ouviu_a_olivia_pede_para_escrever(ligada, com_modelo, ouvido):
    chaves_do_audio(ligada)
    s, ia = SaidaFalsa(), IAFalsa()
    passo(ligada, s, audio_msg("wa1"), ia=ia)
    assert A.transcrever_um(ligada, ouvido)
    ia.conversa = [{"texto": "Não consegui ouvir o áudio. Pode escrever ou mandar de novo?"}]
    R.processar_pendentes(ligada, s, ia, agora=AGORA)
    assert ia.chamadas[-1]["mensagens"][-1]["content"] == A.MARCA + A.NAO_OUVI
    assert s.ultima[2].startswith("Não consegui ouvir")


def test_b_c_o_mesmo_erro_no_audio_da_casa_nao_gera_evento(ligada, com_modelo):
    chaves_do_audio(ligada)
    s = SaidaFalsa()
    passo(ligada, s, audio_msg("wa1", numero=fran(ligada)), numero=fran(ligada), bsuid="BR.fran", nome="Fran")
    assert linhas_de_audio(ligada)[0]["de_fora"] is False
    assert A.transcrever_um(ligada, Ouvido(falha=RuntimeError("audio corrompido")))
    with conexao(ligada) as con:
        assert not con.execute("SELECT 1 FROM atendimento.eventos_meta WHERE chave_meta LIKE '%:transcrito'").fetchone()


def test_b_d_o_audio_da_casa_passa_na_frente(ligada, com_modelo):
    chaves_do_audio(ligada)
    s = SaidaFalsa()
    passo(ligada, s, audio_msg("wa-fora"), ia=IAFalsa())
    passo(ligada, s, audio_msg("wa-casa", numero=fran(ligada)), numero=fran(ligada), bsuid="BR.fran", nome="Fran")
    ouvido = Ouvido()
    A.transcrever_um(ligada, ouvido)
    A.transcrever_um(ligada, ouvido)
    assert ouvido.ouvidos == [("wa-casa.ogg", "pt"), ("wa-fora.ogg", None)]


def test_b_e_o_setimo_audio_em_24h_recebe_a_linha_fixa(ligada, com_modelo):
    chaves_do_audio(ligada)
    s = SaidaFalsa()
    for i in range(6):
        passo(ligada, s, audio_msg("wa%d" % i), ia=IAFalsa())
    assert len(linhas_de_audio(ligada)) == 6 and s.enviadas == []
    passo(ligada, s, audio_msg("wa7"), ia=IAFalsa())
    assert s.ultima[2] == NAO_ABRO_ARQUIVO and len(linhas_de_audio(ligada)) == 6


def test_b_f_audio_na_conversa_de_vaga_vai_a_fila_e_nao_recebe_pdf_ou_foto(ligada, com_modelo):
    chaves_do_audio(ligada)
    s = SaidaFalsa()
    passo(ligada, s, toque("w1", "menu:trabalhe", numero=DE_FORA), ia=IAFalsa())
    passo(ligada, s, toque("w2", "vaga:escolher:2", numero=DE_FORA), ia=IAFalsa())
    n = len(s.enviadas)
    passo(ligada, s, audio_msg("wa1"), ia=IAFalsa())
    assert len(s.enviadas) == n and linhas_de_audio(ligada)[0]["de_fora"]
    # o texto transcrito volta a conversa da vaga, que responde como a qualquer texto
    A.transcrever_um(ligada, Ouvido(texto="eu moro em Cunha Porã"))
    R.processar_pendentes(ligada, s, IAFalsa(resposta="regiao"), agora=AGORA)
    assert len(s.enviadas) == n + 1 and "PDF ou em foto" not in s.ultima[2]


class _EnvioFalsoTodos:
    def convidado_recente(self, con, wa_id, agora):
        return {"erp_codigo": 1}


def test_b_g_consultor_e_cliente_da_carteira_nao_entram(ligada, com_modelo):
    chaves_do_audio(ligada)
    with conexao(ligada) as con:
        con.execute("INSERT INTO atendimento.clientes_consultores (wa_id, comercial_id, nome) VALUES (%s, 42, 'X')",
                    (DE_FORA,))
    with conexao(ligada) as con:
        assert not A.aceita_de_fora(con, _entrada(DE_FORA), AGORA, O.Olivia())
        assert not A.aceita_de_fora(con, _entrada("5549900000000"), AGORA, O.Olivia(), _EnvioFalsoTodos())
        assert A.aceita_de_fora(con, _entrada("5549900000000"), AGORA, O.Olivia())


def test_b_saude_e_o_script_mostram_a_chave(ligada, com_modelo, capsys, monkeypatch):
    chaves_do_audio(ligada, de_fora=False)
    import importlib.util
    from pathlib import Path
    caminho = Path(__file__).resolve().parents[1] / "scripts" / "audio.py"
    spec = importlib.util.spec_from_file_location("script_audio", caminho)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.setattr(script.config, "carregar", lambda *a, **k: ligada)
    monkeypatch.setattr("sys.argv", ["audio.py", "ligar-fora"])
    assert script.main() == 0
    assert "audio de fora (#1520): LIGADO" in capsys.readouterr().out
    with conexao(ligada) as con:
        s = A.saude(ligada, con)
        assert s["de_fora"] is True and s["pendentes_de_fora"] == 0
    monkeypatch.setattr("sys.argv", ["audio.py", "desligar-fora"])
    script.main()
    with conexao(ligada) as con:
        assert A.de_fora_ligado(con) is False


def test_a_instrucao_diz_as_palavras_que_o_filtro_recusa_e_o_que_dizer_no_lugar(ligada):
    """Prova de 16/11/2026: a resposta sobre a vaga foi recusada pela palavra salario."""
    with conexao(ligada) as con:
        sistema = O.instrucao(con)
    for p in O.PALAVRAS_FORA_ESCRITAS:
        assert "\"%s\"" % p in sistema
    assert "a equipe passa no contato com o candidato" in sistema
    assert O.frase_permitida("El salario lo informa el equipo")[0] is False   # em espanhol tambem
