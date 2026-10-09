"""As mudancas do banco do atendimento, aplicadas pelo proprio servico ao subir. #950.

Molde: `C:\\AxiaMarketing\\backend\\migracoes.py` (#869). A Porta-Acao da casa conhece as fases do
ERP e os cinco servicos dela; o banco do atendimento nao esta no catalogo. Cada mudanca e um
arquivo `NNN_assunto.sql` em `backend/migracoes/`, com o `NNN_assunto_VOLTA.sql` ao lado.

TRES REGRAS:

1. **Cada mudanca e uma transacao.** Ou entra inteira, com a linha em `casa.mudancas`, ou nao
   entra. O arquivo NAO escreve BEGIN nem COMMIT: quem abre e fecha e este modulo.
2. **Mudanca aplicada nao se edita.** O sha256 do arquivo e gravado; se o arquivo mudar
   depois, o servico NAO sobe, e diz qual. Conserto e mudanca nova.
3. **O `_VOLTA.sql` nunca e aplicado sozinho.** Ele existe para a mao de quem desfaz.
"""
import hashlib
import re
from pathlib import Path

from .banco import conexao
from .config import Config

PASTA = Path(__file__).resolve().parent / "migracoes"
NOME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
TRAVA = 950001   # pg_advisory_xact_lock: dois processos subindo juntos nao aplicam a mesma mudanca


class MudancaAlterada(RuntimeError):
    pass


def listar() -> list[Path]:
    arquivos = [p for p in PASTA.glob("*.sql")
                if NOME.match(p.name) and not p.name.endswith("_VOLTA.sql")]
    return sorted(arquivos, key=lambda p: p.name)


def _ler(arquivo: Path) -> str:
    # Le os bytes e normaliza o fim de linha: o git do Windows pode trocar LF por CRLF no
    # checkout, e o sha256 de uma mudanca aplicada nao pode depender disso.
    return arquivo.read_bytes().decode("utf-8").replace("\r\n", "\n")


def aplicar(cfg: Config) -> list[str]:
    """Aplica o que falta e devolve os nomes aplicados AGORA (vazio = nada a fazer)."""
    with conexao(cfg) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS casa")
        con.execute(
            "CREATE TABLE IF NOT EXISTS casa.mudancas ("
            " nome text PRIMARY KEY,"
            " sha256 text NOT NULL,"
            " aplicada_em timestamptz NOT NULL DEFAULT now())")

    aplicadas_agora = []
    for arquivo in listar():
        sql = _ler(arquivo)
        digital = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        with conexao(cfg) as con:
            con.execute("SELECT pg_advisory_xact_lock(%s)", (TRAVA,))
            ja = con.execute("SELECT sha256 FROM casa.mudancas WHERE nome = %s",
                             (arquivo.name,)).fetchone()
            if ja:
                if ja["sha256"] != digital:
                    raise MudancaAlterada(
                        "a mudanca %s ja foi aplicada e o arquivo foi alterado depois; "
                        "conserto e mudanca nova, com numero novo" % arquivo.name)
                continue
            con.execute(sql)
            con.execute("INSERT INTO casa.mudancas (nome, sha256) VALUES (%s, %s)",
                        (arquivo.name, digital))
            aplicadas_agora.append(arquivo.name)
    return aplicadas_agora
