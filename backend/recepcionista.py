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
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

from . import config, migracoes, motor, vigia
from . import envio as envio_mod
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


def processar_pendentes(cfg: config.Config, saida, ia=None, envio=None, agora: datetime | None = None,
                        campo=None) -> int:
    """Processa ate LOTE eventos, cada um na sua transacao. Devolve quantos."""
    feitos = 0
    if campo is None:   # #970: o canal de campo; com a chave desligada ele nao faz nada
        from .campo import Campo
        campo = Campo(cfg.campo_pasta, ia)
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
                        if cfg.responde_so_para and envio_mod.com_nove(entrada.pessoa.wa_id) not in {
                                envio_mod.com_nove(n) for n in cfg.responde_so_para}:
                            erro = "escuta (ensaio)"   # o Opa responde a quem nao esta no ensaio
                        else:
                            motor.tratar(con, saida, ia, entrada, momento, envio, campo)
            except Exception as falha:  # noqa: BLE001 -- um evento ruim nao trava a fila
                erro = "%s: %s" % (type(falha).__name__, str(falha)[:300])
            con.execute("UPDATE atendimento.eventos_meta SET processado_em = %s, erro = %s WHERE id = %s",
                        (momento, erro, ev["id"]))
            feitos += 1
    return feitos


def vigiar_o_endereco(cfg: config.Config, perguntar, agora: datetime) -> None:
    """#969: a cada 5 min, o nome publico ainda existe la fora? A pergunta vai fora da transacao."""
    with conexao(cfg) as con:
        if not vigia.venceu(con, agora):
            return
    resposta = perguntar()
    with conexao(cfg) as con:
        vigia.anotar(con, resposta, agora)


def rotina_do_minuto(cfg: config.Config, saida, envio=None, agora: datetime | None = None,
                     perguntar=None, ia=None) -> None:
    if not cfg.responde:
        return
    momento = agora or datetime.now(timezone.utc)
    with conexao(cfg) as con:
        motor.fazer_perguntas_vencidas(con, saida, momento)
        motor.marcar_paradas(con, momento)
    try:   # #989: a retomada pela OlivIA de quem parou no meio; nunca segura o resto da rotina
        with conexao(cfg) as con:
            motor.retomar_paradas(con, saida, ia, momento)
    except Exception as falha:  # noqa: BLE001
        print("retomada: %s: %s" % (type(falha).__name__, falha), flush=True)
    if perguntar is not None:
        try:
            vigiar_o_endereco(cfg, perguntar, momento)
        except Exception as falha:  # noqa: BLE001 -- o vigia nunca segura a pergunta nem o envio
            print("vigia: %s" % type(falha).__name__, flush=True)
    if envio is not None:
        envio.rotina(cfg, saida, momento)
    try:   # #970: os avisos do canal de campo, so dentro da janela de 24 h; nunca seguram o resto
        from .campo import Campo
        with conexao(cfg) as con:
            c = Campo(cfg.campo_pasta, ia)
            c.fazer_perguntas(con, saida, momento)
            c.mandar_avisos(con, saida, momento)
    except Exception as falha:  # noqa: BLE001
        print("campo: %s" % type(falha).__name__, flush=True)
    try:   # #1098: a pre-triagem e o curriculo para a Fran (um por mensagem); a limpeza dos 12 meses
        from . import vaga
        with conexao(cfg) as con:
            vaga.mandar_a_fran(con, saida, ia, cfg.meta_app_secret, momento)
            if momento.minute == 0:
                vaga.limpar(con, momento)
    except Exception as falha:  # noqa: BLE001
        print("vaga: %s: %s" % (type(falha).__name__, falha), flush=True)
    try:   # #1037: quem mandou a logo fica sabendo que ela chegou ao marketing (so dentro das 24 h)
        from . import logos
        with conexao(cfg) as con:
            logos.mandar_avisos(con, saida, momento)
    except Exception as falha:  # noqa: BLE001
        print("logos: %s" % type(falha).__name__, flush=True)


