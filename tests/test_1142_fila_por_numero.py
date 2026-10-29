"""#1142 — a fila por NÚMERO, o papel do contato, e o resumo ao representante no lugar da cópia.

O caso que isto protege: desde o #1141 o ERP entrega uma linha por CONTATO do cliente, e na camada
cooperativa o comprador e o técnico do mesmo cadastro caem no mesmo envio. Pela unicidade antiga (por
cadastro) o segundo era descartado em silêncio pelo `ON CONFLICT ... DO NOTHING` — não era recusa,
era sumir.
"""
from datetime import timedelta

import pytest

from backend import migracoes
from backend.banco import conexao
from backend.envio import Envio
from tests.saida_falsa import SaidaFalsa
from tests.test_envio import QUINTA_10H, cliente, destinatarios, imagens, ligado, pedido, pedir  # noqa: F401

REPRESENTANTE = ("Djeison de Oliveira", "5549999567572")
DONO = ("Maicon Gregory", "5549991505565")


def _com(c, **extra):
    return {**c, **extra}


def avisos(cfg, tipo="lote_do_representante"):
    with conexao(cfg) as con:
        return [dict(a) for a in con.execute(
            "SELECT * FROM atendimento.avisos WHERE tipo = %s ORDER BY id", (tipo,)).fetchall()]


# ── a fila por número ─────────────────────────────────────────────────────────────────────────

def test_dois_contatos_do_mesmo_cadastro_entram_os_dois(ligado, imagens):
    """O caso da cooperativa: o comprador e o técnico do mesmo cliente, no mesmo envio."""
    comprador = _com(cliente(7, 100, whatsapp="47999000007"), papel="comprador",
                     responsavel_canal="representante", resp=REPRESENTANTE)
    tecnico = _com(cliente(7, 100, whatsapp="47999000070"), papel="tecnico",
                   responsavel_canal="representante", resp=REPRESENTANTE)
    comprador["responsavel_nome"], comprador["responsavel_whatsapp"] = REPRESENTANTE
    tecnico["responsavel_nome"], tecnico["responsavel_whatsapp"] = REPRESENTANTE
    assert pedir(ligado, pedido(imagens, [comprador, tecnico])).status_code == 200
    with conexao(ligado) as con:
        linhas = con.execute(
            "SELECT erp_codigo, whatsapp, papel, responsavel_canal FROM atendimento.envio_destinatarios"
            " ORDER BY papel").fetchall()
    assert [(l["papel"], l["whatsapp"]) for l in linhas] == [
        ("comprador", "5547999000007"), ("tecnico", "5547999000070")]
    assert {l["erp_codigo"] for l in linhas} == {7}
    assert {l["responsavel_canal"] for l in linhas} == {"representante"}


def test_a_mesma_pessoa_duas_vezes_no_mesmo_envio_entra_uma(ligado, imagens):
    """O marketing já junta por número antes de montar o pedido; aqui é o cinto do banco."""
    a = _com(cliente(8, 90, whatsapp="47999000008"), papel="comprador")
    b = _com(cliente(9, 80, whatsapp="47999000008"), papel="tecnico")
    assert pedir(ligado, pedido(imagens, [a, b])).status_code == 200
    with conexao(ligado) as con:
        linhas = con.execute("SELECT erp_codigo, whatsapp FROM atendimento.envio_destinatarios").fetchall()
    assert len(linhas) == 1 and linhas[0]["erp_codigo"] == 8   # o de maior faturamento


def test_dois_sem_celular_valido_entram_os_dois(ligado, imagens):
    """A unicidade é PARCIAL de propósito: `whatsapp = ''` é caso legítimo (`sem_whatsapp`), e sem
    o `WHERE` do índice os dois colidiriam."""
    a = _com(cliente(10, 70, whatsapp="4932"), papel="comprador")      # fixo: não é celular
    b = _com(cliente(11, 60, whatsapp="4933"), papel="comprador")
    assert pedir(ligado, pedido(imagens, [a, b])).status_code == 200
    d = destinatarios(ligado)
    assert len(d) == 2
    assert [x["situacao"] for x in d.values()] == ["sem_whatsapp", "sem_whatsapp"]


def test_o_pedido_sem_papel_nem_canal_continua_entrando(ligado, imagens):
    """O pedido do marketing de antes do #1142 não manda os dois campos: eles ficam nulos."""
    assert pedir(ligado, pedido(imagens, [cliente(1, 10)])).status_code == 200
    with conexao(ligado) as con:
        l = con.execute("SELECT papel, responsavel_canal FROM atendimento.envio_destinatarios").fetchone()
    assert l["papel"] is None and l["responsavel_canal"] is None


# ── o resumo ao representante ─────────────────────────────────────────────────────────────────

def _mandar_o_lote(cfg, clientes, imgs):
    assert pedir(cfg, pedido(imgs, clientes)).status_code == 200
    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(cfg, s, QUINTA_10H)
    return s


def test_um_resumo_por_lote_ao_representante_e_nada_ao_cliente_a_mais(ligado, imagens):
    clientes = []
    for i in range(3):
        c = cliente(20 + i, 100 - i, whatsapp="4799900%04d" % i, resp=REPRESENTANTE)
        clientes.append(_com(c, papel="comprador", responsavel_canal="representante"))
    s = _mandar_o_lote(ligado, clientes, imagens)
    convites = [x for x in s.modelos if x["para"].startswith("55479990")]
    assert len(convites) == 3
    # A CÓPIA ACABOU: nada foi mandado ao número do representante neste momento
    assert not [x for x in s.modelos if x["para"] == REPRESENTANTE[1] and x["nome"] == "pecas_da_revenda"]
    # e há UM resumo, com os três contados numa linha só
    todos = avisos(ligado)
    assert len(todos) == 1
    assert todos[0]["para_whatsapp"] == REPRESENTANTE[1]
    assert todos[0]["sobre"].split("|")[:2] == ["Djeison", "3 clientes seus"]


