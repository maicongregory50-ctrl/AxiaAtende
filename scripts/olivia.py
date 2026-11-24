"""#1525: liga, desliga ou mostra a CONDUCAO DA CONVERSA DE VAGA pela OlivIA (a chave `olivia.conduz_vaga`,
que nasce desligada na 067). Liga e desliga SEM restart. So vale com `OLIVIA_FALA=true` no recepcionista.
Em producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\olivia.py mostrar|ligar-vaga|desligar-vaga

#1589: `ligar-venda|desligar-venda`, a conversa de quem quer comprar (070). #1660: `ligar-qualifica|
desligar-qualifica`, o piloto da qualificacao do produtor rural (072); recusa ligar com a venda desligada.
#1754: `ligar-carteira|desligar-carteira`, a OlivIA atende o cliente da carteira no boletim (077). So o DONO
liga, e `ligar-carteira` RECUSA enquanto docs/olivia/parceria-da-carteira.md nao disser APROVADO.

`ligar-vaga` RECUSA ligar enquanto algum texto de cadastro da ficha ainda tiver a marca [TEXTO DO DONO]:
o texto provisorio da 067 nao sai para candidato nenhum.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config, interesse, olivia  # noqa: E402
from backend.banco import conexao  # noqa: E402

MARCA = "[TEXTO DO DONO]"


def provisorios(con) -> list[str]:
    return [r["chave"] for r in con.execute("""SELECT chave FROM atendimento.respostas_da_vaga
                                                WHERE ativo AND position(%s in texto) > 0 ORDER BY ordem, chave""",
                                            (MARCA,)).fetchall()]


def main() -> int:
    acao = (sys.argv[1:] or ["mostrar"])[0]
    if acao not in ("mostrar", "ligar-vaga", "desligar-vaga", "ligar-venda", "desligar-venda",
                    "ligar-qualifica", "desligar-qualifica", "ligar-carteira", "desligar-carteira"):
        print("uso: olivia.py mostrar|ligar-vaga|desligar-vaga|ligar-venda|desligar-venda|"
              "ligar-qualifica|desligar-qualifica|ligar-carteira|desligar-carteira")
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
        if acao in ("ligar-qualifica", "desligar-qualifica"):
            # #1660: o piloto da qualificacao do produtor rural. A chave nasce na migracao 072 e so vale com a
            # venda ligada: ligar com a venda desligada nao faria nada, e por isso e recusado.
            if acao == "ligar-qualifica" and not olivia.conduz_venda(con):
                print("RECUSADO: a conversa de quem quer comprar (%s) esta desligada; ligue-a antes (ligar-venda)"
                      % olivia.AJUSTE_VENDA)
                return 1
            n = con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                                WHERE chave = %s""", ("true" if acao == "ligar-qualifica" else "false",
                                                      olivia.AJUSTE_QUALIFICA)).rowcount
            if n != 1:
                print("RECUSADO: o ajuste %s nao existe neste banco (a migracao 072 nao foi aplicada?)"
                      % olivia.AJUSTE_QUALIFICA)
                return 1
        if acao in ("ligar-carteira", "desligar-carteira"):
            # #1754 (D11): a chave nasce na 077. Ligar exige o texto da parceria aprovado pelo dono.
            if acao == "ligar-carteira" and not interesse.parceria()[0]:
                print("RECUSADO: o texto da parceria (%s) ainda nao esta APROVADO" % interesse.PARCERIA)
                return 1
            n = con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                                WHERE chave = %s""", ("true" if acao == "ligar-carteira" else "false",
                                                      interesse.AJUSTE)).rowcount
            if n != 1:
                print("RECUSADO: o ajuste %s nao existe neste banco (a migracao 077 nao foi aplicada?)"
                      % interesse.AJUSTE)
                return 1
        ligada = olivia.conduz_vaga(con)
        venda = olivia.conduz_venda(con)
        carteira = interesse.ligado(con)
        qualifica = olivia.qualifica(con)
        estados = olivia._estados_do_piloto(con)
        destinos = {r["chave"]: r["nome"] for r in con.execute(
            """SELECT m.chave, d.nome FROM atendimento.menu m LEFT JOIN atendimento.destinos d ON d.id = m.destino_id
                WHERE m.chave = ANY(%s)""", ([olivia.FOLHA_DO_PRODUTOR + uf.lower() for uf in estados],)).fetchall()}
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
    print("qualificacao do produtor rural (#1660): %s; estados do piloto: %s" % (
        "LIGADA" if qualifica else "desligada", ", ".join(estados) or "nenhum"))
    for chave, nome in sorted(destinos.items()):
        print("  %s -> ficha e cartao para: %s" % (chave, nome or "SEM DESTINO"))
    print("a carteira no boletim (#1754): %s; texto da parceria: %s" % (
        "LIGADA" if carteira else "desligada", "APROVADO" if interesse.parceria()[0] else "rascunho"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
