"""#1222: liga, desliga ou mostra o chamado no WhatsApp (a chave `pendencias.ligado`). Em producao,
janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\chamado_no_whatsapp.py ver|ligar|desligar

Ligar nao despeja o historico: a primeira volta das telas so guarda o cursor de agora. Desligar
para tudo na hora (nada sai, nenhuma resposta e tomada); o que ja esperava fica, e sai se religar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402


def main() -> int:
    acao = (sys.argv[1:] or ["ver"])[0]
    if acao not in ("ver", "ligar", "desligar"):
        print("uso: chamado_no_whatsapp.py ver|ligar|desligar")
        return 2
    cfg = config.carregar()
    with conexao(cfg) as con:
        if acao != "ver":
            con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                            WHERE chave = 'pendencias.ligado'""", ("true" if acao == "ligar" else "false",))
        ligado = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'pendencias.ligado'").fetchone()
        cursor = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'pendencias.cursor'").fetchone()
        n = con.execute("""SELECT estado, count(*) AS n FROM atendimento.pendencias_mensagens
                            GROUP BY estado ORDER BY estado""").fetchall()
    print("chamado no WhatsApp: %s" % ("LIGADO" if ligado and ligado["valor"] is True else "desligado"))
    print("cursor do ERP: %s" % (cursor["valor"] if cursor else "ainda nenhum (a primeira volta guarda)"))
    print("mensagens: %s" % (", ".join("%s %d" % (r["estado"], r["n"]) for r in n) or "nenhuma"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
