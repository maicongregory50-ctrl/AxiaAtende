"""#1381: o arquivo (PDF ou Word) que vai junto da resposta do chamado. A volta do ERP o baixa para
envios_pasta\\chamados; o recepcionista o manda logo depois do texto. Meta e ERP falsos."""
from dataclasses import replace
from datetime import timedelta

import pytest

from backend import erp, migracoes
from backend.banco import conexao
from backend.saida import DOCX
from tests.test_pendencias import (AGORA, FRAN, ErpFalso, falou, linha, mandar, mensagens, pendencias_erp,
                                   receber)


@pytest.fixture
def ligado(cfg, tmp_path):
    c = replace(cfg, erp_segredo="segredo-de-teste", porteiro=True, responde=True, envios_pasta=tmp_path)
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'pendencias.ligado'")
        con.execute("UPDATE atendimento.ajustes SET valor = '0'::jsonb WHERE chave = 'pendencias.juntar_minutos'")
    return c


def com_anexo(evento, classe="pergunta", nome="Roteiro.docx", tipo=DOCX, anexo_id=7):
    li = linha(evento, classe, "Fran, segue o roteiro.")
    li["anexo"] = {"id": anexo_id, "nome": nome, "media_type": tipo}
    return li


class ErpComAnexo(ErpFalso):
    def __init__(self, linhas=(), arquivos=None, falha=None):
        super().__init__(linhas)
        self.arquivos, self.falha, self.baixados = arquivos or {7: b"PK-docx"}, falha, []

    def baixar(self, cfg, token, anexo_id):
        self.baixados.append(anexo_id)
        if self.falha:
            raise self.falha
        return self.arquivos[anexo_id]


def volta(cfg, e):
    return pendencias_erp.volta(cfg, trazer=e.trazer, estado=e.estado, responder=e.responder,
                                validar=e.validar, agora=AGORA, baixar=e.baixar)


def test_a_migracao_061_nasce_com_a_chave_ligada_e_a_volta_desfaz(cfg):
    with conexao(cfg) as con:
        assert con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'pendencias.anexo_ligado'"
                           ).fetchone()["valor"] is True
        con.execute((migracoes.PASTA / "061_anexo_na_pendencia_VOLTA.sql").read_text(encoding="utf-8"))
    assert migracoes.aplicar(cfg) == ["061_anexo_na_pendencia.sql"]


def test_a_linha_com_anexo_baixa_o_arquivo_e_grava_o_caminho(ligado, tmp_path):
    e = ErpComAnexo([com_anexo(101)])
    volta(ligado, e)            # a primeira volta so guarda o cursor
    e.linhas = [com_anexo(101)]
    volta(ligado, e)
    (m,) = mensagens(ligado)
    assert m["anexo"]["nome"] == "Roteiro.docx" and m["anexo"]["media_type"] == DOCX
    assert (tmp_path / "chamados" / "101-Roteiro.docx").read_bytes() == b"PK-docx"


def test_erp_fora_ao_baixar_nao_grava_nem_anda_o_cursor(ligado):
    e = ErpComAnexo([com_anexo(101)], falha=erp.ErpIndisponivel("o ERP não respondeu"))
    volta(ligado, e)
    e.linhas = [com_anexo(101)]
    assert "erro" in volta(ligado, e)
    assert mensagens(ligado) == []
    with conexao(ligado) as con:
        assert con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'pendencias.cursor'"
                           ).fetchone()["valor"] == 100 and e.pedidos[-1] == 100


def test_anexo_recusado_de_vez_deixa_a_mensagem_sair_so_com_o_texto(ligado):
    e = ErpComAnexo([com_anexo(101)], falha=erp.ErpRecusou("o anexo 7: o ERP recusou (404)"))
    volta(ligado, e)
    e.linhas = [com_anexo(101)]
    volta(ligado, e)
    (m,) = mensagens(ligado)
    assert m["anexo"] is None and m["texto"] == "Fran, segue o roteiro."


def test_o_documento_sai_logo_depois_do_texto_e_antes_dos_botoes(ligado):
    e = ErpComAnexo([com_anexo(101, classe="entrega", nome="Manual.pdf", tipo="application/pdf")],
                    arquivos={7: b"%PDF-1.4"})
    volta(ligado, e)
    e.linhas = [com_anexo(101, classe="entrega", nome="Manual.pdf", tipo="application/pdf")]
    volta(ligado, e)
    falou(ligado, AGORA - timedelta(hours=1))
    s = mandar(ligado)
    assert [x[0] for x in s.enviadas] == ["texto", "documento", "botoes"]
    assert s.enviadas[1][2] == "Chamado #350"
    assert s.documentos == [(FRAN, b"%PDF-1.4", "Manual.pdf")] and s.mimes == ["application/pdf"]


def test_word_sai_com_o_tipo_do_word(ligado):
    receber_com_anexo(ligado)
    falou(ligado, AGORA - timedelta(hours=1))
    s = mandar(ligado)
    assert s.mimes == [DOCX]


def test_chave_desligada_manda_so_o_texto(ligado):
    receber_com_anexo(ligado)
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'pendencias.anexo_ligado'")
    falou(ligado, AGORA - timedelta(hours=1))
    s = mandar(ligado)
    assert [x[0] for x in s.enviadas] == ["texto"]


def test_arquivo_sumido_do_disco_nao_desfaz_o_texto(ligado, tmp_path):
    receber_com_anexo(ligado)
    (tmp_path / "chamados" / "101-Roteiro.docx").unlink()
    falou(ligado, AGORA - timedelta(hours=1))
    s = mandar(ligado)
    assert [x[0] for x in s.enviadas] == ["texto"]
    (m,) = mensagens(ligado)
    assert m["estado"] == "enviada" and m["erro"].startswith("anexo:")


def test_fora_da_janela_o_anexo_espera_com_o_texto(ligado):
    receber_com_anexo(ligado)
    s = mandar(ligado)
    assert [x[0] for x in s.enviadas] == ["modelo"]      # a reabertura; nem texto nem documento
    (m,) = mensagens(ligado)
    assert m["estado"] == "guardada" and m["anexo"] is not None


def test_linha_sem_anexo_segue_como_sempre(ligado):
    receber(ligado, [linha(101, "pergunta")])
    falou(ligado, AGORA - timedelta(hours=1))
    s = mandar(ligado)
    assert [x[0] for x in s.enviadas] == ["texto"]


def receber_com_anexo(cfg):
    e = ErpComAnexo([com_anexo(101)])
    volta(cfg, e)
    e.linhas = [com_anexo(101)]
    volta(cfg, e)
    return e
