"""O RECEPCIONISTA: o unico processo do AxiaAtende que a internet alcanca. #950, Fase D.

    python -m uvicorn backend.recepcionista:app --host 127.0.0.1 --port 8008

Publicado pelo Funnel do Tailscale em :443 (G5 do plano). Roda como LocalService e le so o
`.env.recepcionista` (config.py).

O QUE ELE FAZ, E SO ISSO:
1. `GET /webhook`: o aperto de mao da Meta (hub.verify_token -> hub.challenge).
2. `POST /webhook`: confere a assinatura `X-Hub-Signature-256` com o segredo do app (sem
   segredo, ou assinatura errada, recusa), grava cada mensagem e cada status em
   `atendimento.eventos_meta` pela chave da Meta (a Meta reenvia por 7 dias: o repetido nao
   entra de novo) e responde 200 na hora. NADA e respondido dentro do pedido da Meta.
3. Um trabalhador, no mesmo processo, le os eventos pendentes, um por um, e chama o motor.
   A cada minuto faz as perguntas das 4h30 vencidas e marca quem parou no meio.

EM ESCUTA (`responde` = False, o padrao): grava tudo e NAO responde ninguem. Enquanto o Opa
atende o numero, responder faria o cliente receber duas respostas (regra 2 do CLAUDE.md).
"""
import hashlib
import hmac
import json
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from . import config, migracoes, motor
from .banco import conexao

LOTE = 20


def assinatura_confere(segredo: str, corpo: bytes, cabecalho: str | None) -> bool:
    if not segredo or not cabecalho or not cabecalho.startswith("sha256="):
        return False
    esperado = hmac.new(segredo.encode("utf-8"), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, cabecalho[7:])


def separar(aviso: dict) -> list[tuple[str, str, str | None, dict]]:
    """Um aviso da Meta em eventos: (chave, tipo, bsuid, corpo)."""
    eventos = []
    for entrada in aviso.get("entry", []):
        for mudanca in entrada.get("changes", []):
            if mudanca.get("field") != "messages":
                continue
            valor = mudanca.get("value", {})
            for msg in valor.get("messages", []):
                contatos = valor.get("contacts", [])
                bsuid = next((c.get("user_id") for c in contatos if c.get("user_id")), None)
                eventos.append((msg["id"], "mensagem", bsuid, {"contacts": contatos, "msg": msg}))
            for st in valor.get("statuses", []):
                eventos.append(("%s:%s" % (st["id"], st.get("status")), "status",
                                st.get("recipient_user_id"), st))
    return eventos


def gravar(cfg: config.Config, aviso: dict) -> int:
    novos = 0
    with conexao(cfg) as con:
        for chave, tipo, bsuid, corpo in separar(aviso):
            novos += con.execute(
                """INSERT INTO atendimento.eventos_meta (chave_meta, tipo, bsuid, corpo)
                   VALUES (%s, %s, %s, %s) ON CONFLICT (chave_meta) DO NOTHING""",
                (chave, tipo, bsuid, json.dumps(corpo))).rowcount
    return novos


STATUS = {"sent": "enviada", "delivered": "entregue", "read": "lida", "failed": "falhou"}
ORDEM = ["aceita", "enviada", "entregue", "lida"]


def aplicar_status(con, st: dict, agora: datetime, envio=None) -> None:
    novo = STATUS.get(st.get("status"))
    if not novo:
        return
    erro = "; ".join("%s %s" % (x.get("code", ""), x.get("title", "")) for x in st.get("errors", []))
    linha = con.execute("SELECT id, status FROM atendimento.enviadas WHERE wamid = %s", (st["id"],)).fetchone()
    # status chega fora de ordem: "lida" pode chegar antes de "entregue". So se avanca.
    atual = linha["status"] if linha else None
    avanca = linha is not None and (novo == "falhou" or (
        atual in ORDEM and novo in ORDEM and ORDEM.index(novo) > ORDEM.index(atual)))
    if avanca:
        con.execute("UPDATE atendimento.enviadas SET status = %s, status_em = %s, erro = %s WHERE id = %s",
                    (novo, agora, erro, linha["id"]))
    if envio is not None:
        envio.aplicar_status(con, st, novo, erro, agora)


