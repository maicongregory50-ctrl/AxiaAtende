"""#1525: a OlivIA conduz a conversa da vaga -- a ficha de contato, o modo da vaga, o toque unico, a parcial,
a visita, o espanhol, a trava da promessa, a chave desligada, a API fora e quem nao passa por ela.
Spec: docs/specs/2026-11-16-olivia-conduz-a-vaga-ficha-e-curriculo.md; plano, passo 13 (a) a (k)."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import olivia as O
from backend import recepcionista as R
from backend import vaga as V
from backend.banco import conexao
from tests.avisos_meta import aviso, na_hora, texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa

AGORA = datetime(2026, 11, 17, 13, 0, tzinfo=timezone.utc)   # 10:00 em Brasilia, terca
DE_FORA = "5549988882222"
ANUNCIO_AUX = "ad-auxiliar"
FICHA = [("nome", "Maria Aparecida da Silva"), ("cidade", "Cunha Porã"), ("experiencia", "Lavoura e aviário"),
         ("quando_comeca", "Segunda que vem"), ("como_chega", "Tenho moto")]


@pytest.fixture
def conduz(cfg, tmp_path):
    """A OlivIA ligada (OLIVIA_FALA) e a chave da vaga ligada; a Auxiliar (2) com anuncio."""
    c = replace(cfg, responde=True, olivia_fala=True, campo_pasta=tmp_path / "campo")
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'olivia.conduz_vaga'")
        con.execute("UPDATE atendimento.vagas SET anuncio_ids = ARRAY[%s] WHERE id = 2", (ANUNCIO_AUX,))
    return c


@pytest.fixture
def desligada(cfg, tmp_path):
    """OLIVIA_FALA ligada, a chave da vaga como nasce (false)."""
    c = replace(cfg, responde=True, olivia_fala=True, campo_pasta=tmp_path / "campo")
    with conexao(c) as con:
        con.execute("UPDATE atendimento.vagas SET anuncio_ids = ARRAY[%s] WHERE id = 2", (ANUNCIO_AUX,))
    return c


def passo(cfg, s, mensagem, ia=None, agora=AGORA, numero=DE_FORA, bsuid="BR.cand.1", nome="Maria"):
    R.gravar(cfg, aviso([na_hora(mensagem, agora)], numero=numero, bsuid=bsuid, nome=nome))
    with conexao(cfg) as con:   # a janela de 24 h conta por LEAST(hora da mensagem, chegada): a chegada no passo
        con.execute("UPDATE atendimento.eventos_meta SET recebido_em = %s WHERE chave_meta = %s", (agora, mensagem["id"]))
    R.processar_pendentes(cfg, s, ia, agora=agora)
    with conexao(cfg) as con:
        erros = con.execute("SELECT erro FROM atendimento.eventos_meta WHERE erro <> ''").fetchall()
    assert not erros, erros


def anuncio(wamid, corpo="Olá! Tenho interesse nesta vaga.", numero=DE_FORA, fonte=ANUNCIO_AUX):
    m = texto(wamid, corpo, numero=numero)
    m["referral"] = {"source_id": fonte, "source_type": "ad"}
    return m


def foto(wamid, numero=DE_FORA):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "image",
            "image": {"id": "mid-foto", "mime_type": "image/jpeg", "caption": ""}}


def ler(cfg, sql, *args):
    with conexao(cfg) as con:
        return con.execute(sql, args).fetchall()


def conversa(cfg):
    return ler(cfg, "SELECT * FROM atendimento.conversas ORDER BY id DESC LIMIT 1")[0]


def candidaturas(cfg):
    return ler(cfg, "SELECT * FROM atendimento.candidaturas ORDER BY id")


def resumos(cfg):
    return [r["resumo"] for r in ler(cfg, "SELECT resumo FROM atendimento.enviadas ORDER BY id")]


def fran(cfg):
    with conexao(cfg) as con:
        return V.quem_atende(con)["whatsapp"]


def fran_escreveu(cfg, agora=AGORA):
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, bsuid, corpo, recebido_em, processado_em)
                       VALUES ('fran-escreveu', 'mensagem', 'BR.fran', %s, %s, %s)""",
                    ('{"msg": {"from": "%s", "type": "text"}}' % fran(cfg), agora, agora))


