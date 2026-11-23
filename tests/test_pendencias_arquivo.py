"""#1528: o chamado no WhatsApp -- a VOLTA COM ARQUIVO. Quem recebeu a pergunta do chamado devolve o arquivo
pelo WhatsApp; o recepcionista baixa para o transito, as TELAS o levam ao ERP (que decide pelo conteudo e
pelo antivirus), e a rajada vira UM comentario. Meta e ERP falsos. Os casos (a) a (j) do passo 12 do plano;
o (k), a chave desligada, e a bateria de sempre (test_pendencias, test_campo, test_logos, test_roteador)."""
from dataclasses import replace
from datetime import timedelta
from itertools import count

import pytest

from backend import arquivo_volta, erp, motor, pendencias, pendencias_erp
from backend.banco import conexao
from backend.envio import Envio
from tests.test_pendencias import AGORA, FRAN, FRAN_META, ErpFalso, falou, linha, mensagens, saida, volta

_IDS = count(1)
OUTRO = "554999000111"


@pytest.fixture
def ligado(cfg, tmp_path):
    c = replace(cfg, erp_segredo="segredo-de-teste", porteiro=True, responde=True)
    with conexao(c) as con:
        for chave, valor in (("pendencias.ligado", "true"), ("pendencias.juntar_minutos", "0"),
                             ("pendencias.arquivo_volta", "true")):
            con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = %s", (valor, chave))
    arquivo_volta.PASTA = tmp_path / "chamados_volta"
    yield c
    arquivo_volta.PASTA = None


class ErpArquivos:
    """O ERP falso da volta com arquivo: a resposta de cada arquivo vem do nome dele."""

    def __init__(self):
        self.enviados, self.respostas = [], []
        self.sem_antivirus = False

    def enviar(self, cfg, token, demanda_id, numero, caminho, nome):
        self.enviados.append((demanda_id, numero, nome, open(caminho, "rb").read()))
        if self.sem_antivirus:
            raise erp.SemAntivirus("Recebi '%s', mas o nosso verificador de segurança está fora do ar." % nome)
        if nome.endswith(".xlsm"):
            raise erp.ArquivoRecusado("macro", "arquivo com macro")
        if "eicar" in nome:
            raise erp.ArquivoRecusado("ameaca", "o antivírus acusou o arquivo")
        if nome.endswith(".exe"):
            raise erp.ArquivoRecusado("tipo", "tipo de arquivo não aceito (só PDF, Word, Excel ou foto)")
        return {"anexo_id": 7000 + len(self.enviados), "nome": nome}

    def responder(self, cfg, token, demanda_id, numero, texto, anexo_ids=None):
        self.respostas.append((demanda_id, numero, texto, list(anexo_ids or [])))
        return 9000 + len(self.respostas)


def pergunta_aberta(cfg, classe="pergunta"):
    """O chamado 350 manda a pergunta a Fran; devolve o wamid da mensagem que saiu."""
    e = ErpFalso([linha(101, classe)])
    volta(cfg, e)
    volta(cfg, e)
    falou(cfg, AGORA - timedelta(hours=1))
    s = saida()
    with conexao(cfg) as con:
        pendencias.mandar(con, s, AGORA)
    return next(m["wamid"] for m in mensagens(cfg, "saiu"))


def arquivo(cfg, s, nome="descricoes.pdf", contexto=None, foto=False, numero=FRAN_META, agora=AGORA):
    wamid = "wamid.arq.%d" % next(_IDS)
    e = motor.Entrada(wamid=wamid, tipo="image" if foto else "document",
                      pessoa=motor.Pessoa(bsuid="BR.f", wa_id=numero, nome="Fran"), contexto=contexto)
    if foto:
        e.midia = motor.Midia(id="m-" + wamid, tipo="foto", mime="image/jpeg")
    else:
        e.documento = motor.Documento(id="m-" + wamid, mime="application/pdf", nome_arquivo=nome)
    with conexao(cfg) as con:
        motor.tratar(con, s, None, e, agora, Envio(), None)
    return wamid


def texto(cfg, s, t, contexto=None, agora=AGORA):
    e = motor.Entrada(wamid="wamid.t.%d" % next(_IDS), tipo="text",
                      pessoa=motor.Pessoa(bsuid="BR.f", wa_id=FRAN_META, nome="Fran"), texto=t, contexto=contexto)
    with conexao(cfg) as con:
        motor.tratar(con, s, None, e, agora, Envio(), None)


