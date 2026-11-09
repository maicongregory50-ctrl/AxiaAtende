"""#1285: o responsavel que muda no ERP chega as linhas de envio ja gravadas (o caso Ceres).

O que estes testes seguram, um por caso do plano:
(a) a linha `aguardando` de envio ativo muda;
(b) a linha de envio encerrado, material, convidada ha 40 dias NAO muda (e historico);
(c) a linha de direta convidada ha 90 dias muda (o link vive na mensagem);
(d) a `sem_responsavel` que ganhou responsavel volta a `aguardando`, e com recusa antes fica fora;
(e) o resumo guardado do numero antigo vira nao visto, e o de quem continua responsavel nao;
(f) `--desfazer` devolve campos e avisos, e o "antes" tem uma linha por campo mudado."""
import csv
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.banco import conexao

_spec = importlib.util.spec_from_file_location(
    "reatribuir_responsavel", Path(__file__).resolve().parent.parent / "scripts" / "reatribuir_responsavel.py")
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)

AGORA = datetime.now(timezone.utc)
CERES = ("CERES REPRESENTACOES", "5549988887777")
DONO = ("Maicon Gregory", "5549991505565")
DJ = ("Djeison", "5549999110001")
_wamid = iter(range(1, 10_000))


def envio(cfg, tipo="material", situacao="ativo", peca="Peca X"):
    with conexao(cfg) as con:
        return con.execute(
            """INSERT INTO atendimento.envios (pedido_ref, tipo, campanha, peca, modelo, capa, imagens,
                   aprovado_por, aprovado_em, situacao)
               VALUES (%s, %s, 'CAM', %s, 'pecas_da_revenda', 'capa.jpg', '[]'::jsonb, 'dono', now(), %s)
               RETURNING id""", ("pub-%d" % next(_wamid), tipo, peca, situacao)).fetchone()["id"]


def linha(cfg, envio_id, codigo, numero, resp=CERES, canal="representante", situacao="aguardando",
          convite_dias=None, pos=1):
    convite = AGORA - timedelta(days=convite_dias) if convite_dias is not None else None
    if convite and situacao == "aguardando":
        situacao = "convidado"
    with conexao(cfg) as con:
        return con.execute(
            """INSERT INTO atendimento.envio_destinatarios
                   (envio_id, erp_codigo, nome, whatsapp, posicao, responsavel_nome, responsavel_whatsapp,
                    responsavel_canal, situacao, convite_em, convite_wamid)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (envio_id, codigo, "Cliente %d" % codigo, numero, pos, resp[0], resp[1], canal, situacao, convite,
             "wamid.%d" % next(_wamid) if convite else None)).fetchone()["id"]


def ver(cfg, id_):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.envio_destinatarios WHERE id = %s", (id_,)).fetchone()


def resumo(cfg, para=CERES):
    with conexao(cfg) as con:
        return con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre, guardado_em)
                              VALUES ('lote_do_representante', %s, %s, 'Ceres|1 cliente seu|Peca X', now())
                              RETURNING id""", (para[0], para[1])).fetchone()["id"]


def aviso(cfg, id_):
    with conexao(cfg) as con:
        return con.execute("SELECT * FROM atendimento.avisos WHERE id = %s", (id_,)).fetchone()


@pytest.fixture
def csv_hoje(tmp_path):
    def escrever(linhas):
        p = tmp_path / "responsaveis.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["erp_codigo", "responsavel_nome", "responsavel_whatsapp", "responsavel_canal"])
            w.writerows(linhas)
        return script.ler(str(p))
    return escrever


def rodar(cfg, novos, antes=None):
    with conexao(cfg) as con:
        plano = script.planejar(con, novos)
        if antes:
            script.gravar(con, plano, str(antes))
    return plano