def comecar(cfg, s, ia, lingua="pt", agora=AGORA):
    """O anuncio, e "nao tenho curriculo" com o aviso da ficha."""
    ia.conversa = [{"texto": "Olá! É a vaga de Auxiliar de produção. Você tem currículo?"}]
    passo(cfg, s, anuncio("w1"), ia, agora=agora)
    ia.conversa = [{"ferramentas": [("comecar_ficha", {"lingua": lingua})]}, {"texto": "Qual é o seu nome completo?"}]
    passo(cfg, s, texto("w2", "não tenho currículo", numero=DE_FORA), ia, agora=agora + timedelta(minutes=1))


def responder(cfg, s, ia, campos, inicio=AGORA + timedelta(minutes=2), prefixo="r"):
    for i, (k, v) in enumerate(campos):
        ia.conversa = [{"ferramentas": [("anotar_ficha", {k: v})]}, {"texto": "Certo. E a próxima?"}]
        passo(cfg, s, texto("%s%d" % (prefixo, i), v, numero=DE_FORA), ia, agora=inicio + timedelta(minutes=i))


# ── (a) a ficha completa ────────────────────────────────────────────────────

def test_a_ficha_completa_vira_candidatura_e_a_fran_recebe_a_pagina_sem_triagem(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá! É a vaga de Auxiliar de produção. Você tem currículo?"}]
    passo(conduz, s, anuncio("w1"), ia)
    c = conversa(conduz)
    assert c["trabalhe"] and c["vaga_id"] == 2 and c["conduzida_por"] == "olivia"
    assert "[chegou pelo anúncio da Vaga Auxiliar de produção]" in ia.chamadas[-1]["mensagens"][-1]["content"]
    vistas = ia.chamadas[-1]["ferramentas"]
    assert "comecar_ficha" in vistas and "anotar_ficha" not in vistas and "marcar_visita" not in vistas
    assert "Ficha ou currículo" not in ia.chamadas[-1]["sistema"] and "aceita currículo OU a ficha" in ia.chamadas[-1]["sistema"]

    ia.conversa = [{"ferramentas": [("comecar_ficha", {"lingua": "pt"})]}, {"texto": "Qual é o seu nome completo?"}]
    passo(conduz, s, texto("w2", "não tenho currículo", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=1))
    assert O.AVISO_FICHA in resumos(conduz)
    assert "12 meses" in s.enviadas[-2][2]   # o aviso, antes da primeira pergunta
    depois = ia.chamadas[-1]["ferramentas"]   # a lista refeita na segunda volta do laco
    assert "anotar_ficha" in depois and "comecar_ficha" not in depois

    responder(conduz, s, ia, FICHA[:-1])
    assert not candidaturas(conduz)
    ia.conversa = [{"ferramentas": [("anotar_ficha", {"como_chega": "Tenho moto"})]},
                   {"texto": "Pronto, a sua ficha foi encaminhada à equipe! Se quiser, pode vir conhecer a empresa."}]
    passo(conduz, s, texto("r9", "Tenho moto", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=9))
    k = candidaturas(conduz)
    assert len(k) == 1 and k[0]["tipo_arquivo"] == "ficha" and k[0]["pdf"] is None and k[0]["vaga_id"] == 2
    assert k[0]["ficha"]["nome"] == "Maria Aparecida da Silva" and "faltou" not in k[0]["ficha"]
    assert k[0]["triagem_erro"] == V.SEM_TRIAGEM_FICHA and k[0]["triagem_em"] is not None
    assert conversa(conduz)["situacao"] == "curriculo_recebido"
    # "encaminhada" com a candidatura gravada NAO e promessa: a frase sai
    assert s.ultima[2].startswith("Pronto, a sua ficha foi encaminhada")
    assert "marcar_visita" in ia.chamadas[-1]["ferramentas"]

    fran_escreveu(conduz)
    with conexao(conduz) as con:
        assert V.mandar_a_fran(con, s, IAFalsa(), "segredo", AGORA + timedelta(minutes=10)) == 1
        triados = getattr(IAFalsa(), "triados", [])
    tipo, para, legenda, opcoes = s.ultima
    assert tipo == "documento" and para == fran(conduz) and [o[1] for o in opcoes] == ["Conversar"]
    assert legenda.startswith("Ficha de contato") and "Tenho moto" in legenda and not triados
    pagina = s.documentos[-1][1]
    assert pagina.startswith(b"%PDF-1.4") and "Cunha Porã".encode("cp1252") in pagina
    assert s.documentos[-1][2] == "ficha-de-contato.pdf"
    assert "ficha %d para a fran" % k[0]["id"] in resumos(conduz)


def test_a_a_ficha_fora_da_janela_da_fran_vai_no_modelo_com_a_pagina(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA)
    with conexao(conduz) as con:
        assert V.mandar_a_fran(con, s, IAFalsa(), "segredo", AGORA + timedelta(minutes=10)) == 1
    m = s.modelos[-1]
    assert m["documento"][1] == "ficha-de-contato.pdf" and m["documento"][0].startswith(b"%PDF-1.4")
    assert m["corpo"][1].startswith("Ficha: Maria Aparecida")


def test_a_recebemos_vale_para_a_ficha(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA)
    with conexao(conduz) as con:
        k = V._ultima_candidatura(con, type("P", (), {"bsuid": "BR.cand.1"})())
        assert k["tipo_arquivo"] == "ficha"
        assert V._texto(con, "recebemos", data="17/11").startswith("Recebemos, sim")


# ── (b) curriculo obrigatorio ───────────────────────────────────────────────

def test_b_na_empilhadeira_nao_ha_ficha_e_a_foto_entra_como_curriculo(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Temos duas vagas. Qual te interessa?"}]
    passo(conduz, s, toque("w1", "menu:trabalhe", numero=DE_FORA), ia)
    c = conversa(conduz)
    assert c["trabalhe"] and c["vaga_id"] is None and c["conduzida_por"] == "olivia"
    assert "[tocou: " in ia.chamadas[-1]["mensagens"][-1]["content"]
    ia.conversa = [{"ferramentas": [("escolher_vaga", {"vaga_id": 3})]},
                   {"texto": "Para essa vaga o currículo é indispensável. Pode ser uma foto."}]
    passo(conduz, s, texto("w2", "empilhadeira, mas não tenho currículo", numero=DE_FORA), ia,
          agora=AGORA + timedelta(minutes=1))
    assert conversa(conduz)["vaga_id"] == 3
    vistas = ia.chamadas[-1]["ferramentas"]
    assert "comecar_ficha" not in vistas and "anotar_ficha" not in vistas
    # se ela chamar mesmo assim, a ferramenta nao existe
    ia.conversa = [{"ferramentas": [("comecar_ficha", {"lingua": "pt"})]}, {"texto": "Ok."}]
    passo(conduz, s, texto("w3", "não tenho mesmo", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=2))
    assert O.AVISO_FICHA not in resumos(conduz)
    assert "não está disponível" in ia.chamadas[-1]["mensagens"][-1]["content"][0]["content"]
    ia.conversa = [{"ferramentas": [("encaminhar_curriculo", {"vaga_id": 3})]}, {"texto": "Recebi! A equipe vai analisar."}]
    passo(conduz, s, foto("w4"), ia, agora=AGORA + timedelta(minutes=3))
    k = candidaturas(conduz)
    assert len(k) == 1 and k[0]["tipo_arquivo"] == "imagem" and k[0]["vaga_id"] == 3


# ── (c) a parcial e o toque unico ───────────────────────────────────────────

def test_c_parcial_um_toque_as_2h_e_a_ficha_incompleta_4h_depois(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA[:2])
    ultima = AGORA + timedelta(minutes=3)
    with conexao(conduz) as con:
        assert O.tocar_vagas(con, s, ultima + timedelta(hours=1, minutes=59)) == 0   # cedo
        assert O.tocar_vagas(con, s, ultima + timedelta(hours=2)) == 1
        assert "Faltou só no que você já trabalhou, quando você pode começar e se você tem como chegar" in s.ultima[2]
        assert O.tocar_vagas(con, s, ultima + timedelta(hours=3)) == 0               # nunca outro
        assert O.enviar_parciais(con, ultima + timedelta(hours=5)) == 0              # 3 h depois do toque
        assert O.enviar_parciais(con, ultima + timedelta(hours=6)) == 1
        assert O.enviar_parciais(con, ultima + timedelta(hours=7)) == 0              # uma so
        assert O.tocar_vagas(con, s, ultima + timedelta(hours=8)) == 0
    assert resumos(conduz).count(O.TOQUE_VAGA) == 1
    k = candidaturas(conduz)
    assert len(k) == 1 and k[0]["ficha"]["faltou"] == ["experiencia", "quando_comeca", "como_chega"]
    with conexao(conduz) as con:
        linhas = V._linhas_da_ficha(con, k[0])
        assert linhas[-1] == ("Incompleta: faltou no que já trabalhou, quando pode começar e como chega a Cunha Porã "
                              "(a pessoa parou de responder)")
        fran_escreveu(conduz, ultima + timedelta(hours=6))
        assert V.mandar_a_fran(con, s, IAFalsa(), "segredo", ultima + timedelta(hours=6, minutes=1)) == 1
    assert "ficha incompleta %d para a fran" % k[0]["id"] in resumos(conduz)


def test_c_quem_responde_depois_do_toque_volta_a_mesma_conversa(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA[:1])
    with conexao(conduz) as con:
        from backend import motor
        motor.marcar_paradas(con, AGORA + timedelta(hours=1))
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=3)) == 1
    c = conversa(conduz)
    assert c["situacao"] == "sem_curriculo"
    responder(conduz, s, ia, FICHA[1:], inicio=AGORA + timedelta(hours=3, minutes=10), prefixo="v")
    assert conversa(conduz)["id"] == c["id"]
    k = candidaturas(conduz)
    assert len(k) == 1 and "faltou" not in k[0]["ficha"]


