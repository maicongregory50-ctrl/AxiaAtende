"""#1128: o pedido de CT-e da Logistica do ERP -- a ficha do frete vai ao WhatsApp do destino "Logistica".

Spec: C:\\AxiaGestao\\docs\\specs\\2026-10-29-logistica-fretes.md (plano ao lado, passo 8).

Quem aperta CT-e na tela Fretes do ERP grava um pedido la. Daqui:

1. **As TELAS** (a cada minuto, `volta`): contam ao ERP a janela de 24 h do destino "Logistica" (o ultimo
   recado que esse numero mandou a empresa, `envio.janela_aberta`, a mesma fonte), trazem os pedidos
   pendentes, baixam a ficha para `envios_pasta\\cte` e gravam a linha em `atendimento.pedidos_cte`. Na
   mesma volta, devolvem ao ERP o que o recepcionista ja mandou ou nao conseguiu mandar.
2. **O RECEPCIONISTA** (na rotina do minuto, `mandar`): manda o PDF com a linha de texto, SO com a janela
   aberta. Fechada: grava o erro com a frase do dono, e a tela do ERP mostra "Falhou" com ela.

SEM MODELO DA META (dono, 29/10/2026): "essa mensagem so sai se tiver janela free de 24 horas aberta, nao
sai por mensagem padrao". O ERP ja recusa o clique com a janela fechada (pela informacao que este modulo
manda); a conferencia aqui e a do minuto entre o clique e o envio.

O recepcionista, que a internet alcanca, nao le o ERP; as telas nao falam com a Meta (config.py).
"""
from __future__ import annotations

import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from . import erp
from .banco import conexao
from .envio import JANELA, com_nove, janela_aberta, so_digitos

INTERVALO_SEGUNDOS = 60
DESTINO_PADRAO = "Logística"
FRASE_JANELA = "Você precisa abrir a janela no WhatsApp."


def _sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().strip().lower()


def destino(con) -> dict | None:
    """Para quem vai a ficha, nesta ordem, sem olhar acento nem caixa:
    1. o destino ativo com o nome do ajuste `logistica.destino` (ausente = "Logística");
    2. o destino ativo com "logistica" no nome ("Benedito - Logística");
    3. o destino do item "Fretes" do menu (chave `fretes`), que e quem cuida de frete para o cliente.
    O nome escolhido vai ao ERP junto com a janela, e a tela Fretes o mostra."""
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'logistica.destino'").fetchone()
    nome = _sem_acento(r["valor"] if r and isinstance(r["valor"], str) else DESTINO_PADRAO)
    ativos = [dict(d) for d in con.execute("SELECT id, nome, whatsapp FROM atendimento.destinos WHERE ativo ORDER BY id").fetchall()]
    for teste in (lambda n: n == nome, lambda n: "logistica" in n):
        for d in ativos:
            if teste(_sem_acento(d["nome"])):
                return d
    m = con.execute("""SELECT d.id, d.nome, d.whatsapp FROM atendimento.menu m
                         JOIN atendimento.destinos d ON d.id = m.destino_id AND d.ativo
                        WHERE m.chave = 'fretes'""").fetchone()
    return dict(m) if m else None


def aberta_ate(con, numero: str):
    """Ate quando a janela de 24 h desse numero esta aberta (o ultimo recado + 24 h), ou None."""
    from .saida import wa_id_do_whatsapp
    formas = list({com_nove(numero), wa_id_do_whatsapp(com_nove(numero))})
    r = con.execute("""SELECT max(recebido_em) AS em FROM atendimento.eventos_meta
                        WHERE tipo = 'mensagem' AND corpo->'msg'->>'from' = ANY(%s)""", (formas,)).fetchone()
    return (r["em"] + JANELA) if r and r["em"] else None


