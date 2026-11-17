"""#1525: liga, desliga ou mostra a CONDUCAO DA CONVERSA DE VAGA pela OlivIA (a chave `olivia.conduz_vaga`,
que nasce desligada na 067). Liga e desliga SEM restart. So vale com `OLIVIA_FALA=true` no recepcionista.
Em producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\olivia.py mostrar|ligar-vaga|desligar-vaga

`ligar-vaga` RECUSA ligar enquanto algum texto de cadastro da ficha ainda tiver a marca [TEXTO DO DONO]:
o texto provisorio da 067 nao sai para candidato nenhum.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config, olivia  # noqa: E402
from backend.banco import conexao  # noqa: E402

MARCA = "[TEXTO DO DONO]"


def provisorios(con) -> list[str]:
    return [r["chave"] for r in con.execute("""SELECT chave FROM atendimento.respostas_da_vaga
                                                WHERE ativo AND position(%s in texto) > 0 ORDER BY ordem, chave""",
                                            (MARCA,)).fetchall()]


def main() -> int:
    acao = (sys.argv[1:] or ["mostrar"])[0]
    if acao not in ("mostrar", "ligar-vaga", "desligar-vaga", "ligar-venda", "desligar-venda"):
        print("uso: olivia.py mostrar|ligar-vaga|desligar-vaga|ligar-venda|desligar-venda")
        return 2
    cfg = config.carregar()
    with conexao(cfg) as con:
        if acao == "ligar-vaga":
            falta = provisorios(con)
            if falta:
                print("RECUSADO: ainda ha texto provisorio %s em: %s" % (MARCA, ", ".join(falta)))
                print("Troque esses textos (respostas_da_vaga) pelos do dono e rode de novo.")
                return 1
        if acao in ("ligar-vaga", "desligar-vaga"):
            con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                            WHERE chave = %s""", ("true" if acao == "ligar-vaga" else "false", olivia.AJUSTE_CONDUZ))
        if acao in ("ligar-venda", "desligar-venda"):
            # #1589: a conversa de quem quer comprar. A chave nasce na migracao 070; sem a linha, nada muda.
            n = con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                                WHERE chave = %s""", ("true" if acao == "ligar-venda" else "false",
                                                      olivia.AJUSTE_VENDA)).rowcount
            if n != 1:
                print("RECUSADO: o ajuste %s nao existe neste banco (a migracao 070 nao foi aplicada?)"
                      % olivia.AJUSTE_VENDA)
                return 1
        ligada = olivia.conduz_vaga(con)
        venda = olivia.conduz_venda(con)
        toque = olivia._horas(con, "olivia.vaga_toque_h", 2)
        parcial = olivia._horas(con, "olivia.ficha_parcial_h", 4)
        falta = provisorios(con)
    print("conducao da vaga pela OlivIA (#1525): %s (ambiente %s; vale so com OLIVIA_FALA=true)"
          % ("LIGADA" if ligada else "desligada", cfg.ambiente))
    print("toque unico: %.0f h depois da ultima mensagem da pessoa; ficha parcial: %.0f h depois do toque"
          % (toque.total_seconds() / 3600, parcial.total_seconds() / 3600))
    print("textos provisorios %s: %s" % (MARCA, ", ".join(falta) or "nenhum"))
    print("conversa de quem quer comprar pela OlivIA (#1589): %s (vale so com OLIVIA_FALA=true)"
          % ("LIGADA" if venda else "desligada"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