# ── (d) uma por conversa ────────────────────────────────────────────────────

def test_d_anotar_depois_de_completa_nao_cria_a_segunda(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA)
    assert "anotar_ficha" not in ia.chamadas[-1]["ferramentas"]
    ia.conversa = [{"ferramentas": [("anotar_ficha", {"nome": "Outra Pessoa"})]}, {"texto": "Ok."}]
    passo(conduz, s, texto("x1", "meu nome é outro", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=30))
    k = candidaturas(conduz)
    assert len(k) == 1 and k[0]["ficha"]["nome"] == "Maria Aparecida da Silva"
    with conexao(conduz) as con:
        c = con.execute("SELECT * FROM atendimento.conversas WHERE id = %s", (k[0]["conversa_id"],)).fetchone()
        assert V.receber_ficha(con, c, {"nome": "X"}, AGORA) == k[0]["id"]


# ── (e) espanhol ────────────────────────────────────────────────────────────

def test_e_espanhol_aviso_toque_e_pagina(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia, lingua="es")
    assert "12 meses" in s.enviadas[-2][2] and "equipo de selección" in s.enviadas[-2][2]
    assert conversa(conduz)["lingua"] == "es"
    responder(conduz, s, ia, [("nome", "José Pérez")])
    with conexao(conduz) as con:
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=3)) == 1
        assert s.ultima[2].startswith("[TEXTO DO DONO] Solo faltó la ciudad donde vives")
        O.enviar_parciais(con, AGORA + timedelta(hours=8))
        k = con.execute("SELECT * FROM atendimento.candidaturas").fetchone()
        assert k["ficha"]["lingua"] == "es" and "Respondeu em espanhol" in V._linhas_da_ficha(con, k)


