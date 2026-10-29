"""A leitura do cadastro no ERP, pela porta de agente. #969.

`POST /auth/agente` (o agente ATENDIMENTO, fase551, com o segredo de `.env.secrets`) e
`GET /atendimento/agenda` (STK.R): numero, codigo, nome, papeis e contato de cada cadastro com
celular valido. Molde: `C:\\AxiaMarketing\\backend\\erp.py`.

SO O PROCESSO DAS TELAS le o ERP: o recepcionista, que a internet alcanca, nunca carrega este
segredo (config.py). SEM A CHAVE, NEM TENTA. O segredo nunca entra em mensagem, `repr` nem log.
"""
import json
import urllib.error
import urllib.request

TEMPO = 30


class ErpIndisponivel(RuntimeError):
    pass


def _pedir(url: str, corpo: dict | None = None, token: str = "") -> dict:
    dados = json.dumps(corpo).encode() if corpo is not None else None
    pedido = urllib.request.Request(url, data=dados, method="POST" if corpo is not None else "GET")
    pedido.add_header("Accept", "application/json")
    if dados is not None:
        pedido.add_header("Content-Type", "application/json")
    if token:
        pedido.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(pedido, timeout=TEMPO) as r:   # noqa: S310 -- URL da config
        return json.loads(r.read().decode("utf-8"))


