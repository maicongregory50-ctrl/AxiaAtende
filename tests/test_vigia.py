"""O vigia do endereco publico (#969, etapa 3): dois "nao existe" seguidos avisam; a volta avisa;
sem resposta nao se afirma nada."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from backend import recepcionista as R
from backend import vigia
from backend.banco import conexao
from tests.saida_falsa import SaidaFalsa

T0 = datetime(2026, 10, 8, 17, 0, tzinfo=timezone.utc)    # 14:00 em Sao Paulo


@pytest.fixture
def ligado(cfg):
    return replace(cfg, responde=True)


def _avisos(cfg):
    with conexao(cfg) as con:
        return [(a["tipo"], a["sobre"]) for a in con.execute("SELECT * FROM atendimento.avisos ORDER BY id").fetchall()]


def _rodar(cfg, respostas, de=T0, passo=timedelta(minutes=5)):
    perguntas = []
    for i, r in enumerate(respostas):
        R.rotina_do_minuto(cfg, SaidaFalsa(), agora=de + passo * i,
                           perguntar=lambda r=r: perguntas.append(1) or r)
    return len(perguntas)


def test_dois_nao_existe_seguidos_avisam_uma_vez_e_a_volta_avisa(ligado):
    _rodar(ligado, [True, False])
    assert _avisos(ligado) == []                              # um so pode ser soluco
    _rodar(ligado, [False, False, False], de=T0 + timedelta(minutes=10))
    assert [t for t, _ in _avisos(ligado)] == ["endereco_fora"]
    assert _avisos(ligado)[0][1] == "%s|08/10 14:10" % vigia.NOME
    _rodar(ligado, [True, True], de=T0 + timedelta(minutes=95))
    tipos = _avisos(ligado)
    assert [t for t, _ in tipos] == ["endereco_fora", "endereco_voltou"]
    assert tipos[1][1] == "%s|08/10 15:35|1h25" % vigia.NOME
    with conexao(ligado) as con:
        assert vigia.estado(con)["situacao"] == "no_ar"


def test_sem_resposta_nao_e_fora_e_nao_zera_a_contagem(ligado):
    _rodar(ligado, [False, None, None])
    assert _avisos(ligado) == []
    _rodar(ligado, [False], de=T0 + timedelta(minutes=15))
    assert [t for t, _ in _avisos(ligado)] == ["endereco_fora"]


def test_so_pergunta_a_cada_cinco_minutos(ligado):
    assert _rodar(ligado, [True] * 6, passo=timedelta(minutes=1)) == 2


def test_quem_pergunta_falhar_nao_segura_a_rotina(ligado):
    def quebra():
        raise RuntimeError("sem rede")
    R.rotina_do_minuto(ligado, SaidaFalsa(), agora=T0, perguntar=quebra)   # nao levanta


def _http(respostas):
    fila = list(respostas)

    def responder(req):
        r = fila.pop(0)
        if r is None:
            raise httpx.ConnectError("fora")
        return httpx.Response(200, json=r)
    return httpx.Client(transport=httpx.MockTransport(responder))


@pytest.mark.parametrize("respostas, esperado", [
    ([{"Status": 0, "Answer": [{"data": "199.38.181.54"}]}], True),
    ([{"Status": 3}, {"Status": 3}], False),
    ([{"Status": 3}, None], None),              # um resolvedor fora: nao se afirma
    ([{"Status": 2}, {"Status": 3}], None),     # resolvedor com defeito nao e nome fora
    ([None, {"Status": 0, "Answer": [{"data": "1.2.3.4"}]}], True),
])
def test_existe_pergunta_a_dois_resolvedores_publicos(respostas, esperado):
    assert vigia.existe("nome.exemplo", http=_http(respostas)) is esperado


def test_resolver_devolve_o_ip_publico_e_pula_o_apelido():
    resposta = {"Status": 0, "Answer": [{"type": 5, "data": "outro.nome."}, {"type": 1, "data": "9.9.9.9"}]}
    assert vigia.resolver("nome.exemplo", http=_http([resposta])) == (True, "9.9.9.9")


def test_responde_abre_a_saude_pelo_ip_com_o_nome_no_tls():
    pedidos = []

    def responder(req):
        pedidos.append(req)
        return httpx.Response(503)                       # banco fora: mesmo assim o caminho chegou
    assert vigia.responde("9.9.9.9", "nome.exemplo", http=httpx.Client(transport=httpx.MockTransport(responder)))
    p = pedidos[0]
    assert str(p.url) == "https://9.9.9.9/saude" and p.headers["host"] == "nome.exemplo"
    assert p.extensions["sni_hostname"] == "nome.exemplo"
    assert vigia.responde("9.9.9.9", "nome.exemplo", http=_http([None])) is False


@pytest.mark.parametrize("resolvido, abre, esperado", [
    ((True, "9.9.9.9"), True, True),
    ((True, "9.9.9.9"), False, False),      # o nome existe e o Funnel nao repassa
    ((False, None), True, False),
    ((None, None), True, None),             # sem internet: nao se afirma
    ((True, None), False, True),            # existe, sem IP para abrir: vale o nome
])
def test_confere_junta_o_nome_e_o_repasse(resolvido, abre, esperado):
    assert vigia.confere("nome.exemplo", resolver=lambda n: resolvido, responde=lambda ip, n: abre) is esperado
