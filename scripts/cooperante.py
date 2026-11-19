"""#1664: liga, desliga ou mostra a RESPOSTA PADRAO ao cooperante que responde a um aviso automatico do contrato
(a chave `cooperante.resposta_padrao`, que nasce desligada na 073). Liga e desliga SEM restart. Em producao,
janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\cooperante.py mostrar|ligar|desligar

RECUSA quando o ajuste nao existe (a migracao 073 nao foi aplicada), e `ligar` recusa tambem quando o contato
(`cooperante.destino`) nao aponta um destino da tela Destinos: sem ele a resposta nao teria a quem mandar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config, cooperante  # noqa: E402
from backend.banco import conexao  # noqa: E402

USO = "uso: cooperante.py mostrar|ligar|desligar"


def rodar(con, acao: str) -> int:
    if acao not in ("mostrar", "ligar", "desligar"):
        print(USO)
        return 2
    if acao in ("ligar", "desligar"):
        if acao == "ligar" and cooperante.destino(con) is None:
            print("RECUSADO: o ajuste %s nao aponta um destino da tela Destinos." % cooperante.AJUSTE_DESTINO)
            return 1
        n = con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                            WHERE chave = %s""", ("true" if acao == "ligar" else "false",
                                                  cooperante.AJUSTE_CHAVE)).rowcount
        if n != 1:
            print("RECUSADO: o ajuste %s nao existe neste banco (a migracao 073 nao foi aplicada?)"
                  % cooperante.AJUSTE_CHAVE)
            return 1
    existe = con.execute("SELECT 1 FROM atendimento.ajustes WHERE chave = %s",
                         (cooperante.AJUSTE_CHAVE,)).fetchone()
    if not existe:
        print("RECUSADO: o ajuste %s nao existe neste banco (a migracao 073 nao foi aplicada?)"
              % cooperante.AJUSTE_CHAVE)
        return 1
    d = cooperante.destino(con)
    texto = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s",
                        (cooperante.AJUSTE_TEXTO,)).fetchone()
    print("Resposta padrao ao cooperante: %s" % ("LIGADA" if cooperante.ligado(con) else "desligada"))
    print("Prazo depois do aviso: %d dias" % cooperante.dias(con))
    print("Contato: %s" % (("%s (%s)" % (d["nome"], d["whatsapp"])) if d else "SEM DESTINO"))
    print("Texto: %s" % ((texto or {}).get("valor") or ""))
    return 0


def main() -> int:
    acao = (sys.argv[1:] or ["mostrar"])[0]
    if acao not in ("mostrar", "ligar", "desligar"):
        print(USO)
        return 2
    cfg = config.carregar()
    with conexao(cfg) as con:
        return rodar(con, acao)


if __name__ == "__main__":
    sys.exit(main())