def toque(cfg, s, t, agora=AGORA):
    e = motor.Entrada(wamid="wamid.k.%d" % next(_IDS), tipo="interactive",
                      pessoa=motor.Pessoa(bsuid="BR.f", wa_id=FRAN_META, nome="Fran"), toque=t)
    with conexao(cfg) as con:
        motor.tratar(con, s, None, e, agora, Envio(), None)


def levar(cfg, falso, agora):
    return pendencias_erp.levar_arquivos(cfg, "t", agora, falso.enviar, falso.responder)


def recepcionista(cfg, agora):
    s = saida()
    with conexao(cfg) as con:
        pendencias.mandar(con, s, agora)
    return s


def arquivos(cfg):
    return [m for m in mensagens(cfg, "entrou") if m["classe"] == "arquivo"]


def avisos(cfg, tipo):
    with conexao(cfg) as con:
        return [r["sobre"] for r in con.execute("SELECT sobre FROM atendimento.avisos WHERE tipo = %s ORDER BY id",
                                                (tipo,)).fetchall()]


# ── a migracao e a chave ─────────────────────────────────────────────────────

def test_a_chave_nasce_desligada_e_desligada_nada_e_baixado(cfg, tmp_path):
    # #1722: antes este teste afirmava que, desligada, o arquivo deslizado nao deixava linha nenhuma -- e
    # descia a corrente ate virar logo. Agora fica a linha de rastro da recusa (D1), e nada e baixado.
    c = replace(cfg, erp_segredo="segredo-de-teste", porteiro=True, responde=True)
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'pendencias.ligado'")
        con.execute("UPDATE atendimento.ajustes SET valor = '0'::jsonb WHERE chave = 'pendencias.juntar_minutos'")
        assert arquivo_volta.ligado(con) is False
    w = pergunta_aberta(c)
    arquivo_volta.PASTA = tmp_path
    try:
        s = saida()
        arquivo(c, s, contexto=w)
        assert [a["estado"] for a in arquivos(c)] == ["arquivo_recusado"] and not getattr(s, "baixadas", [])
    finally:
        arquivo_volta.PASTA = None


# ── #1722: a chave desligada e o arquivo que desliza uma mensagem de chamado ─

@pytest.fixture
def desligado(cfg, tmp_path):
    """Pendencias ligadas, volta com arquivo DESLIGADA (o estado de producao de 17/11 a 23/11/2026), e a
    Fran como da casa (destino ativo): e assim que o PDF dela chegou a logos.receber."""
    c = replace(cfg, erp_segredo="segredo-de-teste", porteiro=True, responde=True)
    with conexao(c) as con:
        for chave, valor in (("pendencias.ligado", "true"), ("pendencias.juntar_minutos", "0")):
            con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = %s", (valor, chave))
        con.execute("INSERT INTO atendimento.destinos (nome, whatsapp, ativo) VALUES ('Fran', %s, true)", (FRAN,))
    arquivo_volta.PASTA = tmp_path / "chamados_volta"
    yield c
    arquivo_volta.PASTA = None


def _pela_corrente(cfg, s, tmp_path, nome="RESCISAO LUCAS.pdf", contexto=None, agora=AGORA):
    """O arquivo pelo motor INTEIRO, com o campo presente: sem o campo a corrente nem chega a logo."""
    from backend import campo as C
    wamid = "wamid.arq.%d" % next(_IDS)
    e = motor.Entrada(wamid=wamid, tipo="document", contexto=contexto,
                      pessoa=motor.Pessoa(bsuid="BR.f", wa_id=FRAN_META, nome="Fran"))
    e.documento = motor.Documento(id="m-" + wamid, mime="application/pdf", nome_arquivo=nome)
    with conexao(cfg) as con:
        motor.tratar(con, s, None, e, agora, Envio(), C.Campo(tmp_path / "campo", None))
    return wamid


def _logos(cfg):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.logos_de_cliente").fetchall()


