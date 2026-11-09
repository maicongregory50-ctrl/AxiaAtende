"""O responsavel que muda no ERP chega aos envios ja gravados (#1285, o caso Ceres).

Dono, 09/11/2026: a Ceres saiu, o cadastro do ERP ja aponta os clientes dela a ele, e "temos que
ajustar o atendimento". O responsavel e gravado em cada linha de `envio_destinatarios` quando o
pedido nasce, e e DA LINHA que leem o botao "Falar com meu atendimento", a copia, o resumo do lote,
o aviso de recusa e a frase do portao da carteira ("Quem cuida de voce e ..."). Este script recebe o
CSV dos responsaveis de hoje, que nasce no marketing (`C:\\AxiaMarketing\\scripts\\responsaveis_de_hoje.py`,
a regra da casa fica la), e regrava as linhas que ainda decidem alguma coisa:

  (a) envio nao encerrado (`concluido` e o encerrado; `suspenso` volta com --religar), qualquer
      situacao da linha; ou
  (b) convite nos ultimos 30 dias (`Envio.PORTAO_DIAS`, o portao da carteira); ou
  (c) envio `direta` com convite, de qualquer data (o link vive na mensagem).

Muda a linha cujo NOME ou WHATSAPP difere do CSV (o canal vai junto, mas sozinho nao conta: linha de
antes da 033 tem canal nulo). Cadastro fora do CSV, ou sem responsavel hoje, FICA COMO ESTA.
A linha `sem_responsavel` que ganhou responsavel passa pela regra do #1197 (recusou, ja recebeu, nao
e WhatsApp) e volta a `aguardando`, ou fica fora com o motivo.

Os resumos de lote guardados (`lote_do_representante`, nao enviados e nao vencidos) para o numero
antigo -- o de quem deixou de ser responsavel de qualquer cadastro do CSV -- viram NAO VISTOS: nao
saem mais e nao somem (`nao_visto_em`, `erro` com o motivo).

Sem `--gravar`, SO MOSTRA. Com `--gravar`, exige `--antes <csv>` (arquivo novo): ali vai cada campo
mudado com o valor antigo ANTES de qualquer UPDATE, e e por ele que se desfaz. Linhas e avisos vao
numa transacao so: ou tudo, ou nada. O que ja bate com o CSV nao aparece de novo (idempotente).

Em producao, janela elevada (`--medir CERES` e so leitura: a medicao do passo 1 do plano):

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\reatribuir_responsavel.py C:\\Temp\\responsaveis.csv
    ... o mesmo com --antes C:\\AxiaAtende\\docs\\medicoes\\AAAA-MM-DD-antes.csv --gravar
    ... para desfazer: --desfazer C:\\AxiaAtende\\docs\\medicoes\\AAAA-MM-DD-antes.csv --gravar
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import CELULAR, RESUMO, Envio, _ja_recebeu, _nao_e_whatsapp, _ultimo_consentimento  # noqa: E402

CANAIS = ("representante", "corretor", "dono", "flutuante")
CAMPOS = ("responsavel_nome", "responsavel_whatsapp", "responsavel_canal", "situacao")
CAMPOS_AVISO = ("nao_visto_em", "erro")
MOTIVO = "responsável saiu do atendimento (#1285)"
ANTES = ["tabela", "id", "campo", "valor_antigo"]


def ler(caminho: str) -> dict:
    """{erp_codigo: linha} -- so quem tem responsavel valido hoje; o resto fica como esta."""
    with open(caminho, encoding="utf-8-sig") as fh:
        return {int(r["erp_codigo"]): r for r in csv.DictReader(fh)
                if CELULAR.match(r["responsavel_whatsapp"] or "") and r["responsavel_nome"]
                and r["responsavel_canal"] in CANAIS}


def _no_recorte(con, agora):
    return con.execute(
        """SELECT d.*, e.peca, e.tipo AS envio_tipo, e.situacao AS envio_situacao
             FROM atendimento.envio_destinatarios d
             JOIN atendimento.envios e ON e.id = d.envio_id
            WHERE e.situacao <> 'concluido'
               OR d.convite_em > %s
               OR (e.tipo = 'direta' AND d.convite_em IS NOT NULL)
            ORDER BY d.envio_id, d.posicao, d.id""",
        (agora - timedelta(days=Envio.PORTAO_DIAS),)).fetchall()


def planejar(con, novos: dict, agora: datetime | None = None) -> dict:
    """O que mudaria: {"linhas": [(d, novo, o que acontece, {campo: valor novo})], "avisos": [aviso]}."""
    agora = agora or datetime.now(timezone.utc)
    linhas = []
    for d in _no_recorte(con, agora):
        r = novos.get(d["erp_codigo"])
        if not r or (d["responsavel_nome"], d["responsavel_whatsapp"]) == (r["responsavel_nome"],
                                                                         r["responsavel_whatsapp"]):
            continue
        valores = {"responsavel_nome": r["responsavel_nome"], "responsavel_whatsapp": r["responsavel_whatsapp"],
                   "responsavel_canal": r["responsavel_canal"]}
        if d["situacao"] == "sem_responsavel":
            # a regra do #1197 (`religar_sem_responsavel.py`), pelas mesmas funcoes do envio
            if _ultimo_consentimento(con, d["whatsapp"]) == "recusa":
                linhas.append((d, r, "fica fora: recusou antes", {}))
                continue
            if _ja_recebeu(con, d["whatsapp"], d["peca"]):
                linhas.append((d, r, "fica fora: já recebeu esta peça", {}))
                continue
            if _nao_e_whatsapp(con, d["whatsapp"]):
                linhas.append((d, r, "fica fora: o número não é WhatsApp", {}))
                continue
            valores["situacao"] = "aguardando"
            linhas.append((d, r, "volta à fila", valores))
        else:
            linhas.append((d, r, "muda", valores))
    hoje = {r["responsavel_whatsapp"] for r in novos.values()}
    antigos = {d["responsavel_whatsapp"] for d, _r, _o, v in linhas
               if v and d["responsavel_whatsapp"] and d["responsavel_whatsapp"] not in hoje}
    avisos = con.execute(
        """SELECT * FROM atendimento.avisos
            WHERE tipo = %s AND enviado_em IS NULL AND nao_visto_em IS NULL AND para_whatsapp = ANY(%s)
            ORDER BY id""", (RESUMO, sorted(antigos))).fetchall() if antigos else []
    return {"linhas": linhas, "avisos": avisos}


def _valor(v):
    return v.isoformat() if isinstance(v, datetime) else v


def gravar(con, plano: dict, antes: str) -> None:
    """Escreve o "antes" (um registro por campo mudado) e SO DEPOIS faz os UPDATE, numa transacao."""
    registros = []
    for d, _r, _o, valores in plano["linhas"]:
        registros += [("envio_destinatarios", d["id"], c, d[c]) for c, v in valores.items() if d[c] != v]
    for a in plano["avisos"]:
        registros += [("avisos", a["id"], c, a[c]) for c in CAMPOS_AVISO]
    with open(antes, "x", encoding="utf-8", newline="") as fh:   # "x": nunca sobrescreve um "antes"
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(ANTES)
        for tabela, id_, campo, valor in registros:
            w.writerow([tabela, id_, campo, json.dumps(_valor(valor), ensure_ascii=False)])
    for d, _r, _o, valores in plano["linhas"]:
        if valores:
            con.execute("UPDATE atendimento.envio_destinatarios SET %s WHERE id = %%s"
                        % ", ".join("%s = %%s" % c for c in valores), (*valores.values(), d["id"]))
    for a in plano["avisos"]:
        con.execute("UPDATE atendimento.avisos SET nao_visto_em = now(), erro = %s WHERE id = %s", (MOTIVO, a["id"]))


def desfazer(con, antes: str, gravar_: bool) -> list:
    """Devolve cada campo pelo id, como estava no "antes". [(tabela, id, campo, valor)]."""
    with open(antes, encoding="utf-8") as fh:
        registros = [(r["tabela"], int(r["id"]), r["campo"], json.loads(r["valor_antigo"]))
                     for r in csv.DictReader(fh)]
    permitidos = {"envio_destinatarios": CAMPOS, "avisos": CAMPOS_AVISO}
    for tabela, id_, campo, valor in registros:
        if campo not in permitidos.get(tabela, ()):
            raise SystemExit("campo fora do que este script grava: %s.%s" % (tabela, campo))
        if gravar_:
            con.execute("UPDATE atendimento.%s SET %s = %%s WHERE id = %%s" % (tabela, campo), (valor, id_))
    return registros


def medir(con, quem: str, agora: datetime | None = None) -> str:
    """A medicao do passo 1 do plano, so leitura, em Markdown: as linhas cujo responsavel e `quem`
    (parte do nome, ou o WhatsApp), por envio e situacao; quantas no recorte; resumos pendentes."""
    agora = agora or datetime.now(timezone.utc)
    corte = agora - timedelta(days=Envio.PORTAO_DIAS)
    filtro = "(d.responsavel_nome ILIKE %s OR d.responsavel_whatsapp = %s)"
    args = ("%%%s%%" % quem, quem)
    por = con.execute(
        """SELECT d.envio_id, e.tipo, e.situacao AS envio, d.situacao, count(*) AS n,
                  count(*) FILTER (WHERE e.situacao <> 'concluido' OR d.convite_em > %s
                                   OR (e.tipo = 'direta' AND d.convite_em IS NOT NULL)) AS no_recorte
             FROM atendimento.envio_destinatarios d JOIN atendimento.envios e ON e.id = d.envio_id
            WHERE """ + filtro + """
            GROUP BY 1, 2, 3, 4 ORDER BY 1, 4""", (corte, *args)).fetchall()
    numeros = [r["responsavel_whatsapp"] for r in con.execute(
        "SELECT DISTINCT d.responsavel_whatsapp FROM atendimento.envio_destinatarios d WHERE " + filtro,
        args).fetchall()]
    avisos = con.execute(
        """SELECT count(*) AS n FROM atendimento.avisos
            WHERE tipo = %s AND enviado_em IS NULL AND nao_visto_em IS NULL AND para_whatsapp = ANY(%s)""",
        (RESUMO, numeros)).fetchone()["n"]
    out = ["# Medição antes (#1285): responsável \"%s\" — %s" % (quem, agora.strftime("%d/%m/%Y %H:%M UTC")), "",
           "Números gravados para esse responsável: %s" % (", ".join(numeros) or "nenhum"), "",
           "| envio | tipo | situação do envio | situação da linha | linhas | no recorte |",
           "|---|---|---|---|---|---|"]
    out += ["| %s | %s | %s | %s | %s | %s |" % (r["envio_id"], r["tipo"], r["envio"], r["situacao"], r["n"],
                                              r["no_recorte"]) for r in por]
    out += ["", "**Total:** %d linha(s); **no recorte:** %d (é o que o ensaio deve mostrar como muda/volta/fica fora)."
            % (sum(r["n"] for r in por), sum(r["no_recorte"] for r in por)),
            "**Resumos de lote pendentes** para esses números: %d." % avisos, ""]
    return "\n".join(out)


def _mostrar(plano: dict) -> None:
    mudam = [x for x in plano["linhas"] if x[3]]
    print("No recorte: %d linha(s) com responsável diferente do ERP de hoje; %d mudam"
          % (len(plano["linhas"]), len(mudam)))
    for d, r, o, _v in plano["linhas"]:
        print("  envio %s  %3s  %-40s ERP %-6s %-15s %s -> %s  [%s]"
              % (d["envio_id"], d["posicao"], (d["nome"] or "")[:40], d["erp_codigo"], d["situacao"],
                 d["responsavel_nome"] or "(ninguém)", r["responsavel_nome"], o))
    if plano["avisos"]:
        print("%d resumo(s) guardado(s) do número antigo não saem mais (ficam como não vistos):"
              % len(plano["avisos"]))
        for a in plano["avisos"]:
            print("  aviso %s  para %s  criado em %s  %s" % (a["id"], a["para_nome"], a["criado_em"], a["sobre"]))
    else:
        print("Nenhum resumo guardado do número antigo.")


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("csv", nargs="?", help="o CSV dos responsáveis de hoje (do marketing)")
    a.add_argument("--antes", help="onde gravar os valores antigos (arquivo novo); obrigatório com --gravar")
    a.add_argument("--desfazer", metavar="ANTES_CSV")
    a.add_argument("--medir", metavar="NOME_OU_WHATSAPP", help="só leitura: as linhas desse responsável hoje")
    a.add_argument("--gravar", action="store_true")
    args = a.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = config.carregar()
    if args.medir:
        with conexao(cfg) as con:
            print(medir(con, args.medir))
        return 0
    if args.desfazer:
        with conexao(cfg) as con:
            regs = desfazer(con, args.desfazer, args.gravar)
        print("%d campo(s) %s." % (len(regs), "devolvidos" if args.gravar else "seriam devolvidos"))
        if not args.gravar:
            print("Nada foi gravado. Para desfazer: o mesmo comando com --gravar")
        return 0
    if not args.csv:
        a.print_help()
        return 2
    if args.gravar and not args.antes:
        print("--gravar exige --antes <csv>: é por ele que se desfaz.")
        return 2
    if args.antes and Path(args.antes).exists():
        print("%s já existe: o \"antes\" não se sobrescreve. Use outro nome." % args.antes)
        return 2
    novos = ler(args.csv)
    with conexao(cfg) as con:
        plano = planejar(con, novos)
        _mostrar(plano)
        if args.gravar:
            gravar(con, plano, args.antes)
    print("GRAVADO. Para desfazer: --desfazer %s --gravar" % args.antes if args.gravar
          else "Nada foi gravado. Para gravar: o mesmo comando com --antes <csv> --gravar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