def rotina_dos_clientes(cfg: config.Config, saida, ia=None, agora: datetime | None = None) -> int:
    """#1090 etapa 3: a cada 5 s, le o que o consultor parou de escrever e avisa gravado/recusado."""
    if not cfg.responde or saida is None:
        return 0
    from . import clientes_do_dia
    with conexao(cfg) as con:
        return clientes_do_dia.rodar(con, saida, ia, agora or datetime.now(timezone.utc))


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
    # Toda chegada da Meta, aceita ou recusada (#969, 11/10/2026): em 09/10 a Meta parou de
    # entregar (app despublicado) e nada aqui mostrava se ela mandava e era recusada ou se nao
    # mandava. So contagem e hora, nunca o corpo. Zera a cada subida.
    chegadas = {"desde": datetime.now(timezone.utc).isoformat(), "aceitas": 0, "recusadas": 0,
                "ultima_aceita": None, "ultima_recusada": None}

    def laco():
        segundos = 0
        while not parar.wait(1):
            try:
                if saida is not None or not cfg.responde:
                    processar_pendentes(cfg, saida, ia, envio)
                segundos += 1
                if segundos % 5 == 0:
                    try:   # #1090 etapa 3: nunca segura o atendimento
                        rotina_dos_clientes(cfg, saida, ia)
                    except Exception as falha:  # noqa: BLE001
                        print("clientes: %s: %s" % (type(falha).__name__, falha), flush=True)
                if segundos >= 60 and saida is not None:
                    segundos = 0
                    rotina_do_minuto(cfg, saida, envio, perguntar=vigia.confere, ia=ia)
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
                endereco = vigia.estado(con)
        except Exception as erro:  # noqa: BLE001
            return JSONResponse({"de_pe": False, "ambiente": cfg.ambiente, "erro": type(erro).__name__},
                                status_code=503)
        return {"de_pe": True, "ambiente": cfg.ambiente, "responde": cfg.responde,
                "so_para": len(cfg.responde_so_para),
                "meta_ligada": saida is not None, "ia_ligada": ia is not None,
                "pendentes": r["pendentes"], "ultimo_aviso": r["ultimo"].isoformat() if r["ultimo"] else None,
                "chegadas": chegadas,
                # #1028: o que o motor DEIXOU de mandar desde que o servico subiu, para a regra que
                # cala nao ser ela mesma um fracasso silencioso. Zero nao quer dizer desligada: quer
                # dizer que ninguem esbarrou nela, ou que o servico acabou de subir.
                "calados": dict(motor.calados),
                # o nome publico la fora (vigia.py): None = ainda nao conferido
                "endereco": endereco and {"situacao": endereco["situacao"], "desde": endereco["desde"].isoformat(),
                                          "conferido_em": endereco["conferido_em"].isoformat()}}

    @app.get("/falar/{codigo}")
    def falar(codigo: str):
        """O botao de link da comunicacao direta: anota o toque e manda para o WhatsApp do
        responsavel. Codigo que nao assinamos e 404 (o endereco nao serve de atalho)."""
        with conexao(cfg) as con:
            numero = envio_mod.falar(con, cfg.meta_app_secret, codigo, datetime.now(timezone.utc))
        if not numero:
            return PlainTextResponse("", status_code=404)
        return RedirectResponse("https://wa.me/%s" % numero, status_code=302)

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
        agora = datetime.now(timezone.utc).isoformat()
        if not assinatura_confere(cfg.meta_app_secret, corpo, request.headers.get("X-Hub-Signature-256")):
            chegadas["recusadas"] += 1
            chegadas["ultima_recusada"] = agora
            print("aviso recusado: assinatura nao confere (%d bytes)" % len(corpo), flush=True)
            return PlainTextResponse("assinatura", status_code=401)
        chegadas["aceitas"] += 1
        chegadas["ultima_aceita"] = agora
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