def test_e_a_instrucao_pede_a_lingua_da_ultima_mensagem(conduz):
    with conexao(conduz) as con:
        assert "língua da ÚLTIMA mensagem" in O.instrucao(con)


# ── (f) a visita ────────────────────────────────────────────────────────────

def test_f_visita_antes_do_envio_marca_a_pagina(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA)
    ia.conversa = [{"ferramentas": [("marcar_visita", {})]}, {"texto": "Combinado, a equipe te chama para marcar."}]
    passo(conduz, s, texto("v1", "quero sim conhecer", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=20))
    k = candidaturas(conduz)[0]
    assert k["quer_visita"]
    fran_escreveu(conduz)
    with conexao(conduz) as con:
        V.mandar_a_fran(con, s, IAFalsa(), "segredo", AGORA + timedelta(minutes=21))
        assert not con.execute("SELECT 1 FROM atendimento.avisos WHERE tipo = 'vaga_visita'").fetchone()
    assert "Quer visitar a empresa" in s.ultima[2]


def test_f_visita_depois_do_envio_a_fran_recebe_a_linha(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA)
    with conexao(conduz) as con:
        V.mandar_a_fran(con, s, IAFalsa(), "segredo", AGORA + timedelta(minutes=12))
    ia.conversa = [{"ferramentas": [("marcar_visita", {})]}, {"texto": "Combinado, a equipe te chama."}]
    passo(conduz, s, texto("v1", "quero conhecer a empresa", numero=DE_FORA), ia, agora=AGORA + timedelta(hours=1))
    a = ler(conduz, "SELECT * FROM atendimento.avisos WHERE tipo = 'vaga_visita'")
    assert len(a) == 1 and a[0]["para_whatsapp"] == fran(conduz) and "Maria Aparecida da Silva" in a[0]["sobre"]
    with conexao(conduz) as con:
        from backend.envio import texto_do_aviso
        assert texto_do_aviso(con, a[0]).startswith("O candidato Maria Aparecida da Silva")


