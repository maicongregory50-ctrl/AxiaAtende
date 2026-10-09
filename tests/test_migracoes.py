"""C1 do plano #950: o banco nasce, a semente e o menu de hoje da OlivIA, e o consentimento nao
se apaga."""
import psycopg
import pytest

from backend import migracoes
from backend.banco import conexao


def test_aplicar_de_novo_nao_muda_nada(cfg):
    assert migracoes.aplicar(cfg) == []


def test_mudanca_aplicada_alterada_recusa_subir(cfg, tmp_path, monkeypatch):
    pasta = tmp_path / "migracoes"
    pasta.mkdir()
    for p in migracoes.listar():
        (pasta / p.name).write_bytes(p.read_bytes())
    (pasta / "002_menu_da_olivia.sql").write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr(migracoes, "PASTA", pasta)
    with pytest.raises(migracoes.MudancaAlterada):
        migracoes.aplicar(cfg)


def test_menu_principal_e_o_de_hoje(cfg):
    with conexao(cfg) as con:
        raiz = con.execute("SELECT id FROM atendimento.menu WHERE chave = 'raiz'").fetchone()["id"]
        filhos = [r["rotulo"] for r in con.execute(
            "SELECT rotulo FROM atendimento.menu WHERE pai_id = %s ORDER BY ordem", (raiz,))]
    assert filhos == ["🛒 Comercial", "🚚 Fretes", "🧾 Financeiro", "📦 Fornecedores",
                      "🤝 Trabalhe conosco", "🏆 Qualidade", "🔚 Encerrar"]


@pytest.mark.parametrize("chave, quem", [
    ("comercial.corretor", "Maicon Gregory"),
    ("comercial.produtor.sc", "Maicon Gregory"),
    ("comercial.revenda.rs", "Maicon Gregory"),
    ("comercial.produtor.outro", "Maicon Gregory"),
    ("comercial.produtor.sp", "Djeison de Oliveira"),
    ("comercial.revenda.pr.ponta_grossa", "Djeison de Oliveira"),
    ("comercial.produtor.pr.cascavel", "Willian Souza"),
    ("fretes", "Benedito"),
    ("fornecedores.ainda", "Benedito"),
    ("financeiro.boleto", "Fran"),
    ("trabalhe", "Fran"),
    ("qualidade", "Alisson"),
])
def test_cada_caminho_termina_em_quem_atende(cfg, chave, quem):
    with conexao(cfg) as con:
        r = con.execute("""SELECT d.nome FROM atendimento.menu m JOIN atendimento.destinos d
                            ON d.id = m.destino_id WHERE m.chave = %s""", (chave,)).fetchone()
    assert r and r["nome"] == quem


def test_toda_opcao_cabe_no_botao_e_todo_menu_tem_filho(cfg):
    with conexao(cfg) as con:
        longos = con.execute("SELECT chave FROM atendimento.menu WHERE char_length(rotulo) > 20").fetchall()
        vazios = con.execute("""SELECT m.chave FROM atendimento.menu m WHERE m.acao = 'menu'
                                 AND NOT EXISTS (SELECT 1 FROM atendimento.menu f WHERE f.pai_id = m.id)""").fetchall()
        sem_pergunta = con.execute(
            "SELECT chave FROM atendimento.menu WHERE acao = 'menu' AND btrim(pergunta) = ''").fetchall()
    assert longos == [] and vazios == [] and sem_pergunta == []


def test_consentimento_nao_se_altera_nem_se_apaga(cfg):
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, tipo, wamid)
                       VALUES ('5549999990000', 'recusa', 'wamid.X')""")
    for sql in ("UPDATE atendimento.consentimentos SET tipo = 'aceite'",
                "DELETE FROM atendimento.consentimentos",
                "TRUNCATE atendimento.consentimentos"):
        with pytest.raises(psycopg.errors.RaiseException):
            with conexao(cfg) as con:
                con.execute(sql)
    with conexao(cfg) as con:
        assert con.execute("SELECT count(*) AS n FROM atendimento.consentimentos").fetchone()["n"] == 1


def test_aviso_repetido_da_meta_nao_entra_duas_vezes(cfg):
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo)
                       VALUES ('wamid.A', 'mensagem', '{}')""")
    with pytest.raises(psycopg.errors.UniqueViolation):
        with conexao(cfg) as con:
            con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, corpo)
                           VALUES ('wamid.A', 'mensagem', '{}')""")
