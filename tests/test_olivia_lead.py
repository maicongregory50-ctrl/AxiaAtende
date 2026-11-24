"""#1660: a OlivIA qualifica o produtor rural (piloto SC e RS) e entrega a ficha a quem atende.
Spec: docs/specs/2026-11-19-olivia-qualifica-o-produtor-rural.md (D1 a D10); plano, passos 1 a 7."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from backend import lead as L
from backend import migracoes
from backend import olivia as O
from backend import recepcionista as R
from backend import vaga as V
from backend.banco import conexao
from tests.avisos_meta import aviso, texto
from tests.saida_falsa import IAFalsa, SaidaFalsa

AGORA = datetime(2026, 11, 19, 13, 0, tzinfo=timezone.utc)   # 10:00 em Brasilia, quinta
DE_FORA = "5549988883333"
FOLHA = "comercial.produtor.sc"
FALA_FINAL = ("Anotei tudo! O nosso consultor Maicon está recebendo agora o resumo da nossa conversa. Segue o "
              "contato dele; se quiser dar uns 5 minutinhos, ele já vai saber do que tratamos.")


def _ligar(con, chave, valor="true"):
    con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = %s", (valor, chave))


@pytest.fixture
def piloto(cfg, tmp_path):
    """OLIVIA_FALA, a venda e o piloto ligados."""
    c = replace(cfg, responde=True, olivia_fala=True, campo_pasta=tmp_path / "campo")
    with conexao(c) as con:
        _ligar(con, O.AJUSTE_VENDA)
        _ligar(con, O.AJUSTE_QUALIFICA)
    return c


def destino(cfg, chave=FOLHA):
    with conexao(cfg) as con:
        return con.execute("""SELECT d.* FROM atendimento.menu m JOIN atendimento.destinos d ON d.id = m.destino_id
                               WHERE m.chave = %s""", (chave,)).fetchone()


def abrir_janela(cfg, numero, quando=AGORA - timedelta(hours=1)):
    """O representante escreveu ao numero da empresa ha uma hora: a janela de 24 h dele esta aberta."""
    from backend.saida import wa_id_do_whatsapp
    corpo = {"msg": {"from": wa_id_do_whatsapp(numero), "id": "wamid.rep", "type": "text",
                     "timestamp": str(int(quando.timestamp())), "text": {"body": "oi"}}}
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo, recebido_em, processado_em)
                       VALUES ('rep.1', 'mensagem', %s::jsonb, %s, %s)""", (json.dumps(corpo), quando, quando))


def passo(cfg, s, mensagem, ia, agora=AGORA, nome="João da Silva"):
    R.gravar(cfg, aviso([mensagem], numero=DE_FORA, bsuid="BR.lead.1", nome=nome))
    R.processar_pendentes(cfg, s, ia, agora=agora)
    with conexao(cfg) as con:
        erros = con.execute("SELECT erro FROM atendimento.eventos_meta WHERE erro <> ''").fetchall()
    assert not erros, erros


def ler(cfg, sql, *args):
    with conexao(cfg) as con:
        return con.execute(sql, args).fetchall()


def resumos(cfg):
    return [r["resumo"] for r in ler(cfg, "SELECT resumo FROM atendimento.enviadas ORDER BY id")]


def o_lead(cfg):
    r = ler(cfg, "SELECT * FROM atendimento.leads ORDER BY id DESC LIMIT 1")
    return r[0] if r else None


def conversa(cfg):
    return ler(cfg, "SELECT * FROM atendimento.conversas ORDER BY id DESC LIMIT 1")[0]


def ate_a_licenca(cfg, s, ia):
    """Os dois primeiros passos: o "temos" com a licenca, e o "pode" com a primeira pergunta."""
    ia.conversa = [{"texto": "Temos sim, João! Para o nosso consultor já te atender sabendo do que você "
                             "precisa, posso te fazer quatro perguntas rápidas?"}]
    passo(cfg, s, texto("w1", "sou produtor de SC, tem aveia?", numero=DE_FORA), ia)
    ia.conversa = [{"texto": "Qual semente você procura e para quê?"}]
    passo(cfg, s, texto("w2", "pode", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=1))