def test_1722_desligada_o_pdf_que_desliza_a_pergunta_nao_vira_logo(desligado, tmp_path):
    """O caso da Fran, 23/11/2026 15:06: o PDF deslizando a pergunta do 1541 virou "De qual cliente e a logo?"."""
    w = pergunta_aberta(desligado)
    s = saida()
    _pela_corrente(desligado, s, tmp_path, contexto=w)
    assert s.enviadas[-1][2] == arquivo_volta.DESLIGADA % "350"
    assert _logos(desligado) == [] and not getattr(s, "baixadas", [])
    (a,) = arquivos(desligado)
    assert a["estado"] == "arquivo_recusado" and a["arquivo"]["motivo"] == "desligada" and a["arquivo"]["avisado"]
    (av,) = avisos(desligado, "arquivo_sem_antivirus")
    assert av.startswith("está desligada, e Fran tentou mandar um arquivo no chamado 350,") and "ligar-arquivo" in av
    # a volta do minuto nao repete a frase (a linha ja nasce avisada)
    with conexao(desligado) as con:
        assert arquivo_volta.mandar(con, saida(), AGORA) == 0


def test_1722_segundo_arquivo_no_dia_ouve_a_frase_sem_segundo_aviso(desligado, tmp_path):
    w = pergunta_aberta(desligado)
    s = saida()
    _pela_corrente(desligado, s, tmp_path, contexto=w)
    _pela_corrente(desligado, s, tmp_path, "outro.pdf", contexto=w, agora=AGORA + timedelta(hours=1))
    assert [x[2] for x in s.enviadas].count(arquivo_volta.DESLIGADA % "350") == 2
    assert len(avisos(desligado, "arquivo_sem_antivirus")) == 1
    _pela_corrente(desligado, s, tmp_path, "amanha.pdf", contexto=w, agora=AGORA + timedelta(days=1))
    assert len(avisos(desligado, "arquivo_sem_antivirus")) == 2        # outro dia, outro aviso


def test_1722_o_aviso_da_desligada_so_sai_na_janela_e_acumula_calado(desligado, tmp_path):
    """Dono, 23/11/2026: "e melhor que so rode dentro da janela de 24 horas mesmo... quando acumula,
    deixa acumular". O aviso nasce guardado, sem reabertura: fora da janela nada e pago na Meta, oito
    dias depois continua guardado (nao vira "nao visto"), e sai como texto quando o dono escreve."""
    from tests.test_1188_porteiro import falou, volta
    w = pergunta_aberta(desligado)
    _pela_corrente(desligado, saida(), tmp_path, contexto=w)
    _pela_corrente(desligado, saida(), tmp_path, "amanha.pdf", contexto=w, agora=AGORA + timedelta(days=1))
    with conexao(desligado) as con:
        linhas = con.execute("""SELECT * FROM atendimento.avisos WHERE tipo = 'arquivo_sem_antivirus'
                                 ORDER BY id""").fetchall()
    assert len(linhas) == 2 and all(a["guardado_em"] and a["reabertura_id"] is None for a in linhas)
    dono = linhas[0]["para_whatsapp"]
    porteiro = replace(desligado, porteiro=True)
    s = saida()
    volta(porteiro, s, AGORA + timedelta(days=8))
    assert s.modelos == [] and s.enviadas == []                       # janela fechada: nada pago, nada sai
    with conexao(desligado) as con:
        assert con.execute("""SELECT count(*) AS n FROM atendimento.avisos WHERE tipo = 'arquivo_sem_antivirus'
                               AND nao_visto_em IS NULL AND enviado_em IS NULL""").fetchone()["n"] == 2
    meta = dono[:4] + dono[5:] if len(dono) == 13 else dono
    falou(porteiro, AGORA + timedelta(days=9), numero=meta)
    s = saida()
    volta(porteiro, s, AGORA + timedelta(days=9, minutes=1))
    assert s.modelos == [] and len(s.enviadas) == 2                   # os dois acumulados, como texto
    assert all("ligar-arquivo" in x[2] for x in s.enviadas)


def test_1722_reenvio_da_meta_nao_repete_a_frase(desligado):
    w = pergunta_aberta(desligado)
    s = saida()
    e = motor.Entrada(wamid="wamid.repetido", tipo="document", contexto=w,
                      pessoa=motor.Pessoa(bsuid="BR.f", wa_id=FRAN_META, nome="Fran"))
    e.documento = motor.Documento(id="m-rep", mime="application/pdf", nome_arquivo="r.pdf")
    with conexao(desligado) as con:
        assert arquivo_volta.tratar(con, s, e, AGORA) is True
        assert arquivo_volta.tratar(con, s, e, AGORA) is True
    assert len(s.enviadas) == 1 and len(arquivos(desligado)) == 1