def test_o_resumo_nunca_vai_ao_dono_nem_ao_flutuante(ligado, imagens):
    """A cópia ia ao dono, porque o marketing o põe como responsável de toda revenda -- e foi assim
    que as artes da Agro Real e da Agro Símil chegaram ao WhatsApp dele em 23/10."""
    clientes = [_com(cliente(30, 100, whatsapp="47999000030", resp=DONO),
                     papel="comprador", responsavel_canal="dono"),
                _com(cliente(31, 90, whatsapp="47999000031", resp=DONO),
                     papel="comprador", responsavel_canal="flutuante")]
    s = _mandar_o_lote(ligado, clientes, imagens)
    assert len([x for x in s.modelos if x["para"].startswith("5547999000")]) == 2   # os clientes recebem
    assert avisos(ligado) == []
    assert not [x for x in s.modelos if x["para"] == DONO[1]]


def test_um_cliente_so_fala_no_singular(ligado, imagens):
    c = _com(cliente(40, 100, whatsapp="47999000040", resp=REPRESENTANTE),
             papel="comprador", responsavel_canal="representante")
    _mandar_o_lote(ligado, [c], imagens)
    assert avisos(ligado)[0]["sobre"].split("|")[1] == "1 cliente seu"


def test_o_resumo_sai_pelo_caminho_dos_avisos_com_o_modelo_novo(ligado, imagens):
    """Nada é mandado por `_resumo_ao_representante`: quem manda é `mandar_avisos`, que já existia."""
    c = _com(cliente(50, 100, whatsapp="47999000050", resp=REPRESENTANTE),
             papel="comprador", responsavel_canal="representante")
    s = _mandar_o_lote(ligado, [c], imagens)
    enviado = [x for x in s.modelos if x["nome"] == "aviso_lote_do_representante"]
    assert len(enviado) == 1 and enviado[0]["para"] == REPRESENTANTE[1]
    assert enviado[0]["corpo"] == ["Djeison", "1 cliente seu", "Trigo Mourisco IPR 92"]
    with conexao(ligado) as con:
        m = con.execute("SELECT categoria, botao, cabecalho_imagem FROM atendimento.modelos"
                        " WHERE uso = 'aviso_lote_do_representante'").fetchone()
    assert (m["categoria"], m["botao"], m["cabecalho_imagem"]) == ("UTILITY", "nenhum", False)
    assert avisos(ligado)[0]["enviado_em"] is not None and avisos(ligado)[0]["erro"] == ""


# ── o papel vai ao ERP ────────────────────────────────────────────────────────────────────────

def test_o_evento_ao_erp_leva_o_papel(ligado, imagens):
    from backend import eventos_erp
    c = _com(cliente(60, 100, whatsapp="47999000060", resp=REPRESENTANTE),
             papel="tecnico", responsavel_canal="representante")
    _mandar_o_lote(ligado, [c], imagens)
    with conexao(ligado) as con:
        eventos = eventos_erp.montar(con, QUINTA_10H + timedelta(minutes=1))
    assert [e["papel"] for e in eventos] == ["tecnico"]


# ── a VOLTA (o ida-volta-ida: a bateria de migrações não a cobre) ─────────────────────────────

def test_a_volta_desfaz_e_a_ida_volta_a_aplicar(cfg):
    """`tests/test_migracoes.py` prova a IDA; a VOLTA precisa da prova dela. E ela RECUSA desfazer
    quando há o que a unicidade antiga não aceita -- contando, em vez de falhar no meio."""
    volta = (migracoes.PASTA / "033_fila_por_numero_e_resumo_VOLTA.sql").read_text(encoding="utf-8")
    corpo = volta.split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0]
    # a 039 (#1188) reescreve o mesmo CHECK de uso do modelo: a volta dela vem antes (ordem inversa das idas)
    volta_039 = (migracoes.PASTA / "039_porteiro_dos_avisos_VOLTA.sql").read_text(encoding="utf-8")
    with conexao(cfg) as con:
        con.execute(volta_039.split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0])
        con.execute(corpo)
        assert not con.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'"
            " AND table_name = 'envio_destinatarios' AND column_name = 'papel'").fetchone()
        assert con.execute("SELECT 1 FROM pg_constraint WHERE conname = 'envio_dest_um_por_cliente'").fetchone()
        assert not con.execute("SELECT 1 FROM atendimento.modelos"
                               " WHERE uso = 'aviso_lote_do_representante'").fetchone()
    # e a ida aplica de novo, do zero
    assert migracoes.aplicar(cfg) == ["033_fila_por_numero_e_resumo.sql", "039_porteiro_dos_avisos.sql"]
    with conexao(cfg) as con:
        assert con.execute("SELECT 1 FROM pg_indexes WHERE schemaname = 'atendimento'"
                           " AND indexname = 'envio_dest_um_por_numero'").fetchone()


def test_a_volta_recusa_com_o_numero_quando_ha_aviso_do_tipo_novo(cfg):
    volta = (migracoes.PASTA / "033_fila_por_numero_e_resumo_VOLTA.sql").read_text(encoding="utf-8")
    corpo = volta.split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0]
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                       VALUES ('lote_do_representante', 'X', '5549999567572', 'a|b|c')""")
        with pytest.raises(Exception, match="aviso"):
            con.execute(corpo)
