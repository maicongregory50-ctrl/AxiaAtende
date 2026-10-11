"""A porta do canal de campo para o AxiaMarketing (#970, decisao 4 do dono: o marketing BUSCA).

So no servidor (127.0.0.1:8009, o processo das telas) e so com a chave do pedido no cabecalho
`X-Axiaatende-Chave`, a mesma de `rotas_pedido.py` (o instalador escreve as duas pontas). O
publicador do marketing chama a cada minuto: o que esta pronto, o arquivo, e devolve "buscado",
"catalogado" e "foi ao ar" para os avisos a quem mandou sairem dentro da janela.
"""
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import campo
from .banco import conexao


class Buscado(BaseModel):
    lote: str = Field(min_length=1, max_length=200)
    linha: int | None = None


class Catalogado(BaseModel):
    atv: str = Field(min_length=1, max_length=20)


class FoiAoAr(BaseModel):
    peca: str = Field(min_length=1, max_length=200)


def rotas(cfg) -> APIRouter:
    r = APIRouter()

    def conferir(chave: str | None):
        if not cfg.chave_pedido or not chave or not hmac.compare_digest(chave, cfg.chave_pedido):
            raise HTTPException(status_code=403, detail="chave do pedido ausente ou errada")

    def agora():
        return datetime.now(timezone.utc)

    @r.get("/campo/pendentes")
    def pendentes(x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            return {"ligado": campo.ligado(con), "itens": campo.pendentes(con, agora())}

    @r.get("/campo/medidas")
    def medidas(dias: int = 7, x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            return campo.medidas(con, agora(), max(1, min(dias, 90)))

    @r.get("/campo/{item_id}/arquivo")
    def arquivo(item_id: int, x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            x = con.execute("SELECT arquivo FROM atendimento.material_de_campo WHERE id = %s", (item_id,)).fetchone()
        if not x or not x["arquivo"]:
            raise HTTPException(status_code=404, detail="material não encontrado")
        caminho = (cfg.campo_pasta / x["arquivo"]).resolve()
        if not caminho.is_file() or not caminho.is_relative_to(cfg.campo_pasta.resolve()):
            raise HTTPException(status_code=404, detail="o arquivo não está na pasta do campo")
        return FileResponse(caminho, filename=caminho.name)

    @r.post("/campo/{item_id}/buscado")
    def buscado(item_id: int, dados: Buscado, x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            x = campo.buscado(con, item_id, dados.lote, dados.linha, agora())
        if not x:
            raise HTTPException(status_code=404, detail="material não encontrado")
        return x

    @r.post("/campo/{item_id}/catalogado")
    def catalogado(item_id: int, dados: Catalogado, x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            x = campo.catalogado(con, item_id, dados.atv.strip().upper(), agora())
        if not x:
            raise HTTPException(status_code=404, detail="material não encontrado")
        return x

    @r.post("/campo/{item_id}/foi-ao-ar")
    def foi_ao_ar(item_id: int, dados: FoiAoAr, x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            x = campo.foi_ao_ar(con, item_id, dados.peca.strip(), agora())
        if not x:
            raise HTTPException(status_code=404, detail="material não encontrado")
        return x

    return r
