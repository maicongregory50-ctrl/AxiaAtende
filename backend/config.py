"""Configuracao do AxiaAtende. #950 (molde: `C:\\AxiaMarketing\\backend\\config.py`).

TRES AMBIENTES, escolhidos por `AXIAATENDE_AMBIENTE`:

- `producao`: banco na 5436, senha e chaves lidas de `.env.secrets` (fechado a administrador; os
  servicos rodam como conta de servico e leem). E o unico ambiente que fala com a Meta de verdade.
- `dev` (o padrao): banco na 5437, sem senha, so em 127.0.0.1.
- `teste`: como `dev`, em outro banco. A Meta e a Anthropic sao sempre FALSAS nos testes.

O PADRAO E `dev`, DE PROPOSITO. Quem esquece de dizer o ambiente cai no rascunho.

SEM SEGREDO NA SESSAO. A sessao de agente nao le `.env.secrets`; `dev` e `teste` nao tem senha.
Nenhum segredo entra em `repr`, log ou mensagem de erro.

DOIS PROCESSOS, DOIS ARQUIVOS DE SEGREDO (`AXIAATENDE_PROCESSO`):

- `telas` (o padrao; `backend/main.py`, 127.0.0.1:8009, LocalSystem): le `.env.secrets`, que so
  tem a senha do banco. NAO tem a chave da Meta nem a da Anthropic: as telas so gravam e leem o
  banco (o pedido de envio entra como fila).
- `recepcionista` (`backend/recepcionista.py`, 127.0.0.1:8008, LocalService, o unico exposto):
  le `.env.recepcionista`, com a senha do banco, o token da Meta, o segredo do app, o token de
  verificacao do webhook e a chave da Anthropic. E o UNICO processo que fala com a Meta: responde,
  manda convite, imagem e aviso. Mesmo desenho do publicador do AxiaMarketing (D14 do #923).

A CHAVE QUE MAIS IMPORTA E `responde`. Com ela `False` (o padrao, inclusive em producao) o
recepcionista grava tudo o que chega e NAO responde ninguem (regra 2 do CLAUDE.md): enquanto o
Opa atende o numero, responder faria o cliente receber duas respostas. Ela so liga pela linha
`ATENDE_RESPONDE=true` no `.env.secrets`, no ensaio e na troca do dia (Fase H do plano).
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# A versao da Graph API fica fixa; trocar e decisao, nao acidente (a mesma do AxiaMarketing).
META_VERSAO = "v23.0"
META_URL = "https://graph.facebook.com"
# O numero 49 3664 0121 e a conta do WhatsApp (medidos no A1 do plano, 09/10/2026). Nao sao segredo.
META_PHONE_ID = "725888737278277"
META_CONTA_WA = "1442233593867052"
ANTHROPIC_URL = "https://api.anthropic.com"

AMBIENTES = ("producao", "dev", "teste")
# o processo e o arquivo de segredo que ele le em producao
PROCESSOS = {"telas": ".env.secrets", "recepcionista": ".env.recepcionista"}


@dataclass(frozen=True)
class Config:
    ambiente: str
    banco_host: str
    banco_porta: int
    banco_nome: str
    banco_usuario: str
    banco_senha: str = field(repr=False)
    processo: str = "telas"
    # A chave do pedido de envio: so o publicador do AxiaMarketing a tem (o instalador a escreve
    # nos dois lados). Sem ela, a API de pedido recusa: convite e mensagem paga.
    chave_pedido: str = field(default="", repr=False)
    # As imagens de cada envio, copiadas do Marketing para ca, onde o recepcionista (LocalService) le.
    envios_pasta: Path = Path(r"C:\Dados\AxiaAtende\envios")
    logs: Path = Path(r"C:\Logs\AxiaAtende")
    tela: Path = RAIZ / "frontend" / "dist"
    cookie_seguro: bool = False
    sessao_horas: int = 12
    # Meta (app `axiaatende`, token SO de WhatsApp). Fora do repr.
    meta_url: str = META_URL
    meta_versao: str = META_VERSAO
    meta_phone_id: str = META_PHONE_ID
    meta_conta_wa: str = META_CONTA_WA
    meta_token: str = field(default="", repr=False)
    meta_app_secret: str = field(default="", repr=False)    # confere a assinatura dos avisos
    meta_verify_token: str = field(default="", repr=False)  # o aperto de mao do webhook
    # Anthropic (chave PROPRIA do AxiaAtende, com teto). Sem ela, quem escreve recebe o menu.
    anthropic_url: str = ANTHROPIC_URL
    anthropic_chave: str = field(default="", repr=False)
    responde: bool = False
    # O ENSAIO (#950, H1): o Opa so desliga pelo suporte dele, entao no ensaio o recepcionista
    # responde SO a estes numeros (`ATENDE_SO_PARA=5549...,5549...`) e grava os outros em escuta.
    # Vazio = responde a todos (a troca de verdade).
    responde_so_para: tuple = ()

    def dsn(self) -> str:
        partes = ["host=%s" % self.banco_host, "port=%d" % self.banco_porta,
                  "dbname=%s" % self.banco_nome, "user=%s" % self.banco_usuario]
        if self.banco_senha:
            partes.append("password=%s" % self.banco_senha)
        return " ".join(partes)


def _ler_segredos(caminho: Path) -> dict:
    """Le `CHAVE=valor` por linha. Arquivo ausente ou ilegivel devolve vazio, e quem chama
    decide se isso e erro. `utf-8-sig` porque um BOM na primeira linha faria a primeira chave
    nao ser achada, em silencio."""
    try:
        texto = caminho.read_text(encoding="utf-8-sig")
    except OSError:
        return {}
    saida = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        saida[chave.strip()] = valor.strip()
    return saida


def carregar(ambiente: str | None = None, **trocas) -> Config:
    ambiente = ambiente or os.environ.get("AXIAATENDE_AMBIENTE", "dev")
    if ambiente not in AMBIENTES:
        raise RuntimeError("AXIAATENDE_AMBIENTE=%r nao existe; use um de %s"
                           % (ambiente, ", ".join(AMBIENTES)))

    processo = os.environ.get("AXIAATENDE_PROCESSO", "telas")
    if processo not in PROCESSOS:
        raise RuntimeError("AXIAATENDE_PROCESSO=%r nao existe; use um de %s"
                           % (processo, ", ".join(PROCESSOS)))
    if ambiente == "producao":
        arquivo = PROCESSOS[processo]
        segredos = _ler_segredos(RAIZ / arquivo)
        senha = segredos.get("AXIAATENDE_BANCO_SENHA", "")
        if not senha:
            # Falha aqui, dizendo o que falta e sem dizer valor nenhum.
            raise RuntimeError("producao sem AXIAATENDE_BANCO_SENHA em %s" % arquivo)
        if processo == "telas":
            # As telas nunca carregam chave de fora, mesmo que alguem as escreva no arquivo.
            segredos = {"AXIAATENDE_BANCO_SENHA": senha,
                        "AXIAATENDE_CHAVE_PEDIDO": segredos.get("AXIAATENDE_CHAVE_PEDIDO", "")}
        base = dict(
            banco_porta=5436, banco_nome="axiaatende", banco_usuario="axiaatende_app",
            banco_senha=senha,
            meta_token=segredos.get("META_TOKEN", ""),
            meta_app_secret=segredos.get("META_APP_SECRET", ""),
            meta_verify_token=segredos.get("META_VERIFY_TOKEN", ""),
            anthropic_chave=segredos.get("ANTHROPIC_API_KEY", ""),
            chave_pedido=segredos.get("AXIAATENDE_CHAVE_PEDIDO", ""),
            responde=segredos.get("ATENDE_RESPONDE", "false").lower() == "true",
            responde_so_para=tuple(n.strip() for n in segredos.get("ATENDE_SO_PARA", "").split(",") if n.strip()),
            # `AXIAATENDE_SAIDA`: `local` (o padrao: as telas so em http://127.0.0.1:8009).
            cookie_seguro=os.environ.get("AXIAATENDE_SAIDA", "local") == "vpn",
        )
    else:
        base = dict(
            banco_porta=5437,
            # AXIAATENDE_BANCO_TESTE: outro banco de teste na mesma instancia, para duas sessoes
            # rodarem a bateria ao mesmo tempo sem uma apagar o esquema da outra.
            banco_nome="axiaatende_dev" if ambiente == "dev"
            else os.environ.get("AXIAATENDE_BANCO_TESTE", "axiaatende_teste"),
            banco_usuario="axiaatende_su", banco_senha="",
            logs=Path(os.environ.get("AXIAATENDE_LOGS",
                                     r"C:\Dados\AxiaAtende\%s\logs" % ambiente)),
            envios_pasta=Path(r"C:\Dados\AxiaAtende\%s\envios" % ambiente),
        )
    if ambiente == "producao" and os.environ.get("AXIAATENDE_LOGS"):
        base["logs"] = Path(os.environ["AXIAATENDE_LOGS"])   # o recepcionista escreve so no dele
    base.update(ambiente=ambiente, banco_host="127.0.0.1", processo=processo)
    base.update(trocas)
    return Config(**base)