def processar_pendentes(cfg: config.Config, saida, ia=None, envio=None, agora: datetime | None = None) -> int:
    """Processa ate LOTE eventos, cada um na sua transacao. Devolve quantos."""
    feitos = 0
    for _ in range(LOTE):
        with conexao(cfg) as con:
            ev = con.execute("""SELECT * FROM atendimento.eventos_meta WHERE processado_em IS NULL
                                 ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED""").fetchone()
            if not ev:
                return feitos
            momento = agora or datetime.now(timezone.utc)
            erro = ""
            try:
                with con.transaction():
                    if ev["tipo"] == "status":
                        aplicar_status(con, ev["corpo"], momento, envio)
                    elif ev["tipo"] == "mensagem" and not cfg.responde:
                        erro = "escuta"   # gravado, e ninguem respondido (regra 2)
                    elif ev["tipo"] == "mensagem":
                        corpo = ev["corpo"]
                        entrada = motor.ler_mensagem({"contacts": corpo["contacts"]}, corpo["msg"])
                        motor.tratar(con, saida, ia, entrada, momento, envio)
            except Exception as falha:  # noqa: BLE001 -- um evento ruim nao trava a fila
                erro = "%s: %s" % (type(falha).__name__, str(falha)[:300])
            con.execute("UPDATE atendimento.eventos_meta SET processado_em = %s, erro = %s WHERE id = %s",
                        (momento, erro, ev["id"]))
            feitos += 1
    return feitos


def rotina_do_minuto(cfg: config.Config, saida, envio=None, agora: datetime | None = None) -> None:
    if not cfg.responde:
        return
    momento = agora or datetime.now(timezone.utc)
    with conexao(cfg) as con:
        motor.fazer_perguntas_vencidas(con, saida, momento)
        motor.marcar_paradas(con, momento)
    if envio is not None:
        envio.rotina(cfg, saida, momento)


def criar_app(cfg: config.Config | None = None, saida=None, ia=None, envio=None,
              trabalhador: bool = True) -> FastAPI:
    cfg = cfg or config.carregar()
    if saida is None and cfg.meta_token:
        from .saida import SaidaMeta
        saida = SaidaMeta(cfg.meta_phone_id, cfg.meta_token)
    if ia is None and cfg.anthropic_chave:
        from .ia import IA
        ia = IA(cfg)
    if envio is None and saida is not None:
        from .envio import Envio
        envio = Envio(ler_nota=getattr(saida, "nota", None))
    parar = threading.Event()

    def laco():
        segundos = 0
        while not parar.wait(1):
            try:
                if saida is not None or not cfg.responde:
                    processar_pendentes(cfg, saida, ia, envio)
                segundos += 1
                if segundos >= 60 and saida is not None:
                    segundos = 0
                    rotina_do_minuto(cfg, saida, envio)
            except Exception as falha:  # noqa: BLE001 -- o laco nunca morre
                print("trabalhador: %s" % falha, flush=True)

    @asynccontextmanager
    async def vida(app: FastAPI):
        migracoes.aplicar(cfg)
        t = threading.Thread(target=laco, name="trabalhador", daemon=True) if trabalhador else None
        if t:
            t.start()
        yield
        parar.set()

    app = FastAPI(title="AxiaAtende recepcionista", lifespan=vida, docs_url=None, redoc_url=None,
                  openapi_url=None)

    @app.get("/saude")
    def saude():
        try:
            with conexao(cfg) as con:
                r = con.execute("""SELECT count(*) FILTER (WHERE processado_em IS NULL) AS pendentes,
                                          max(recebido_em) AS ultimo FROM atendimento.eventos_meta""").fetchone()
        except Exception as erro:  # noqa: BLE001
            return JSONResponse({"de_pe": False, "ambiente": cfg.ambiente, "erro": type(erro).__name__},
                                status_code=503)
        return {"de_pe": True, "ambiente": cfg.ambiente, "responde": cfg.responde,
                "meta_ligada": saida is not None, "ia_ligada": ia is not None,
                "pendentes": r["pendentes"], "ultimo_aviso": r["ultimo"].isoformat() if r["ultimo"] else None}

    @app.get("/webhook")
    def aperto_de_mao(request: Request):
        q = request.query_params
        if (q.get("hub.mode") == "subscribe" and cfg.meta_verify_token
                and hmac.compare_digest(q.get("hub.verify_token", ""), cfg.meta_verify_token)):
            return PlainTextResponse(q.get("hub.challenge", ""))
        return PlainTextResponse("recusado", status_code=403)

    @app.post("/webhook")
    async def aviso(request: Request):
        corpo = await request.body()
        if not assinatura_confere(cfg.meta_app_secret, corpo, request.headers.get("X-Hub-Signature-256")):
            return PlainTextResponse("assinatura", status_code=401)
        try:
            dados = json.loads(corpo)
        except ValueError:
            return PlainTextResponse("json", status_code=400)
        gravar(cfg, dados)
        return PlainTextResponse("ok")

    # Nada mais: qualquer outro caminho e 404, e o processo exposto nao serve tela nem API.
    return app


def __getattr__(nome: str):
    if nome == "app":
        global app
        app = criar_app()
        return app
    raise AttributeError(nome)