def test_1722_desligada_o_pdf_sem_deslizar_vira_logo_como_hoje(desligado, tmp_path):
    """E a prova de que o teste acima chega mesmo a logo: sem citar, o mesmo PDF vira logo."""
    pergunta_aberta(desligado)
    s = saida()
    _pela_corrente(desligado, s, tmp_path)
    assert len(_logos(desligado)) == 1 and arquivos(desligado) == []
    assert avisos(desligado, "arquivo_sem_antivirus") == []


# ── (a) a Fran: deslizou, o ERP aceitou, um comentario, "Anotado" ───────────

def test_a_fran_desliza_o_pdf_e_ele_entra_no_chamado(ligado):
    w = pergunta_aberta(ligado)
    s = saida()
    arquivo(ligado, s, "descricoes.pdf", contexto=w)
    (a,) = arquivos(ligado)
    assert a["estado"] == "arquivo_a_validar" and a["arquivo"]["sha256"] and a["arquivo"]["tamanho"] > 0
    assert s.enviadas == []          # silencio: a rajada pode crescer
    falso = ErpArquivos()
    levar(ligado, falso, AGORA + timedelta(minutes=1))
    assert falso.enviados[0][:3] == (350, FRAN, "descricoes.pdf") and falso.respostas == []   # ainda aberta
    (a,) = arquivos(ligado)
    assert a["estado"] == "arquivo_validado" and a["arquivo"]["anexo_id"] == 7001
    from pathlib import Path
    assert not list(Path(arquivo_volta.PASTA).iterdir())   # a copia do transito ja saiu
    r = levar(ligado, falso, AGORA + timedelta(minutes=6))
    assert r["comentarios"] == 1 and falso.respostas == [(350, FRAN, "", [7001])]
    s = recepcionista(ligado, AGORA + timedelta(minutes=6))
    assert s.enviadas[-1][2] == "Anotado no chamado 350: 1 arquivo. ✓"
    with conexao(ligado) as con:
        assert con.execute("SELECT espera FROM atendimento.pendencias").fetchone()["espera"] is None


# ── (b) nao e dela ───────────────────────────────────────────────────────────

def test_outro_numero_citando_a_mesma_mensagem_nao_baixa_nada(ligado):
    w = pergunta_aberta(ligado)
    s = saida()
    arquivo(ligado, s, contexto=w, numero=OUTRO)
    assert arquivos(ligado) == [] and not getattr(s, "baixadas", [])
    falso = ErpArquivos()
    levar(ligado, falso, AGORA + timedelta(minutes=10))
    assert falso.enviados == [] and falso.respostas == []


# ── (c) a rajada ─────────────────────────────────────────────────────────────

def test_tres_arquivos_em_quatro_minutos_viram_um_comentario_e_o_quarto_pergunta(ligado):
    w = pergunta_aberta(ligado)
    s = saida()
    arquivo(ligado, s, "a.pdf", contexto=w)
    arquivo(ligado, s, "b.pdf", agora=AGORA + timedelta(minutes=2))
    arquivo(ligado, s, "c.pdf", agora=AGORA + timedelta(minutes=4))
    assert len({a["rajada_id"] for a in arquivos(ligado)}) == 1 and len(arquivos(ligado)) == 3
    arquivo(ligado, s, "d.pdf", agora=AGORA + timedelta(minutes=10))   # a rajada fechou as 9 min
    assert s.enviadas[-1][0] == "botoes" and s.enviadas[-1][2].startswith("É para o Chamado 350")
    falso = ErpArquivos()
    levar(ligado, falso, AGORA + timedelta(minutes=10))
    assert falso.respostas == [(350, FRAN, "", [7001, 7002, 7003])]


def test_o_texto_logo_depois_fecha_a_rajada_e_vai_junto(ligado):
    w = pergunta_aberta(ligado)
    s = saida()
    arquivo(ligado, s, "a.pdf", contexto=w)
    texto(ligado, s, "São as descrições da produção.", agora=AGORA + timedelta(minutes=1))
    assert [m for m in mensagens(ligado, "entrou") if m["classe"] == "resposta"][0]["texto"] == "São as descrições da produção."
    falso = ErpArquivos()
    levar(ligado, falso, AGORA + timedelta(minutes=1))   # fechou na hora: nao espera os 5 min
    assert falso.respostas == [(350, FRAN, "São as descrições da produção.", [7001])]