# ── passo 1: a migracao ─────────────────────────────────────────────────────

def test_1_a_072_nasce_desligada_com_sc_e_rs_e_a_volta_desfaz(cfg):
    with conexao(cfg) as con:
        assert O.qualifica(con) is False
        assert O._estados_do_piloto(con) == ["SC", "RS"]
        assert con.execute("SELECT count(*) AS n FROM atendimento.leads").fetchone()["n"] == 0
        con.execute((migracoes.PASTA / "072_leads_da_olivia_VOLTA.sql").read_text(encoding="utf-8"))
        assert con.execute("SELECT to_regclass('atendimento.leads') AS t").fetchone()["t"] is None
        assert con.execute("""SELECT count(*) AS n FROM atendimento.ajustes
                               WHERE chave LIKE 'olivia.qualifica%%'""").fetchone()["n"] == 0
        assert O.qualifica(con) is False   # sem a linha, o codigo le desligada
    assert migracoes.aplicar(cfg) == ["072_leads_da_olivia.sql"]   # e a ida volta inteira


def test_1_uma_ficha_por_conversa(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Temos sim!"}]
    passo(piloto, s, texto("w1", "tem aveia?", numero=DE_FORA), ia)
    cid = conversa(piloto)["id"]
    with conexao(piloto) as con:
        con.execute("INSERT INTO atendimento.leads (conversa_id) VALUES (%s)", (cid,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        with conexao(piloto) as con:
            con.execute("INSERT INTO atendimento.leads (conversa_id) VALUES (%s)", (cid,))


# ── passo 2: as ferramentas so com a chave, fora da vaga, so SC e RS ─────────

def test_2_chave_desligada_as_ferramentas_nao_aparecem(cfg):
    with conexao(cfg) as con:
        _ligar(con, O.AJUSTE_VENDA)
        nomes = [f["name"] for f in O.ferramentas(con, {"id": 0, "trabalhe": False})]
        assert "passar_contato" in nomes and "anotar_lead" not in nomes and "fechar_lead" not in nomes
        _ligar(con, O.AJUSTE_QUALIFICA)
        _ligar(con, O.AJUSTE_VENDA, "false")   # o piloto so vale com a venda
        nomes = [f["name"] for f in O.ferramentas(con, {"id": 0, "trabalhe": False})]
        assert "anotar_lead" not in nomes and O.qualifica(con) is False


def test_2_na_conversa_de_vaga_nao_aparecem(piloto):
    with conexao(piloto) as con:
        nomes = [f["name"] for f in O.ferramentas(con, {"id": 0, "trabalhe": True})]
    assert "anotar_lead" not in nomes and "fechar_lead" not in nomes


def test_2_a_lista_de_fechar_lead_e_so_sc_e_rs(piloto):
    with conexao(piloto) as con:
        f = {x["name"]: x for x in O.ferramentas(con, {"id": 0, "trabalhe": False})}
        assert f["fechar_lead"]["input_schema"]["properties"]["chave"]["enum"] == \
            ["comercial.produtor.sc", "comercial.produtor.rs"]
        # o ajuste amplia sem codigo (D1)
        _ligar(con, O.AJUSTE_ESTADOS, '["SC", "RS", "SP"]')
        f = {x["name"]: x for x in O.ferramentas(con, {"id": 0, "trabalhe": False})}
        assert "comercial.produtor.sp" in f["fechar_lead"]["input_schema"]["properties"]["chave"]["enum"]


def test_2_fechar_lead_com_chave_de_fora_do_piloto_e_recusado(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("fechar_lead", {"chave": "comercial.revenda.sc", "resumo": "x"})]},
                   {"texto": "Você é produtor ou revenda?"}]
    passo(piloto, s, texto("w1", "tem aveia?", numero=DE_FORA), ia)
    assert "não é de um estado do piloto" in ia.chamadas[-1]["mensagens"][-1]["content"][0]["content"]
    assert o_lead(piloto) is None and "contato" not in [x[0] for x in s.enviadas]


# ── passo 3: o envio da ficha ───────────────────────────────────────────────

def saida_nova():
    """Uma SaidaFalsa cujos ids nao colidem com os da conversa que montou a ficha."""
    from itertools import count
    s = SaidaFalsa()
    s._n = count(1000)
    return s


def _lead_pronto(cfg, completo=True):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Temos sim!"}]
    passo(cfg, s, texto("w1", "tem aveia?", numero=DE_FORA), ia)
    cid = conversa(cfg)["id"]
    campos = dict(nome="João da Silva", produto="aveia preta", finalidade="cobertura", tamanho="50 ha",
                  quando="abril", municipio="Xanxerê", uf="SC", resumo="Produtor de Xanxerê, aveia para cobertura.")
    if not completo:
        campos.update(tamanho="", quando="", municipio="")
    with conexao(cfg) as con:
        return con.execute("""INSERT INTO atendimento.leads (conversa_id, nome, produto, finalidade, tamanho, quando,
                                                               municipio, uf, resumo)
                              VALUES (%(c)s, %(nome)s, %(produto)s, %(finalidade)s, %(tamanho)s, %(quando)s,
                                      %(municipio)s, %(uf)s, %(resumo)s) RETURNING *""",
                           dict(campos, c=cid)).fetchone()


def test_3_na_janela_sai_texto_com_o_link(piloto):
    lead, d = _lead_pronto(piloto), destino(piloto)
    abrir_janela(piloto, d["whatsapp"])
    s = saida_nova()
    with conexao(piloto) as con:
        assert L.mandar(con, s, lead, d, DE_FORA, AGORA) is True
    tipo, para, corpo, _ = s.ultima
    assert tipo == "texto" and para == d["whatsapp"]
    assert "Lead da OlivIA" in corpo and "https://wa.me/%s" % DE_FORA in corpo
    assert "aveia preta, para cobertura" in corpo and "Xanxerê" in corpo and "incompleta" not in corpo
    x = o_lead(piloto)
    assert x["enviada_como"] == "texto" and x["enviada_em"] is not None and x["wamid"] and x["erro"] == ""
    assert L.RESUMO_ENVIADA in resumos(piloto)


def test_3_fora_da_janela_sai_o_modelo_com_uma_linha(piloto):
    lead, d = _lead_pronto(piloto, completo=False), destino(piloto)
    s = saida_nova()
    with conexao(piloto) as con:
        assert L.mandar(con, s, lead, d, DE_FORA, AGORA) is True
    m = s.modelos[-1]
    assert m["nome"] == "olivia_resumo" and m["para"] == d["whatsapp"] and len(m["corpo"]) == 1
    linha = m["corpo"][0]
    assert "\n" not in linha and "     " not in linha and len(linha) <= L.LINHA_ATE
    assert linha.startswith("Lead produtor rural SC") and "+55 49 98888-3333" in linha
    assert "FICHA INCOMPLETA" in linha
    assert o_lead(piloto)["enviada_como"] == "modelo"


def test_3_a_saida_que_falha_devolve_false_e_grava_o_erro(piloto):
    lead, d = _lead_pronto(piloto), destino(piloto)
    s = saida_nova()
    s.modelo_falha = "a Meta recusou"
    with conexao(piloto) as con:
        assert L.mandar(con, s, lead, d, DE_FORA, AGORA) is False
    x = o_lead(piloto)
    assert x["enviada_em"] is None and "a Meta recusou" in x["erro"]


def test_3_o_destino_que_e_a_propria_pessoa_nao_recebe_ficha(piloto):
    lead, d = _lead_pronto(piloto), destino(piloto)
    with conexao(piloto) as con:
        assert L.mandar(con, SaidaFalsa(), lead, d, d["whatsapp"], AGORA) is False
    assert "própria pessoa" in o_lead(piloto)["erro"]


# ── passo 4: as regras e a conversa inteira ─────────────────────────────────

def test_4_as_regras_so_entram_com_a_chave(cfg):
    with conexao(cfg) as con:
        _ligar(con, O.AJUSTE_VENDA)
        assert "QUALIFICAÇÃO DO PRODUTOR RURAL" not in O.instrucao(con)
        _ligar(con, O.AJUSTE_QUALIFICA)
        i = O.instrucao(con)
    assert "QUALIFICAÇÃO DO PRODUTOR RURAL" in i and "SC e RS" in i
    assert "posso te fazer quatro perguntas rápidas?" in i and "anotar_lead" in i and "fechar_lead" in i
    assert "única exceção à regra 26" in i and "NÃO diga que avisou" in i   # a 26 fica, com a excecao


def _quatro_respostas(piloto, s, ia, anotar=True):
    ate_a_licenca(piloto, s, ia)
    respostas = [("w3", "aveia preta para cobertura", {"produto": "aveia preta", "finalidade": "cobertura", "uf": "SC"},
                  "Qual a área ou a quantidade?"),
                 ("w4", "50 hectares", {"tamanho": "50 hectares"}, "Quando pretende plantar?"),
                 ("w5", "em abril", {"quando": "abril"}, "E qual o município?")]
    for i, (w, dito, campos, pergunta) in enumerate(respostas, start=2):
        ia.conversa = ([{"texto": "Anotado.", "ferramentas": [("anotar_lead", campos)]}] if anotar else []) + \
            [{"texto": pergunta}]
        passo(piloto, s, texto(w, dito, numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=i))


def test_4_conversa_inteira_quatro_respostas_ficha_cartao_e_fala_final(piloto):
    d = destino(piloto)
    abrir_janela(piloto, d["whatsapp"])
    s, ia = SaidaFalsa(), IAFalsa()
    _quatro_respostas(piloto, s, ia)
    antes = len(s.enviadas)
    ia.conversa = [{"ferramentas": [("anotar_lead", {"municipio": "Xanxerê"}),
                                    ("fechar_lead", {"chave": FOLHA, "resumo": "Produtor de Xanxerê, aveia preta para "
                                                                               "cobertura em 50 ha, planta em abril."})]},
                   {"texto": FALA_FINAL}]
    passo(piloto, s, texto("w6", "Xanxerê", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=5))
    x = o_lead(piloto)
    assert x["completa"] is True and x["faltou"] == [] and x["enviada_como"] == "texto" and x["uf"] == "SC"
    assert x["destino_id"] == d["id"]
    depois = s.enviadas[antes:]
    # a ordem de D5/D6: a ficha ao consultor, a fala final ao produtor, o texto do link e o cartao
    assert [(t, p) for t, p, _, _ in depois] == [("texto", d["whatsapp"]), ("texto", DE_FORA),
                                                  ("texto", DE_FORA), ("contato", DE_FORA)]
    assert depois[1][2] == FALA_FINAL
    assert "A ficha SAIU" in ia.chamadas[-1]["mensagens"][-1]["content"][1]["content"]
    assert conversa(piloto)["situacao"] == "com_link"
    # D9: nenhuma fala da qualificacao foi marcada "travou"
    assert not [r for r in resumos(piloto) if r.startswith(O.FALA_TRAVOU)]
    # e o vigia conta o lead
    with conexao(piloto) as con:
        n = O.fechar_dia(con, AGORA + timedelta(hours=11))
    assert n["leads"] == {"completas": 1, "incompletas": 0, "com_erro": 0}


def test_4_pressa_ficha_incompleta_com_o_que_faltou(piloto):
    d = destino(piloto)
    abrir_janela(piloto, d["whatsapp"])
    s, ia = SaidaFalsa(), IAFalsa()
    ate_a_licenca(piloto, s, ia)
    antes = len(s.enviadas)
    ia.conversa = [{"ferramentas": [("fechar_lead", {"chave": FOLHA, "resumo": "Quer só o contato."})]},
                   {"texto": FALA_FINAL}]
    passo(piloto, s, texto("w3", "só quero o contato", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=2))
    x = o_lead(piloto)
    assert x["completa"] is False and set(x["faltou"]) == set(L.PERGUNTAS) and x["enviada_em"] is not None
    ficha = s.enviadas[antes][2]
    assert "Ficha incompleta: faltou" in ficha and "não disse" in ficha
    assert [t for t, *_ in s.enviadas[antes:]][-1] == "contato"


# ── passo 5: as duas travas ─────────────────────────────────────────────────

def test_5a_aviso_sem_ficha_e_trocado_pela_apresentacao(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    s.modelo_falha = "a Meta recusou"   # fora da janela, e o modelo falha: a ficha NAO sai
    ate_a_licenca(piloto, s, ia)
    antes = len(s.enviadas)
    ia.conversa = [{"ferramentas": [("fechar_lead", {"chave": FOLHA, "resumo": "Quer só o contato."})]},
                   {"texto": FALA_FINAL}]   # ela diz que o consultor esta recebendo, e nao esta
    passo(piloto, s, texto("w3", "só quero o contato", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=2))
    assert "NÃO saiu" in ia.chamadas[-1]["mensagens"][-1]["content"][0]["content"]
    falas = [c for t, p, c, _ in s.enviadas[antes:] if t == "texto" and p == DE_FORA]
    assert FALA_FINAL not in falas
    assert falas[0] == "Na sua região quem atende é o nosso consultor Maicon. Segue o contato dele."
    assert O.RECUSADA_AVISO in resumos(piloto) and s.ultima[0] == "contato"
    assert o_lead(piloto)["enviada_em"] is None and o_lead(piloto)["erro"]


def test_5a_a_mesma_fala_com_a_ficha_enviada_passa(piloto):
    with conexao(piloto) as con:
        assert O.aviso_sem_ficha(con, {"id": 0, "trabalhe": False}, FALA_FINAL) is True
        assert O.aviso_sem_ficha(con, {"id": 0, "trabalhe": False}, "Segue o contato dele, é só chamar.") is False
        assert O.aviso_sem_ficha(con, {"id": 0, "trabalhe": True}, FALA_FINAL) is False   # vaga e outra regra


def test_5b_cartao_sem_fala_ganha_a_apresentacao(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"ferramentas": [("passar_contato", {"chave": "comercial.revenda.sc"})]}]
    passo(piloto, s, texto("w1", "sou revenda de SC, quero o contato", numero=DE_FORA), ia)
    tipos = [(t, c) for t, _, c, _ in s.enviadas]
    assert tipos[0] == ("texto", "Na sua região quem atende é o nosso consultor Maicon. Segue o contato dele.")
    assert [t for t, _ in tipos] == ["texto", "texto", "contato"]


def test_5b_fechar_lead_sem_fala_depois_ganha_a_apresentacao_com_o_nome(piloto):
    abrir_janela(piloto, destino(piloto)["whatsapp"])
    s, ia = SaidaFalsa(), IAFalsa()
    ate_a_licenca(piloto, s, ia)
    antes = len(s.enviadas)
    ia.conversa = [{"ferramentas": [("anotar_lead", {"nome": "João da Silva"}),
                                    ("fechar_lead", {"chave": FOLHA, "resumo": "Quer só o contato."})]}, {}]
    passo(piloto, s, texto("w3", "só quero o contato", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=2))
    para_ele = [(t, c) for t, p, c, _ in s.enviadas[antes:] if p == DE_FORA]
    assert para_ele[0] == ("texto", "João, na sua região quem atende é o nosso consultor Maicon. Segue o contato dele.")
    assert para_ele[-1][0] == "contato" and len([1 for t, _ in para_ele if t == "contato"]) == 1


def test_5b_com_fala_nao_duplica(piloto):
    s, ia = SaidaFalsa(), IAFalsa()
    ia.conversa = [{"texto": "Rissielli, na sua região quem atende é o Maicon.",
                    "ferramentas": [("passar_contato", {"chave": "comercial.revenda.sc"})]}]
    passo(piloto, s, texto("w1", "sou revenda de SC", numero=DE_FORA), ia)
    assert [c for t, _, c, _ in s.enviadas].count("Na sua região quem atende é o nosso consultor Maicon. "
                                                   "Segue o contato dele.") == 0


# ── passo 6: a qualificacao nao e conversa travada ──────────────────────────

def test_6_sem_ficha_comecada_as_mesmas_falas_tambem_nao_travam(piloto):
    """Era o controle do teste de cima (sem `anotar_lead`, a sexta fala sem toque levava a marca). Desde o
    #1784 a conversa de compra inteira anda por texto: com a venda ligada, a marca nao vem pela contagem.
    O controle com a venda desligada esta em test_olivia_venda.py (h)."""
    s, ia = SaidaFalsa(), IAFalsa()
    _quatro_respostas(piloto, s, ia, anotar=False)
    ia.conversa = [{"texto": "E o município?"}]
    passo(piloto, s, texto("w6", "sim", numero=DE_FORA), ia, agora=AGORA + timedelta(minutes=6))
    assert not [r for r in resumos(piloto) if r.startswith(O.FALA_TRAVOU)]


# ── passo 7: o entorno ──────────────────────────────────────────────────────

def test_7_o_vigia_avisa_a_ficha_que_nao_saiu(piloto):
    lead = _lead_pronto(piloto)
    with conexao(piloto) as con:
        con.execute("UPDATE atendimento.leads SET erro = 'a Meta recusou', criado_em = %s WHERE id = %s",
                    (AGORA, lead["id"]))
        n = O.fechar_dia(con, AGORA + timedelta(hours=11))
        sobre = con.execute("SELECT sobre FROM atendimento.avisos WHERE tipo = 'olivia_resumo'").fetchone()
    assert n["leads"]["com_erro"] == 1 and n["avisou"] is True
    assert "leads do produtor: 0 completos, 0 incompletos, 1 sem envio" in sobre["sobre"]


def test_7_a_ficha_sai_com_12_meses(piloto):
    lead = _lead_pronto(piloto)
    with conexao(piloto) as con:
        con.execute("UPDATE atendimento.leads SET criado_em = %s WHERE id = %s", (AGORA, lead["id"]))
        V.limpar(con, AGORA + timedelta(days=364))
        assert con.execute("SELECT count(*) AS n FROM atendimento.leads").fetchone()["n"] == 1
        V.limpar(con, AGORA + timedelta(days=366))
        assert con.execute("SELECT count(*) AS n FROM atendimento.leads").fetchone()["n"] == 0


def test_7_saude_e_o_script(piloto, capsys, monkeypatch):
    from fastapi.testclient import TestClient
    with TestClient(R.criar_app(piloto, saida=SaidaFalsa(), trabalhador=False)) as t:
        assert t.get("/saude").json()["olivia_qualifica"] == "ligada"
    import importlib.util
    from pathlib import Path
    caminho = Path(__file__).resolve().parents[1] / "scripts" / "olivia.py"
    spec = importlib.util.spec_from_file_location("script_olivia_lead", caminho)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.setattr(script.config, "carregar", lambda *a, **k: piloto)
    monkeypatch.setattr("sys.argv", ["olivia.py", "desligar-qualifica"])
    assert script.main() == 0
    with conexao(piloto) as con:
        assert O.qualifica(con) is False
        _ligar(con, O.AJUSTE_VENDA, "false")
    monkeypatch.setattr("sys.argv", ["olivia.py", "ligar-qualifica"])
    assert script.main() == 1   # com a venda desligada, recusa
    assert "RECUSADO" in capsys.readouterr().out
    with conexao(piloto) as con:
        _ligar(con, O.AJUSTE_VENDA)
    assert script.main() == 0
    with conexao(piloto) as con:
        assert O.qualifica(con) is True
        con.execute("DELETE FROM atendimento.ajustes WHERE chave = %s", (O.AJUSTE_QUALIFICA,))
    assert script.main() == 1   # sem a linha da 072, recusa
    out = capsys.readouterr().out
    assert "RECUSADO" in out and "072" in out
