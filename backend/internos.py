"""QUEM E DA CASA: equipe e representante, reconhecidos pelo numero. #1031, 15/10/2026.

POR QUE ESTE MODULO EXISTE. A regra morava em `campo.quem_e` e `campo.e_interno`, onde ser interno
dependia de `campo.ligado` -- a chave do canal de FOTOS do marketing. Sao duas coisas distintas
presas na mesma chave: desligar o canal de fotos devolvia a equipe inteira ao menu de cliente.
Decisao do dono em 15/10/2026, no #1031: interno e conceito proprio, com chave propria.

DUAS CAMADAS, e a ordem importa:

1. **O ERP decide primeiro.** `agenda.reconhecer` acha o numero na agenda (lida do ERP todo dia as
   06:00) e devolve os papeis. Papel `equipe` ou `representante` num cadastro so: e da casa.
2. **O destino ativo completa** (decisao do dono, 14/10/2026, "por hora"): o celular de TRABALHO de
   quem atende nem sempre esta no cadastro do ERP, e os numeros da tela Destinos sao justamente
   "os que orientamos o cliente a chamar". Entram como `equipe`, sem codigo.

   Medido em 15/10/2026: dos 6 destinos ativos, 3 estao no ERP (Maicon e Benedito como `equipe`,
   Djeison como `representante`) e 3 so entram por esta camada (Willian, Fran, Alisson). O caminho
   de volta e cadastrar o numero como contato do colaborador no ERP e tirar o complemento -- e e
   chamado proprio, nao desta etapa.

O QUE ISTO **NAO** DECIDE: o que fazer com quem e da casa. Isso e do motor (o menu interno) e do
canal de campo (a frase da proxima foto). Aqui so se responde "e da casa?".
"""
from . import agenda
from .envio import com_nove

PAPEIS = ("equipe", "representante")

# "Pediu o menu?" -- a lista veio de `campo.PEDE_MENU` e mora aqui porque DOIS modulos a perguntam
# (#1031): o canal de campo, para nao anotar como frase de foto o que era pedido de menu; e o motor,
# para saber que uma saudacao de quem e da casa pede o menu DA CASA, nao o do cliente.
#
# A saudacao esta nesta lista de proposito, e e o que explica o #1031: para um CLIENTE, "boa tarde"
# e o acolhimento e o menu e a resposta certa. O que estava errado era usar a mesma leitura para
# quem e da casa. A lista NAO muda nesta etapa.
PEDE_MENU = ("menu", "menu.", "atendimento", "opções", "opcoes", "ajuda", "oi", "olá", "ola",
             "bom dia", "boa tarde", "boa noite")


def pede_menu(texto: str) -> bool:
    return (texto or "").lower().strip(" !") in PEDE_MENU


def ligado(con) -> bool:
    """A chave de `interno.ligado`. AUSENTE = LIGADO, de proposito (#1031).

    A linha nasce na migracao 018 com `true`, porque e o comportamento que o dono pediu. O padrao
    ligado na ausencia cobre o caso de alguem apagar a linha: o reconhecimento nao morre em
    silencio por falta de cadastro -- quem quiser desligar escreve `false`, que e um ato.
    """
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = 'interno.ligado'").fetchone()
    if not r:
        return True
    return bool(r["valor"] is True)


def quem_e(con, wa_id: str | None) -> dict | None:
    """O cadastro de quem mandou, se for da casa. None: trate como cliente.

    NAO consulta `ligado`: devolve o que o cadastro diz. Quem decide se a chave importa e quem
    chama -- o motor usa `e_interno` (que confere a chave), e o canal de campo confere a dele.
    """
    q = agenda.reconhecer(con, wa_id)
    if q and q.get("erp_cadastros") == 1:
        papel = next((p for p in PAPEIS if p in (q.get("erp_papeis") or [])), None)
        if papel:
            return {"codigo": q["erp_codigo"], "papel": papel, "nome": q["erp_nome"] or ""}
    numero = com_nove(wa_id or "")
    if not numero:
        return None
    for d in con.execute("SELECT nome, whatsapp FROM atendimento.destinos WHERE ativo ORDER BY id").fetchall():
        if com_nove(d["whatsapp"]) == numero:
            return {"codigo": None, "papel": "equipe", "nome": d["nome"]}
    return None


def e_interno(con, wa_id: str | None) -> bool:
    """Da casa E com o reconhecimento ligado. E o que o motor pergunta antes de trocar o menu."""
    return ligado(con) and quem_e(con, wa_id) is not None


def destino_proprio(con, wa_id: str | None, destino_id: int | None) -> bool:
    """Esse destino e a PROPRIA pessoa que esta falando? (#1031, decisao 4 da spec)

    Medido em 15/10/2026: o Benedito percorreu o menu de cliente e recebeu o cartao de contato dele
    mesmo TRES vezes, por ser o destino de Fretes. Vale para qualquer um, interno ou nao: o que se
    compara e o numero de quem fala com o numero do destino.
    """
    if not destino_id:
        return False
    numero = com_nove(wa_id or "")
    if not numero:
        return False
    d = con.execute("SELECT whatsapp FROM atendimento.destinos WHERE id = %s", (destino_id,)).fetchone()
    return bool(d and com_nove(d["whatsapp"]) == numero)
