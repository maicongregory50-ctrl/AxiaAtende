"""#1238, passo 12: a tubulacao da maquete -- as 30 cenas de `tests/maquete_roteador.py` montadas no banco de
teste, o retrato real (passo 3), a IA FALSA respondendo o esperado, e o texto chegando ao fio certo (30/30).

`AXIAATENDE_GRAVAR_MAQUETE=1` grava os retratos em `tests/maquete_roteador.json`, que e o que
`scripts/ensaiar_roteador.py` manda a OlivIA real."""
import json
import os
import uuid
from datetime import timedelta
from pathlib import Path

from backend.banco import conexao
from tests.avisos_meta import texto
from tests.maquete_roteador import CENAS, ROTULO
from tests.saida_falsa import SaidaFalsa
from tests.test_campo import AGORA, EQUIPE, canal, ligar  # noqa: F401 -- `canal` e fixture
from tests.test_campo import passo
from tests.test_roteador import Aponta, chamado, cliente_aberto, curriculo, foto_aberta, logo_esperando

MIN = timedelta(minutes=1)
JSON = Path(__file__).resolve().parent / "maquete_roteador.json"
LIMPAR = ("roteador", "audios", "pendencias_mensagens", "pendencias", "material_de_campo", "campo_frases",
          "logos_de_cliente", "clientes_registros", "candidaturas", "enviadas", "conversas", "eventos_meta")


def _nos(cfg, quando, resumo):
    """O que a empresa mandou (o historico do retrato), com a hora certa."""
    with conexao(cfg) as con:
        con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo, enviada_em) VALUES (%s, %s, 'texto', %s, %s)",
                    ("wamid.nos.%s" % uuid.uuid4().hex[:12], EQUIPE, resumo, quando))


def _limpar(cfg):
    with conexao(cfg) as con:
        for t in LIMPAR:
            con.execute("DELETE FROM atendimento.%s" % t)


def _montar(cfg, s, n, abertos):
    for a in abertos:
        if a == "chamado":
            chamado(cfg, quando=AGORA - 30 * MIN)
            _nos(cfg, AGORA - 30 * MIN, "pendencias: Chamado 1222 · Chamado no WhatsApp — Ficou claro o passo 3?")
        elif a in ("foto", "foto_agora"):
            quando = AGORA - (timedelta(seconds=26) if a == "foto_agora" else 10 * MIN)
            foto_aberta(cfg, s, quando=quando, wamid="wf%d" % n)
            _nos(cfg, quando + timedelta(seconds=2), "Recebi.")
        elif a == "logo":
            logo_esperando(cfg, quando=AGORA - 20 * MIN)
            _nos(cfg, AGORA - 20 * MIN, "logo: Recebi a logo *logo.pdf*. De qual cliente ela é? Me diga o *nome do cliente*")
        elif a == "cliente":
            cliente_aberto(cfg, quando=AGORA - 40 * MIN)
            _nos(cfg, AGORA - 40 * MIN, "clientes: ficha com link Chamar Junior (PLANTAGRO, Tangará/SC)")
            _nos(cfg, AGORA - 40 * MIN, "clientes: Quando falar com ele, me conte aqui como foi.")
        elif a == "curriculo":
            curriculo(cfg, quando=AGORA - 50 * MIN)
            _nos(cfg, AGORA - 50 * MIN, "vaga: triagem errada")


def _numero(retrato, fio):
    for linha in retrato["texto"].splitlines():
        n, _, resto = linha.partition(". ")
        if n.isdigit() and resto.startswith(ROTULO[fio]):
            return n
    return None


def _linha(cfg, wamid):
    with conexao(cfg) as con:
        r = con.execute("SELECT * FROM atendimento.roteador WHERE wamid = %s", (wamid,)).fetchone()
    return dict(r) if r else None


def test_a_tubulacao_da_maquete_30_de_30(canal):
    ligar(canal)
    with conexao(canal) as con:
        for chave, valor in (("pendencias.ligado", "true"), ("pendencias.juntar_minutos", "0"), ("roteador.ligado", "true")):
            con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = %s", (valor, chave))
    falhas, retratos = [], []
    for n, cena in enumerate(CENAS, 1):
        _limpar(canal)
        s = SaidaFalsa()
        _montar(canal, s, n, cena["abertos"])
        if "antes" in cena:
            texto_antes, fio_errado = cena["antes"]
            passo(canal, s, texto("wantes%d" % n, texto_antes, numero=EQUIPE), agora=AGORA - MIN,
                  ia=Aponta({"destino": ROTULO[fio_errado]}))
        esp = cena["esperado"]
        if esp == "correcao":
            ia = Aponta({"destino": "correcao", "sinal": "correcao", "destino_certo": ROTULO[cena["certo"]]})
        elif esp in ("nenhum", "corrente"):
            ia = Aponta({"destino": "nenhum", "sinal": "nenhum"})
        else:
            ia = Aponta({"destino": ROTULO[esp], "sinal": "proximidade"})
        wamid = "wm%d" % n
        passo(canal, s, texto(wamid, cena["texto"], numero=EQUIPE), agora=AGORA, ia=ia)
        r = _linha(canal, wamid)
        vistos = getattr(ia, "retratos", [])
        ok = {
            "corrente": lambda: not vistos and r is None,
            "nenhum": lambda: r is not None and r["destino"] is None and not r["aplicado"],
            "correcao": lambda: r is not None and r["sinal"] == "correcao"
            and (r["destino"] or "").startswith(cena.get("certo", "?") + ":") and r["aplicado"],
        }.get(esp, lambda: r is not None and r["aplicado"]
              and (r["destino"] or "").startswith(("foto" if esp == "foto_agora" else esp) + ":"))()
        if "foto_agora" in cena["abertos"] and esp == "foto":
            ok = ok and not vistos and r["sinal"] == "proximidade"   # a foto de 26 s vence sem a OlivIA
        if not ok:
            falhas.append((n, cena["texto"], esp, r and r["destino"], r and r["sinal"]))
        if vistos:
            rt = vistos[-1]
            retratos.append({"n": n, "texto": cena["texto"], "abertos": cena["abertos"], "esperado": esp,
                             "numero_esperado": _numero(rt, cena["certo"]) if esp == "correcao"
                             else (_numero(rt, esp) if esp not in ("nenhum", "corrente") else "nenhum"),
                             "retrato": rt})
    assert falhas == [], falhas
    assert len(retratos) == 28   # a foto de 26 s e o "bom dia" nao chegam a OlivIA
    if os.environ.get("AXIAATENDE_GRAVAR_MAQUETE") == "1":
        JSON.write_text(json.dumps(retratos, ensure_ascii=False, indent=1), encoding="utf-8")
