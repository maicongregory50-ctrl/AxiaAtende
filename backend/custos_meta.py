"""O que a Meta diz ter cobrado, por dia e categoria: a conferencia diaria da tela Custos. #1223.

A conta da tela e NOSSA: a quantidade cobrada vem do `pricing` de cada aviso de status (eventos_meta) e o
valor e quantidade x preco da tabela. Esta conferencia e a outra metade (decisao do dono, 31/10/2026):
uma vez por dia o recepcionista -- o unico processo com o token da Meta -- pergunta a API de analise de
precos da conta quanto foi cobrado nos ultimos 3 dias, e a tela mostra "calculado x cobrado".

So GET, uma chamada por dia. Os 3 dias sao relidos a cada vez (upsert) porque a Meta fecha o dia com
atraso: o "ontem" de hoje pode mudar amanha.

NUNCA GRAVA ZERO ONDE NAO LEU: permissao negada vira `sem_acesso`, qualquer outra falha (rede, forma
inesperada da resposta) vira `erro` com o detalhe, nos tres dias. A chave `custos.conferir_meta` em
`atendimento.ajustes` desliga a conferencia sem restart.
"""
from datetime import date, datetime, time, timedelta, timezone

import httpx

from .motor import _ajuste

DIAS = 3
HORA = 6   # depois das 06:00 (hora do servidor): a Meta ja fechou boa parte de ontem


def _cliente(cfg) -> httpx.Client:
    return httpx.Client(base_url="%s/v%s" % (cfg.meta_url, cfg.meta_versao.lstrip("v")),
                        headers={"Authorization": "Bearer " + cfg.meta_token}, timeout=60)


def ja_conferiu_hoje(con, hoje: date) -> bool:
    r = con.execute("SELECT max(lido_em) AS m FROM atendimento.meta_conferencia").fetchone()
    return bool(r and r["m"] and r["m"].astimezone().date() >= hoje)


def deve_conferir(con, momento: datetime) -> bool:
    local = momento.astimezone()
    if local.hour < HORA or _ajuste(con, "custos.conferir_meta", False) is not True:
        return False
    return not ja_conferiu_hoje(con, local.date())


def _dias(hoje: date) -> list[date]:
    return [hoje - timedelta(days=n) for n in range(DIAS, 0, -1)]


def ler(cfg, hoje: date, http=None) -> dict:
    """{"situacao": "ok"|"sem_acesso"|"erro", "detalhe": str, "moeda": str, "linhas": [(dia, cat, volume, custo)]}."""
    dias = _dias(hoje)
    inicio = int(datetime.combine(dias[0], time(), timezone.utc).timestamp())
    fim = int(datetime.combine(hoje, time(), timezone.utc).timestamp())
    campos = ("currency,pricing_analytics.start(%d).end(%d).granularity(DAILY)"
              '.dimensions(["PRICING_CATEGORY"])' % (inicio, fim))
    try:
        with (http or _cliente(cfg)) as c:
            r = c.get("/%s" % cfg.meta_conta_wa, params={"fields": campos})
    except httpx.HTTPError as e:
        return {"situacao": "erro", "detalhe": "a Meta nao respondeu (%s)" % type(e).__name__, "moeda": "", "linhas": []}
    try:
        corpo = r.json()
    except ValueError:
        corpo = {}
    if r.status_code != 200:
        erro = corpo.get("error", {}) if isinstance(corpo, dict) else {}
        msg = "%s %s" % (erro.get("code", r.status_code), (erro.get("message") or "")[:160])
        # 10 = sem permissao; 200-299 = permissao da API; 190 = token; 403 = proibido
        sem = r.status_code == 403 or erro.get("code") in (10, 190) or 200 <= int(erro.get("code") or 0) < 300
        return {"situacao": "sem_acesso" if sem else "erro", "detalhe": msg.strip(), "moeda": "", "linhas": []}
    try:
        pontos = []
        for bloco in corpo["pricing_analytics"]["data"]:
            pontos.extend(bloco.get("data_points") or [])
        linhas = []
        for p in pontos:
            dia = datetime.fromtimestamp(int(p["start"]), timezone.utc).date()
            linhas.append((dia, str(p.get("pricing_category") or "?").lower(), int(p.get("volume") or 0),
                           float(p.get("cost") or 0)))
    except (KeyError, TypeError, ValueError) as e:
        return {"situacao": "erro", "detalhe": "resposta da Meta em forma inesperada (%s)" % type(e).__name__,
                "moeda": "", "linhas": []}
    return {"situacao": "ok", "detalhe": "", "moeda": str(corpo.get("currency") or ""), "linhas": linhas}


def gravar(con, hoje: date, lido: dict, momento: datetime) -> None:
    """Os tres dias sempre ganham a linha da conferencia; o cobrado so quando a leitura deu certo."""
    for dia in _dias(hoje):
        con.execute(
            """INSERT INTO atendimento.meta_conferencia (dia, situacao, detalhe, lido_em) VALUES (%s, %s, %s, %s)
               ON CONFLICT (dia) DO UPDATE SET situacao = EXCLUDED.situacao, detalhe = EXCLUDED.detalhe,
                                               lido_em = EXCLUDED.lido_em""",
            (dia, lido["situacao"], lido["detalhe"], momento))
        if lido["situacao"] == "ok":
            con.execute("DELETE FROM atendimento.meta_cobrado WHERE dia = %s", (dia,))
    if lido["situacao"] == "ok":
        for dia, cat, volume, custo in lido["linhas"]:
            con.execute(
                """INSERT INTO atendimento.meta_cobrado (dia, categoria, volume, custo, moeda, lido_em) VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (dia, categoria) DO UPDATE SET volume = atendimento.meta_cobrado.volume + EXCLUDED.volume,
                                                              custo = atendimento.meta_cobrado.custo + EXCLUDED.custo""",
                (dia, cat, volume, custo, lido["moeda"], momento))


def conferir(cfg, con, momento: datetime, http=None) -> str | None:
    """Chamado a cada minuto pela rotina do recepcionista; trabalha uma vez por dia. Devolve a situacao."""
    if not cfg.meta_token or not deve_conferir(con, momento):
        return None
    hoje = momento.astimezone().date()
    lido = ler(cfg, hoje, http)
    gravar(con, hoje, lido, momento)
    return lido["situacao"]
