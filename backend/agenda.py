"""A agenda do cadastro: quem ja e nosso, pelo numero. #969, etapa 1.

DOIS LADOS:
- `atualizar` (processo das TELAS, uma vez ao subir e todo dia as 06:00): le o ERP e troca a agenda
  inteira numa transacao. ERP fora do ar, ou agenda vazia: a de ontem continua, e o erro fica em
  `agenda_leitura` para a tela mostrar.
- `reconhecer` (RECEPCIONISTA, na chegada): procura o numero (com o 9, `com_nove`) e devolve o
  retrato que a conversa guarda. So REGISTRA: o motor nao muda de caminho por isso.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import erp
from .banco import conexao
from .envio import com_nove

FUSO = ZoneInfo("America/Sao_Paulo")
HORA_DA_LEITURA = 6


def atualizar(cfg, buscar=erp.agenda, agora: datetime | None = None) -> dict:
    """Le e grava. Devolve {"linhas": n} ou {"erro": motivo}. Sem o segredo, nem tenta."""
    agora = agora or datetime.now(timezone.utc)
    if not cfg.erp_segredo:
        return {"erro": "a leitura do cadastro não está ligada"}
    try:
        linhas = buscar(cfg)
        if not linhas:
            raise erp.ErpIndisponivel("o ERP devolveu a agenda vazia")
    except erp.ErpIndisponivel as e:
        with conexao(cfg) as con:
            con.execute("INSERT INTO atendimento.agenda_leitura (lida_em, linhas, erro) VALUES (%s, NULL, %s)",
                        (agora, str(e)))
        return {"erro": str(e)}
    with conexao(cfg) as con:
        with con.transaction():
            con.execute("DELETE FROM atendimento.agenda")
            with con.cursor() as cur:
                cur.executemany(
                    """INSERT INTO atendimento.agenda (numero, codigo, nome, papeis, contato_setor, contato_nome)
                       VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (numero, codigo) DO NOTHING""",
                    [(com_nove(l["numero"]), int(l["codigo"]), l.get("nome") or "", list(l.get("papeis") or []),
                      l.get("contato_setor") or "", l.get("contato_nome") or "") for l in linhas])
            con.execute("INSERT INTO atendimento.agenda_leitura (lida_em, linhas, erro) VALUES (%s, %s, '')",
                        (agora, len(linhas)))
    return {"linhas": len(linhas)}


def proxima_leitura(agora: datetime) -> datetime:
    local = agora.astimezone(FUSO)
    alvo = local.replace(hour=HORA_DA_LEITURA, minute=0, second=0, microsecond=0)
    if alvo <= local:
        alvo += timedelta(days=1)
    return alvo.astimezone(timezone.utc)


def ultima_leitura(con) -> dict | None:
    """A ultima leitura certa e, se a mais recente falhou, o erro dela."""
    certa = con.execute("""SELECT lida_em, linhas FROM atendimento.agenda_leitura WHERE erro = ''
                            ORDER BY lida_em DESC, id DESC LIMIT 1""").fetchone()
    ultima = con.execute("SELECT erro FROM atendimento.agenda_leitura ORDER BY lida_em DESC, id DESC LIMIT 1").fetchone()
    if not certa and not ultima:
        return None
    return {"lida_em": certa["lida_em"].isoformat() if certa else None,
            "linhas": certa["linhas"] if certa else 0,
            "erro": ultima["erro"] if ultima else ""}


def reconhecer(con, wa_id: str | None) -> dict | None:
    """O retrato para a conversa. None: a agenda nunca foi carregada (nao se afirma nada)."""
    if not con.execute("SELECT 1 FROM atendimento.agenda LIMIT 1").fetchone():
        return None
    achados = con.execute("SELECT * FROM atendimento.agenda WHERE numero = %s ORDER BY codigo",
                          (com_nove(wa_id or ""),)).fetchall()
    if len(achados) != 1:
        return {"erp_cadastros": len(achados), "erp_codigo": None, "erp_nome": None, "erp_papeis": None,
                "erp_contato_setor": None, "erp_contato_nome": None}
    a = achados[0]
    return {"erp_cadastros": 1, "erp_codigo": a["codigo"], "erp_nome": a["nome"], "erp_papeis": a["papeis"],
            "erp_contato_setor": a["contato_setor"], "erp_contato_nome": a["contato_nome"]}