# ── (g) silencio total ──────────────────────────────────────────────────────

def test_g_so_a_frase_do_anuncio_recebe_o_convite_e_fora_das_24h_nada(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá! É a vaga de Auxiliar de produção. Você tem currículo?"}]
    passo(conduz, s, anuncio("w1"), ia)
    with conexao(conduz) as con:
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=2)) == 1
        assert s.ultima[2] == "[TEXTO DO DONO] Não quer deixar a sua ficha? São cinco perguntas rápidas."
        assert O.enviar_parciais(con, AGORA + timedelta(hours=30)) == 0   # sem nome, nenhuma candidatura
        from backend import motor
        motor.marcar_paradas(con, AGORA + timedelta(hours=30))
        O.fechar_dia(con, AGORA + timedelta(hours=30))
    assert not candidaturas(conduz) and conversa(conduz)["saida"] == "sem_saida"


def test_g_fora_das_24h_o_toque_nao_sai(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá! Você tem currículo?"}]
    passo(conduz, s, anuncio("w1"), ia)
    with conexao(conduz) as con:
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=24, minutes=1)) == 0
    assert O.TOQUE_VAGA not in resumos(conduz)


def test_g_vaga_de_curriculo_recebe_o_toque_do_curriculo(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("escolher_vaga", {"vaga_id": 3})]}, {"texto": "Você tem currículo?"}]
    passo(conduz, s, toque("w1", "menu:trabalhe", numero=DE_FORA), ia)
    with conexao(conduz) as con:
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=2)) == 1
    assert s.ultima[2] == "[TEXTO DO DONO] Ainda dá tempo de mandar o seu currículo. Pode ser uma foto."


# ── (h) a chave desligada ───────────────────────────────────────────────────

def test_h_desligada_a_conversa_de_vaga_e_a_de_hoje(desligada):
    s, ia = SaidaFalsa(), IAFalsa()
    passo(desligada, s, anuncio("w1"), ia)
    assert not getattr(ia, "chamadas", [])   # a OlivIA nao foi chamada
    assert "vaga: abertura" in resumos(desligada)
    with conexao(desligada) as con:
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=2)) == 0
        assert [f["name"] for f in O.ferramentas(con, conversa(desligada))] == list(O.FERRAMENTAS_NOMES)
        assert "A CONVERSA DE VAGA" not in O.instrucao(con)


def test_h_desligada_a_parcial_deixada_ainda_vai(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA[:1])
    with conexao(conduz) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'olivia.conduz_vaga'")
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=3)) == 0
        assert O.enviar_parciais(con, AGORA + timedelta(hours=25)) == 1   # a janela fechou
    assert candidaturas(conduz)[0]["ficha"]["faltou"]


def test_h_saude_e_o_script(conduz, capsys, monkeypatch):
    from fastapi.testclient import TestClient
    with TestClient(R.criar_app(conduz, saida=SaidaFalsa(), trabalhador=False)) as t:
        assert t.get("/saude").json()["olivia_vaga"] == "ligada"
    import importlib.util
    from pathlib import Path
    caminho = Path(__file__).resolve().parents[1] / "scripts" / "olivia.py"
    spec = importlib.util.spec_from_file_location("script_olivia", caminho)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.setattr(script.config, "carregar", lambda *a, **k: conduz)
    monkeypatch.setattr("sys.argv", ["olivia.py", "desligar-vaga"])
    assert script.main() == 0
    with conexao(conduz) as con:
        assert O.conduz_vaga(con) is False
    monkeypatch.setattr("sys.argv", ["olivia.py", "ligar-vaga"])
    assert script.main() == 1   # os textos provisorios recusam
    assert "RECUSADO" in capsys.readouterr().out
    with conexao(conduz) as con:
        con.execute("UPDATE atendimento.respostas_da_vaga SET texto = replace(texto, '[TEXTO DO DONO] ', '')")
    assert script.main() == 0
    with conexao(conduz) as con:
        assert O.conduz_vaga(con) is True


