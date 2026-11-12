"""#1434: o aviso de classe 1 do painel da casa, de pasta para a fila dos avisos.

A revisao ativa do painel (#1411, AxiaSecurity) roda como SYSTEM e nao tem remetente. Quando sobra algo
que parou para o dono, ela grava `<id>.json` (`{"id": int, "texto": str}`) em `cfg.painel_pedidos`. Este
modulo e o `ir` e o `devolver` do canal `painel_classe1` de `auditoria_erp.py`: a volta de sempre grava a
linha em `atendimento.avisos`, o porteiro manda (texto na janela, reabertura fora), e o estado volta como
`<id>.json` (`{"estado", "motivo", "wamid", "em"}`) em `cfg.painel_devolucao`, que a revisao le.

Spec: docs/specs/2026-11-12-aviso-do-painel-no-whatsapp.md.

Sem segredo e sem porta: arquivo local, como os `.req` das portas da casa. O canal nao depende do ERP.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class OrigemIndisponivel(RuntimeError):
    """A pasta dos pedidos nao existe ou nao pode ser lida: e erro do canal, os outros seguem."""


def ir(cfg) -> dict:
    """Os pedidos da pasta, no formato dos canais: {"pendentes": [{"id", "partes": [texto]}], "token"}.
    Arquivo ilegivel ou sem id inteiro e texto e pulado e dito no log -- um arquivo ruim nao para os outros."""
    pasta = Path(cfg.painel_pedidos)
    try:
        arquivos = sorted(pasta.glob("*.json"))
    except OSError as e:
        raise OrigemIndisponivel("nao consegui ler %s (%s)" % (pasta, e)) from None
    if not pasta.is_dir():
        raise OrigemIndisponivel("a pasta dos pedidos do painel nao existe: %s" % pasta)
    pendentes = []
    for a in arquivos:
        try:
            d = json.loads(a.read_text(encoding="utf-8-sig"))
            pid, texto = int(d["id"]), str(d["texto"]).strip()
            if pid <= 0 or not texto:
                raise ValueError("id ou texto vazio")
        except (OSError, ValueError, KeyError, TypeError) as e:
            print("painel_classe1: pedido ilegivel %s (%s)" % (a.name, type(e).__name__), flush=True)
            continue
        pendentes.append({"id": pid, "partes": [texto[:900]]})
    return {"pendentes": pendentes, "token": ""}


def devolver(cfg, token: str, aviso_id: int, estado: str, motivo: str = "", wamid: str = "") -> None:
    """Grava a devolucao de forma atomica (arquivo temporario e troca): a revisao nunca le meio arquivo."""
    pasta = Path(cfg.painel_devolucao)
    pasta.mkdir(parents=True, exist_ok=True)
    corpo = {"id": int(aviso_id), "estado": estado, "motivo": (motivo or "")[:500], "wamid": wamid or "",
             "em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    destino = pasta / ("%d.json" % int(aviso_id))
    tmp = pasta / ("%d.json.tmp" % int(aviso_id))
    tmp.write_text(json.dumps(corpo, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, destino)
