"""#1188, passo 1: quanto o porteiro dos avisos internos economiza. So leitura (so SELECT).

Os avisos dos ultimos 30 dias, por tipo e por numero, e quantos teriam saido DE GRACA: a pessoa tinha
mandado alguma mensagem ao numero da empresa nas 24 h antes do aviso (a mesma regra do porteiro,
`envio.janela_aberta`). Mostra o numero mascarado, nunca o texto. Em producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\medir_avisos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import JANELA, com_nove  # noqa: E402
from backend.saida import wa_id_do_whatsapp  # noqa: E402

DIAS = 30


def mascarar(numero: str) -> str:
    return "..." + numero[-4:] if len(numero) > 4 else numero


def main() -> int:
    cfg = config.carregar()
    with conexao(cfg) as con:
        con.execute("SET TRANSACTION READ ONLY")
        avisos = con.execute("""SELECT id, tipo, para_whatsapp, criado_em, enviado_em, erro
                                  FROM atendimento.avisos WHERE criado_em > now() - make_interval(days => %s)
                                 ORDER BY id""", (DIAS,)).fetchall()
        por_tipo: dict = {}
        por_numero: dict = {}
        for a in avisos:
            n = com_nove(a["para_whatsapp"])
            formas = list({n, wa_id_do_whatsapp(n)})
            r = con.execute("""SELECT 1 FROM atendimento.eventos_meta
                                WHERE tipo = 'mensagem' AND corpo->'msg'->>'from' = ANY(%s)
                                  AND recebido_em <= %s AND recebido_em > %s LIMIT 1""",
                            (formas, a["criado_em"], a["criado_em"] - JANELA)).fetchone()
            t = por_tipo.setdefault(a["tipo"], {"total": 0, "saiu": 0, "erro": 0, "de_graca": 0})
            t["total"] += 1
            t["saiu"] += bool(a["enviado_em"])
            t["erro"] += bool(a["erro"])
            t["de_graca"] += bool(r)
            m = por_numero.setdefault(n, {"total": 0, "de_graca": 0})
            m["total"] += 1
            m["de_graca"] += bool(r)

    total = sum(t["total"] for t in por_tipo.values())
    gratis = sum(t["de_graca"] for t in por_tipo.values())
    print("AVISOS INTERNOS DOS ULTIMOS %d DIAS: %d, a %d numeros distintos" % (DIAS, total, len(por_numero)))
    print("  teriam saido de graca (a pessoa escreveu nas 24 h antes): %d de %d" % (gratis, total))
    print()
    print("POR TIPO                        total  saiu  erro  de graca")
    for tipo, t in sorted(por_tipo.items()):
        print("  %-28s %5d %5d %5d %9d" % (tipo, t["total"], t["saiu"], t["erro"], t["de_graca"]))
    print()
    print("POR NUMERO (mascarado)          total  de graca")
    for numero, m in sorted(por_numero.items(), key=lambda x: -x[1]["total"]):
        print("  %-28s %5d %9d" % (mascarar(numero), m["total"], m["de_graca"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