# ── (i) a API fora ──────────────────────────────────────────────────────────

def test_i_api_fora_o_fluxo_fixo_responde(conduz):
    s = SaidaFalsa()
    passo(conduz, s, anuncio("w1"), IAFalsa(falha=True))
    assert "vaga: abertura" in resumos(conduz)
    assert conversa(conduz)["conduzida_por"] == "menu"


# ── (j) a promessa ──────────────────────────────────────────────────────────

def test_j_promessa_sem_candidatura_e_recusada(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA[:2])
    ia.conversa = [{"texto": "Anotei tudo, a equipe vai te chamar!"}]
    passo(conduz, s, texto("p1", "é isso", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=30))
    assert O.RECUSADA_PROMESSA in resumos(conduz)
    assert s.ultima[2].startswith("[TEXTO DO DONO] Para eu passar a sua ficha à equipe, ainda falta no que você")
    assert not candidaturas(conduz)


# ── (k) quem nao passa por ela ──────────────────────────────────────────────

def test_k_toque_vaga_antigo_fica_no_fluxo_fixo(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    passo(conduz, s, toque("w1", "vaga:escolher:2", numero=DE_FORA), ia)
    assert not getattr(ia, "chamadas", [])
    assert "vaga: abertura" in resumos(conduz)


def test_k_interno_nao_passa_pela_olivia(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    with conexao(conduz) as con:
        interno = con.execute("SELECT whatsapp FROM atendimento.destinos WHERE ativo LIMIT 1").fetchone()["whatsapp"]
    passo(conduz, s, anuncio("w1", numero=interno), ia, numero=interno, bsuid="BR.casa")
    assert not getattr(ia, "chamadas", [])


def test_k_consultor_nao_passa_pela_olivia(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    with conexao(conduz) as con:
        con.execute("INSERT INTO atendimento.clientes_consultores (wa_id, comercial_id, nome) VALUES (%s, 42, 'X')",
                    (DE_FORA,))
    passo(conduz, s, anuncio("w1"), ia)
    assert not getattr(ia, "chamadas", [])


def test_k_o_retorno_da_fran_fica_onde_esta(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA)
    k = candidaturas(conduz)[0]
    fran_escreveu(conduz)
    with conexao(conduz) as con:
        V.mandar_a_fran(con, s, IAFalsa(), "segredo", AGORA + timedelta(minutes=12))
    n = len(getattr(ia, "chamadas", []))
    passo(conduz, s, toque("f1", "vaga:falar:%d" % k["id"], numero=fran(conduz)), ia, numero=fran(conduz),
          bsuid="BR.fran", agora=AGORA + timedelta(minutes=13))
    assert len(ia.chamadas) == n and s.ultima[0] == "contato"


# ── a migracao ──────────────────────────────────────────────────────────────

def test_a_067_nasce_desligada_e_a_volta_recusa_com_ficha(cfg, tmp_path):
    import psycopg
    from backend import migracoes
    with conexao(cfg) as con:
        assert con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'olivia.conduz_vaga'").fetchone()["valor"] is False
        assert {r["id"]: r["modo"] for r in con.execute("SELECT id, modo FROM atendimento.vagas WHERE aberta")} == \
            {2: "ficha_ou_curriculo", 3: "curriculo"}
        assert "salário" not in con.execute("SELECT beneficios FROM atendimento.vagas WHERE id = 2").fetchone()["beneficios"]
    volta = (migracoes.PASTA / "067_olivia_conduz_vaga_VOLTA.sql").read_text(encoding="utf-8")
    c = replace(cfg, responde=True, olivia_fala=True, campo_pasta=tmp_path / "campo")
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'olivia.conduz_vaga'")
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá!"}]
    passo(c, s, toque("w1", "menu:trabalhe", numero=DE_FORA), ia)
    with conexao(c) as con:
        conv = con.execute("SELECT * FROM atendimento.conversas ORDER BY id DESC LIMIT 1").fetchone()
        V.receber_ficha(con, conv, dict(FICHA), AGORA)
    with pytest.raises(psycopg.errors.RaiseException, match="067 VOLTA"):
        with conexao(c) as con:
            con.execute(volta)


# ── os doze meses, o vigia e o lugar da funcao ──────────────────────────────

def test_doze_meses_apagam_a_ficha_e_o_rascunho(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    comecar(conduz, s, ia)
    responder(conduz, s, ia, FICHA)
    with conexao(conduz) as con:
        assert V.limpar(con, AGORA + timedelta(days=366)) == 1
    k = candidaturas(conduz)[0]
    assert k["ficha"] is None and k["apagada_em"] is not None
    assert conversa(conduz)["ficha"] is None


def test_vigia_conta_as_fichas_incompletas():
    assert O.resumo_do_dia(3, 1, [7], 0, [], 2).endswith("2 fichas incompletas.")
    assert "incompleta" not in O.resumo_do_dia(3, 1, [7], 0, [], 0)


def test_funcao_da_vaga_entra_quando_o_arquivo_existe(conduz, tmp_path, monkeypatch):
    monkeypatch.setattr(O, "FUNCOES", tmp_path)
    with conexao(conduz) as con:
        assert "O QUE A FUNÇÃO FAZ" not in O.instrucao(con)
        (tmp_path / "2.md").write_text("Ensacar semente na linha. [Fran, 20/11/2026]", encoding="utf-8")
        assert "Ensacar semente na linha." in O.instrucao(con)
    assert O.funcao_da_vaga(3, tmp_path) == ""


def test_destinos_mostra_e_troca_o_modo(conduz):
    from fastapi.testclient import TestClient
    from backend import seguranca
    from backend.main import CABECALHO_DA_TELA, criar_app
    with conexao(conduz) as con:
        con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash) VALUES ('dono', 'Dono', %s)",
                    (seguranca.gerar_hash("senha-de-teste-1"),))
    seguranca.limpar_erros("dono")
    with TestClient(criar_app(conduz), headers={CABECALHO_DA_TELA: "1"}) as t:
        assert t.post("/api/entrar", json={"login": "dono", "senha": "senha-de-teste-1"}).status_code == 200
        vagas = {v["id"]: v for v in t.get("/api/destinos").json()["vagas"]}
        assert vagas[2]["modo"] == "ficha_ou_curriculo" and vagas[3]["modo"] == "curriculo"
        assert t.put("/api/vagas/3/modo", json={"modo": "ficha_ou_curriculo"}).status_code == 200
        assert t.put("/api/vagas/3/modo", json={"modo": "outro"}).status_code == 422
    assert ler(conduz, "SELECT modo FROM atendimento.vagas WHERE id = 3")[0]["modo"] == "ficha_ou_curriculo"


# ── #1543: os quatro defeitos da primeira noite (16 para 17/11/2026) ──────────

def test_1543_trabalhe_conosco_sai_do_que_ela_oferece(conduz):
    with conexao(conduz) as con:
        enum = [f for f in O.ferramentas(con) if f["name"] == "oferecer_opcao_do_menu"][0][
            "input_schema"]["properties"]["chave"]["enum"]
        assert "trabalhe" not in enum and "trabalhe" not in [o["chave"] for o in O._opcoes_do_menu(con)]
        assert "Quem atende a vaga é você" in O.instrucao(con)
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'olivia.conduz_vaga'")
        assert "trabalhe" in [o["chave"] for o in O._opcoes_do_menu(con)]   # desligada, o menu de sempre


def test_1543_o_sim_do_botao_antigo_nao_devolve_o_botao(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("oferecer_opcao_do_menu", {"chave": "trabalhe"})]},
                   {"texto": "Qual vaga te interessa?"}]
    passo(conduz, s, toque("w1", "ia:sim:trabalhe", numero=DE_FORA), ia)
    assert not [r for r in resumos(conduz) if "oferecer_opcao_do_menu" in r]
    assert s.ultima[2] == "Qual vaga te interessa?"


