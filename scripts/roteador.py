"""#1238: liga, desliga ou mostra o ROTEADOR com contexto por contato (a chave `roteador.ligado`), com a
medida da spec: a contagem por sinal dos ultimos 7 dias e a fracao que entrou sem botao e sem correcao.
Em producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\roteador.py ver|ligar|desligar [--dias N]

Desligar vale na hora, sem reiniciar: a corrente volta a ser a de antes, com os freios de 03/11. O registro
de decisao fica.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config, roteador  # noqa: E402
from backend.banco import conexao  # noqa: E402


def main() -> int:
    args = sys.argv[1:] or ["ver"]
    acao = args[0]
    dias = int(args[args.index("--dias") + 1]) if "--dias" in args else 7
    if acao not in ("ver", "ligar", "desligar"):
        print("uso: roteador.py ver|ligar|desligar [--dias N]")
        return 2
    cfg = config.carregar()
    agora = datetime.now(timezone.utc)
    with conexao(cfg) as con:
        if acao != "ver":
            con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                            WHERE chave = 'roteador.ligado'""", ("true" if acao == "ligar" else "false",))
        ligado = roteador.ligado(con)
        carencia = roteador.carencia(con)
        m = roteador.medida(con, agora, dias)
        ultimas = con.execute("""SELECT criado_em, wa_id, sinal, confianca, destino, aplicado, corrigido_em, texto
                                   FROM atendimento.roteador ORDER BY id DESC LIMIT 10""").fetchall()
    print("roteador: %s (ambiente %s; carencia do chamado %d min)"
          % ("LIGADO" if ligado else "desligado", cfg.ambiente, carencia.total_seconds() // 60))
    print("ultimos %d dias: %d textos" % (dias, m["total"]))
    for sinal, n in sorted(m["por_sinal"].items()):
        print("  %-12s %d" % (sinal, n))
    print("  corrigidas  %d" % m["corrigidas"])
    if m["fracao"] is not None:
        print("sem botao e sem correcao: %d de %d (%.0f%%)" % (m["sem_botao_nem_correcao"], m["total"], m["fracao"] * 100))
    if ultimas:
        print("os ultimos:")
        for r in ultimas:
            print("  %s ...%s %-11s %-5s %-20s %s%s | %s" % (
                r["criado_em"].astimezone().strftime("%d/%m %H:%M"), (r["wa_id"] or "")[-4:], r["sinal"],
                r["confianca"] or "", r["destino"] or "-", "aplicado" if r["aplicado"] else "",
                " CORRIGIDO" if r["corrigido_em"] else "", (r["texto"] or "")[:50].replace("\n", " ")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
