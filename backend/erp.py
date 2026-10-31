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


# ── #1128: o pedido de CT-e da Logistica (LOG.CTE, fase609 do ERP) ────────────────────────────────

def _baixar(url: str, token: str) -> bytes:
    pedido = urllib.request.Request(url, method="GET")
    pedido.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(pedido, timeout=60) as r:   # noqa: S310 -- URL da config
        return r.read()


def logistica(cfg, janela: dict) -> dict:
    """Uma ida ao ERP com um token so: informa a janela de 24 h do destino da Logistica e traz os pedidos
    de CT-e pendentes. Devolve {"pendentes": [...], "token": ...} (o token serve as fichas e aos estados
    desta mesma volta, e nunca sai daqui). Fora do ar ou recusa: `ErpIndisponivel`."""
    if not cfg.erp_agente or not cfg.erp_segredo:
        raise ErpIndisponivel("a ligação com o ERP não está ligada")
    base = cfg.erp_url.rstrip("/")
    try:
        token = _token(cfg)
        _pedir(base + "/logistica/agente/janela", janela, token=token)
        return {"pendentes": _pedir(base + "/logistica/agente/pendentes", token=token), "token": token}
    except urllib.error.HTTPError as e:
        motivo = {401: "o ERP recusou o agente (segredo)", 403: "o agente está sem a permissão LOG.CTE",
                  404: "o ERP ainda não tem a Logística (#1128)"}
        raise ErpIndisponivel(motivo.get(e.code, "o ERP respondeu %d" % e.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    except (KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP respondeu algo inesperado") from None


def ficha_do_frete(cfg, token: str, frete_id: int) -> bytes:
    """O PDF da ficha do frete. Erro: `ErpIndisponivel`."""
    try:
        return _baixar(cfg.erp_url.rstrip("/") + "/logistica/agente/fretes/%d/ficha.pdf" % int(frete_id), token)
    except urllib.error.HTTPError as e:
        raise ErpIndisponivel("a ficha não veio (%d)" % e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None


def estado_do_pedido(cfg, token: str, pedido_id: int, estado: str, motivo: str = "", wamid: str = "") -> None:
    """Devolve ao ERP ENVIADO (com o wamid) ou FALHOU (com o motivo, em portugues). 404 = ja respondido."""
    corpo = {"estado": estado, "motivo": motivo[:500] or None, "ref_externa": wamid[:120] or None}
    try:
        _pedir(cfg.erp_url.rstrip("/") + "/logistica/agente/pedidos/%d/estado" % int(pedido_id), corpo, token=token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return
        raise ErpIndisponivel("o ERP respondeu %d" % e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None


def auditoria_pendentes(cfg) -> dict:
    """#350: os avisos de auditoria de estoque vencida que o ERP deixou PENDENTE, num token so.
    Devolve {"pendentes": [{"id", "partes": [filial, ultima lista]}], "token": ...}."""
    if not cfg.erp_agente or not cfg.erp_segredo:
        raise ErpIndisponivel("a ligação com o ERP não está ligada")
    base = cfg.erp_url.rstrip("/")
    try:
        token = _token(cfg)
        return {"pendentes": _pedir(base + "/relatorios/auditoria-estoque/agente/pendentes", token=token),
                "token": token}
    except urllib.error.HTTPError as e:
        motivo = {401: "o ERP recusou o agente (segredo)", 403: "o agente está sem a permissão AUD.AVISO",
                  404: "o ERP ainda não tem a auditoria de estoque (#350)"}
        raise ErpIndisponivel(motivo.get(e.code, "o ERP respondeu %d" % e.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    except (KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP respondeu algo inesperado") from None


def estado_do_aviso_auditoria(cfg, token: str, aviso_id: int, estado: str, motivo: str = "", wamid: str = "") -> None:
    """Devolve ao ERP ENVIADO ou FALHOU do aviso da auditoria. 404 = ja respondido."""
    corpo = {"estado": estado, "motivo": motivo[:500] or None, "ref_externa": wamid[:120] or None}
    try:
        _pedir(cfg.erp_url.rstrip("/") + "/relatorios/auditoria-estoque/agente/avisos/%d/estado" % int(aviso_id),
               corpo, token=token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return
        raise ErpIndisponivel("o ERP respondeu %d" % e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None


# ── #1222: o chamado no WhatsApp (as rotas /demandas/whatsapp do ERP, atividade SUP.WPP) ─────────

class ErpRecusou(ErpIndisponivel):
    """O ERP respondeu, e disse nao (403 numero errado, 400 o chamado nao esta na entrega). Nao adianta
    tentar de novo: a mensagem fica com o erro."""


def _whatsapp(url: str, corpo: dict | None, token: str) -> dict:
    try:
        return _pedir(url, corpo, token=token)
    except urllib.error.HTTPError as e:
        if e.code in (400, 403, 404, 422):
            try:
                detalhe = json.loads(e.read().decode("utf-8")).get("detail")
            except Exception:  # noqa: BLE001
                detalhe = None
            raise ErpRecusou(str(detalhe or "o ERP recusou (%d)" % e.code)[:300]) from None
        motivo = {401: "o ERP recusou o agente (segredo)"}
        raise ErpIndisponivel(motivo.get(e.code, "o ERP respondeu %d" % e.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    except (KeyError, ValueError, TypeError):
        raise ErpIndisponivel("o ERP respondeu algo inesperado") from None


def chamados_saida(cfg, depois: int | None) -> dict:
    """O que chegou aos autores depois do evento `depois`, num token so. Sem `depois`, so o cursor."""
    if not cfg.erp_agente or not cfg.erp_segredo:
        raise ErpIndisponivel("a ligação com o ERP não está ligada")
    base = cfg.erp_url.rstrip("/") + "/demandas/whatsapp"
    try:
        token = _token(cfg)
    except urllib.error.HTTPError:
        raise ErpIndisponivel("o ERP recusou o agente (segredo)") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErpIndisponivel("o ERP não respondeu") from None
    r = _whatsapp(base + "/saida" + ("" if depois is None else "?depois=%d" % int(depois)), None, token)
    return {"linhas": r["linhas"], "cursor": r["cursor"], "token": token}


def chamados_estado(cfg, token: str, ids: list[int]) -> list[dict]:
    if not ids:
        return []
    url = cfg.erp_url.rstrip("/") + "/demandas/whatsapp/estado?ids=" + ",".join(str(int(i)) for i in ids)
    return _whatsapp(url, None, token)["demandas"]


def chamado_resposta(cfg, token: str, demanda_id: int, numero: str, texto: str) -> None:
    _whatsapp(cfg.erp_url.rstrip("/") + "/demandas/whatsapp/%d/resposta" % int(demanda_id),
              {"numero": numero, "texto": texto}, token)


def chamado_validar(cfg, token: str, demanda_id: int, numero: str, resultado: str, motivo: str | None) -> None:
    _whatsapp(cfg.erp_url.rstrip("/") + "/demandas/whatsapp/%d/validar" % int(demanda_id),
              {"numero": numero, "resultado": resultado, "motivo": motivo}, token)