def agenda(cfg) -> list[dict]:
    """As linhas da agenda. Fora do ar, recusa ou resposta estranha: `ErpIndisponivel`, com o
    motivo em portugues e sem o segredo."""
    if not cfg.erp_agente or not cfg.erp_segredo:
        raise ErpIndisponivel("a leitura do cadastro não está ligada")
    base = cfg.erp_url.rstrip("/")
    try:
        token = _pedir(base + "/auth/agente", {"agente": cfg.erp_agente, "segredo": cfg.erp_segredo,
                                               "minutos": 5})["access_token"]
        return _pedir(base + "/atendimento/agenda", token=token)["linhas"]
    except urllib.error.HTTPError as e:
        motivo = {401: "o ERP recusou o agente (segredo)", 403: "o agente está sem permissão ou desligado"}
        raise ErpIndisponivel(motivo.get(e.code, "o ERP respondeu %d" % e.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    except (KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP respondeu algo que não é a agenda") from None


def empurrar_eventos(cfg, eventos: list[dict]) -> dict:
    """#1090: empurra ao Relacionamento do ERP o estado de cada mensagem enviada a um cliente, pelo
    MESMO agente e o MESMO segredo da agenda (CRM.EVT.W, fase575). O ERP e idempotente: o mesmo lote
    duas vezes nao duplica, e o estado so avanca. Fora do ar ou recusa: `ErpIndisponivel`."""
    if not cfg.erp_agente or not cfg.erp_segredo:
        raise ErpIndisponivel("a ligação com o ERP não está ligada")
    base = cfg.erp_url.rstrip("/")
    try:
        token = _pedir(base + "/auth/agente", {"agente": cfg.erp_agente, "segredo": cfg.erp_segredo,
                                               "minutos": 5})["access_token"]
        return _pedir(base + "/relacionamento/eventos-envio", {"eventos": eventos}, token=token)
    except urllib.error.HTTPError as e:
        motivo = {401: "o ERP recusou o agente (segredo)", 403: "o agente está sem a permissão CRM.EVT.W",
                  404: "o ERP ainda não tem o Relacionamento"}
        raise ErpIndisponivel(motivo.get(e.code, "o ERP respondeu %d" % e.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    except (KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP respondeu algo inesperado") from None


def retomadas(cfg, depois: int) -> list[dict]:
    """#1193: as retomadas que uma pessoa registrou no Relacionamento do ERP depois de falar com o
    cliente, com id maior que `depois` (ate 200 por vez). O MESMO agente e o MESMO segredo dos eventos
    (CRM.EVT.W). Fora do ar ou recusa: `ErpIndisponivel`."""
    if not cfg.erp_agente or not cfg.erp_segredo:
        raise ErpIndisponivel("a ligação com o ERP não está ligada")
    base = cfg.erp_url.rstrip("/")
    try:
        token = _pedir(base + "/auth/agente", {"agente": cfg.erp_agente, "segredo": cfg.erp_segredo,
                                               "minutos": 5})["access_token"]
        return _pedir(base + "/relacionamento/retomadas?depois=%d" % int(depois), token=token)["retomadas"]
    except urllib.error.HTTPError as e:
        motivo = {401: "o ERP recusou o agente (segredo)", 403: "o agente está sem a permissão CRM.EVT.W",
                  404: "o ERP ainda não tem as retomadas (#1193)"}
        raise ErpIndisponivel(motivo.get(e.code, "o ERP respondeu %d" % e.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    except (KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP respondeu algo que não são as retomadas") from None


# ── #1090 etapa 3: "Meus clientes" (CRM.WPP, fase586 do ERP) ──────────────────────────────────────

class ErpRecusou(ValueError):
    """O ERP leu o registro e recusou, com a frase da tela (422/403/404). Nao adianta mandar de novo."""


def _token(cfg) -> str:
    base = cfg.erp_url.rstrip("/")
    return _pedir(base + "/auth/agente", {"agente": cfg.erp_agente, "segredo": cfg.erp_segredo,
                                         "minutos": 5})["access_token"]


def _frase(e: urllib.error.HTTPError) -> str:
    try:
        d = json.loads(e.read().decode("utf-8")).get("detail")
        return d if isinstance(d, str) else "o ERP recusou (%d)" % e.code
    except Exception:   # noqa: BLE001 -- sem corpo legivel, o codigo
        return "o ERP recusou (%d)" % e.code


def fila_do_consultor(cfg, comercial_id: int, limite: int = 60) -> dict:
    """A fila do consultor com a ficha de cada cliente. Fora do ar ou sem permissao: `ErpIndisponivel`."""
    if not cfg.erp_agente or not cfg.erp_segredo:
        raise ErpIndisponivel("a ligação com o ERP não está ligada")
    base = cfg.erp_url.rstrip("/")
    try:
        return _pedir(base + "/relacionamento/agente/fila?comercial=%d&limite=%d" % (int(comercial_id), int(limite)),
                      token=_token(cfg))
    except urllib.error.HTTPError as e:
        motivo = {401: "o ERP recusou o agente (segredo)", 403: "o agente está sem a permissão CRM.WPP",
                  404: _frase(e)}
        raise ErpIndisponivel(motivo.get(e.code, "o ERP respondeu %d" % e.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    except (KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP respondeu algo inesperado") from None


def registrar_contato(cfg, corpo: dict) -> dict:
    """Grava no Relacionamento o contato que o consultor conferiu. 422/403/404: `ErpRecusou` com a frase;
    fora do ar, 401 ou sem a permissao: `ErpIndisponivel` (tenta de novo depois)."""
    if not cfg.erp_agente or not cfg.erp_segredo:
        raise ErpIndisponivel("a ligação com o ERP não está ligada")
    base = cfg.erp_url.rstrip("/")
    try:
        token = _token(cfg)
    except urllib.error.HTTPError as e:
        raise ErpIndisponivel("o ERP recusou o agente (%d)" % e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    try:
        return _pedir(base + "/relacionamento/agente/contatos", corpo, token=token)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404, 422):
            frase = _frase(e)
            if "permiss" in frase.lower() or "atividade" in frase.lower():
                raise ErpIndisponivel(frase) from None   # "Atividade CRM.WPP nao atribuida": espera o dono
            raise ErpRecusou(frase) from None
        raise ErpIndisponivel("o ERP respondeu %d" % e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    except (KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP respondeu algo inesperado") from None