def volta(cfg, ir=erp.logistica, ficha=erp.ficha_do_frete, devolver=erp.estado_do_pedido) -> dict:
    """Uma volta das TELAS. Devolve a contagem, ou {"erro": motivo}. Sem o segredo, nem tenta."""
    if not cfg.erp_segredo:
        return {"erro": "a ligação com o ERP não está ligada"}
    with conexao(cfg) as con:
        d = destino(con)
        ate = aberta_ate(con, d["whatsapp"]) if d else None
        ja = {r["erp_pedido_id"] for r in con.execute("SELECT erp_pedido_id FROM atendimento.pedidos_cte").fetchall()}
        a_devolver = [dict(r) for r in con.execute(
            """SELECT id, erp_pedido_id, wamid, erro, enviado_em FROM atendimento.pedidos_cte
                WHERE devolvido_em IS NULL AND (enviado_em IS NOT NULL OR erro <> '') ORDER BY id""").fetchall()]
    janela = {"destino": d["nome"] if d else None, "aberta_ate": ate.isoformat() if ate else None}
    try:
        r = ir(cfg, janela)
    except erp.ErpIndisponivel as e:
        return {"erro": str(e)}
    token, novos, devolvidos = r["token"], 0, 0

    pasta = Path(cfg.envios_pasta) / "cte"
    for p in r["pendentes"]:
        if p["id"] in ja:
            continue
        erro, arquivo = "", ""
        if not d:
            erro = "Não há destino \"%s\" ativo no AxiaAtende (tela Destinos)." % DESTINO_PADRAO
        else:
            try:
                pasta.mkdir(parents=True, exist_ok=True)
                caminho = pasta / ("%s-%d.pdf" % (p["numero"], p["id"]))
                caminho.write_bytes(ficha(cfg, token, p["frete_id"]))
                arquivo = str(caminho)
            except (erp.ErpIndisponivel, OSError) as e:
                print("logistica: ficha do pedido %s: %s" % (p["id"], e), flush=True)
                continue   # tenta na proxima volta
        with conexao(cfg) as con:
            con.execute(
                """INSERT INTO atendimento.pedidos_cte (erp_pedido_id, frete_numero, texto, arquivo, para_nome,
                                                       para_whatsapp, erro)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (erp_pedido_id) DO NOTHING""",
                (p["id"], p["numero"], p["texto"], arquivo, d["nome"] if d else "",
                 com_nove(so_digitos(d["whatsapp"])) if d else "", erro))
        novos += 1

    for a in a_devolver:
        try:
            if a["enviado_em"]:
                devolver(cfg, token, a["erp_pedido_id"], "ENVIADO", wamid=a["wamid"])
            else:
                devolver(cfg, token, a["erp_pedido_id"], "FALHOU", motivo=a["erro"])
        except erp.ErpIndisponivel as e:
            print("logistica: estado do pedido %s: %s" % (a["erp_pedido_id"], e), flush=True)
            continue
        with conexao(cfg) as con:
            con.execute("UPDATE atendimento.pedidos_cte SET devolvido_em = now() WHERE id = %s", (a["id"],))
        devolvidos += 1
    # os que nasceram com erro (sem destino) voltam ao ERP na proxima volta, pelo mesmo caminho
    return {"pendentes": len(r["pendentes"]), "novos": novos, "devolvidos": devolvidos}


def mandar(con, saida, agora: datetime | None = None) -> int:
    """O RECEPCIONISTA: manda o que as telas enfileiraram. So com a janela aberta. Devolve quantos sairam."""
    agora = agora or datetime.now(timezone.utc)
    saiu = 0
    for p in con.execute("""SELECT * FROM atendimento.pedidos_cte WHERE enviado_em IS NULL AND erro = ''
                             ORDER BY id LIMIT 10""").fetchall():
        try:
            if not janela_aberta(con, p["para_whatsapp"], agora):
                raise RuntimeError(FRASE_JANELA)
            dados = Path(p["arquivo"]).read_bytes()
            w = saida.documento(p["para_whatsapp"], dados, "ficha-%s.pdf" % p["frete_numero"], legenda=p["texto"])
            con.execute("UPDATE atendimento.pedidos_cte SET enviado_em = %s, wamid = %s WHERE id = %s",
                        (agora, w or "", p["id"]))
            saiu += 1
        except Exception as falha:  # noqa: BLE001 -- um pedido nao segura o outro
            motivo = str(falha) if str(falha) == FRASE_JANELA else "Não saiu: %s" % (str(falha)[:250] or type(falha).__name__)
            con.execute("UPDATE atendimento.pedidos_cte SET erro = %s WHERE id = %s", (motivo, p["id"]))
    return saiu
