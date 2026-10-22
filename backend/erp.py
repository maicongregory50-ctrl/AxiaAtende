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
