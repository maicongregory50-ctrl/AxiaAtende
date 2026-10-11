"""O vigia do endereco publico (#969, etapa 3, dono 11/10/2026).

Em 09/10/2026 o nome do Funnel (`serverrenascer.taild57672.ts.net`) deixou de existir no DNS
publico: a Meta nao achava o recepcionista, ninguem recebeu resposta por um dia e meio, e nada
avisou. De DENTRO do servidor o nome resolve pela rede do Tailscale mesmo sem existir la fora,
entao a conferencia pergunta a dois resolvedores publicos, por HTTPS.

Existindo o nome, ele abre a propria saude pelo IP publico que o resolvedor devolveu (a entrada do
Funnel), e assim ve tambem o nome existir e o Funnel nao repassar (reforco, dono 11/10/2026).

A cada 5 minutos. Dois "nao" seguidos = fora do ar: um aviso ao gestor (o mesmo da pergunta
"Nao"), pela fila de avisos, que SAI do servidor e nao depende do endereco. Quando volta, outro.
Nao conseguir perguntar (sem internet) nao e "fora": sem resposta, nao se afirma nada.

O QUE ELE NAO VE: a internet ou o servidor caidos (ele mora aqui). Para isso so um vigia de fora
(PROJETO.md, "Se o endereco publico cair"); o dono cria se houver outra queda.
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


def resolver(nome: str = NOME, http=None) -> tuple[bool | None, str | None]:
    """(True, ip): algum resolvedor publico devolve o endereco. (False, None): todos dizem que o nome
    nao existe. (None, None): nao deu para perguntar a todos (sem internet, resolvedor fora)."""
    respostas = []
    with (http or httpx.Client(timeout=10)) as c:
        for url in RESOLVEDORES:
            try:
                r = c.get(url, params={"name": nome, "type": "A"}, headers={"accept": "application/dns-json"}).json()
            except Exception:  # noqa: BLE001 -- resolvedor fora nao e nome fora
                respostas.append(None)
                continue
            if r.get("Status") == 0 and r.get("Answer"):
                ips = [a.get("data") for a in r["Answer"] if a.get("type", 1) == 1]
                return True, (ips[0] if ips else None)
            respostas.append(False if r.get("Status") in (0, 3) else None)
    return (False if all(x is False for x in respostas) else None), None


def existe(nome: str = NOME, http=None) -> bool | None:
    return resolver(nome, http)[0]


def responde(ip: str, nome: str = NOME, http=None) -> bool:
    """Abre a saude pelo IP PUBLICO da entrada do Funnel, com o nome no TLS: o pedido sai para a
    internet e volta, como o da Meta. Pelo nome ele iria pelo atalho da rede interna e nao provaria
    nada. Qualquer resposta HTTP serve (ate 503: o caminho chegou aqui); nao conectar e "nao"."""
    try:
        with (http or httpx.Client(timeout=15)) as c:
            c.get("https://%s/saude" % ip, headers={"host": nome}, extensions={"sni_hostname": nome})
        return True
    except Exception:  # noqa: BLE001
        return False


def confere(nome: str = NOME, resolver=resolver, responde=responde) -> bool | None:
    """A pergunta do vigia: o nome existe la fora E o Funnel repassa. Quem chegou a resolver o nome
    tem internet, entao nao conseguir abrir e "fora" (e so dois seguidos avisam)."""
    ha, ip = resolver(nome)
    if ha and ip:
        return responde(ip, nome)
    return ha


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