# ── (d) sem deslizar ─────────────────────────────────────────────────────────

def test_documento_sem_deslizar_pergunta_e_o_sim_faz_entrar(ligado):
    pergunta_aberta(ligado)
    s = saida()
    arquivo(ligado, s, "funcoes.docx")
    tipo, _, frase, opcoes = s.enviadas[-1]
    assert tipo == "botoes" and frase == "É para o Chamado 350 · Auditoria de estoque?"
    assert [t for _, t in opcoes] == ["Sim", "Outro assunto"]
    (a,) = arquivos(ligado)
    assert a["estado"] == "escolher" and not getattr(s, "baixadas", [])   # nada baixado antes do Sim
    toque(ligado, s, opcoes[0][0])
    (a,) = arquivos(ligado)
    assert a["estado"] == "arquivo_a_validar" and a["rajada_id"]


# ── (e) o canal de campo ─────────────────────────────────────────────────────

def test_foto_sem_deslizar_de_quem_e_do_campo_continua_foto_de_campo(ligado, monkeypatch):
    w = pergunta_aberta(ligado)
    monkeypatch.setattr(arquivo_volta, "_do_campo", lambda con, numero: True)
    s = saida()
    arquivo(ligado, s, foto=True)
    assert arquivos(ligado) == [] and not [x for x in s.enviadas if x[0] == "botoes"]
    arquivo(ligado, s, foto=True, contexto=w)   # a mesma foto, deslizada: vai ao chamado
    (a,) = arquivos(ligado)
    assert a["estado"] == "arquivo_a_validar" and a["arquivo"]["nome"].endswith(".jpg")


# ── (f) sem antivirus ────────────────────────────────────────────────────────

def test_sem_antivirus_a_frase_e_propria_o_suporte_e_avisado_e_o_arquivo_espera(ligado):
    w = pergunta_aberta(ligado)
    arquivo(ligado, saida(), "funcoes.pdf", contexto=w)
    falso = ErpArquivos()
    falso.sem_antivirus = True
    levar(ligado, falso, AGORA + timedelta(minutes=1))
    (a,) = arquivos(ligado)
    assert a["estado"] == "arquivo_a_validar" and a["arquivo"]["av_desde"]
    (av,) = avisos(ligado, "arquivo_sem_antivirus")
    assert "falta de antivírus" in av and "Chamado 350, de Fran" in av
    s = recepcionista(ligado, AGORA + timedelta(minutes=1))
    assert "verificador de segurança está fora do ar" in s.enviadas[-1][2] and "não precisa mandar de novo" in s.enviadas[-1][2]
    levar(ligado, falso, AGORA + timedelta(minutes=20))   # ainda fora: o aviso nao se repete antes de 1 h
    assert len(avisos(ligado, "arquivo_sem_antivirus")) == 1
    falso.sem_antivirus = False
    levar(ligado, falso, AGORA + timedelta(minutes=30))
    assert arquivos(ligado)[0]["estado"] == "entregue" and falso.respostas
    assert "o antivírus voltou" in avisos(ligado, "arquivo_sem_antivirus")[-1]
    s = recepcionista(ligado, AGORA + timedelta(minutes=30))
    assert s.enviadas[-1][2] == "Anotado no chamado 350: 1 arquivo. ✓"


def test_uma_hora_sem_antivirus_o_arquivo_sai_e_a_pessoa_sabe(ligado):
    w = pergunta_aberta(ligado)
    arquivo(ligado, saida(), "funcoes.pdf", contexto=w)
    falso = ErpArquivos()
    falso.sem_antivirus = True
    levar(ligado, falso, AGORA + timedelta(minutes=1))
    levar(ligado, falso, AGORA + timedelta(minutes=70))
    (a,) = arquivos(ligado)
    assert a["estado"] == "arquivo_recusado" and a["arquivo"]["motivo"] == "antivirus_expirou"
    s = recepcionista(ligado, AGORA + timedelta(minutes=70))
    assert "O verificador não voltou" in s.enviadas[-1][2] and "chamado 350" in s.enviadas[-1][2]


# ── (g) recusas ──────────────────────────────────────────────────────────────

