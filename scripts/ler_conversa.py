"""LE, SO LEITURA, o que aconteceu no WhatsApp da Renascer: a conversa de um numero, o canal de campo
da semana, as ultimas conversas. #981 (dono, 13/10/2026: "a sessao precisa ter um acesso de leitura").

Na sessao, sem elevacao:

    python scripts\\ler_conversa.py --numero 5549999990000 [--dias 2 | --desde 2026-10-12]
    python scripts\\ler_conversa.py --bsuid BR.xxx
    python scripts\\ler_conversa.py --campo [--dias 7]
    python scripts\\ler_conversa.py --ultimas 20

Entra no banco de producao (127.0.0.1:5436, axiaatende) como o papel `axiaatende_ro`, que so tem
SELECT em `atendimento` e nasce em transacao somente leitura: quem recusa escrever e o Postgres. A
senha vem de C:\\AxiaAtende\\.pgpass_leitura (criado por servicos\\criar_leitura.ps1, elevado), pelo
PGPASSFILE; este script NUNCA le .env.secrets. Sem o arquivo, sai 2 e diz o que rodar.

Cada chamada acrescenta uma linha a C:\\Logs\\AxiaAtende\\leituras.jsonl (quando, quem, o que, quantas
linhas): e o registro das leituras que o dono pediu. O Postgres tambem anota (log_statement do papel).

O que NAO mostra: senha, token, hash, nada de `casa`; nao baixa midia (diz que houve, com o id); nao
transcreve audio; nao manda mensagem a ninguem.
"""
import argparse
import getpass
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from backend import agenda  # noqa: E402 -- o reconhecimento do numero, o mesmo do atendimento
# #1205: a montagem da conversa mora no backend, e a janela da Recepcao usa a mesma
from backend.leitura import BASTIDORES, FASES, FUSO, bsuids_de, descrever_entrada, itens  # noqa: E402,F401
from backend.leitura import hora as _hora  # noqa: E402
PGPASS = RAIZ / ".pgpass_leitura"
LOG = Path(r"C:\Logs\AxiaAtende\leituras.jsonl")
DSN = "host=127.0.0.1 port=5436 dbname=axiaatende user=axiaatende_ro"


class SemAcesso(Exception):
    pass


def conectar(dsn: str | None = None, pgpass: Path | None = None):
    """A conexao so-leitura. `dsn` e so para teste (o banco de teste nao tem pgpass nem papel)."""
    if dsn:
        con = psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5)
    else:
        arquivo = Path(pgpass or PGPASS)
        if not arquivo.is_file():
            raise SemAcesso("nao achei %s: rode servicos\\criar_leitura.ps1 numa janela elevada" % arquivo)
        os.environ["PGPASSFILE"] = str(arquivo)
        try:
            con = psycopg.connect(DSN, row_factory=dict_row, connect_timeout=5)
        except psycopg.OperationalError as e:
            raise SemAcesso("o banco recusou o papel de leitura (%s): rode servicos\\criar_leitura.ps1 de novo" % str(e).strip()) from None
    con.read_only = True
    return con


def conversa(con, wa_id: str | None = None, bsuid: str | None = None, desde: datetime | None = None) -> list[str]:
    """A conversa de um numero (ou bsuid), em ordem de tempo: o que chegou, o que saiu, o atendimento
    e o canal de campo. Devolve as linhas prontas para imprimir (a montagem e `backend.leitura.itens`)."""
    wa_id, bsuids, lista = itens(con, wa_id, bsuid, desde)
    cabeca = "Conversa de %s%s%s" % (wa_id or "?", (" / " + ", ".join(bsuids)) if bsuids else "",
                                     "" if not lista else " (%d linhas)" % len(lista))
    if not lista:
        return [cabeca, "  nenhuma mensagem no período" if (wa_id and bsuids_de(con, wa_id) or bsuid) else "  número não reconhecido: nunca escreveu"]
    return [cabeca] + ["%s %s" % (_hora(i["quando"]), i["linha"]) for i in lista]


def campo(con, dias: int = 7) -> list[str]:
    """O canal de campo da semana: cada grupo, quem, as perguntas, a classe, o fechamento, o ATV."""
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    linhas = ["Canal de campo, %d dias" % dias]
    grupos = con.execute("""SELECT grupo_id, min(recebido_em) AS inicio, count(*) AS n, max(erp_nome) AS nome,
                                   max(wa_id) AS wa_id, max(legenda) AS legenda,
                                   max(classe_bastidor) AS b, max(classe_produto) AS p, max(classe_fase) AS f,
                                   max(data_dita) AS d, bool_or(data_presumida) AS presumida,
                                   bool_or(fechado_em IS NOT NULL) AS fechado, bool_or(desistiu_em IS NOT NULL) AS desistiu,
                                   max(pergunta_n) AS perguntas, string_agg(DISTINCT atv, ', ') AS atvs,
                                   bool_or(pergunta_pendente IS NOT NULL) AS pendente
                              FROM atendimento.material_de_campo WHERE recebido_em >= %s
                             GROUP BY grupo_id ORDER BY inicio""", (desde,)).fetchall()
    if not grupos:
        return linhas + ["  nada chegou pelo canal no período"]
    for g in grupos:
        classe = ", ".join(x for x in [BASTIDORES.get(g["b"] or "", g["b"]), g["p"], FASES.get(g["f"] or "", g["f"])] if x)
        estado = "desistiu" if g["desistiu"] else ("fechado" if g["fechado"] else ("pergunta aberta" if g["pendente"] else "aberto"))
        linhas.append("%s %s (%s): %d %s; legenda %r; %d pergunta(s); classe: %s; data %s%s; %s%s" % (
            _hora(g["inicio"]), g["nome"] or "?", g["wa_id"], g["n"], "foto" if g["n"] == 1 else "fotos/vídeos",
            g["legenda"] or "", g["perguntas"] or 0, classe or "a classificar", g["d"] or "-",
            " (presumida)" if g["presumida"] else "", estado, (", no catálogo: %s" % g["atvs"]) if g["atvs"] else ""))
    return linhas


