"""Cria um usuario do AxiaAtende, ou troca a senha de um que ja existe. #950 (copia do AxiaMarketing #869).

A SENHA NUNCA VEM POR ARGUMENTO: argumento fica no historico do PowerShell e na lista de
processos. Ela e pedida duas vezes, sem aparecer na tela.

Em producao, rodar numa janela elevada (o arquivo de segredo do banco e fechado a
administrador):

    $env:AXIAATENDE_AMBIENTE = 'producao'
    python C:\\AxiaAtende\\scripts\\criar_usuario.py

Sem `AXIAATENDE_AMBIENTE`, o usuario nasce no banco de DESENVOLVIMENTO (5437).
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config, migracoes, seguranca  # noqa: E402
from backend.banco import conexao  # noqa: E402


def perguntar(texto: str) -> str:
    while True:
        valor = input(texto).strip()
        if valor:
            return valor


def main() -> int:
    cfg = config.carregar()
    print("Ambiente: %s (banco na porta %d)" % (cfg.ambiente, cfg.banco_porta))
    migracoes.aplicar(cfg)

    login = perguntar("Login (minusculas, sem espaco): ").lower()
    if " " in login:
        print("O login nao pode ter espaco.")
        return 1
    with conexao(cfg) as con:
        existente = con.execute("SELECT id, nome FROM casa.usuarios WHERE login = %s",
                                (login,)).fetchone()
    if existente:
        resposta = input("%s ja existe (%s). Trocar a senha? [s/N] "
                         % (login, existente["nome"])).strip().lower()
        if resposta != "s":
            print("Nada mudou.")
            return 0
        nome = existente["nome"]
    else:
        nome = perguntar("Nome para aparecer na tela: ")

    while True:
        senha = getpass.getpass("Senha (pelo menos %d caracteres, nao aparece): "
                                % seguranca.SENHA_MINIMA)
        if len(senha) < seguranca.SENHA_MINIMA:
            print("Curta demais.")
            continue
        if getpass.getpass("A mesma senha de novo: ") != senha:
            print("As duas nao conferem. De novo.")
            continue
        break

    digital = seguranca.gerar_hash(senha)
    with conexao(cfg) as con:
        if existente:
            con.execute("UPDATE casa.usuarios SET senha_hash = %s, ativo = true WHERE id = %s",
                        (digital, existente["id"]))
            # Senha trocada derruba as sessoes abertas com a senha antiga.
            con.execute("DELETE FROM casa.sessoes WHERE usuario_id = %s", (existente["id"],))
        else:
            con.execute("INSERT INTO casa.usuarios (login, nome, senha_hash)"
                        " VALUES (%s, %s, %s)", (login, nome, digital))
    print("Pronto: %s %s." % (login, "com senha nova" if existente else "criado"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
