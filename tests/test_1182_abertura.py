"""#1182 (AxiaMarketing): o modelo da abertura do canal. O pedido `material` com ele e aceito, o convite
sai com o primeiro nome e os botoes Quero / Nao quero, e conta no teto do comprador como um envio.
Meta falsa: nada sai."""
from datetime import datetime, timezone

from backend.banco import conexao
from backend.envio import Envio
from tests.saida_falsa import SaidaFalsa
from tests.test_envio import cliente, ligado, imagens, pedido, pedir  # noqa: F401 (fixtures)

DIA_5 = datetime(2026, 11, 5, 13, 0, tzinfo=timezone.utc)   # quinta, 10:00 em Sao Paulo (#1192)


def test_a_abertura_sai_como_convite_com_o_primeiro_nome_e_os_botoes(ligado, imagens):
    c = cliente(1, 1000, whatsapp="47991110001")
    c["papel"] = "comprador"
    dados = dict(pedido(imagens, [c], ref="pub-abertura"), modelo="abertura_do_canal")
    assert pedir(ligado, dados).status_code == 200
    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, DIA_5)
    m = next(x for x in s.modelos if x["nome"] == "abertura_do_canal")
    assert len(m["corpo"]) == 1 and m["imagem"]
    assert m["botoes"] and m["botoes"][0].endswith(":quero") and m["botoes"][1].endswith(":nao_quero")
    with conexao(ligado) as con:
        r = con.execute("SELECT texto, uso FROM atendimento.modelos WHERE nome = 'abertura_do_canal'").fetchone()
    # o texto APROVADO na Meta (o da 036; a 037 o trocou e a 038 o devolveu, 28/10/2026)
    assert r["uso"] == "convite" and "começou a falar com você por aqui" in r["texto"]
    assert r["texto"].endswith("mandamos aqui na conversa.")