def test_1543_o_toque_usa_a_vaga_da_conversa_anterior(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("escolher_vaga", {"vaga_id": 3})]}, {"texto": "Você tem currículo?"}]
    passo(conduz, s, toque("w1", "menu:trabalhe", numero=DE_FORA), ia)
    with conexao(conduz) as con:   # a pessoa fecha pelo menu e reabre: conversa nova, de vaga, sem vaga
        con.execute("UPDATE atendimento.conversas SET situacao = 'encerrada'")
    ia.conversa = [{"texto": "Quando o currículo estiver pronto, mande por aqui."}]
    passo(conduz, s, toque("w2", "menu:trabalhe", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=5))
    c = conversa(conduz)
    assert c["trabalhe"] and c["vaga_id"] is None
    with conexao(conduz) as con:
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=2, minutes=10)) == 1
    assert "currículo" in s.ultima[2] and "ficha" not in s.ultima[2]


def test_1543_conversa_em_espanhol_sem_ficha_recebe_o_toque_em_espanhol(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("escolher_vaga", {"vaga_id": 3})]},
                   {"texto": "Para esta vacante el currículum es obligatorio. ¿Lo tienes a mano?"}]
    passo(conduz, s, texto("w1", "Trabajar con ustedes", numero=DE_FORA), ia)
    c = conversa(conduz)
    assert c["trabalhe"] and c["lingua"] is None
    with conexao(conduz) as con:
        assert O._lingua_da_conversa(con, c) == "es"
        assert O.tocar_vagas(con, s, AGORA + timedelta(hours=2)) == 1
    assert "Todavía" in s.ultima[2]


