"""#981: o leitor so-leitura da sessao. No banco de teste (sem pgpass nem papel: `--dsn`), monta uma
conversa com texto, botao e foto, o que a OlivIA mandou e o canal de campo, e confere a ordem, o que
aparece, o que nao aparece e o registro da leitura."""
import json
from datetime import date, datetime, timedelta, timezone

from backend import agenda, campo, recepcionista as R
from backend.banco import conexao
from scripts import ler_conversa as L
from tests.avisos_meta import aviso, texto, toque
from tests.test_campo import EQUIPE, LINHAS, foto

AGORA = datetime(2026, 10, 12, 13, 0, tzinfo=timezone.utc)


def _montar(cfg):
    from dataclasses import replace
    c = replace(cfg, responde=True, campo_pasta=cfg.logs / "campo", erp_segredo="x")
    agenda.atualizar(c, buscar=lambda x: LINHAS, agora=AGORA)
    with conexao(c) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'campo.ligado'")
    R.gravar(c, aviso([texto("wamid.t0", "Colheita do centeio no Jair", numero=EQUIPE)], numero=EQUIPE, bsuid="BR.equipe"))
    R.gravar(c, aviso([foto("wamid.f1")], numero=EQUIPE, bsuid="BR.equipe"))
    R.gravar(c, aviso([toque("wamid.t1", "campo:hoje:sim", "Sim", numero=EQUIPE)], numero=EQUIPE, bsuid="BR.equipe"))
    with conexao(c) as con:
        con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo, status, enviada_em)
                       VALUES ('wamid.s1', %s, 'texto', 'Recebi.', 'lida', now() - interval '1 minute'),
                              ('wamid.s2', %s, 'botoes', 'É de hoje?', 'entregue', now())""", (EQUIPE, EQUIPE))
        con.execute("""INSERT INTO atendimento.material_de_campo
                       (bsuid, wa_id, erp_codigo, erp_papel, erp_nome, wamid, tipo, mime, arquivo, legenda, recebido_em,
                        grupo_id, perguntas_feitas, classe_bastidor, classe_produto, data_dita, fechado_em, atv, pergunta_n)
                       VALUES ('BR.equipe', %s, 12, 'equipe', 'Maicon Gregory', 'wamid.f1', 'foto', 'image/jpeg', 'x.jpg',
                               'Colheita do centeio no Jair', now(), 0, '{data}', 'colheita', 'CENTEIO IPR 89', %s, now(),
                               'ATV-0700', 0)""", (EQUIPE, date(2026, 10, 12)))
        con.execute("UPDATE atendimento.material_de_campo SET grupo_id = id")
        con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash, ativo) VALUES ('x', 'X', 'segredo-hash', true)"
                    " ON CONFLICT DO NOTHING")
    return c


def test_a_conversa_sai_em_ordem_com_o_que_chegou_o_que_saiu_e_o_campo(cfg, capsys, tmp_path):
    c = _montar(cfg)
    log = tmp_path / "leituras.jsonl"
    assert L.main(["--numero", EQUIPE, "--dsn", c.dsn(), "--log", str(log)]) == 0
    saida = capsys.readouterr().out
    linhas = saida.splitlines()
    assert linhas[0].startswith("Conversa de %s / BR.equipe" % EQUIPE)
    corpo = "\n".join(linhas[1:])
    assert "→ Colheita do centeio no Jair" in corpo
    assert "→ [foto id=midia-wamid.f1]" in corpo
    assert "→ [botão] Sim (campo:hoje:sim)" in corpo
    assert "← [texto, lida] Recebi." in corpo and "← [botoes, entregue] É de hoje?" in corpo
    assert "[campo] foto" in corpo and "classe: Colheita, CENTEIO IPR 89" in corpo and "fechado, ATV-0700" in corpo
    assert "segredo-hash" not in saida and "casa" not in corpo   # nada de casa, nunca
    registro = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert len(registro) == 1 and registro[0]["o_que"] == ["--numero", EQUIPE] and registro[0]["linhas"] == len(linhas)
    assert registro[0]["quem"]


def test_o_campo_da_semana_e_as_ultimas_conversas(cfg, capsys, tmp_path):
    c = _montar(cfg)
    log = tmp_path / "l.jsonl"
    assert L.main(["--campo", "--dias", "3", "--dsn", c.dsn(), "--log", str(log)]) == 0
    saida = capsys.readouterr().out
    assert saida.startswith("Canal de campo, 3 dias") and "Maicon Gregory" in saida
    assert "classe: Colheita, CENTEIO IPR 89" in saida and "fechado, no catálogo: ATV-0700" in saida
    assert L.main(["--ultimas", "5", "--dsn", c.dsn(), "--log", str(log)]) == 0
    saida = capsys.readouterr().out
    assert saida.startswith("Últimas 5 conversas") and EQUIPE in saida and "Maicon Gregory (equipe/representante, cadastro 12)" in saida
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2


def test_numero_que_nunca_escreveu_e_janela_vazia(cfg, capsys, tmp_path):
    c = _montar(cfg)
    assert L.main(["--numero", "5500000000000", "--dsn", c.dsn(), "--log", str(tmp_path / "l")]) == 0
    assert "número não reconhecido" in capsys.readouterr().out
    assert L.main(["--numero", EQUIPE, "--desde", "2030-01-01", "--dsn", c.dsn(), "--log", str(tmp_path / "l")]) == 0
    assert "nenhuma mensagem no período" in capsys.readouterr().out


def test_sem_pgpass_sai_2_e_diz_o_que_rodar(tmp_path, capsys):
    assert L.main(["--ultimas", "--pgpass", str(tmp_path / "nao-existe"), "--log", str(tmp_path / "l")]) == 2
    assert "criar_leitura.ps1" in capsys.readouterr().err
    assert not (tmp_path / "l").exists()   # sem leitura, sem registro


def test_descrever_entrada():
    assert L.descrever_entrada({"msg": {"type": "text", "text": {"body": "oi"}}}) == "oi"
    assert L.descrever_entrada({"msg": {"type": "audio", "audio": {"id": "a1"}}}) == "[áudio id=a1]"
    assert L.descrever_entrada({"msg": {"type": "reaction", "reaction": {"emoji": "👍"}}}) == "[reação 👍]"
    assert L.descrever_entrada({"msg": {"type": "interactive", "interactive": {"list_reply": {"id": "x:1", "title": "Um"}}}}) == "[lista] Um (x:1)"
    assert L.descrever_entrada({}) == "[?]"


def test_a_candidatura_aparece_sem_o_conteudo_do_pdf(cfg, capsys, tmp_path):
    """#1098: a leitura mostra que o curriculo chegou, a triagem e a Fran; o PDF, nunca."""
    from dataclasses import replace
    from tests.test_vaga import CANDIDATO, do_anuncio, doc
    from tests.saida_falsa import SaidaFalsa
    c = replace(cfg, responde=True)
    s = SaidaFalsa()
    R.gravar(c, aviso([do_anuncio("w1")], numero=CANDIDATO, bsuid="BR.cand.1"))
    R.gravar(c, aviso([doc("w2")], numero=CANDIDATO, bsuid="BR.cand.1"))
    R.processar_pendentes(c, s, None, agora=AGORA)
    assert L.main(["--numero", CANDIDATO, "--dsn", c.dsn(), "--log", str(tmp_path / "l.jsonl")]) == 0
    saida = capsys.readouterr().out
    assert "[vaga] currículo #1 'Curriculo - Gabriel.pdf'" in saida and "na fila" in saida
    assert "MIDIA:" not in saida


