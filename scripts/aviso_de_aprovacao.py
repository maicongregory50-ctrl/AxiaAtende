"""#1276: liga, desliga ou mostra o aviso de aprovação no WhatsApp (a chave `pendencias.aprovacao.ligado`).
Em producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\aviso_de_aprovacao.py ver|ligar|desligar

Depende tambem de `pendencias.ligado` (o chamado no WhatsApp): e o mesmo envio. Sai so com a janela
aberta; fora dela espera calado e nunca chama modelo pago. Desligar para de trazer pedidos novos na
hora; o aviso que ja esperava continua esperando a janela, e cai quando o pedido for decidido.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402

CHAVE = "pendencias.aprovacao.ligado"


def main() -> int:
    acao = (sys.argv[1:] or ["ver"])[0]
    if acao not in ("ver", "ligar", "desligar"):
        print("uso: aviso_de_aprovacao.py ver|ligar|desligar")
        return 2
    cfg = config.carregar()
    with conexao(cfg) as con:
        if acao != "ver":
            con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                            WHERE chave = %s""", ("true" if acao == "ligar" else "false", CHAVE))
        r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (CHAVE,)).fetchone()
        envio = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'pendencias.ligado'").fetchone()
        n = con.execute("""SELECT m.estado, count(*) AS n FROM atendimento.pendencias_mensagens m
                             JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                            WHERE p.tipo = 'aprovacao' GROUP BY m.estado ORDER BY m.estado""").fetchall()
    print("aviso de aprovacao: %s" % ("LIGADO" if r and r["valor"] is True else "desligado"))
    print("envio das pendencias (pendencias.ligado): %s" % ("ligado" if envio and envio["valor"] is True else "DESLIGADO"))
    print("avisos: %s" % (", ".join("%s %d" % (x["estado"], x["n"]) for x in n) or "nenhum"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
