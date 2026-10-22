"""#1099: o lote e a frase pela hora de ENVIO, e grupo fechado nao recebe lote novo.

Os casos sao os de 22/10/2026 (tabela da spec): o album que chegou 1 min depois de o grupo anterior
fechar e herdou o titulo dele; a frase mandada 19 s depois do album e que chegou 45 min antes da foto;
a frase de 49 min antes que nao e do album. E a pergunta "E do mesmo assunto da anterior?"."""
from datetime import date, timedelta

from backend import campo
from backend.banco import conexao
from tests.avisos_meta import texto, toque
from tests.saida_falsa import IAFalsa, SaidaFalsa
from tests.test_campo import AGORA, EQUIPE, MIN, canal, foto, ligar, material, minuto, passo  # noqa: F401
from tests.test_campo import textos

QUALIDADE = {"bastidor": "controle-de-qualidade", "produto": None, "fase": None}


def mandada(m: dict, quando) -> dict:
    """A mensagem MANDADA em `quando` (o celular pode entrega-la bem depois)."""
    return dict(m, timestamp=str(int(quando.timestamp())))


def _fechar_com_hoje(cfg, s, ia, agora, wamid="t-hoje"):
    minuto(cfg, s, agora, ia=ia)
    passo(cfg, s, toque(wamid, "campo:hoje:sim", numero=EQUIPE), agora=agora, ia=ia)


def grupos(cfg):
    return [m["grupo_id"] for m in material(cfg)]


def test_album_que_chega_depois_do_grupo_fechar_e_lote_novo(canal):
    """10:24 o grupo 58 fechou; 10:25 o album de 3 fotos entrou nele e herdou "Analise interna"."""
    ligar(canal)
    ia = IAFalsa(campo=QUALIDADE)
    s = SaidaFalsa()
    passo(canal, s, foto("a1", "Análise interna de qualidade"), ia=ia)
    _fechar_com_hoje(canal, s, ia, AGORA + 3 * MIN)
    assert material(canal)[0]["fechado_em"] is not None
    for i in range(3):
        passo(canal, s, foto("b%d" % i), agora=AGORA + 4 * MIN, ia=ia)
    passo(canal, s, mandada(texto("bt", "Beneficiamento Nabo-forrageiro IPR116, safra 2026, hoje", numero=EQUIPE),
                           AGORA + 4 * MIN + timedelta(seconds=18)), agora=AGORA + 4 * MIN + timedelta(seconds=21), ia=ia)
    m = material(canal)
    assert len({x["grupo_id"] for x in m[1:]}) == 1 and m[1]["grupo_id"] != m[0]["grupo_id"]
    assert all(x["legenda"].startswith("Beneficiamento Nabo") for x in m[1:])
    assert m[0]["legenda"] == "Análise interna de qualidade"
    assert all(x["fechado_em"] is None for x in m[1:])


def test_frase_mandada_19s_depois_do_album_chega_antes_da_foto_e_e_dela(canal):
    """08:54:56 o album, 08:55:15 a frase; a frase chegou 09:39, a foto 10:05."""
    ligar(canal)
    s = SaidaFalsa()
    t0 = AGORA - 70 * MIN
    passo(canal, s, mandada(texto("q1", "Qualidade, amostrando Nabo Forrageiro Safra 2026.", numero=EQUIPE),
                           t0 + timedelta(seconds=19)), agora=t0 + 45 * MIN)
    passo(canal, s, mandada(foto("f1"), t0), agora=t0 + 70 * MIN)
    m = material(canal)[0]
    assert m["legenda"] == "Qualidade, amostrando Nabo Forrageiro Safra 2026."
    assert m["enviado_em"] == t0


def test_frase_de_49_min_antes_nao_e_do_album(canal):
    """A frase de Qualidade (08:55) nao e titulo do album das 09:44; a das 09:44:46 e."""
    ligar(canal)
    s = SaidaFalsa()
    t0 = AGORA
    passo(canal, s, mandada(texto("q1", "Qualidade, amostrando Nabo", numero=EQUIPE), t0), agora=t0 + 45 * MIN)
    passo(canal, s, mandada(foto("f1"), t0 + 49 * MIN), agora=t0 + 49 * MIN)
    passo(canal, s, mandada(texto("q2", "Beneficiamento Nabo IPR116 2026", numero=EQUIPE), t0 + 49 * MIN + timedelta(seconds=10)),
          agora=t0 + 49 * MIN + timedelta(seconds=14))
    assert material(canal)[0]["legenda"] == "Beneficiamento Nabo IPR116 2026"
    with conexao(canal) as con:
        livre = con.execute("SELECT usada_em FROM atendimento.campo_frases WHERE texto LIKE 'Qualidade%'").fetchone()
    assert livre["usada_em"] is None


