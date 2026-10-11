"""O vigia do endereco publico (#969, etapa 3, dono 11/10/2026).

Em 09/10/2026 o nome do Funnel (`serverrenascer.taild57672.ts.net`) deixou de existir no DNS
publico: a Meta nao achava o recepcionista, ninguem recebeu resposta por um dia e meio, e nada
avisou. De DENTRO do servidor o nome resolve pela rede do Tailscale mesmo sem existir la fora,
entao a conferencia pergunta a dois resolvedores publicos, por HTTPS.

A cada 5 minutos. Dois "nao existe" seguidos = fora do ar: um aviso ao gestor (o mesmo da pergunta
"Nao"), pela fila de avisos, que SAI do servidor e nao depende do endereco. Quando volta, outro.
Nao conseguir perguntar (sem internet) nao e "fora": sem resposta, nao se afirma nada.

O QUE ELE NAO VE: o nome existir e o Funnel nao repassar; a internet ou o servidor caidos (ele mora
aqui). Para isso serve o vigia de fora (PROJETO.md, "Se eu cair").
"""
from datetime import datetime, timedelta
from urllib.parse import urlparse

import httpx

from .modelos_meta import ENDERECO_FALAR
from .motor import FUSO, _ajuste

NOME = urlparse(ENDERECO_FALAR).hostname
RESOLVEDORES = ("https://dns.google/resolve", "https://cloudflare-dns.com/dns-query")
INTERVALO = timedelta(minutes=5)
FALHAS_PARA_AVISAR = 2


def existe(nome: str = NOME, http=None) -> bool | None:
    """True: algum resolvedor publico devolve o endereco. False: todos dizem que o nome nao existe.
    None: nao deu para perguntar a todos (sem internet, resolvedor fora): nao se afirma nada."""
    respostas = []
    with (http or httpx.Client(timeout=10)) as c:
        for url in RESOLVEDORES:
            try:
                r = c.get(url, params={"name": nome, "type": "A"}, headers={"accept": "application/dns-json"}).json()
            except Exception:  # noqa: BLE001 -- resolvedor fora nao e nome fora
                respostas.append(None)
                continue
            if r.get("Status") == 0 and r.get("Answer"):
                return True
            respostas.append(False if r.get("Status") in (0, 3) else None)
    return False if all(x is False for x in respostas) else None


def estado(con) -> dict | None:
    r = con.execute("SELECT situacao, desde, falhas, conferido_em FROM atendimento.vigia_endereco").fetchone()
    return dict(r) if r else None


def _avisar(con, tipo: str, partes: list[str]) -> None:
    quem = con.execute("SELECT nome, whatsapp FROM atendimento.destinos WHERE id = %s",
                       (_ajuste(con, "avisado_no_nao"),)).fetchone()
    if quem:
        con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre)
                       VALUES (%s, %s, %s, %s)""", (tipo, quem["nome"], quem["whatsapp"], "|".join(partes)))


def _hora(quando: datetime) -> str:
    return quando.astimezone(FUSO).strftime("%d/%m %H:%M")


def _duracao(d: timedelta) -> str:
    minutos = max(1, int(d.total_seconds() // 60))
    return "%d min" % minutos if minutos < 60 else "%dh%02d" % divmod(minutos, 60)


def venceu(con, agora: datetime) -> bool:
    e = estado(con)
    return e is None or e["conferido_em"] is None or agora - e["conferido_em"] >= INTERVALO


def anotar(con, resposta: bool | None, agora: datetime) -> None:
    """Grava o que a conferencia viu e poe o aviso na fila quando a situacao muda."""
    e = estado(con) or {"situacao": "no_ar", "desde": agora, "falhas": 0}
    situacao, desde, falhas = e["situacao"], e["desde"], e["falhas"]
    if resposta is True:
        if situacao == "fora":
            _avisar(con, "endereco_voltou", [NOME, _hora(agora), _duracao(agora - desde)])
            situacao, desde = "no_ar", agora
        falhas = 0
    elif resposta is False:
        falhas += 1
        if situacao == "no_ar" and falhas >= FALHAS_PARA_AVISAR:
            situacao, desde = "fora", agora
            _avisar(con, "endereco_fora", [NOME, _hora(agora)])
    con.execute("""INSERT INTO atendimento.vigia_endereco (situacao, desde, falhas, conferido_em)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (unica) DO UPDATE SET situacao = EXCLUDED.situacao, desde = EXCLUDED.desde,
                       falhas = EXCLUDED.falhas, conferido_em = EXCLUDED.conferido_em""",
                (situacao, desde, falhas, agora))
