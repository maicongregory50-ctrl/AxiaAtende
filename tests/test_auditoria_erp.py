"""#350: o aviso da auditoria de estoque vencida. O ERP deixa PENDENTE; as telas gravam um aviso por
destino do ajuste (o dono e a Fran) e devolvem o estado; quem manda e o porteiro dos avisos."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from backend import auditoria_erp, erp
from backend.banco import conexao
from backend.envio import Envio
from tests.saida_falsa import SaidaFalsa

AGORA = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
PENDENTE = {"id": 4, "partes": ["Matriz", "29/10/2026"]}


@pytest.fixture
def ligado(cfg):
    return replace(cfg, erp_segredo="segredo-de-teste", porteiro=True, responde=True)


class ErpFalso:
    def __init__(self, pendentes=()):
        self.pendentes = list(pendentes)
        self.estados = []

    def ir(self, cfg):
        return {"pendentes": self.pendentes, "token": "t"}

    def devolver(self, cfg, token, aviso_id, estado, motivo="", wamid=""):
        self.estados.append((aviso_id, estado, motivo, wamid))


def _volta(cfg, e):
    return auditoria_erp.volta(cfg, ir=e.ir, devolver=e.devolver)


def _avisos(cfg):
    with conexao(cfg) as con:
        return [dict(a) for a in con.execute(
            "SELECT * FROM atendimento.avisos WHERE tipo = 'auditoria_estoque' ORDER BY id").fetchall()]


def test_a_migracao_poe_o_dono_e_a_fran(cfg):
    with conexao(cfg) as con:
        nomes = [d["nome"] for d in auditoria_erp.destinos(con)]
        m = con.execute("SELECT * FROM atendimento.modelos WHERE uso = 'aviso_auditoria_estoque'").fetchone()
    assert sorted(nomes) == ["Fran", "Maicon Gregory"]
    assert m["variaveis"] == ["aviso1", "aviso2"] and "{{1}}" in m["texto"] and "{{2}}" in m["texto"]


def test_sem_o_segredo_nem_tenta(cfg):
    assert auditoria_erp.volta(cfg) == {"erro": "a ligação com o ERP não está ligada"}


def test_erp_fora_do_ar_e_dito(ligado):
    def ir(cfg):
        raise erp.ErpIndisponivel("o ERP não respondeu")
    assert auditoria_erp.volta(ligado, ir=ir) == {"erro": "o ERP não respondeu"}


def test_um_aviso_por_destino_e_nao_duplica(ligado):
    e = ErpFalso([PENDENTE])
    assert _volta(ligado, e)["novos"] == 1
    assert _volta(ligado, e)["novos"] == 0
    a = _avisos(ligado)
    assert len(a) == 2 and {x["sobre"] for x in a} == {"Matriz|29/10/2026"}
    assert e.estados == []                       # ninguem recebeu ainda: o ERP nao ouve nada


def test_saiu_para_um_e_o_erp_ouve_enviado(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    with conexao(ligado) as con:
        con.execute("""UPDATE atendimento.avisos SET enviado_em = %s, wamid = 'wamid.a'
                        WHERE id = (SELECT min(id) FROM atendimento.avisos WHERE tipo = 'auditoria_estoque')""", (AGORA,))
    _volta(ligado, e)
    assert e.estados == [(4, "ENVIADO", "", "wamid.a")]
    _volta(ligado, e)
    assert len(e.estados) == 1                   # devolvido uma vez so


def test_todos_com_erro_o_erp_ouve_falhou(ligado):
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.avisos SET erro = 'numero invalido' WHERE tipo = 'auditoria_estoque'")
    _volta(ligado, e)
    assert e.estados == [(4, "FALHOU", "numero invalido", "")]


def test_sem_ninguem_no_ajuste_falha_com_o_motivo(ligado):
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = '[]'::jsonb WHERE chave = 'auditoria_estoque_para'")
    e = ErpFalso([PENDENTE])
    _volta(ligado, e)
    assert e.estados and e.estados[0][1] == "FALHOU" and "Ninguém configurado" in e.estados[0][2]


def test_o_porteiro_guarda_fora_da_janela_com_o_texto_do_modelo(ligado):
    from backend import envio as envio_mod
    _volta(ligado, ErpFalso([PENDENTE]))
    with conexao(ligado) as con:
        a = con.execute("SELECT * FROM atendimento.avisos WHERE tipo = 'auditoria_estoque' ORDER BY id LIMIT 1").fetchone()
        texto = envio_mod.texto_do_aviso(con, a)
        en = Envio()
        en._porteiro = True
        en.mandar_avisos(con, SaidaFalsa(), AGORA)
    assert texto == ("A auditoria de estoque da Matriz está vencida: a última lista foi gerada em 29/10/2026. "
                     "Abra Relatórios → Auditoria de estoque no AxiaGestão.")
    # ninguem falou com a empresa: fora da janela, o aviso fica guardado esperando o Ver
    assert all(x["guardado_em"] is not None and x["enviado_em"] is None for x in _avisos(ligado))
