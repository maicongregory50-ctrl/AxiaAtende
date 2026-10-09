"""A porta do AxiaMarketing para o AxiaAtende: o pedido de envio e o resumo do KR2. #950, E1 e E5.

So no servidor (127.0.0.1:8009, o processo das telas) e so com a chave do pedido no cabecalho
`X-Axiaatende-Chave`. A chave mora no `.env.secrets` daqui e no `.env.publicador` do Marketing (o
instalador escreve as duas); sem ela configurada, a porta recusa tudo. O motivo: cada convite e
uma mensagem paga a um cliente, e nao pode sair de qualquer programa desta maquina.

O PEDIDO chega depois da aprovacao do dono no Marketing (trava D7 do #923). As imagens vem como
caminho de arquivo no disco do servidor e sao COPIADAS para `envios_pasta`, onde o recepcionista
(LocalService) as le: ele nao enxerga as pastas do Marketing.
"""
import hashlib
import hmac
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from . import envio as E
from .banco import conexao

TIPOS = {".jpg", ".jpeg", ".png"}


class Cliente(BaseModel):
    erp_codigo: int
    nome: str
    cidade: str = ""
    uf: str = ""
    whatsapp: str = ""
    faturamento: float = 0
    responsavel_nome: str = ""
    responsavel_whatsapp: str = ""
    sugestao_vendedor: str = ""


class Pedido(BaseModel):
    pedido_ref: str = Field(min_length=1, max_length=120)
    campanha: str
    peca: str
    capa: str
    imagens: list[str] = Field(min_length=1, max_length=20)
    aprovado_por: str
    aprovado_em: datetime
    lote_tamanho: int = 20
    clientes: list[Cliente] = Field(min_length=1)


def rotas(cfg) -> APIRouter:
    r = APIRouter()

    def conferir(chave: str | None):
        if not cfg.chave_pedido or not chave or not hmac.compare_digest(chave, cfg.chave_pedido):
            raise HTTPException(status_code=403, detail="chave do pedido ausente ou errada")

    def copiar(origem: str, destino: Path) -> str:
        p = Path(origem)
        if p.suffix.lower() not in TIPOS or not p.is_file():
            raise HTTPException(status_code=422, detail="imagem não encontrada ou de tipo errado: %s" % p.name)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, destino.with_suffix(p.suffix.lower()))
        return str(destino.with_suffix(p.suffix.lower()))

    @r.post("/pedido/envio")
    def pedir_envio(pedido: Pedido, x_axiaatende_chave: str | None = Header(default=None)):
        conferir(x_axiaatende_chave)
        pasta = cfg.envios_pasta / hashlib.sha256(pedido.pedido_ref.encode()).hexdigest()[:16]
        capa = copiar(pedido.capa, pasta / "capa")
        imagens = [copiar(img, pasta / ("%02d" % i)) for i, img in enumerate(pedido.imagens, start=1)]
        dados = pedido.model_dump()
        dados.update(capa=capa, imagens=imagens, clientes=[c.model_dump() for c in pedido.clientes])
        with conexao(cfg) as con:
            envio_id = E.receber_pedido(con, dados)
            contagem = {x["situacao"]: x["n"] for x in con.execute(
                """SELECT situacao, count(*) AS n FROM atendimento.envio_destinatarios
                    WHERE envio_id = %s GROUP BY situacao""", (envio_id,))}
        return {"envio_id": envio_id, "situacoes": contagem}

    @r.get("/pedido/resumo")
    def resumo(desde: datetime, ate: datetime, x_axiaatende_chave: str | None = Header(default=None)):
        """O KR2: no periodo, quantos clientes receberam convite, quantos responderam (tocaram ou
        escreveram) e quantos aceitaram. Por cliente (codigo do ERP), nao por mensagem."""
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            r1 = con.execute(
                """SELECT count(DISTINCT erp_codigo) FILTER (WHERE convite_em >= %(d)s AND convite_em < %(a)s) AS convidados,
                          count(DISTINCT erp_codigo) FILTER (WHERE resposta IS NOT NULL
                                                             AND resposta_em >= %(d)s AND resposta_em < %(a)s) AS responderam,
                          count(DISTINCT erp_codigo) FILTER (WHERE resposta = 'quero'
                                                             AND resposta_em >= %(d)s AND resposta_em < %(a)s) AS aceitaram,
                          count(DISTINCT erp_codigo) FILTER (WHERE resposta = 'nao_quero'
                                                             AND resposta_em >= %(d)s AND resposta_em < %(a)s) AS recusaram
                     FROM atendimento.envio_destinatarios""", {"d": desde, "a": ate}).fetchone()
        return dict(r1)

    return r
