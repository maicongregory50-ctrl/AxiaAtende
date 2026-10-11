"""O servico das TELAS do AxiaAtende (Recepcao, Envios, Destinos). #950.

Molde: `C:\\AxiaMarketing\\backend\\main.py` (#869). UM PROCESSO SO: a API em `/api` e a tela
pronta (`frontend/dist`) no resto. Preso a 127.0.0.1:8009, sem saida externa.

ESTE NAO E O PROCESSO EXPOSTO. Quem a internet alcanca e o recepcionista
(`backend/recepcionista.py`, 127.0.0.1:8008, publicado pelo Funnel). Este fica so no servidor.

Ao subir, aplica as mudancas do banco que faltam. Se uma mudanca ja aplicada foi editada depois,
o servico NAO sobe: conserto e mudanca nova.

Rodar em desenvolvimento, contra o banco da 5437:

    python -m uvicorn backend.main:app --host 127.0.0.1 --port 8009
"""
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import agenda, config, migracoes, seguranca
from .banco import conexao

COOKIE = "axiaatende_sessao"

# Pedido que muda alguma coisa tem de trazer este cabecalho. Formulario de outro site nao
# consegue po-lo, e o cookie ja e SameSite=Strict: sao dois cintos contra pedido forjado.
CABECALHO_DA_TELA = "X-Axiaatende"


class Entrada(BaseModel):
    login: str
    senha: str


def criar_app(cfg: config.Config | None = None) -> FastAPI:
    cfg = cfg or config.carregar()

    parar = threading.Event()

    def ler_o_cadastro():
        """#969: a agenda do cadastro ao subir e todo dia as 06:00. Sem o segredo, nem nasce."""
        while True:
            try:
                agenda.atualizar(cfg)
            except Exception as falha:  # noqa: BLE001 -- a leitura nunca derruba as telas
                print("agenda: %s" % type(falha).__name__, flush=True)
            agora = datetime.now(timezone.utc)
            if parar.wait((agenda.proxima_leitura(agora) - agora).total_seconds()):
                return

    @asynccontextmanager
    async def vida(app: FastAPI):
        migracoes.aplicar(cfg)
        if cfg.erp_segredo:
            threading.Thread(target=ler_o_cadastro, name="agenda", daemon=True).start()
        yield
        parar.set()

    app = FastAPI(title="AxiaAtende", lifespan=vida, docs_url=None, redoc_url=None,
                  openapi_url=None)
    app.state.cfg = cfg

    @app.middleware("http")
    async def so_da_tela(request: Request, chamar):
        if (request.url.path.startswith("/api/")
                and request.method not in ("GET", "HEAD", "OPTIONS")
                and request.headers.get(CABECALHO_DA_TELA) != "1"):
            return JSONResponse({"detail": "pedido sem o cabeçalho da tela"}, status_code=403)
        return await chamar(request)

    # ── saude ────────────────────────────────────────────────────────────────

    @app.get("/saude")
    @app.get("/api/saude")
    def saude():
        """De pe = o banco respondeu e as mudancas estao aplicadas."""
        try:
            with conexao(cfg) as con:
                mudancas = [r["nome"] for r in con.execute(
                    "SELECT nome FROM casa.mudancas ORDER BY nome").fetchall()]
        except Exception as erro:  # noqa: BLE001 -- a saude diz o que houve, sem cair
            return JSONResponse({"de_pe": False, "ambiente": cfg.ambiente,
                                 "erro": type(erro).__name__}, status_code=503)
        return {"de_pe": True, "ambiente": cfg.ambiente, "mudancas": mudancas,
                "responde": cfg.responde}

    # ── login (copia do AxiaMarketing) ───────────────────────────────────────

    def usuario(request: Request) -> dict:
        with conexao(cfg) as con:
            u = seguranca.usuario_da_sessao(con, request.cookies.get(COOKIE))
        if not u:
            raise HTTPException(status_code=401, detail="entre com o seu usuário")
        return u

    app.state.usuario = usuario

    @app.post("/api/entrar")
    def entrar(dados: Entrada, response: Response):
        login = dados.login.strip().lower()
        if seguranca.trancado(login):
            raise HTTPException(status_code=429,
                                detail="muitas senhas erradas; espere cinco minutos")
        with conexao(cfg) as con:
            u = con.execute("SELECT id, login, nome, senha_hash FROM casa.usuarios"
                            " WHERE login = %s AND ativo", (login,)).fetchone()
            if not u:
                seguranca.gastar_tempo_de_senha(dados.senha)
            if not u or not seguranca.conferir_senha(dados.senha, u["senha_hash"]):
                seguranca.anotar_erro(login)
                raise HTTPException(status_code=401, detail="usuário ou senha não conferem")
            seguranca.limpar_erros(login)
            token = seguranca.abrir_sessao(con, u["id"], cfg.sessao_horas)
        response.set_cookie(COOKIE, token, max_age=cfg.sessao_horas * 3600, httponly=True,
                            secure=cfg.cookie_seguro, samesite="strict", path="/")
        return {"login": u["login"], "nome": u["nome"]}

    @app.post("/api/sair")
    def sair(request: Request, response: Response):
        with conexao(cfg) as con:
            seguranca.fechar_sessao(con, request.cookies.get(COOKIE))
        response.delete_cookie(COOKIE, path="/")
        return {"saiu": True}

    @app.get("/api/eu")
    def eu(u: dict = Depends(usuario)):
        return {"login": u["login"], "nome": u["nome"]}

    # ── as tres telas (F1): Recepcao, Envios e Destinos ──
    from .rotas_telas import rotas as rotas_telas
    app.include_router(rotas_telas(cfg, usuario), prefix="/api")

    # ── a porta do AxiaMarketing (E1 e E5): fora de /api, com a chave do pedido ──
    from .rotas_pedido import rotas as rotas_pedido
    app.include_router(rotas_pedido(cfg))
    # ── o canal de campo (#970): o marketing busca o que a equipe mandou, com a mesma chave ──
    from .rotas_campo import rotas as rotas_campo
    app.include_router(rotas_campo(cfg))

    # ── a tela ───────────────────────────────────────────────────────────────

    @app.get("/{caminho:path}", include_in_schema=False)
    def tela(caminho: str):
        if caminho.startswith(("api/", "pedido/", "campo/")):
            raise HTTPException(status_code=404)
        raiz = cfg.tela.resolve()
        pedido = (raiz / caminho).resolve()
        if caminho and pedido.is_file() and pedido.is_relative_to(raiz):
            return FileResponse(pedido)
        indice = raiz / "index.html"
        if not indice.is_file():
            return JSONResponse({"detail": "a tela ainda não foi construída (frontend/dist)"},
                                status_code=503)
        return FileResponse(indice, headers={"Cache-Control": "no-cache"})

    return app


def __getattr__(nome: str):
    # `uvicorn backend.main:app`: o app so nasce quando alguem o pede, para importar este
    # modulo nos testes nao abrir o ambiente do padrao.
    if nome == "app":
        global app
        app = criar_app()
        return app
    raise AttributeError(nome)