def test_foto_do_mesmo_envio_que_chega_atrasada_entra_no_grupo_dela_mesmo_fechado(canal):
    ligar(canal)
    ia = IAFalsa(campo=QUALIDADE)
    s = SaidaFalsa()
    passo(canal, s, foto("f1", "Amostra de nabo"), ia=ia)
    _fechar_com_hoje(canal, s, ia, AGORA + 3 * MIN)
    passo(canal, s, mandada(foto("f2"), AGORA + timedelta(seconds=20)), agora=AGORA + 30 * MIN, ia=ia)
    m = material(canal)
    assert m[1]["grupo_id"] == m[0]["grupo_id"] and m[1]["fechado_em"] is not None
    assert len(s.enviadas) == 3                       # nada de "Recebi." de novo


def test_lote_sem_frase_logo_depois_de_um_fechado_pergunta_se_e_o_mesmo_e_sim_herda(canal):
    """O caso do Benedito em 14/10: a foto 2 min depois de "Carregamento do dia" fechar, sem frase."""
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "entrega", "produto": None, "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("f1", "Carregamento do dia"), ia=ia)
    _fechar_com_hoje(canal, s, ia, AGORA + 3 * MIN)
    passo(canal, s, foto("f2"), agora=AGORA + 5 * MIN, ia=ia)
    minuto(canal, s, AGORA + 8 * MIN, ia=ia)
    tipo, _, corpo, opcoes = s.ultima
    assert tipo == "botoes" and corpo == "É do mesmo assunto da anterior (Carregamento do dia)?"
    assert [o[1] for o in opcoes] == ["Sim", "Outra coisa"]
    assert material(canal)[1]["pergunta_n"] == 0      # nao conta no limite de tres
    passo(canal, s, toque("t2", "campo:mesmo:sim", numero=EQUIPE), agora=AGORA + 9 * MIN, ia=ia)
    a, b = material(canal)
    assert b["grupo_id"] != a["grupo_id"] and b["fechado_em"] is not None
    assert (b["legenda"], b["classe_bastidor"], b["data_dita"]) == ("Carregamento do dia", "entrega", date(2026, 10, 12))
    assert s.ultima[2] == campo.ANOTADO


def test_outra_coisa_segue_o_roteiro_de_sempre(canal):
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "entrega", "produto": None, "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("f1", "Carregamento do dia"), ia=ia)
    _fechar_com_hoje(canal, s, ia, AGORA + 3 * MIN)
    passo(canal, s, foto("f2"), agora=AGORA + 5 * MIN, ia=ia)
    minuto(canal, s, AGORA + 8 * MIN, ia=ia)
    passo(canal, s, toque("t2", "campo:mesmo:outra", numero=EQUIPE), agora=AGORA + 9 * MIN, ia=ia)
    assert s.ultima[2] == campo.PERGUNTA_LEGENDA
    assert material(canal)[1]["fechado_em"] is None


def test_lote_sem_frase_muito_depois_nao_pergunta_se_e_o_mesmo(canal):
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "entrega", "produto": None, "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("f1", "Carregamento do dia"), ia=ia)
    _fechar_com_hoje(canal, s, ia, AGORA + 3 * MIN)
    passo(canal, s, foto("f2"), agora=AGORA + 30 * MIN, ia=ia)
    minuto(canal, s, AGORA + 33 * MIN, ia=ia)
    assert s.ultima[2] == campo.PERGUNTA_LEGENDA


def test_com_a_chave_desligada_volta_a_regra_de_chegada(canal):
    ligar(canal)
    with conexao(canal) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'campo.lote_pelo_envio'")
    ia = IAFalsa(campo=QUALIDADE)
    s = SaidaFalsa()
    passo(canal, s, foto("a1", "Análise interna de qualidade"), ia=ia)
    _fechar_com_hoje(canal, s, ia, AGORA + 3 * MIN)
    passo(canal, s, foto("b1"), agora=AGORA + 4 * MIN, ia=ia)
    a, b = material(canal)
    assert b["grupo_id"] == a["grupo_id"]             # o comportamento de antes, como rollback


def test_hora_de_envio_no_futuro_vale_a_chegada():
    class E:
        enviado_em = AGORA + 10 * MIN
    assert campo.hora_de_envio(E(), AGORA) == AGORA
    E.enviado_em = AGORA - 33 * 60 * MIN              # 33 h de atraso e legitimo
    assert campo.hora_de_envio(E(), AGORA) == AGORA - 33 * 60 * MIN


def test_a_volta_da_028_limpa_a_pergunta_mesmo(canal):
    from pathlib import Path
    ligar(canal)
    ia = IAFalsa(campo={"bastidor": "entrega", "produto": None, "fase": None})
    s = SaidaFalsa()
    passo(canal, s, foto("f1", "Carregamento do dia"), ia=ia)
    _fechar_com_hoje(canal, s, ia, AGORA + 3 * MIN)
    passo(canal, s, foto("f2"), agora=AGORA + 5 * MIN, ia=ia)
    minuto(canal, s, AGORA + 8 * MIN, ia=ia)
    assert material(canal)[1]["pergunta_pendente"] == "mesmo"
    volta = Path(__file__).resolve().parents[1] / "backend" / "migracoes" / "028_lote_pelo_envio_VOLTA.sql"
    with conexao(canal) as con:
        con.execute(volta.read_text(encoding="utf-8").replace("BEGIN;", "").replace("COMMIT;", ""))
    assert material(canal)[1]["pergunta_pendente"] is None
    assert textos(s)