def test_1543_conversa_em_portugues_continua_em_portugues(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá! É a vaga de Auxiliar de produção. Você tem currículo?"}]
    passo(conduz, s, anuncio("w1"), ia)
    with conexao(conduz) as con:
        assert O._lingua_da_conversa(con, conversa(conduz)) == "pt"


def test_1543_o_toque_espera_o_horario(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    noite = datetime(2026, 11, 17, 0, 16, tzinfo=timezone.utc)   # 21:16 de 16/11 em Brasilia
    ia.conversa = [{"texto": "Olá! É a vaga de Auxiliar de produção. Você tem currículo?"}]
    passo(conduz, s, anuncio("w1"), ia, agora=noite)
    with conexao(conduz) as con:
        assert O.tocar_vagas(con, s, noite + timedelta(hours=2, minutes=40)) == 0   # 23:56: espera
        assert conversa(conduz)["vaga_lembrada_em"] is None
        assert O.tocar_vagas(con, s, datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)) == 1   # 07:00
        assert O.tocar_vagas(con, s, datetime(2026, 11, 17, 11, 0, tzinfo=timezone.utc)) == 0   # um so


def test_1543_o_toque_que_esperou_e_perdeu_a_janela_nao_sai(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    cedo = datetime(2026, 11, 17, 9, 30, tzinfo=timezone.utc)   # 06:30 em Brasilia
    ia.conversa = [{"texto": "Olá! Você tem currículo?"}]
    passo(conduz, s, anuncio("w1"), ia, agora=cedo)
    with conexao(conduz) as con:
        assert O.tocar_vagas(con, s, cedo + timedelta(minutes=20)) == 0                          # 06:50: cedo demais
        assert O.tocar_vagas(con, s, datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)) == 0   # 07:00, 24 h 30 depois
    assert O.TOQUE_VAGA not in resumos(conduz)


def test_1543_respostas_curtas_na_vaga_nao_travam(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá! É a vaga de Auxiliar de produção. Você tem currículo?"}]
    passo(conduz, s, anuncio("w1"), ia)
    for i, t in enumerate(["Tenho", "Sim", "Sim", "Já envio", "Ok", "Ok", "Uma pergunta", "Qual a função"]):
        ia.conversa = [{"texto": "Certo, resposta %d." % i}]
        passo(conduz, s, texto("t%d" % i, t, numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=1 + i))
    assert not [r for r in resumos(conduz) if r.startswith(O.FALA_TRAVOU)]
    assert conversa(conduz)["conduzida_por"] == "olivia" and "Certo, resposta 7." == s.ultima[2]


def test_1543_nao_e_isso_continua_marcando_na_vaga(conduz):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Olá! É a vaga de Auxiliar de produção. Você tem currículo?"}]
    passo(conduz, s, anuncio("w1"), ia)
    ia.conversa = [{"texto": "Me diga em uma frase o que você precisa."}]
    passo(conduz, s, texto("t1", "não é isso que eu perguntei", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=1))
    assert [r for r in resumos(conduz) if r.startswith(O.FALA_TRAVOU)]