def ultimas(con, n: int = 20) -> list[str]:
    """Uma linha por numero que escreveu, do mais recente: para achar quem procurar."""
    linhas = ["Últimas %d conversas" % n]
    for r in con.execute("""SELECT corpo->'msg'->>'from' AS wa_id, max(recebido_em) AS ultima, count(*) AS n,
                                   max(corpo->'contacts'->0->'profile'->>'name') AS nome
                              FROM atendimento.eventos_meta WHERE tipo = 'mensagem'
                             GROUP BY 1 ORDER BY ultima DESC LIMIT %s""", (n,)).fetchall():
        # o mesmo reconhecimento do atendimento (a Meta manda o numero sem o nono digito; a agenda o tem)
        q = agenda.reconhecer(con, r["wa_id"]) or {}
        quem = ("%s (%s, cadastro %s)" % (q.get("erp_nome") or "?", "/".join(q.get("erp_papeis") or []), q.get("erp_codigo"))
                if q.get("erp_codigo") else (r["nome"] or "sem cadastro"))
        linhas.append("%s %s  %s  %d mensagem(ns)" % (_hora(r["ultima"]), r["wa_id"], quem, r["n"]))
    return linhas


def registrar(args: list[str], linhas: int, log: Path = LOG) -> None:
    """A linha do registro das leituras. Um escritor por arquivo: so este script escreve aqui."""
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "quem": getpass.getuser(), "sessao": os.environ.get("AXIA_SESSAO") or os.environ.get("CLAUDE_SESSION_NAME") or "",
                                "o_que": args, "linhas": linhas}, ensure_ascii=False) + "\n")
    except OSError as e:
        print("(registro das leituras falhou: %s)" % e, file=sys.stderr)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="le, so leitura, o que aconteceu no WhatsApp da Renascer (#981)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--numero", help="o wa_id (DDI+DDD+numero, so digitos)")
    g.add_argument("--bsuid", help="o BSUID da Meta")
    g.add_argument("--campo", action="store_true", help="o canal de campo da semana")
    g.add_argument("--ultimas", type=int, nargs="?", const=20, help="as ultimas N conversas (padrao 20)")
    p.add_argument("--dias", type=int, help="so os ultimos N dias")
    p.add_argument("--desde", help="so a partir de AAAA-MM-DD")
    p.add_argument("--pgpass", help="outro pgpass (padrao: C:\\AxiaAtende\\.pgpass_leitura)")
    p.add_argument("--dsn", help=argparse.SUPPRESS)   # so para teste
    p.add_argument("--log", help=argparse.SUPPRESS)   # so para teste
    a = p.parse_args(argv)
    desde = None
    if a.desde:
        desde = datetime.strptime(a.desde, "%Y-%m-%d").replace(tzinfo=FUSO)
    elif a.dias:
        desde = datetime.now(timezone.utc) - timedelta(days=a.dias)
    try:
        con = conectar(a.dsn, Path(a.pgpass) if a.pgpass else None)
    except SemAcesso as e:
        print("sem acesso: %s" % e, file=sys.stderr)
        return 2
    try:
        if a.campo:
            linhas = campo(con, a.dias or 7)
        elif a.ultimas is not None:
            linhas = ultimas(con, a.ultimas)
        else:
            linhas = conversa(con, a.numero, a.bsuid, desde)
    finally:
        con.close()
    for l in linhas:
        print(l)
    registrar(_sem_os_de_teste(argv if argv is not None else sys.argv[1:]), len(linhas), Path(a.log) if a.log else LOG)
    return 0


def _sem_os_de_teste(args: list[str]) -> list[str]:
    """Os argumentos como foram dados, menos `--dsn X` e `--log X` (so de teste; a DSN tem senha)."""
    saida, pular = [], False
    for x in args:
        if pular:
            pular = False
            continue
        if x in ("--dsn", "--log"):
            pular = True
            continue
        if x.startswith(("--dsn=", "--log=")):
            continue
        saida.append(x)
    return saida


if __name__ == "__main__":
    sys.exit(main())
