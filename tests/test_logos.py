"""#1036: a logo de cliente que chega pelo WhatsApp, e o nome de quem e da casa.

O caso real: as 15:27 de 15/10/2026 o Benedito mandou a logo de um cliente em PDF e recebeu
SILENCIO -- documento nao e midia, e para quem e da casa a linha curta nao sai de proposito.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend import logos as L
from backend import recepcionista as R
from backend.banco import conexao
from tests.avisos_meta import aviso, texto
from tests.saida_falsa import SaidaFalsa

AGORA = datetime(2026, 10, 15, 18, 27, tzinfo=timezone.utc)   # 15:27 em Sao Paulo
NUMERO = "5549999990000"


@pytest.fixture
def ligado(cfg):
    return replace(cfg, responde=True)


def documento(wamid, nome="Logo rigo sem..pdf", mime="application/pdf", numero=NUMERO):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "document",
            "document": {"id": "mid-%s" % wamid, "mime_type": mime, "filename": nome}}


def _sou_da_casa(cfg, numero=NUMERO):
    """Destino ativo = equipe, a 2a camada do reconhecimento (dono, 14/10/2026)."""
    with conexao(cfg) as con:
        con.execute("INSERT INTO atendimento.destinos (nome, whatsapp, ativo) VALUES (%s, %s, true)",
                    ("Benedito Vaskevicz", numero))


def passo(cfg, s, mensagem, agora=AGORA):
    R.gravar(cfg, aviso([mensagem]))
    R.processar_pendentes(cfg, s, None, agora=agora)
    return s.ultima


def _logos(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.logos_de_cliente ORDER BY id").fetchall()


def _campo(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT count(*) AS n FROM atendimento.material_de_campo").fetchone()["n"]


def test_a_logo_do_benedito_nao_se_perde_mais(ligado):
    """Ponta a ponta, o caso real: documento -> pergunta -> codigo -> marca -> guardada."""
    _sou_da_casa(ligado)
    s = SaidaFalsa()
    passo(ligado, s, documento("wamid.1"))
    assert "código" in s.ultima[2] and "ERP" in s.ultima[2]
    linha = _logos(ligado)[0]
    assert linha["formato"] == "pdf" and linha["nome_arquivo"] == "Logo rigo sem..pdf"
    assert linha["pergunta_pendente"] == "erp_codigo" and linha["puxada_em"] is None

    passo(ligado, s, texto("wamid.2", "7687"), agora=AGORA + timedelta(minutes=1))
    assert "7687" in s.ultima[2] and "marca" in s.ultima[2].lower()

    passo(ligado, s, texto("wamid.3", "Agro Rigo"), agora=AGORA + timedelta(minutes=2))
    linha = _logos(ligado)[0]
    assert linha["erp_codigo"] == 7687 and linha["nome_marca"] == "Agro Rigo"
    assert linha["pergunta_pendente"] is None and linha["completada_em"] is not None
    assert "Parceiras" in s.ultima[2]      # o limite e dito a quem mandou


def test_nenhuma_logo_entra_no_catalogo_do_campo(ligado):
    """A mistura que o desenho evita: logo no catalogo do marketing como foto de lavoura."""
    _sou_da_casa(ligado)
    s = SaidaFalsa()
    passo(ligado, s, documento("wamid.1"))
    assert len(_logos(ligado)) == 1 and _campo(ligado) == 0


def test_a_logo_fica_guardada_sem_o_codigo(ligado):
    """Descartar seria repetir em outra forma o defeito que o modulo conserta."""
    _sou_da_casa(ligado)
    s = SaidaFalsa()
    passo(ligado, s, documento("wamid.1"))
    passo(ligado, s, texto("wamid.2", "nao sei agora"), agora=AGORA + timedelta(minutes=1))
    assert "Não achei um código" in s.ultima[2]
    passo(ligado, s, texto("wamid.3", "nao sei mesmo"), agora=AGORA + timedelta(minutes=2))
    assert "guardada" in s.ultima[2]
    linha = _logos(ligado)[0]
    assert linha["erp_codigo"] is None and linha["pergunta_pendente"] is None   # guardada, nao perdida
    assert linha["arquivo"] is not None or linha["erro"] != ""


def test_pede_menu_escapa_da_pergunta_e_a_logo_fica(ligado):
    _sou_da_casa(ligado)
    s = SaidaFalsa()
    passo(ligado, s, documento("wamid.1"))
    passo(ligado, s, texto("wamid.2", "menu"), agora=AGORA + timedelta(minutes=1))
    assert _logos(ligado)[0]["pergunta_pendente"] is None
    assert s.ultima[0] == "botoes"      # o menu da casa, nao a pergunta da logo


def test_o_mesmo_aviso_repetido_nao_cria_duas_logos(ligado):
    """`wamid` UNICO: a Meta repete avisos por ate 7 dias."""
    _sou_da_casa(ligado)
    s = SaidaFalsa()
    passo(ligado, s, documento("wamid.1"))
    R.gravar(ligado, aviso([documento("wamid.1")]))
    R.processar_pendentes(ligado, s, None, agora=AGORA + timedelta(minutes=1))
    assert len(_logos(ligado)) == 1


def test_documento_de_quem_nao_e_da_casa_segue_na_linha_de_arquivo(ligado):
    """O #1027 continua valendo para cliente: nada de logo, e a linha que explica."""
    from backend import motor
    s = SaidaFalsa()
    passo(ligado, s, documento("wamid.1"))
    assert _logos(ligado) == [] and s.ultima[2] == motor.NAO_ABRO_ARQUIVO


