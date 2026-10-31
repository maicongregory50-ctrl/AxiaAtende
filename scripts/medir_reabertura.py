"""#1222: a reabertura dos avisos internos ("Voce tem N aviso(s)... Toque em Ver") serve? So leitura.

Para cada reabertura que saiu desde que o porteiro (#1188) ligou: quantos avisos ela guardou, quantos
ja sairam, e por qual porta -- o TOQUE em Ver, a pessoa ter ESCRITO sem tocar, ou ainda guardados --,
e quantos viraram NAO VISTO (7 dias sem toque). Mostra o numero mascarado, nunca o texto. Em
producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\medir_reabertura.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import com_nove  # noqa: E402
from backend.saida import wa_id_do_whatsapp  # noqa: E402


def mascarar(numero: str) -> str:
    return "..." + numero[-4:] if len(numero) > 4 else numero


def main() -> int:
    cfg = config.carregar()
    with conexao(cfg) as con:
        con.execute("SET TRANSACTION READ ONLY")
        reaberturas = con.execute("""SELECT e.id, e.para, e.enviada_em AS criado_em, e.status
                                       FROM atendimento.enviadas e
                                      WHERE e.tipo = 'modelo' AND e.resumo = 'reabertura dos avisos'
                                      ORDER BY e.id""").fetchall()
        tocou = escreveu = guardado = nao_visto = 0
        horas_ate_o_toque = []
        print("REABERTURAS QUE SAIRAM: %d" % len(reaberturas))
        print()
        print("  quando       para      status    avisos  toque(h)  escreveu  guardado  nao visto")
        for r in reaberturas:
            avisos = con.execute("""SELECT enviado_em, nao_visto_em FROM atendimento.avisos
                                     WHERE reabertura_id = %s""", (r["id"],)).fetchall()
            n = com_nove(r["para"])
            formas = list({n, wa_id_do_whatsapp(n)})
            toque = con.execute("""SELECT min(recebido_em) AS em FROM atendimento.eventos_meta
                                    WHERE tipo = 'mensagem' AND corpo->'msg'->>'from' = ANY(%s)
                                      AND recebido_em > %s
                                      AND (corpo->'msg'->'button'->>'payload' LIKE 'reabrir:%%'
                                           OR corpo->'msg'->'interactive'->'button_reply'->>'id' LIKE 'reabrir:%%')""",
                                (formas, r["criado_em"])).fetchone()["em"]
            saidos = [a for a in avisos if a["enviado_em"]]
            pelo_toque = [a for a in saidos if toque and a["enviado_em"] >= toque]
            t, w = len(pelo_toque), len(saidos) - len(pelo_toque)
            g = sum(1 for a in avisos if not a["enviado_em"] and not a["nao_visto_em"])
            nv = sum(1 for a in avisos if a["nao_visto_em"])
            tocou += t
            escreveu += w
            guardado += g
            nao_visto += nv
            h = None
            if toque:
                h = (toque - r["criado_em"]).total_seconds() / 3600
                horas_ate_o_toque.append(h)
            print("  %s  %-8s  %-8s  %6d  %8s  %8d  %8d  %9d" % (
                r["criado_em"].strftime("%d/%m %H:%M"), mascarar(n), r["status"], len(avisos),
                "%.1f" % h if h is not None else "-", w, g, nv))
        print()
        total = tocou + escreveu + guardado + nao_visto
        print("AVISOS GUARDADOS POR REABERTURA: %d" % total)
        print("  sairam pelo toque em Ver:            %d" % tocou)
        print("  sairam porque a pessoa escreveu:     %d" % escreveu)
        print("  ainda guardados (menos de 7 dias):   %d" % guardado)
        print("  nao vistos (7 dias sem toque):       %d" % nao_visto)
        if horas_ate_o_toque:
            horas_ate_o_toque.sort()
            print("  horas ate o toque, mediana:          %.1f" % horas_ate_o_toque[len(horas_ate_o_toque) // 2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
