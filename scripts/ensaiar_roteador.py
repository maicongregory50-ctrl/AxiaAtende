"""#1238, passos 12 e 17: a rodada da maquete com a OlivIA REAL. Manda os 28 retratos de
`tests/maquete_roteador.json` (as 30 cenas menos a foto de 26 s e o "bom dia", que nem chegam a ela) ao
roteador de verdade e imprime, ao lado do esperado, o destino, o sinal e a confianca que ela deu, e o custo.
NAO escreve no banco do atendimento nem manda nada pela Meta: so as 28 chamadas pagas, registradas em
`uso_ia` como qualquer chamada do roteador.

Precisa da chave da Anthropic do Atende, que so o `.env.recepcionista` tem -- janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\ensaiar_roteador.py

A regua sugerida pela spec para ligar: 25 ou mais de 30 (as duas cenas que nao chegam a OlivIA contam como
certas) e NENHUMA legenda de foto indo a chamado. O que errar vira ajuste de prompt antes de ligar.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.ia import IA, MODELO  # noqa: E402

MAQUETE = Path(__file__).resolve().parent.parent / "tests" / "maquete_roteador.json"
PRECO_ENTRADA, PRECO_SAIDA = 0.10, 0.50   # Haiku 5.5, US$ por milhao (a semente da 050)


def main() -> int:
    cfg = config.carregar()
    if not cfg.anthropic_chave:
        print("sem a chave da Anthropic: rode em janela elevada com AXIAATENDE_AMBIENTE=producao e "
              "AXIAATENDE_PROCESSO=recepcionista")
        return 2
    cenas = json.loads(MAQUETE.read_text(encoding="utf-8"))
    tokens = {"entrada": 0, "saida": 0}

    def registrar(funcao, modelo, entrada, saida):
        tokens["entrada"] += entrada
        tokens["saida"] += saida
        try:
            from backend.uso_ia import guardar_no_banco
            guardar_no_banco(cfg)(funcao, modelo, entrada, saida)
        except Exception as falha:   # noqa: BLE001 -- o ensaio vale sem o registro
            print("  (uso nao registrado: %s)" % type(falha).__name__)

    ia = IA(cfg, registrar=registrar)
    certos, foto_no_chamado = 2, 0   # a foto de 26 s e o "bom dia" nao passam pela OlivIA
    print("%-3s %-10s %-8s | %-8s %-6s %-12s %s" % ("n", "esperado", "numero", "destino", "conf", "sinal", "texto"))
    for c in cenas:
        r = ia.rotear(c["retrato"])
        destino = r["destino"]
        if c["esperado"] == "correcao":
            ok = destino == "correcao" and r["destino_certo"] == c["numero_esperado"]
            destino = "corr->%s" % r["destino_certo"]
        else:
            ok = destino == c["numero_esperado"]
        certos += ok
        # a legenda de foto que foi a chamado: o pior erro (a spec manda zero)
        if c["esperado"] == "foto" and destino != c["numero_esperado"] and destino.isdigit():
            if c["retrato"]["texto"].find("%s. Chamado" % destino) >= 0:
                foto_no_chamado += 1
        print("%-3d %-10s %-8s | %-8s %-6s %-12s %s%s" % (c["n"], c["esperado"], c["numero_esperado"], destino,
                                                     r["confianca"] or "", r["sinal"], c["texto"][:50],
                                                     "" if ok else "   <-- ERROU"))
    custo = tokens["entrada"] / 1e6 * PRECO_ENTRADA + tokens["saida"] / 1e6 * PRECO_SAIDA
    print()
    print("certos: %d de 30 (as 2 que nao chegam a OlivIA contam como certas)" % certos)
    print("legenda de foto que foi a chamado: %d" % foto_no_chamado)
    print("modelo %s; tokens %d entrada, %d saida; custo US$ %.4f (%.5f por mensagem)"
          % (MODELO, tokens["entrada"], tokens["saida"], custo, custo / max(len(cenas), 1)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
