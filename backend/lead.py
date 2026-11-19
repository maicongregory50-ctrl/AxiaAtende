"""#1660: a FICHA do produtor rural que a OlivIA qualificou, mandada ao WhatsApp de quem atende.

Spec: docs/specs/2026-11-19-olivia-qualifica-o-produtor-rural.md (D5, D6). Manual: docs/manuais/olivia.md.

QUEM RECEBE: o destino da folha `comercial.produtor.<uf>` (D2) -- o mesmo do cartao. Quem trocar o destino na
tela Destinos troca quem recebe a ficha.

COMO SAI (D5): dentro da janela de 24 h de quem recebe, TEXTO LIVRE com o nome, as quatro respostas (ou "nao
disse"), o resumo dela e o link wa.me do produtor. Fora da janela, o modelo `olivia_resumo` (UTILITY, ja
aprovado), com tudo numa linha e o telefone escrito.

`mandar` NUNCA levanta: qualquer falha grava `leads.erro` e devolve False. E por esse False que a OlivIA nao
diz ao produtor que o consultor "esta recebendo o resumo" (D6).
"""
from datetime import datetime

from . import internos
from .envio import janela_aberta, modelo_do_uso

USO_DO_MODELO = "aviso_olivia_resumo"
RESUMO_ENVIADA = "lead da olivia: ficha"
RESUMO_ATE = 300
CAMPO_ATE = 200
LINHA_ATE = 900   # o corpo do modelo e "Resumo da OlivIA: {{1}} O detalhe ...": a Meta aceita ate 1024 no corpo
# D3: as quatro perguntas, em cinco campos (a primeira pergunta e "qual semente e para que"). A ficha e
# COMPLETA com os cinco; o nome continua valendo como hoje e nao conta.
PERGUNTAS = ("produto", "finalidade", "tamanho", "quando", "municipio")
CAMPOS = ("nome",) + PERGUNTAS + ("uf",)
DITO = {"produto": "o que procura", "finalidade": "para quê", "tamanho": "a área ou a quantidade",
        "quando": "quando planta", "municipio": "o município"}


def limpo(valor, ate: int = CAMPO_ATE) -> str:
    """Uma linha, sem espaco repetido, cortada."""
    return " ".join(str(valor or "").split())[:ate]


def faltou(lead) -> list[str]:
    return [k for k in PERGUNTAS if not (lead.get(k) or "").strip()]


def _juntar(partes: list[str]) -> str:
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]


def faltou_dito(lead) -> str:
    return _juntar([DITO[k] for k in faltou(lead)]) if faltou(lead) else ""


def telefone(numero: str) -> str:
    """+55 49 98888-3333: o numero escrito, para quem le no modelo fora da janela (sem link)."""
    n = "".join(c for c in (numero or "") if c.isdigit())
    if n.startswith("55") and len(n) in (12, 13):
        local = n[4:]
        return "+55 %s %s-%s" % (n[2:4], local[:-4], local[-4:])
    return ("+" + n) if n else "sem número"


def _procura(lead) -> str:
    produto, finalidade = (lead.get("produto") or "").strip(), (lead.get("finalidade") or "").strip()
    if produto and finalidade:
        return "%s, para %s" % (produto, finalidade)
    if produto:
        return "%s (para quê: não disse)" % produto
    return "não disse" + ((" (para %s)" % finalidade) if finalidade else "")


def texto_da_ficha(lead, numero: str) -> str:
    """A ficha inteira, para dentro da janela (texto livre)."""
    def dito(k):
        return (lead.get(k) or "").strip() or "não disse"
    uf = (lead.get("uf") or "").strip().upper()
    linhas = ["*Lead da OlivIA* (produtor rural%s)" % ((", " + uf) if uf else ""),
              "Nome: %s" % dito("nome"),
              "Procura: %s" % _procura(lead),
              "Área ou quantidade: %s" % dito("tamanho"),
              "Quando planta: %s" % dito("quando"),
              "Município: %s" % dito("municipio")]
    if faltou(lead):
        linhas.append("Ficha incompleta: faltou %s." % faltou_dito(lead))
    if (lead.get("resumo") or "").strip():
        linhas.append("Resumo: %s" % limpo(lead["resumo"], RESUMO_ATE))
    n = "".join(c for c in (numero or "") if c.isdigit())
    linhas.append(("Conversar com ele: https://wa.me/%s" % n) if n else "Sem número de WhatsApp na conversa.")
    return "\n".join(linhas)


def linha_da_ficha(lead, numero: str) -> str:
    """A ficha numa linha so, para a variavel do modelo `olivia_resumo` (fora da janela): sem quebra, sem
    espaco repetido (a Meta recusa os dois numa variavel), com o telefone escrito, cortada para caber."""
    uf = (lead.get("uf") or "").strip().upper()
    partes = ["Lead produtor rural%s: %s" % ((" " + uf) if uf else "", (lead.get("nome") or "").strip() or "sem nome"),
              "procura %s" % _procura(lead),
              "área ou quantidade: %s" % ((lead.get("tamanho") or "").strip() or "não disse"),
              "planta: %s" % ((lead.get("quando") or "").strip() or "não disse"),
              "município: %s" % ((lead.get("municipio") or "").strip() or "não disse")]
    if faltou(lead):
        partes.append("FICHA INCOMPLETA, faltou %s" % faltou_dito(lead))
    if (lead.get("resumo") or "").strip():
        partes.append("resumo: %s" % lead["resumo"])
    fim = "telefone %s." % telefone(numero)
    corpo = limpo("; ".join(partes), LINHA_ATE - len(fim) - 2)
    return limpo(corpo + "; " + fim, LINHA_ATE)


def mandar(con, saida, lead, destino, numero: str, agora: datetime) -> bool:
    """Manda a ficha `lead` (linha de atendimento.leads) a `destino` (linha de atendimento.destinos).
    `numero`: o WhatsApp do produtor (o link e o telefone da ficha). True: a Meta aceitou."""
    def falhou(motivo: str) -> bool:
        print("lead: ficha %d nao saiu: %s" % (lead["id"], motivo[:200]), flush=True)
        con.execute("UPDATE atendimento.leads SET erro = %s WHERE id = %s", (motivo[:500], lead["id"]))
        return False

    if destino is None:
        return falhou("a folha não tem destino na tela Destinos")
    if internos.destino_proprio(con, numero, destino["id"]):
        return falhou("o destino da folha é a própria pessoa que conversou")
    para = destino["whatsapp"]
    try:
        if janela_aberta(con, para, agora):
            como, w = "texto", saida.texto(para, texto_da_ficha(lead, numero))
        else:
            m = modelo_do_uso(con, USO_DO_MODELO)
            if not m:
                return falhou("nenhum modelo ativo para %s" % USO_DO_MODELO)
            como, w = "modelo", saida.modelo(para, m["nome"], m["idioma"], [linha_da_ficha(lead, numero)])
    except Exception as falha:   # noqa: BLE001 -- a ficha nunca derruba a conversa
        return falhou("%s: %s" % (type(falha).__name__, falha))
    if not w:
        return falhou("a Meta não aceitou a mensagem")
    con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, %s, %s)",
                (w, para, "texto" if como == "texto" else "modelo", RESUMO_ENVIADA))
    con.execute("""UPDATE atendimento.leads SET enviada_em = %s, enviada_como = %s, wamid = %s, erro = ''
                    WHERE id = %s""", (agora, como, w, lead["id"]))
    return True
