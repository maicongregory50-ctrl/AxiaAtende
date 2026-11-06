"""#1271 (dono, 05/11/2026): "o representante recebe se tiver janela de 24h aberta, se nao, fica na fila
ate abrir". O resumo do lote fora da janela e guardado sem a reabertura paga, nao vira "nao visto", e os
guardados saem juntos numa mensagem so quando ele escreve. Os outros avisos seguem o porteiro do #1188."""
from datetime import timedelta

from backend import envio as envio_mod
from backend.banco import conexao
from tests.test_1188_porteiro import AGORA, REP, avisar, avisos, falou, porteiro, saida, toque_ver, volta  # noqa: F401

RESUMO = "lote_do_representante"


def resumo(cfg, quantos="5 clientes seus", assunto="Boletim de safra nº 1", minutos=0):
    return avisar(cfg, tipo=RESUMO, sobre="Dj|%s|%s" % (quantos, assunto), criado=AGORA + timedelta(minutes=minutos))


def chave(cfg, valor):
    with conexao(cfg) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = 'resumo.espera_calado'",
                    ("true" if valor else "false",))


def test_a_059_liga_a_chave(porteiro):
    with conexao(porteiro) as con:
        assert envio_mod.resumo_espera_calado(con) is True
        con.execute("DELETE FROM atendimento.ajustes WHERE chave = 'resumo.espera_calado'")
        assert envio_mod.resumo_espera_calado(con) is True          # ausente conta como ligada


def test_fora_da_janela_o_resumo_e_guardado_sem_reabertura(porteiro):
    resumo(porteiro)
    s = saida()
    volta(porteiro, s)
    assert s.modelos == [] and s.enviadas == []                     # nada pago
    a = avisos(porteiro)[0]
    assert a["guardado_em"] == AGORA and a["reabertura_id"] is None and a["enviado_em"] is None


def test_oito_dias_depois_o_resumo_continua_guardado(porteiro):
    resumo(porteiro)
    volta(porteiro, saida())
    s = saida()
    volta(porteiro, s, AGORA + timedelta(days=8))
    a = avisos(porteiro)[0]
    assert a["nao_visto_em"] is None and a["enviado_em"] is None and s.modelos == []


def test_quando_ele_escreve_os_resumos_saem_juntos_numa_mensagem(porteiro):
    resumo(porteiro, "5 clientes seus", "Boletim de safra nº 1")
    resumo(porteiro, "3 clientes seus", "Plano safra", minutos=1)
    resumo(porteiro, "1 cliente seu", "Pacote da revenda", minutos=2)
    volta(porteiro, saida(), AGORA + timedelta(minutes=5))
    falou(porteiro, AGORA + timedelta(days=3))
    s = saida()
    volta(porteiro, s, AGORA + timedelta(days=3, minutes=1))
    assert len(s.enviadas) == 1 and s.modelos == []
    texto = s.enviadas[0][2]
    assert texto.startswith("Olá, Dj.")
    assert "• 5 clientes seus: Boletim de safra nº 1" in texto and "• 1 cliente seu: Pacote da revenda" in texto
    todos = avisos(porteiro)
    assert all(a["como"] == "texto" and a["enviado_em"] is not None for a in todos)
    assert len({a["wamid"] for a in todos}) == 1


def test_um_resumo_so_sai_com_a_frase_de_sempre(porteiro):
    resumo(porteiro)
    volta(porteiro, saida())
    falou(porteiro, AGORA + timedelta(hours=2))
    s = saida()
    volta(porteiro, s, AGORA + timedelta(hours=2, minutes=1))
    assert len(s.enviadas) == 1 and "acabaram de receber" in s.enviadas[0][2]


def test_outro_aviso_da_equipe_ainda_pede_a_reabertura(porteiro):
    resumo(porteiro)
    avisar(porteiro, criado=AGORA + timedelta(minutes=1))           # a recusa de um cliente
    s = saida()
    volta(porteiro, s, AGORA + timedelta(minutes=2))
    assert [m["nome"] for m in s.modelos] == ["reabrir_avisos"]
    r, recusa = avisos(porteiro)
    assert r["reabertura_id"] is None and recusa["reabertura_id"] is not None
    # o toque em Ver solta os dois; a recusa conta os 7 dias, o resumo nao
    s2 = saida()
    toque_ver(porteiro, s2, agora=AGORA + timedelta(hours=1))
    assert len(s2.enviadas) == 2 and all(a["enviado_em"] for a in avisos(porteiro))


def test_a_recusa_vira_nao_visto_e_o_resumo_do_mesmo_numero_nao(porteiro):
    resumo(porteiro)
    avisar(porteiro, criado=AGORA + timedelta(minutes=1))
    volta(porteiro, saida(), AGORA + timedelta(minutes=2))
    volta(porteiro, saida(), AGORA + timedelta(days=8))
    r, recusa = avisos(porteiro)
    assert recusa["nao_visto_em"] is not None and r["nao_visto_em"] is None


def test_chave_desligada_volta_ao_porteiro_de_hoje(porteiro):
    """O ROLLBACK: desligada, o resumo guardado calado volta a ser aviso novo e pede a reabertura."""
    resumo(porteiro)
    volta(porteiro, saida())
    chave(porteiro, False)
    s = saida()
    volta(porteiro, s, AGORA + timedelta(hours=1))
    assert [m["nome"] for m in s.modelos] == ["reabrir_avisos"]
    a = avisos(porteiro)[0]
    assert a["reabertura_id"] is not None and a["guardado_em"] == AGORA + timedelta(hours=1)
