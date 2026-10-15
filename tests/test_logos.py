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
