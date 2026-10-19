"""A porta das logos de cliente para o AxiaMarketing (#1037, 19/10/2026: a outra metade do #1036).

So no servidor (127.0.0.1:8009, o processo das telas) e so com a chave do pedido no cabecalho
`X-Axiaatende-Chave`, a mesma de `rotas_pedido.py` e `rotas_campo.py`. O publicador do marketing
chama a cada minuto: o que esta pronto, o arquivo, e devolve "puxada" com o que fez -- e a
recepcionista avisa quem mandou (logos.mandar_avisos). O marketing PUXA: a seta nao se inverte e
nao nasce segredo novo (padrao #267). Nada aqui apaga a logo: o original fica.
"""
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import logos
from .banco import conexao


class Puxada(BaseModel):
    resultado: str = Field(pattern=r"^(parceira_nova|a_conferir)$")


def rotas(cfg) -> APIRouter:
    r = APIRouter()

    def conferir(chave: str | None):
        if not cfg.chave_pedido or not chave or not hmac.compare_digest(chave, cfg.chave_pedido):
            raise HTTPException(status_code=403, detail="chave do pedido ausente ou errada")

    def agora():
        return datetime.now(timezone.utc)

    @r.get("/logos/pendentes")
    def pendentes(x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            return {"itens": logos.a_puxar(con, agora())}

    @r.get("/logos/{logo_id}/arquivo")
    def arquivo(logo_id: int, x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            x = con.execute("SELECT arquivo FROM atendimento.logos_de_cliente WHERE id = %s",
                            (logo_id,)).fetchone()
        if not x or not x["arquivo"]:
            raise HTTPException(status_code=404, detail="logo não encontrada")
        # o logos.receber grava em <campo_pasta>/logos/<dia>/...: o arquivo nao sai dela
        caminho = (cfg.campo_pasta / x["arquivo"]).resolve()
        if not caminho.is_file() or not caminho.is_relative_to(cfg.campo_pasta.resolve()):
            raise HTTPException(status_code=404, detail="o arquivo não está na pasta das logos")
        return FileResponse(caminho, filename=caminho.name)

    @r.post("/logos/{logo_id}/puxada")
    def puxada(logo_id: int, dados: Puxada, x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            x = logos.puxada(con, logo_id, dados.resultado, agora())
        if not x:
            raise HTTPException(status_code=404, detail="logo não encontrada")
        return x

    return r