def test_rajada_com_um_recusado_entram_os_outros_e_a_confirmacao_diz_quais(ligado):
    w = pergunta_aberta(ligado)
    s = saida()
    arquivo(ligado, s, "a.pdf", contexto=w)
    arquivo(ligado, s, "planilha.xlsm", agora=AGORA + timedelta(minutes=1))
    arquivo(ligado, s, "b.pdf", agora=AGORA + timedelta(minutes=2))
    falso = ErpArquivos()
    levar(ligado, falso, AGORA + timedelta(minutes=3))
    s = recepcionista(ligado, AGORA + timedelta(minutes=3))
    assert s.enviadas[-1][2] == "Não aceitei 'planilha.xlsm': arquivo com macro."
    levar(ligado, falso, AGORA + timedelta(minutes=8))
    assert falso.respostas == [(350, FRAN, "", [7001, 7003])]
    s = recepcionista(ligado, AGORA + timedelta(minutes=8))
    assert s.enviadas[-1][2] == "Anotado no chamado 350: 2 arquivos. ✓\nEntraram: a.pdf, b.pdf."


@pytest.mark.parametrize("nome, frase", [("x.exe", "tipo de arquivo não aceito")])
def test_cada_recusa_do_erp_chega_com_a_frase_dele(ligado, nome, frase):
    w = pergunta_aberta(ligado)
    arquivo(ligado, saida(), nome, contexto=w)
    levar(ligado, ErpArquivos(), AGORA + timedelta(minutes=1))
    s = recepcionista(ligado, AGORA + timedelta(minutes=1))
    assert frase in s.enviadas[-1][2]


# ── (h) sem pergunta aberta ──────────────────────────────────────────────────

def test_chamado_que_nao_espera_resposta_nao_aceita_arquivo(ligado):
    w = pergunta_aberta(ligado, classe="informativo")
    s = saida()
    arquivo(ligado, s, contexto=w)
    assert s.enviadas[-1][2] == arquivo_volta.NAO_ESPERA and arquivos(ligado) == []
    assert not getattr(s, "baixadas", [])


# ── (i) ameaca ───────────────────────────────────────────────────────────────

def test_ameaca_recusa_e_avisa_o_suporte(ligado):
    w = pergunta_aberta(ligado)
    arquivo(ligado, saida(), "eicar.docx", contexto=w)
    levar(ligado, ErpArquivos(), AGORA + timedelta(minutes=1))
    (a,) = arquivos(ligado)
    assert a["estado"] == "arquivo_recusado" and a["arquivo"]["motivo"] == "ameaca"
    (av,) = avisos(ligado, "arquivo_ameaca")
    assert "'eicar.docx', de Fran" in av and "chamado 350" in av
    from pathlib import Path
    assert not list(Path(arquivo_volta.PASTA).iterdir())


# ── (j) tetos ────────────────────────────────────────────────────────────────

def test_o_decimo_fecha_a_rajada_e_o_decimo_primeiro_e_recusado(ligado):
    w = pergunta_aberta(ligado)
    s = saida()
    for i in range(10):
        arquivo(ligado, s, "%d.pdf" % i, contexto=w, agora=AGORA + timedelta(seconds=10 * i))
    arquivo(ligado, s, "10.pdf", contexto=w, agora=AGORA + timedelta(minutes=2))
    assert s.enviadas[-1][2] == arquivo_volta.TETO_RAJADA % "10.pdf"
    falso = ErpArquivos()
    levar(ligado, falso, AGORA + timedelta(minutes=2))
    assert len(falso.respostas) == 1 and len(falso.respostas[0][3]) == 10   # fechou no decimo


def test_o_teto_do_dia_e_o_tamanho(ligado):
    w = pergunta_aberta(ligado)
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = '2'::jsonb WHERE chave = 'pendencias.arquivo_dia_teto'")
    s = saida()
    s.tamanhos = {}
    arquivo(ligado, s, "a.pdf", contexto=w)
    arquivo(ligado, s, "b.pdf", contexto=w)
    arquivo(ligado, s, "c.pdf", contexto=w)
    assert s.enviadas[-1][2] == arquivo_volta.TETO_DIA % "c.pdf"
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = '20'::jsonb WHERE chave = 'pendencias.arquivo_dia_teto'")
    wamid = "wamid.arq.%d" % (next(_IDS) + 1)
    s.tamanhos = {"m-" + wamid: 10 * 1024 * 1024 + 100_000}
    arquivo(ligado, s, "grande.pdf", contexto=w)
    assert s.enviadas[-1][2] == arquivo_volta.GRANDE % "grande.pdf"
