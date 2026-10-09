"""Senha e sessao. #950, copia do AxiaMarketing (#869). So biblioteca padrao.

SENHA: `scrypt`, com sal por usuario. O que se guarda e `scrypt$n$r$p$sal$hash`, para os
parametros poderem subir depois sem invalidar quem ja tem senha.

SESSAO: um token aleatorio vai no cookie; no banco fica so o sha256 dele. Nao ha chave de
assinatura, entao nao ha segredo de login para guardar, vazar ou rotacionar.

TENTATIVAS: cinco senhas erradas para o mesmo login trancam aquele login por cinco minutos.
A contagem mora na memoria do processo: reiniciar o servico zera, e esta certo -- sao ate
poucas pessoas, so no proprio servidor.
"""
import base64
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

N, R, P, TAMANHO = 2 ** 15, 8, 1, 32
SENHA_MINIMA = 10

MAX_ERROS = 5
TRANCA_SEGUNDOS = 300
_erros: dict[str, list[float]] = {}


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def gerar_hash(senha: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=N, r=R, p=P, dklen=TAMANHO,
                       maxmem=64 * 1024 * 1024)
    return "scrypt$%d$%d$%d$%s$%s" % (N, R, P, _b64(sal), _b64(h))


def conferir_senha(senha: str, guardado: str) -> bool:
    try:
        nome, n, r, p, sal, esperado = guardado.split("$")
        if nome != "scrypt":
            return False
        sal_b, esperado_b = base64.b64decode(sal), base64.b64decode(esperado)
        h = hashlib.scrypt(senha.encode("utf-8"), salt=sal_b, n=int(n), r=int(r), p=int(p),
                           dklen=len(esperado_b), maxmem=64 * 1024 * 1024)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(h, esperado_b)


# Conferido contra senha nenhuma quando o login nao existe: sem isso, login inexistente
# responderia mais rapido que senha errada, e o tempo diria quais logins existem.
_HASH_DE_NINGUEM = gerar_hash(secrets.token_urlsafe(24))


def gastar_tempo_de_senha(senha: str) -> None:
    conferir_senha(senha, _HASH_DE_NINGUEM)


def trancado(login: str) -> bool:
    agora = time.monotonic()
    recentes = [t for t in _erros.get(login, []) if agora - t < TRANCA_SEGUNDOS]
    _erros[login] = recentes
    return len(recentes) >= MAX_ERROS


def anotar_erro(login: str) -> None:
    _erros.setdefault(login, []).append(time.monotonic())


def limpar_erros(login: str) -> None:
    _erros.pop(login, None)


def novo_token() -> tuple[str, str]:
    """Devolve (token para o cookie, sha256 para o banco)."""
    token = secrets.token_urlsafe(32)
    return token, digital_do_token(token)


def digital_do_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", "replace")).hexdigest()


def abrir_sessao(con, usuario_id: int, horas: int) -> str:
    token, digital = novo_token()
    expira = datetime.now(timezone.utc) + timedelta(hours=horas)
    con.execute("DELETE FROM casa.sessoes WHERE expira_em < now()")
    con.execute("INSERT INTO casa.sessoes (token_sha256, usuario_id, expira_em)"
                " VALUES (%s, %s, %s)", (digital, usuario_id, expira))
    return token


def usuario_da_sessao(con, token: str | None):
    if not token:
        return None
    return con.execute(
        "SELECT u.id, u.login, u.nome FROM casa.sessoes s"
        " JOIN casa.usuarios u ON u.id = s.usuario_id"
        " WHERE s.token_sha256 = %s AND s.expira_em > now() AND u.ativo",
        (digital_do_token(token),)).fetchone()


def fechar_sessao(con, token: str | None) -> None:
    if token:
        con.execute("DELETE FROM casa.sessoes WHERE token_sha256 = %s",
                    (digital_do_token(token),))
