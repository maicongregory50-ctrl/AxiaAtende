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
