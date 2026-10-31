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
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from . import envio as E
from .banco import conexao
from .motor import _ajuste

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
    aceite_cadastro: bool | None = None    # o aceite do cadastro (#952): True, False (recusou) ou None
    capa: str | None = None                # a versao deste cliente (a peca da revenda com a logo dela)
    imagens: list[str] | None = None
    # #1142: quem e este contato no cliente (#1141, uma linha por contato), e o CANAL do responsavel
    # no ERP -- e por ele que o resumo do lote vai so a representante e corretor, porque este projeto
    # nao sabe qual numero e o do dono. Ausentes no pedido de antes, e ai ficam nulos.
    papel: Literal["comprador", "tecnico"] | None = None
    responsavel_canal: Literal["representante", "corretor", "dono", "flutuante"] | None = None


class UsoIA(BaseModel):
    """#1223: uma chamada ao Gemini feita no AxiaMarketing, com o id da linha de la."""
    id: int
    em: datetime
    funcao: str = Field(min_length=1, max_length=40)
    modelo: str = Field(min_length=1, max_length=80)
    entrada: int = Field(ge=0)
    saida: int = Field(ge=0)


class LoteUsoIA(BaseModel):
    usos: list[UsoIA] = Field(min_length=1, max_length=200)


class Pedido(BaseModel):
    pedido_ref: str = Field(min_length=1, max_length=120)
    tipo: Literal["material", "direta"] = "material"
    modelo: str                            # o nome do modelo no cadastro (atendimento.modelos)
    campanha: str
    peca: str
    assunto: str = ""                      # o {{2}} da direta: "plantio do Trigo Mourisco"
    capa: str
    imagens: list[str] = Field(default_factory=list, max_length=20)
    aprovado_por: str
    aprovado_em: datetime
    lote_tamanho: int = 20
    passa_do_teto: bool = False            # #1175: a peca a mais, que o dono manda alem do teto do mes
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
        if pedido.tipo == "material" and not pedido.imagens and not any(c.imagens for c in pedido.clientes):
            raise HTTPException(status_code=422, detail="envio de material sem imagens")
        pasta = cfg.envios_pasta / hashlib.sha256(pedido.pedido_ref.encode()).hexdigest()[:16]
        capa = copiar(pedido.capa, pasta / "capa")
        imagens = [copiar(img, pasta / ("%02d" % i)) for i, img in enumerate(pedido.imagens, start=1)]
        clientes = []
        for c in pedido.clientes:
            d = c.model_dump()
            sub = pasta / str(c.erp_codigo)
            if c.capa:
                d["capa"] = copiar(c.capa, sub / "capa")
            if c.imagens:
                d["imagens"] = [copiar(img, sub / ("%02d" % i)) for i, img in enumerate(c.imagens, start=1)]
            clientes.append(d)
        dados = pedido.model_dump()
        dados.update(capa=capa, imagens=imagens, clientes=clientes)
        with conexao(cfg) as con:
            try:
                envio_id = E.receber_pedido(con, dados)
            except E.PedidoInvalido as erro:
                raise HTTPException(status_code=422, detail=str(erro)) from None
            contagem = {x["situacao"]: x["n"] for x in con.execute(
                """SELECT situacao, count(*) AS n FROM atendimento.envio_destinatarios
                    WHERE envio_id = %s GROUP BY situacao""", (envio_id,))}
        return {"envio_id": envio_id, "situacoes": contagem}

    @r.get("/pedido/modelos")
    def modelos(x_axiaatende_chave: str | None = Header(default=None)):
        """Os modelos ativos do cadastro, para a ficha do marketing oferecer so os que existem."""
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            return {"modelos": [dict(m) for m in con.execute(
                """SELECT nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto
                     FROM atendimento.modelos WHERE ativo ORDER BY uso, nome""")]}

    class Numeros(BaseModel):
        numeros: list[str] = Field(max_length=5000)

    @r.post("/pedido/aceites")
    def aceites(pedido: Numeros, x_axiaatende_chave: str | None = Header(default=None)):
        """O ultimo toque de cada numero ("aceite" ou "recusa"); quem nunca tocou nao aparece.
        A conferencia da comunicacao direta usa isto junto com o aceite do cadastro."""
        conferir(x_axiaatende_chave)
        numeros = sorted({E.so_digitos(n) for n in pedido.numeros if n})
        with conexao(cfg) as con:
            linhas = con.execute(
                """SELECT DISTINCT ON (whatsapp) whatsapp, tipo FROM atendimento.consentimentos
                    WHERE whatsapp = ANY(%s) ORDER BY whatsapp, em DESC, id DESC""", (numeros,)).fetchall()
        return {"aceites": {l["whatsapp"]: l["tipo"] for l in linhas}}

    @r.post("/pedido/teto")
    def teto(pedido: Numeros, x_axiaatende_chave: str | None = Header(default=None)):
        """#1163: quantas mensagens de envio cada numero recebeu no MES de agora (Sao Paulo), e o teto
        do comprador. E a previa da tela Publicacoes, antes de o dono agendar: quem decide de verdade
        e o laco do lote, na hora de sair. A chave do resultado e o numero como veio."""
        conferir(x_axiaatende_chave)
        agora = datetime.now(E.FUSO)
        with conexao(cfg) as con:
            no_mes = {n: E.Envio.recebidas_no_mes(con, E.so_digitos(n), agora) for n in dict.fromkeys(pedido.numeros) if n}
        return {"teto": E.TETO_DO_COMPRADOR, "no_mes": no_mes}

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

    class Aviso(BaseModel):
        tipo: Literal["plano_sem_registro", "status_do_dia"]
        partes: list[str] = Field(default_factory=list, max_length=3)
        # #1207: o status do dia -- as artes do Stories, na ordem, e a legenda que vai na ultima
        imagens: list[str] = Field(default_factory=list, max_length=10)
        legenda: str = ""
        ref: str = Field(default="", max_length=120)   # o codigo da publicacao no Marketing (PUB-0000)

    # quem recebe cada aviso pedido pelo Marketing (o ajuste aponta para um destino)
    PARA = {"plano_sem_registro": "avisado_no_nao", "status_do_dia": "status_do_dia_para"}

    @r.post("/pedido/aviso")
    def pedir_aviso(pedido: Aviso, x_axiaatende_chave: str | None = Header(default=None)):
        """O aviso ao dono pedido pelo Marketing: o do plano (#926, o Controle do plano) e o status do
        dia (#1207, as artes do Stories para ele postar). Vai para a fila de avisos, para quem o ajuste
        do tipo aponta, e sai na volta do envio. Os outros avisos nascem aqui dentro."""
        conferir(x_axiaatende_chave)
        if pedido.tipo == "plano_sem_registro":
            if not pedido.partes:
                raise HTTPException(status_code=422, detail="aviso do plano sem as partes")
            if any("|" in p for p in pedido.partes):
                raise HTTPException(status_code=422, detail="parte do aviso com barra vertical")
            sobre = "|".join(pedido.partes)
        else:
            if not pedido.imagens:
                raise HTTPException(status_code=422, detail="status do dia sem imagens")
            sobre = "%s · %d imagem(ns)" % (pedido.ref or "status do dia", len(pedido.imagens))
        imagens = []
        if pedido.imagens:
            pasta = cfg.envios_pasta / "avisos" / hashlib.sha256(
                ("%s|%s" % (pedido.ref, datetime.now().isoformat())).encode()).hexdigest()[:16]
            imagens = [copiar(img, pasta / ("%02d" % i)) for i, img in enumerate(pedido.imagens, start=1)]
        with conexao(cfg) as con:
            quem = con.execute("SELECT nome, whatsapp FROM atendimento.destinos WHERE id = %s",
                               (_ajuste(con, PARA[pedido.tipo]),)).fetchone()
            if not quem:
                raise HTTPException(status_code=422, detail="ninguém configurado para receber o aviso")
            a = con.execute("""INSERT INTO atendimento.avisos (tipo, para_nome, para_whatsapp, sobre, imagens, legenda)
                               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                            (pedido.tipo, quem["nome"], quem["whatsapp"], sobre, imagens,
                             pedido.legenda)).fetchone()
        return {"aviso_id": a["id"]}

    @r.get("/pedido/aviso/{aviso_id}")
    def situacao_do_aviso(aviso_id: int, x_axiaatende_chave: str | None = Header(default=None)):
        """Na fila (sem enviado_em e sem erro), enviado (com a hora) ou com o erro. So os que o
        Marketing pede (o do plano e o status do dia, #1207). #1188: a `situacao` continua nesses tres valores (o CHECK do marketing so os aceita); o
        guardado (esperando o toque em Ver) e o nao visto vem ao lado, e na fila continuam."""
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            a = con.execute("""SELECT criado_em, enviado_em, erro, guardado_em, nao_visto_em FROM atendimento.avisos
                                WHERE id = %s AND tipo IN ('plano_sem_registro', 'status_do_dia')""",
                            (aviso_id,)).fetchone()
        if not a:
            raise HTTPException(status_code=404, detail="aviso não encontrado")
        situacao = "erro" if a["erro"] else ("enviado" if a["enviado_em"] else "na_fila")
        return {"situacao": situacao, "criado_em": a["criado_em"], "enviado_em": a["enviado_em"],
                "erro": a["erro"], "guardado": a["guardado_em"] is not None and not a["enviado_em"],
                "nao_visto": a["nao_visto_em"] is not None}

    @r.post("/pedido/uso-ia")
    def receber_uso_ia(lote: LoteUsoIA, x_axiaatende_chave: str | None = Header(default=None)):
        """#1223 (emenda do dono, 31/10/2026): o AxiaMarketing EMPURRA o uso real do Gemini, com a mesma
        chave do pedido, e a tela Custos daqui o soma. A seta da casa nao inverte: o Atende nunca chama o
        Marketing. Idempotente por (origem, id): o lote reenviado depois de uma queda vira nada novo, e
        a resposta devolve TODOS os ids do lote, para o Marketing marcar como entregues."""
        conferir(x_axiaatende_chave)
        with conexao(cfg) as con:
            for u in lote.usos:
                con.execute(
                    """INSERT INTO atendimento.uso_ia (em, origem, id_origem, servico, funcao, modelo, entrada, saida)
                       VALUES (%s, 'axiamarketing', %s, 'gemini', %s, %s, %s, %s)
                       ON CONFLICT (origem, id_origem) DO NOTHING""",
                    (u.em, u.id, u.funcao, u.modelo, u.entrada, u.saida))
        return {"aceitos": [u.id for u in lote.usos]}

    return r