def test_formato_que_o_marketing_nao_aceita_nao_vira_logo(ligado):
    """A tela Parceiras aceita pdf, svg, png e jpg. Um .docx cai na linha de arquivo."""
    from backend import motor
    _sou_da_casa(ligado)
    s = SaidaFalsa()
    passo(ligado, s, documento("wamid.1", nome="contrato.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
    assert _logos(ligado) == []
    # de quem e da casa o ramo do silencio continua valendo para o que nao e logo
    assert s.enviadas == [] or s.ultima[2] == motor.NAO_ABRO_ARQUIVO


def test_o_menu_da_casa_chama_pelo_nome(ligado):
    """O nome vem de primeiro_nome(), que resolve a caixa alta do ERP."""
    _sou_da_casa(ligado)
    s = SaidaFalsa()
    passo(ligado, s, texto("wamid.1", "oi"))
    assert "Benedito" in s.ultima[2] and "BENEDITO" not in s.ultima[2]
    assert "{nome}" not in s.ultima[2]


def test_a_frase_sem_o_marcador_nao_quebra(ligado):
    """O texto continua CADASTRO: quem tirar o {nome} recebe a frase, nao um erro."""
    _sou_da_casa(ligado)
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.menu SET pergunta = 'O que precisa?' WHERE chave = 'raiz_interna'")
    s = SaidaFalsa()
    passo(ligado, s, texto("wamid.1", "oi"))
    assert s.ultima[2] == "O que precisa?"


def test_formato_lido_do_mime_ou_do_nome():
    assert L._formato("application/pdf", "x") == "pdf"
    assert L._formato("", "LOGO.SVG") == "svg"
    assert L._formato("application/octet-stream", "logo.png") == "png"
    assert L._formato("application/zip", "pacote.zip") is None


def test_o_dialogo_da_logo_fica_em_enviadas(ligado):
    """O defeito achado na PRIMEIRA rodada em producao (15/10, 16:30): a logo foi colhida certo, mas
    `ler_conversa.py` mostrou so o que o Benedito mandou -- as falas da OlivIA nao estavam em
    `enviadas`, entao o dialogo nao se reconstroi e o status da Meta nao tem onde pousar.

    E a mesma falha que o commit 71047bb do #981 consertou para o canal de campo. Este teste existe
    para ela nao voltar uma terceira vez."""
    _sou_da_casa(ligado)
    s = SaidaFalsa()
    passo(ligado, s, documento("wamid.1"))
    passo(ligado, s, texto("wamid.2", "7687"), agora=AGORA + timedelta(minutes=1))
    passo(ligado, s, texto("wamid.3", "Agro Rigo"), agora=AGORA + timedelta(minutes=2))
    with conexao(ligado) as con:
        ditas = con.execute("""SELECT resumo FROM atendimento.enviadas
                                WHERE resumo LIKE 'logo:%' ORDER BY id""").fetchall()
    # as tres falas: recebi + pergunta da marca + guardada
    assert len(ditas) == 3, [d["resumo"] for d in ditas]
    assert "ERP" in ditas[0]["resumo"] and "marca" in ditas[1]["resumo"].lower()
    assert "Parceiras" in ditas[2]["resumo"]


# ── #1037: o marketing puxa ─────────────────────────────────────────────────

@pytest.fixture
def porta(cfg, tmp_path):
    return replace(cfg, responde=True, campo_pasta=tmp_path / "campo", chave_pedido="chave-de-teste")


def _api(cfg):
    from fastapi.testclient import TestClient
    from backend.main import criar_app
    return TestClient(criar_app(cfg)), {"X-Axiaatende-Chave": "chave-de-teste"}


def _logo_completa(cfg, s, agora=AGORA):
    passo(cfg, s, documento("wamid.1"), agora=agora)
    passo(cfg, s, texto("wamid.2", "7687"), agora=agora + timedelta(minutes=1))
    passo(cfg, s, texto("wamid.3", "Agro Rigo"), agora=agora + timedelta(minutes=2))
    return _logos(cfg)[0]


def _janela_em(cfg, quando):
    """A janela conta da ultima mensagem DELA, que o banco carimba com o relogio real: fixa."""
    with conexao(cfg) as con:
        con.execute("UPDATE atendimento.eventos_meta SET recebido_em = %s", (quando,))


def test_o_marketing_so_leva_o_dialogo_terminado_ou_largado(porta):
    """Terminado entra; a meio caminho espera; largado ha mais de 24 h entra -- senao a logo ficaria
    esperando para sempre, que e o defeito que o #1036 consertou, em outra forma."""
    _sou_da_casa(porta)
    s = SaidaFalsa()
    passo(porta, s, documento("wamid.1"))                       # so a pergunta do codigo, sem resposta
    with conexao(porta) as con:
        assert L.a_puxar(con, AGORA + timedelta(hours=1)) == []
        largada = L.a_puxar(con, AGORA + timedelta(hours=25))
    assert [x["id"] for x in largada] == [_logos(porta)[0]["id"]]
    assert largada[0]["erp_codigo"] is None and "wa_id" not in largada[0] and "bsuid" not in largada[0]


def test_puxada_duas_vezes_nao_muda_nada(porta):
    _sou_da_casa(porta)
    linha = _logo_completa(porta, SaidaFalsa())
    with conexao(porta) as con:
        assert [x["id"] for x in L.a_puxar(con, AGORA + timedelta(minutes=3))] == [linha["id"]]
        primeira = L.puxada(con, linha["id"], "parceira_nova", AGORA + timedelta(minutes=4))
        segunda = L.puxada(con, linha["id"], "a_conferir", AGORA + timedelta(minutes=9))
        assert L.a_puxar(con, AGORA + timedelta(minutes=10)) == []
    assert segunda == primeira and segunda["resultado"] == "parceira_nova"


def test_puxada_fecha_a_pergunta_largada(porta):
    """A logo largada no meio e levada; a pergunta aberta nao pode roubar a proxima mensagem."""
    _sou_da_casa(porta)
    passo(porta, SaidaFalsa(), documento("wamid.1"))
    with conexao(porta) as con:
        L.puxada(con, _logos(porta)[0]["id"], "a_conferir", AGORA + timedelta(hours=25))
    assert _logos(porta)[0]["pergunta_pendente"] is None


def test_quem_mandou_sabe_que_chegou_so_dentro_da_janela(porta):
    _sou_da_casa(porta)
    linha = _logo_completa(porta, SaidaFalsa())
    _janela_em(porta, AGORA)
    with conexao(porta) as con:
        L.puxada(con, linha["id"], "parceira_nova", AGORA + timedelta(minutes=4))
    s = SaidaFalsa()
    R.rotina_do_minuto(porta, s, agora=AGORA + timedelta(minutes=5))
    frase = L.CHEGOU_PARCEIRA_NOVA.format(marca="Agro Rigo")
    assert frase in [e[2] for e in s.enviadas if e[0] == "texto"]
    assert _logos(porta)[0]["aviso"] == "enviado"
    R.rotina_do_minuto(porta, s, agora=AGORA + timedelta(minutes=6))   # uma vez so
    assert [e[2] for e in s.enviadas if e[0] == "texto"].count(frase) == 1


def test_fora_da_janela_nada_sai(porta):
    _sou_da_casa(porta)
    linha = _logo_completa(porta, SaidaFalsa())
    _janela_em(porta, AGORA)
    with conexao(porta) as con:
        L.puxada(con, linha["id"], "a_conferir", AGORA + timedelta(hours=30))
    s = SaidaFalsa()
    R.rotina_do_minuto(porta, s, agora=AGORA + timedelta(hours=30, minutes=1))
    assert not any("chegou ao marketing" in e[2] for e in s.enviadas if e[0] == "texto")
    assert _logos(porta)[0]["aviso"] == "fora_da_janela"


def test_as_rotas_das_logos_so_com_a_chave(porta):
    _sou_da_casa(porta)
    linha = _logo_completa(porta, SaidaFalsa())
    api, chave = _api(porta)
    assert api.get("/logos/pendentes").status_code == 403
    assert api.get("/logos/pendentes", headers={"X-Axiaatende-Chave": "errada"}).status_code == 403
    itens = api.get("/logos/pendentes", headers=chave).json()["itens"]
    assert [x["id"] for x in itens] == [linha["id"]] and itens[0]["nome_marca"] == "Agro Rigo"
    assert itens[0]["enviada_por"] == "Benedito Vaskevicz" and itens[0]["tem_arquivo"] is True
    arq = api.get("/logos/%d/arquivo" % linha["id"], headers=chave)
    assert arq.status_code == 200 and arq.content == (porta.campo_pasta / linha["arquivo"]).read_bytes()
    assert api.get("/logos/999/arquivo", headers=chave).status_code == 404
    assert api.post("/logos/%d/puxada" % linha["id"], headers=chave, json={"resultado": "outro"}).status_code == 422
    r = api.post("/logos/%d/puxada" % linha["id"], headers=chave, json={"resultado": "a_conferir"})
    assert r.status_code == 200 and r.json()["resultado"] == "a_conferir"
    assert api.get("/logos/pendentes", headers=chave).json()["itens"] == []


def test_o_arquivo_nao_sai_da_pasta_das_logos(porta):
    _sou_da_casa(porta)
    linha = _logo_completa(porta, SaidaFalsa())
    with conexao(porta) as con:
        con.execute("UPDATE atendimento.logos_de_cliente SET arquivo = '../../fora.pdf' WHERE id = %s",
                    (linha["id"],))
    api, chave = _api(porta)
    assert api.get("/logos/%d/arquivo" % linha["id"], headers=chave).status_code == 404