HOJE = [[101, DONO[0], DONO[1], "dono"], [102, DONO[0], DONO[1], "dono"], [103, DONO[0], DONO[1], "dono"],
        [104, DONO[0], DONO[1], "dono"], [105, DJ[0], DJ[1], "representante"], [106, "", "", ""]]


def test_a_linha_aguardando_de_envio_ativo_muda(cfg, csv_hoje, tmp_path):
    e = envio(cfg)
    i = linha(cfg, e, 101, "5549999000101")
    plano = rodar(cfg, csv_hoje(HOJE), tmp_path / "antes.csv")
    assert [o for _d, _r, o, _v in plano["linhas"]] == ["muda"]
    d = ver(cfg, i)
    assert (d["responsavel_nome"], d["responsavel_whatsapp"], d["responsavel_canal"]) == (*DONO, "dono")
    assert d["situacao"] == "aguardando"


def test_b_envio_encerrado_material_de_40_dias_fica(cfg, csv_hoje, tmp_path):
    e = envio(cfg, situacao="concluido")
    i = linha(cfg, e, 101, "5549999000101", convite_dias=40)
    plano = rodar(cfg, csv_hoje(HOJE), tmp_path / "antes.csv")
    assert plano["linhas"] == []
    assert ver(cfg, i)["responsavel_nome"] == CERES[0]


def test_b2_encerrado_mas_convidado_ha_10_dias_muda_pelo_portao(cfg, csv_hoje, tmp_path):
    e = envio(cfg, situacao="concluido")
    i = linha(cfg, e, 101, "5549999000101", convite_dias=10)
    rodar(cfg, csv_hoje(HOJE), tmp_path / "antes.csv")
    assert ver(cfg, i)["responsavel_nome"] == DONO[0]


def test_c_direta_convidada_ha_90_dias_muda(cfg, csv_hoje, tmp_path):
    e = envio(cfg, tipo="direta", situacao="concluido")
    i = linha(cfg, e, 102, "5549999000102", convite_dias=90)
    rodar(cfg, csv_hoje(HOJE), tmp_path / "antes.csv")
    assert ver(cfg, i)["responsavel_whatsapp"] == DONO[1]