def test_a_mensagem_atrasada_mostra_quando_foi_mandada(cfg, capsys, tmp_path):
    """#1099: a frase das 08:55 de 22/10 chegou as 09:39; a leitura diz as duas horas."""
    from dataclasses import replace
    c = replace(cfg, responde=True)
    m = texto("wamid.atraso", "Qualidade, amostrando Nabo", numero=EQUIPE)
    m["timestamp"] = str(int((AGORA - timedelta(minutes=44)).timestamp()))
    R.gravar(c, aviso([m], numero=EQUIPE, bsuid="BR.equipe"))
    assert L.main(["--numero", EQUIPE, "--dsn", c.dsn(), "--log", str(tmp_path / "l.jsonl")]) == 0
    assert "Qualidade, amostrando Nabo (mandada " in capsys.readouterr().out


def test_1205_o_texto_guardado_aparece_e_o_antigo_fica_em_resumo(cfg, capsys, tmp_path):
    """A COPERMAP, 28/10: o convite foi ao numero COM o nono digito e a saudacao veio SEM ele; os dois
    estao na mesma conversa. O envio com texto guardado mostra o texto; o de antes, so o resumo."""
    from backend.leitura import itens
    cliente = "554988116066"
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo, status, enviada_em) VALUES
                         ('wamid.c1', '5549988116066', 'modelo', 'direta informativo', 'lida', now() - interval '2 hours'),
                         ('wamid.c2', %s, 'lista', 'menu principal', 'lida', now() - interval '1 hour'),
                         ('wamid.c3', %s, 'texto', 'antigo', 'entregue', now() - interval '3 hours')""", (cliente, cliente))
        con.execute("""INSERT INTO atendimento.enviadas_texto (wamid, tipo, texto, opcoes, modelo, variaveis) VALUES
                         ('wamid.c1', 'modelo', '', NULL, 'informativo_curto', ARRAY['Alex']),
                         ('wamid.c2', 'lista', 'Como podemos ajudar?',
                          '{"botao": "Ver opções", "linhas": [{"titulo": "Fretes", "descricao": ""}]}'::jsonb, NULL, NULL)""")
    R.gravar(cfg, aviso([texto("wamid.e1", "Copermap Compras Como posso lhe ajudar?", numero=cliente)],
                        numero=cliente, bsuid="BR.copermap"))
    with conexao(cfg) as con:
        _, _, lista = itens(con, cliente)
    nos = [(i["texto"], i["opcoes"], i["resumo"]) for i in lista if i["lado"] == "nos"]
    assert nos == [("antigo", [], True),
                   ("Olá, Alex! Informativo da Sementes Renascer.", [], False),
                   ("Como podemos ajudar?", ["Fretes"], False)]
    assert [i["texto"] for i in lista if i["lado"] == "cliente"] == ["Copermap Compras Como posso lhe ajudar?"]
    assert L.main(["--numero", cliente, "--dsn", cfg.dsn(), "--log", str(tmp_path / "l.jsonl")]) == 0
    saida = capsys.readouterr().out
    assert "← [lista, lida] menu principal | 'Como podemos ajudar?' ['Fretes']" in saida
    assert "← [texto, entregue] antigo\n" in saida
