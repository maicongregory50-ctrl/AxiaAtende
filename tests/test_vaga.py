"""#1098: o Trabalhe conosco. A conversa do candidato (as tres telas da maquete, com o ajuste "so
PDF"), as respostas fixas, a mensagem a Fran, o retorno dela e os doze meses."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import envio as envio_mod
from backend import recepcionista as R
from backend import vaga as V
from backend.banco import conexao
from tests.avisos_meta import aviso, texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa

QUINTA_14H = datetime(2026, 10, 8, 17, 0, tzinfo=timezone.utc)
ANUNCIO = "120249624037810192"
CANDIDATO = "5549988887777"
TRIAGEM = {"requisitos": [{"situacao": "consta", "fonte": "Agronomia UFSC"},
                          {"situacao": "nao_consta", "fonte": ""},
                          {"situacao": "consta", "fonte": "revenda"},
                          {"situacao": "nao", "fonte": "Cascavel, PR"}],
           "resumo": "perfil comercial", "legivel": True}


@pytest.fixture
def ligado(cfg):
    return replace(cfg, responde=True)


def fran(cfg):
    with conexao(cfg) as con:
        return V.quem_atende(con)


def passo(cfg, s, mensagem, agora=QUINTA_14H, ia=None, numero=CANDIDATO, bsuid="BR.cand.1", nome="Gabriel Rodrigues"):
    R.gravar(cfg, aviso([mensagem], numero=numero, bsuid=bsuid, nome=nome))
    R.processar_pendentes(cfg, s, ia, agora=agora)
    with conexao(cfg) as con:   # um erro no evento DESFAZ o que o motor gravou: nenhum pode passar calado
        erros = con.execute("SELECT erro FROM atendimento.eventos_meta WHERE erro <> ''").fetchall()
    assert not erros, erros
    return s.ultima


def do_anuncio(wamid, corpo="Olá! Posso ter mais informações sobre isso?", anuncio=ANUNCIO):
    m = texto(wamid, corpo, numero=CANDIDATO)
    m["referral"] = {"source_type": "ad", "source_id": anuncio, "headline": "Vaga Comercial"}
    return m


def doc(wamid, nome="Curriculo - Gabriel.pdf", mime="application/pdf", numero=CANDIDATO):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "document",
            "document": {"id": "mid-%s" % wamid, "mime_type": mime, "filename": nome}}


def foto(wamid, numero=CANDIDATO):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "image",
            "image": {"id": "mid-%s" % wamid, "mime_type": "image/jpeg"}}


def conversa(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.conversas ORDER BY id DESC LIMIT 1").fetchone()


def candidaturas(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.candidaturas ORDER BY id").fetchall()


# ── a entrada ───────────────────────────────────────────────────────────────

def test_quem_vem_do_anuncio_cai_direto_na_vaga_sem_menu(ligado):
    s = SaidaFalsa()
    tipo, para, corpo, opcoes = passo(ligado, s, do_anuncio("w1"))
    assert tipo == "botoes" and para == CANDIDATO
    assert corpo.startswith("Olá, Gabriel!") and "*Vaga Comercial*" in corpo
    assert "• Morar em Maravilha (SC) ou cidade vizinha" in corpo and corpo.endswith("requisitos?")
    assert [o[1] for o in opcoes] == ["Sim, atendo todos", "Não atendo todos", "Era outro assunto"]
    assert len(s.enviadas) == 1                       # nada de boas-vindas nem menu antes
    c = conversa(ligado)
    assert c["trabalhe"] and c["vaga_id"]


def test_anuncio_de_vaga_fechada_cai_no_menu_de_sempre(ligado):
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.vagas SET aberta = false")
    s = SaidaFalsa()
    tipo, *_ = passo(ligado, s, do_anuncio("w1"))
    assert tipo == "lista"                            # o menu principal
    assert not conversa(ligado)["trabalhe"]


def test_o_no_trabalhe_conosco_do_menu_abre_a_vaga(ligado):
    s = SaidaFalsa()
    passo(ligado, s, texto("w1", "oi", numero=CANDIDATO))
    tipo, _, corpo, opcoes = passo(ligado, s, toque("w2", "menu:trabalhe", lista=True, numero=CANDIDATO))
    assert tipo == "botoes" and "O anúncio pede" in corpo and opcoes[0][0] == V.TODOS


def test_sem_vaga_aberta_o_no_pede_o_pdf_para_as_proximas(ligado):
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.vagas SET aberta = false")
    s = SaidaFalsa()
    passo(ligado, s, texto("w1", "oi", numero=CANDIDATO))
    tipo, _, corpo, _ = passo(ligado, s, toque("w2", "menu:trabalhe", lista=True, numero=CANDIDATO))
    assert tipo == "texto" and corpo.startswith("No momento não temos vaga aberta")
    passo(ligado, s, doc("w3"))
    c = candidaturas(ligado)
    assert len(c) == 1 and c[0]["vaga_id"] is None


# ── a conversa (as tres telas da maquete) ───────────────────────────────────

def test_tela_1_atende_e_manda_o_pdf(ligado):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    _, _, corpo, _ = passo(ligado, s, toque("w2", V.TODOS, numero=CANDIDATO))
    assert "*currículo em PDF*" in corpo and "decisão é sempre de uma pessoa da equipe" in corpo
    _, _, corpo, _ = passo(ligado, s, doc("w3"))
    assert corpo.startswith("Recebemos o seu currículo ✅") and "pré-triagem" in corpo
    c = candidaturas(ligado)[0]
    assert bytes(c["pdf"]) == b"MIDIA:mid-w3" and c["declarou"] == "todos" and c["pdf_nome"] == "Curriculo - Gabriel.pdf"
    assert c["apagar_em"] - c["recebida_em"] == timedelta(days=365)
    assert conversa(ligado)["situacao"] == "curriculo_recebido"


def test_tela_2_nao_atende_e_manda_assim_mesmo(ligado):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    tipo, _, corpo, opcoes = passo(ligado, s, toque("w2", V.NEM_TODOS, numero=CANDIDATO))
    assert tipo == "botoes" and "fica guardado para as próximas vagas" in corpo
    assert [o[1] for o in opcoes] == ["Mandar currículo", "Encerrar"]
    passo(ligado, s, toque("w3", V.MANDAR, numero=CANDIDATO))
    passo(ligado, s, doc("w4"))
    assert candidaturas(ligado)[0]["declarou"] == "nem_todos"


def test_tela_2_encerrar_termina_sem_curriculo(ligado):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    passo(ligado, s, toque("w2", V.NEM_TODOS, numero=CANDIDATO))
    passo(ligado, s, toque("w3", V.ENCERRAR, numero=CANDIDATO))
    assert conversa(ligado)["situacao"] == "sem_curriculo"


def test_tela_3_escreve_em_vez_de_mandar_e_leva_um_lembrete_so(ligado):
    s = SaidaFalsa()
    ia = IAFalsa(resposta="apresentacao")
    passo(ligado, s, do_anuncio("w1"), ia=ia)
    passo(ligado, s, toque("w2", V.TODOS, numero=CANDIDATO), ia=ia)
    _, _, corpo, _ = passo(ligado, s, texto("w3", "Sou agrônomo formado em 2019", numero=CANDIDATO), ia=ia)
    assert corpo.startswith("Anotei 👍")
    n = len(s.enviadas)
    passo(ligado, s, texto("w4", "trabalhei 3 anos em revenda", numero=CANDIDATO), ia=ia)
    assert len(s.enviadas) == n                       # um lembrete so
    passo(ligado, s, doc("w5"), ia=ia)
    assert "agrônomo formado em 2019" in candidaturas(ligado)[0]["texto"]   # o texto vai junto


@pytest.mark.parametrize("mensagem", [foto("w3"), doc("w3", "curriculo.docx", "application/msword")])
def test_so_pdf_foto_e_word_nao_servem(ligado, mensagem):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    passo(ligado, s, toque("w2", V.TODOS, numero=CANDIDATO))
    tipo, _, corpo, _ = passo(ligado, s, mensagem)
    assert tipo == "texto" and corpo.startswith("Precisamos do seu currículo em PDF")
    assert not candidaturas(ligado)


def test_o_pdf_repetido_pela_meta_nao_vira_dois(ligado):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    passo(ligado, s, doc("w2"))
    with conexao(ligado) as con:   # a Meta reenvia o mesmo aviso com outra chave de evento
        con.execute("UPDATE atendimento.conversas SET situacao = 'em_curso'")
    R.gravar(ligado, aviso([dict(doc("w2"))], numero=CANDIDATO, bsuid="BR.cand.1"))
    R.processar_pendentes(ligado, s, None, agora=QUINTA_14H)
    assert len(candidaturas(ligado)) == 1


# ── as respostas fixas (a IA so escolhe a chave) ─────────────────────────────

@pytest.mark.parametrize("chave,comeca", [
    ("regiao", "A vaga é para quem mora em Maravilha (SC)"),
    ("salario", "Oferecemos salário atrativo, plano de saúde Unimed"),
    ("retorno", "Estamos fazendo a pré-triagem"),
    ("sem_pdf", "Precisamos do seu currículo em PDF"),
    ("recebemos", "Ainda não chegou nenhum currículo seu"),
])
def test_cada_resposta_fixa(ligado, chave, comeca):
    s = SaidaFalsa()
    ia = IAFalsa(resposta=chave)
    passo(ligado, s, do_anuncio("w1"), ia=ia)
    _, _, corpo, _ = passo(ligado, s, texto("w2", "qualquer pergunta", numero=CANDIDATO), ia=ia)
    assert corpo.startswith(comeca)
    assert ia.opcoes[-1] == ["regiao", "recebemos", "apresentacao", "sem_pdf", "salario", "retorno",
                             "pessoa", "outro_assunto"]


def test_falar_com_uma_pessoa_manda_o_cartao_da_fran(ligado):
    s = SaidaFalsa()
    ia = IAFalsa(resposta="pessoa")
    passo(ligado, s, do_anuncio("w1"), ia=ia)
    passo(ligado, s, texto("w2", "quero falar com alguém", numero=CANDIDATO), ia=ia)
    (t1, _, corpo, _), (t2, _, nome, _) = s.enviadas[-2:]
    assert t1 == "texto" and corpo.startswith("Pode falar com a Fran") and t2 == "contato" and nome == "Fran"


@pytest.mark.parametrize("resposta", ["outro_assunto", None])
def test_outro_assunto_vai_ao_menu_e_fora_da_lista_repergunta(ligado, resposta):
    s = SaidaFalsa()
    ia = IAFalsa(resposta=resposta)
    passo(ligado, s, do_anuncio("w1"), ia=ia)
    tipo, _, corpo, _ = passo(ligado, s, texto("w2", "quero comprar semente de aveia", numero=CANDIDATO), ia=ia)
    if resposta == "outro_assunto":
        assert tipo == "lista" and not conversa(ligado)["trabalhe"]
    else:
        assert tipo == "botoes" and "O anúncio pede" in corpo   # o menu da vaga de novo


def test_era_outro_assunto_vai_ao_menu_principal(ligado):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    tipo, *_ = passo(ligado, s, toque("w2", V.OUTRO, numero=CANDIDATO))
    assert tipo == "lista" and not conversa(ligado)["trabalhe"]


def test_quem_volta_em_30_dias_pergunta_e_ouve_que_recebemos(ligado):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    passo(ligado, s, doc("w2"))
    ia = IAFalsa(resposta="recebemos")
    _, _, corpo, _ = passo(ligado, s, texto("w3", "vocês receberam meu currículo?", numero=CANDIDATO),
                           agora=QUINTA_14H + timedelta(days=3), ia=ia)
    assert corpo.startswith("Recebemos, sim ✅ (em 08/10)")
    assert conversa(ligado)["trabalhe"]


# ── a parada: nunca "parou no meio" ─────────────────────────────────────────

def test_conversa_de_vaga_parada_termina_sem_curriculo_e_nao_e_retomada(ligado):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    with conexao(ligado) as con:
        R.motor.marcar_paradas(con, QUINTA_14H + timedelta(hours=1))
        assert R.motor.retomar_paradas(con, s, IAFalsa(resposta="trabalhe"), QUINTA_14H + timedelta(hours=1)) == 0
    assert conversa(ligado)["situacao"] == "sem_curriculo"


def test_pdf_fora_da_conversa_de_vaga_segue_o_caminho_de_hoje(ligado):
    s = SaidaFalsa()
    tipo, _, corpo, _ = passo(ligado, s, doc("w1"))
    assert tipo == "texto" and "não consigo abrir arquivo" in corpo
    assert not candidaturas(ligado)


# ── a Fran ───────────────────────────────────────────────────────────────────

def _um_curriculo(cfg, s):
    passo(cfg, s, do_anuncio("w1"))
    passo(cfg, s, toque("w2", V.TODOS, numero=CANDIDATO))
    passo(cfg, s, doc("w3"))


def _rodar_minuto(cfg, s, ia, agora=QUINTA_14H + timedelta(minutes=1)):
    with conexao(cfg) as con:
        return V.mandar_a_fran(con, s, ia, "segredo", agora)


def test_fora_da_janela_vai_o_modelo_com_o_pdf_e_a_triagem(ligado):
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    ia = IAFalsa()
    ia.triagem = TRIAGEM
    assert _rodar_minuto(ligado, s, ia) == 1
    m = s.modelos[-1]
    assert m["nome"] == "curriculo_para_fran" and m["para"] == fran(ligado)["whatsapp"]
    assert m["documento"] == (b"MIDIA:mid-w3", "Curriculo - Gabriel.pdf")
    assert m["corpo"][0] == "Vaga Comercial" and m["corpo"][1] == "Gabriel Rodrigues (49 9 8888-7777)"
    assert m["corpo"][2] == "atende a todos os requisitos"
    assert m["corpo"][3] == "Formação em Agronomia, com pós-graduação: consta (Agronomia UFSC)"
    assert m["corpo"][4] == "Ao menos 2 anos de experiência com sementes: não consta no currículo"
    assert m["corpo"][6] == "Morar em Maravilha (SC) ou cidade vizinha: não (Cascavel, PR)"
    assert all("\n" not in v for v in m["corpo"]) and len(m["corpo"]) == 8
    c = candidaturas(ligado)[0]
    assert m["botoes"] == ["vaga:certa:%d" % c["id"], "vaga:errada:%d" % c["id"]]
    assert m["url"] == V.codigo_candidato("segredo", c["id"])
    assert _rodar_minuto(ligado, s, ia) == 0          # uma mensagem por curriculo


def test_dentro_da_janela_da_fran_vai_o_pdf_com_os_botoes(ligado):
    s = SaidaFalsa()
    numero_fran = fran(ligado)["whatsapp"]
    R.gravar(ligado, aviso([texto("f1", "bom dia", numero=numero_fran)], numero=numero_fran, bsuid="BR.fran"))
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.eventos_meta SET processado_em = now(), recebido_em = %s", (QUINTA_14H,))
    _um_curriculo(ligado, s)
    ia = IAFalsa()
    ia.triagem = TRIAGEM
    _rodar_minuto(ligado, s, ia)
    tipo, para, legenda, opcoes = s.enviadas[-1]
    assert tipo == "documento" and legenda.startswith("Novo currículo · Vaga Comercial")
    assert "Pré-triagem (IA):\nFormação em Agronomia" in legenda
    assert [o[1] for o in opcoes] == ["Triagem certa", "Triagem errada", "Conversar"]


@pytest.mark.parametrize("como,diz", [("desligada", "pré-triagem desligada"), ("ia_fora", "a IA não respondeu")])
def test_sem_triagem_o_curriculo_vai_igual_dizendo_isso(ligado, como, diz):
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    if como == "desligada":
        with conexao(ligado) as con:
            con.execute("UPDATE atendimento.vagas SET triagem_ligada = false")
    _rodar_minuto(ligado, s, IAFalsa(falha=True) if como == "ia_fora" else IAFalsa())
    assert s.modelos[-1]["corpo"][3] == "Sem pré-triagem (%s)" % diz


def test_modelo_recusado_espera_uma_hora_para_tentar_de_novo(ligado):
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    s.modelo_falha = "132001 Template name does not exist"
    assert _rodar_minuto(ligado, s, IAFalsa()) == 0
    assert "132001" in candidaturas(ligado)[0]["fran_erro"]
    s.modelo_falha = None
    assert _rodar_minuto(ligado, s, IAFalsa(), QUINTA_14H + timedelta(minutes=30)) == 0
    assert _rodar_minuto(ligado, s, IAFalsa(), QUINTA_14H + timedelta(minutes=62)) == 1


def test_conversar_com_o_candidato_pelo_link_assinado(ligado):
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    cid = candidaturas(ligado)[0]["id"]
    with conexao(ligado) as con:
        assert envio_mod.falar(con, "segredo", V.codigo_candidato("segredo", cid), QUINTA_14H) == CANDIDATO
        assert envio_mod.falar(con, "segredo", "v%d-0000000000000000" % cid, QUINTA_14H) is None


def test_triagem_errada_pede_uma_linha_e_o_texto_nao_vira_frase_de_foto(ligado):
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    _rodar_minuto(ligado, s, IAFalsa())
    cid = candidaturas(ligado)[0]["id"]
    numero_fran = fran(ligado)["whatsapp"]
    _, _, corpo, _ = passo(ligado, s, toque("f1", "vaga:errada:%d" % cid, numero=numero_fran),
                           numero=numero_fran, bsuid="BR.fran", nome="Fran")
    assert corpo.startswith("O que ela errou?")
    _, _, corpo, _ = passo(ligado, s, texto("f2", "Ele trabalhou com semente, página 2", numero=numero_fran),
                           numero=numero_fran, bsuid="BR.fran", nome="Fran")
    assert corpo == "Anotado, obrigado."
    c = candidaturas(ligado)[0]
    assert c["feedback"] == "errada" and c["feedback_texto"] == "Ele trabalhou com semente, página 2"
    with conexao(ligado) as con:
        assert not con.execute("SELECT 1 FROM atendimento.campo_frases").fetchone()


def test_triagem_certa_e_de_outro_numero_nao_vale(ligado):
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    _rodar_minuto(ligado, s, IAFalsa())
    cid = candidaturas(ligado)[0]["id"]
    passo(ligado, s, toque("x1", "vaga:certa:%d" % cid))   # o candidato nao marca a propria triagem
    assert candidaturas(ligado)[0]["feedback"] is None
    numero_fran = fran(ligado)["whatsapp"]
    passo(ligado, s, toque("f1", "vaga:certa:%d" % cid, numero=numero_fran), numero=numero_fran, bsuid="BR.fran")
    assert candidaturas(ligado)[0]["feedback"] == "certa"


# ── os doze meses ────────────────────────────────────────────────────────────

def test_doze_meses_apaga_o_pdf_e_quem_e_e_guarda_o_retorno(ligado):
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.candidaturas SET feedback = 'certa'")
        assert V.limpar(con, QUINTA_14H + timedelta(days=364)) == 0
        assert V.limpar(con, QUINTA_14H + timedelta(days=366)) == 1
    c = candidaturas(ligado)[0]
    assert c["pdf"] is None and c["wa_id"] is None and c["nome_perfil"] == "" and c["texto"] == ""
    assert c["feedback"] == "certa" and c["vaga_id"] and c["apagada_em"]


# ── a volta da 025 ───────────────────────────────────────────────────────────

def test_a_volta_da_025_devolve_o_no_a_fran_e_guarda_os_curriculos(ligado):
    from pathlib import Path
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    volta = (Path(__file__).resolve().parents[1] / "backend" / "migracoes" / "025_trabalhe_conosco_VOLTA.sql")
    with conexao(ligado) as con:
        con.execute(volta.read_text(encoding="utf-8").replace("BEGIN;", "").replace("COMMIT;", ""))
        assert con.execute("SELECT acao FROM atendimento.menu WHERE chave = 'trabalhe'").fetchone()["acao"] == "destino"
        assert con.execute("SELECT count(*) AS n FROM atendimento.candidaturas").fetchone()["n"] == 1
        assert con.execute("SELECT situacao FROM atendimento.conversas ORDER BY id DESC LIMIT 1").fetchone()["situacao"] == "encerrada"
    s2 = s   # a mesma saida: os wamids falsos nao se repetem
    passo(ligado, s2, texto("w9", "oi", numero="5549977776666"), bsuid="BR.outro")
    passo(ligado, s2, toque("w10", "menu:trabalhe", lista=True, numero="5549977776666"), bsuid="BR.outro")
    assert s2.ultima[0] == "contato" and s2.ultima[2] == "Fran"   # como era antes


def test_a_mensagem_da_fran_cabe_no_teto_da_meta_mesmo_com_triagem_longa(ligado):
    """22/10/2026: o 2o curriculo real foi recusado pela Meta (131009, corpo acima de 1024)."""
    s = SaidaFalsa()
    _um_curriculo(ligado, s)
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.candidaturas SET texto = %s", ("Sou agrônomo e trabalhei muito " * 40,))
    ia = IAFalsa()
    longa = "Graduação em Agronomia (2002-2006), Centro Universitário Integrado; pós-graduação lato sensu em Proteção de Plantas (200"
    ia.triagem = {"requisitos": [{"situacao": "consta", "fonte": longa}] * 4, "resumo": "perfil " * 100, "legivel": True}
    _rodar_minuto(ligado, s, ia)
    m = s.modelos[-1]
    with conexao(ligado) as con:
        corpo = V.corpo_do_modelo(con, m["corpo"])
    assert len(corpo) <= 1024 and all("\n" not in v for v in m["corpo"])
    assert m["corpo"][3].endswith("…)") and "(200…" not in m["corpo"][3]


def test_a_fran_recebe_so_o_que_o_candidato_escreveu(ligado):
    """22/10/2026: o 1o curriculo real foi com a frase do anuncio e os nomes dos botoes em "Escreveu"."""
    s = SaidaFalsa()
    ia = IAFalsa(resposta="apresentacao")
    passo(ligado, s, do_anuncio("w1"), ia=ia)
    passo(ligado, s, toque("w2", V.NEM_TODOS, "Não atendo todos", numero=CANDIDATO), ia=ia)
    passo(ligado, s, texto("w3", "Sou técnico agrícola", numero=CANDIDATO), ia=ia)
    passo(ligado, s, toque("w4", V.MANDAR, "Mandar currículo", numero=CANDIDATO), ia=ia)
    passo(ligado, s, doc("w5"), ia=ia)
    assert candidaturas(ligado)[0]["texto"] == "Sou técnico agrícola"


def test_quem_manda_assim_mesmo_ouve_grato_e_nao_otimo(ligado):
    s = SaidaFalsa()
    passo(ligado, s, do_anuncio("w1"))
    passo(ligado, s, toque("w2", V.NEM_TODOS, numero=CANDIDATO))
    _, _, corpo, _ = passo(ligado, s, toque("w3", V.MANDAR, numero=CANDIDATO))
    assert corpo.startswith("Grato! Mande aqui o seu *currículo em PDF*.")
    s2 = s   # a mesma saida: os wamids falsos nao se repetem
    passo(ligado, s2, do_anuncio("x1"), numero="5549911112222", bsuid="BR.cand.2")
    _, _, corpo, _ = passo(ligado, s2, toque("x2", V.TODOS, numero="5549911112222"), numero="5549911112222", bsuid="BR.cand.2")
    assert corpo.startswith("Ótimo!")
