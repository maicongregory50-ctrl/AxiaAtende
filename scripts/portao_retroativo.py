"""O portao do #1189 para quem escreveu ANTES de ele existir (dono, 29/10/2026: "2 apenas").

O cliente da carteira que escreveu nas ultimas 24 h (a janela em que a Meta deixa mandar texto) recebe
agora o que o portao manda a quem escreve: o representante e o menu dele -- pelo mesmo
`motor.portao_do_cliente`, com as mesmas travas (a resposta automatica fica em silencio; quem ja esta
numa conversa aberta nao recebe; uma vez por dia).

Sem `--mandar`, SO MOSTRA a lista. `--so 4829,7613` escolhe pelo codigo do ERP: so esses entram. Em producao, janela elevada:

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\portao_retroativo.py
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\portao_retroativo.py --mandar
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config, motor  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import Envio  # noqa: E402

JANELA = timedelta(hours=23)   # uma hora de folga antes de a Meta fechar as 24 h


def quem_escreveu(con, envio, agora):
    """O ultimo texto de cada numero nas ultimas 23 h, de quem recebeu envio da carteira."""
    vistos, lista = set(), []
    for ev in con.execute("""SELECT id, recebido_em, corpo FROM atendimento.eventos_meta
                              WHERE tipo = 'mensagem' AND corpo->'msg'->>'type' = 'text' AND recebido_em > %s
                              ORDER BY id DESC""", (agora - JANELA,)).fetchall():
        e = motor.ler_mensagem({"contacts": ev["corpo"].get("contacts") or []}, ev["corpo"]["msg"])
        if not e.pessoa.wa_id or e.pessoa.wa_id in vistos:
            continue
        vistos.add(e.pessoa.wa_id)
        d = envio.convidado_recente(con, e.pessoa.wa_id, agora)
        if d:
            lista.append((ev, e, d))
    return lista


def main() -> int:
    mandar = "--mandar" in sys.argv
    cfg = config.carregar()
    agora = datetime.now(timezone.utc)
    saida = ia = None
    if mandar:
        from backend.saida import SaidaMeta
        saida = SaidaMeta(cfg.meta_phone_id, cfg.meta_token)
        if cfg.anthropic_chave:
            from backend.ia import IA
            ia = IA(cfg)
    envio = Envio(ler_nota=None)
    so = next((sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x == "--so"), "")
    so = {c.strip() for c in so.split(",") if c.strip()}
    with conexao(cfg) as con:
        lista = quem_escreveu(con, envio, agora)
    if so:   # --so 4829,7613: so esses codigos do ERP
        lista = [x for x in lista if str(x[2]["erp_codigo"]) in so]
    print("Clientes da carteira que escreveram nas ultimas 23 h: %d" % len(lista))
    for ev, e, d in lista:
        print("  %s  %s (ERP %s)  escreveu as %s  representante: %s"
              % (e.pessoa.wa_id, d["nome"], d["erp_codigo"],
                 ev["recebido_em"].astimezone(motor.FUSO).strftime("%d/%m %H:%M"), d["responsavel_nome"] or "-"))
    if not mandar:
        print("Nada foi mandado. Para mandar: o mesmo comando com --mandar")
        return 0
    for ev, e, d in lista:
        with conexao(cfg) as con:
            antes = con.execute("SELECT count(*) AS n FROM atendimento.enviadas WHERE para = %s",
                                (e.pessoa.para,)).fetchone()["n"]
            tratou = motor.portao_do_cliente(con, saida, ia, e, agora, envio)
            depois = con.execute("SELECT count(*) AS n FROM atendimento.enviadas WHERE para = %s",
                                 (e.pessoa.para,)).fetchone()["n"]
        if not tratou:
            r = "nao mandado (conversa aberta, da casa ou portao desligado)"
        elif depois > antes:
            r = "MANDADO"
        else:
            r = "silencio (resposta automatica, ou ja recebeu hoje)"
        print("  %s %s: %s" % (e.pessoa.wa_id, d["nome"], r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
