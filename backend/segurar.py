"""Segurar o envio a carteira (#1169, dono 05/11/2026). Spec: docs/specs/2026-11-05-segurar-o-envio-a-carteira.md.

O despacho de lotes (`envio.mandar_lotes`) so manda envio `ativo` ou `parado_nota`: `suspenso` ja fica
parado desde a 001. Este modulo e quem SUSPENDE e RELIGA, com quem e quando, e e a chave geral:

- por envio (a tela): `suspender` (de ativo ou parado pela nota) e `religar` (de suspenso ou parado pela
  nota). Com o "segurar tudo" ligado, religar e recusado: a trava geral vale para todos;
- o "segurar tudo": ao LIGAR, todo envio `ativo` vira `suspenso` com `suspenso_por = 'segurar tudo'`; ao
  DESLIGAR, so esses voltam a `ativo`. O pedido que chega com a chave ligada nasce suspenso
  (`'chegou no segurar tudo'`) e CONTINUA suspenso depois: alguem religa, um a um (decisao 1 do dono);
- imagens a quem ja disse "quero", avisos, chamados e Status do dia nao passam por aqui (decisao 2).

POR QUE NAO DENTRO DE `envio.py`: em 05/11 outra sessao (#1267) editava o laco de lotes do mesmo
arquivo. A trava pelo ESTADO do envio da o mesmo efeito sem tocar o despacho: nada sai de envio suspenso.
"""
from __future__ import annotations

import json
from datetime import datetime

POR_SEGURAR = "segurar tudo"
POR_CHEGOU = "chegou no segurar tudo"


class Recusa(Exception):
    """A acao nao cabe no estado do envio (a frase vai a tela)."""


def estado(con) -> dict:
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'envio.segurar'").fetchone()
    v = (r["valor"] if r else None) or {}
    if not isinstance(v, dict):
        v = {"ligado": bool(v)}
    return {"ligado": bool(v.get("ligado")), "por": v.get("por"), "em": v.get("em")}


def _gravar_chave(con, ligado: bool, por: str, agora: datetime) -> None:
    con.execute("""INSERT INTO atendimento.ajustes (chave, valor) VALUES ('envio.segurar', %s::jsonb)
                   ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor, atualizado_em = now()""",
                (json.dumps({"ligado": ligado, "por": por, "em": agora.isoformat()}),))


def ligar(con, por: str, agora: datetime) -> int:
    """Liga a trava geral; devolve quantos envios ativos pararam."""
    _gravar_chave(con, True, por, agora)
    return con.execute("""UPDATE atendimento.envios SET situacao = 'suspenso', suspenso_por = %s, suspenso_em = %s
                           WHERE situacao = 'ativo'""", (POR_SEGURAR, agora)).rowcount


def desligar(con, por: str, agora: datetime) -> int:
    """Solta a trava geral; devolve quantos envios voltaram a andar (so os que ela tinha parado)."""
    _gravar_chave(con, False, por, agora)
    return con.execute("""UPDATE atendimento.envios SET situacao = 'ativo', suspenso_por = %s, suspenso_em = %s
                           WHERE situacao = 'suspenso' AND suspenso_por = %s""", (por, agora, POR_SEGURAR)).rowcount


def no_pedido(con, envio_id: int, novo: bool, agora: datetime) -> bool:
    """O pedido que acabou de nascer com a trava ligada fica suspenso. Pedido repetido nao muda."""
    if not novo or not estado(con)["ligado"]:
        return False
    return con.execute("""UPDATE atendimento.envios SET situacao = 'suspenso', suspenso_por = %s, suspenso_em = %s
                           WHERE id = %s AND situacao = 'ativo'""", (POR_CHEGOU, agora, envio_id)).rowcount > 0


def suspender(con, envio_id: int, por: str, agora: datetime) -> None:
    n = con.execute("""UPDATE atendimento.envios SET situacao = 'suspenso', suspenso_por = %s, suspenso_em = %s
                        WHERE id = %s AND situacao IN ('ativo', 'parado_nota')""", (por, agora, envio_id)).rowcount
    if not n:
        raise Recusa("só se suspende envio que está enviando ou parado pela nota")


def religar(con, envio_id: int, por: str, agora: datetime) -> None:
    if estado(con)["ligado"]:
        raise Recusa("o envio à carteira está SEGURADO: desligue o \"Segurar tudo\" antes de religar um envio")
    n = con.execute("""UPDATE atendimento.envios SET situacao = 'ativo', suspenso_por = %s, suspenso_em = %s
                        WHERE id = %s AND situacao IN ('suspenso', 'parado_nota')""", (por, agora, envio_id)).rowcount
    if not n:
        raise Recusa("este envio não está suspenso nem parado pela nota")