def test_d_sem_responsavel_volta_a_fila_e_com_recusa_fica_fora(cfg, csv_hoje, tmp_path):
    e = envio(cfg)
    volta = linha(cfg, e, 103, "5549999000103", resp=("", ""), canal=None, situacao="sem_responsavel")
    fora = linha(cfg, e, 104, "5549999000104", resp=("", ""), canal=None, situacao="sem_responsavel", pos=2)
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, tipo, wamid)
                       VALUES ('5549999000104', 'recusa', 'wamid.recusa')""")
    plano = rodar(cfg, csv_hoje(HOJE), tmp_path / "antes.csv")
    assert sorted(o for _d, _r, o, _v in plano["linhas"]) == ["fica fora: recusou antes", "volta à fila"]
    assert ver(cfg, volta)["situacao"] == "aguardando" and ver(cfg, volta)["responsavel_nome"] == DONO[0]
    assert ver(cfg, fora)["situacao"] == "sem_responsavel" and ver(cfg, fora)["responsavel_nome"] == ""


def test_quem_esta_sem_responsavel_hoje_ou_fora_do_csv_fica_como_esta(cfg, csv_hoje, tmp_path):
    e = envio(cfg)
    sem = linha(cfg, e, 106, "5549999000106")                       # no CSV, mas sem responsavel hoje
    fora = linha(cfg, e, 999, "5549999000999", pos=2)                # fora do CSV
    rodar(cfg, csv_hoje(HOJE), tmp_path / "antes.csv")
    assert ver(cfg, sem)["responsavel_nome"] == CERES[0] and ver(cfg, fora)["responsavel_nome"] == CERES[0]


def test_e_o_resumo_guardado_do_numero_antigo_vira_nao_visto(cfg, csv_hoje, tmp_path):
    e = envio(cfg)
    linha(cfg, e, 101, "5549999000101")
    da_ceres = resumo(cfg, CERES)
    do_dj = resumo(cfg, DJ)                                          # o Djeison continua responsavel
    plano = rodar(cfg, csv_hoje(HOJE), tmp_path / "antes.csv")
    assert [a["id"] for a in plano["avisos"]] == [da_ceres]
    a = aviso(cfg, da_ceres)
    assert a["nao_visto_em"] is not None and "#1285" in a["erro"] and a["enviado_em"] is None
    assert aviso(cfg, do_dj)["nao_visto_em"] is None


def test_f_desfazer_devolve_tudo_e_o_antes_tem_uma_linha_por_campo(cfg, csv_hoje, tmp_path):
    e = envio(cfg)
    muda = linha(cfg, e, 101, "5549999000101", canal=None)           # canal nulo, de antes da 033
    volta = linha(cfg, e, 103, "5549999000103", resp=("", ""), canal=None, situacao="sem_responsavel", pos=2)
    r = resumo(cfg, CERES)
    antes = tmp_path / "antes.csv"
    rodar(cfg, csv_hoje(HOJE), antes)
    with open(antes, encoding="utf-8") as fh:
        regs = list(csv.DictReader(fh))
    assert sorted((x["tabela"], int(x["id"]), x["campo"]) for x in regs) == sorted(
        [("envio_destinatarios", muda, c) for c in ("responsavel_nome", "responsavel_whatsapp", "responsavel_canal")]
        + [("envio_destinatarios", volta, c) for c in ("responsavel_nome", "responsavel_whatsapp",
                                                      "responsavel_canal", "situacao")]
        + [("avisos", r, "nao_visto_em"), ("avisos", r, "erro")])
    assert json.loads(next(x for x in regs if int(x["id"]) == muda and x["campo"] == "responsavel_canal")
                      ["valor_antigo"]) is None

    with conexao(cfg) as con:
        script.desfazer(con, str(antes), True)
    d = ver(cfg, muda)
    assert (d["responsavel_nome"], d["responsavel_whatsapp"], d["responsavel_canal"]) == (*CERES, None)
    v = ver(cfg, volta)
    assert (v["situacao"], v["responsavel_nome"], v["responsavel_canal"]) == ("sem_responsavel", "", None)
    a = aviso(cfg, r)
    assert a["nao_visto_em"] is None and a["erro"] == ""


def test_rodar_de_novo_nao_acha_nada_e_o_antes_nao_se_sobrescreve(cfg, csv_hoje, tmp_path):
    e = envio(cfg)
    linha(cfg, e, 101, "5549999000101")
    resumo(cfg, CERES)
    antes = tmp_path / "antes.csv"
    rodar(cfg, csv_hoje(HOJE), antes)
    plano = rodar(cfg, csv_hoje(HOJE))
    assert plano["linhas"] == [] and plano["avisos"] == []
    with pytest.raises(FileExistsError):
        rodar(cfg, csv_hoje(HOJE), antes)


def test_so_o_canal_diferente_nao_conta_como_mudanca(cfg, csv_hoje, tmp_path):
    e = envio(cfg)
    linha(cfg, e, 105, "5549999000105", resp=DJ, canal=None)
    assert rodar(cfg, csv_hoje(HOJE))["linhas"] == []


def test_medir_conta_as_linhas_o_recorte_e_os_resumos_sem_gravar(cfg):
    ativo, velho = envio(cfg), envio(cfg, situacao="concluido")
    linha(cfg, ativo, 101, "5549999000101")
    linha(cfg, velho, 102, "5549999000102", convite_dias=40)
    linha(cfg, ativo, 105, "5549999000105", resp=DJ, pos=2)
    resumo(cfg, CERES)
    with conexao(cfg) as con:
        texto = script.medir(con, "CERES")
    assert "**Total:** 2 linha(s); **no recorte:** 1" in texto
    assert "pendentes** para esses números: 1." in texto and CERES[1] in texto
