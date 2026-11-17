"""Recontato dos candidatos que ficaram sem o atendimento certo (#1543, dono, 17/11/2026: "precisamos
recontatar os candidatos que ficaram sem o atendimento correto").

QUEM: quem teve conversa de vaga desde 12/11/2026 (o dia em que as duas vagas abriram), NAO tem candidatura
(curriculo nem ficha), nao e da casa, escreveu nas ultimas 23 h (a janela em que a Meta deixa mandar texto;
uma hora de folga) e ainda nao recebeu este recontato. Quem esta fora da janela aparece na lista como "fora
da janela" e NAO recebe nada: ali so modelo pago da Meta alcanca, e isso e decisao a parte.

O QUE VAI: um texto so, pelo caso -- a vaga que aceita ficha, a de curriculo obrigatorio, ou sem vaga dita --,
na lingua em que a conversa correu. Os textos estao em TEXTOS, aprovados pelo dono antes de mandar.
A resposta da pessoa e atendida pela OlivIA, que le este texto no historico dela.

Sem `--mandar`, SO MOSTRA a lista, com o texto de cada um. `--so 5549...,5549...` escolhe os numeros.
Rode DEPOIS do restart do recepcionista com o conserto do #1543. Em producao, janela elevada:

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\recontatar_candidatos.py
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\recontatar_candidatos.py --mandar
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config, internos, motor, olivia, vaga  # noqa: E402
from backend.banco import conexao  # noqa: E402

DESDE = "2026-11-12"
JANELA = timedelta(hours=23)
ESPERA = timedelta(hours=3)   # quem escreveu ha menos disso ainda esta no tempo dele: nao se recontata
RESUMO = "olivia: recontato"

TEXTOS = {
    ("ficha", "pt"): "Olá! Aqui é a OlivIA, da Sementes Renascer. Você procurou a vaga de {vaga} e ficou sem "
                     "concluir. Não precisa de currículo: são 5 perguntas rápidas, por aqui mesmo. Quer começar?",
    ("ficha", "es"): "¡Hola! Soy OlivIA, de Sementes Renascer. Buscaste la vacante de {vaga} y no terminaste. "
                     "No hace falta currículum: son 5 preguntas rápidas, por aquí mismo. ¿Empezamos?",
    ("curriculo", "pt"): "Olá! Aqui é a OlivIA, da Sementes Renascer. Você procurou a vaga de {vaga} e ficou "
                         "faltando o currículo. Pode ser uma foto dele, até feito à mão. Mandando por aqui, eu "
                         "passo à equipe.",
    ("curriculo", "es"): "¡Hola! Soy OlivIA, de Sementes Renascer. Buscaste la vacante de {vaga} y faltó el "
                         "currículum. Puede ser una foto, incluso hecho a mano. Si lo envías por aquí, lo paso "
                         "al equipo.",
    ("sem_vaga", "pt"): "Olá! Aqui é a OlivIA, da Sementes Renascer. Você procurou as nossas vagas e ficou sem "
                        "concluir. Temos Auxiliar de produção, que não precisa de currículo, e Operador de "
                        "empilhadeira. Qual te interessa?",
    ("sem_vaga", "es"): "¡Hola! Soy OlivIA, de Sementes Renascer. Buscaste nuestras vacantes y no terminaste. "
                        "Tenemos Auxiliar de producción, que no necesita currículum, y Operador de montacargas. "
                        "¿Cuál te interesa?",
}


EM_ESPANHOL = {"Auxiliar de produção": "Auxiliar de producción", "Operador de empilhadeira": "Operador de montacargas"}


def titulo(v, lingua: str = "pt") -> str:
    t = (v["titulo"] or "").strip()
    t = t[5:] if t.lower().startswith("vaga ") else t
    return EM_ESPANHOL.get(t, t) if lingua == "es" else t


def candidatos(con, agora: datetime) -> list[dict]:
    """Um por pessoa: a ultima conversa de vaga dela, a vaga, a lingua, a ultima mensagem e o caso."""
    lista = []
    for r in con.execute("""
            SELECT c.bsuid, max(c.id) AS conversa_id FROM atendimento.conversas c
             WHERE c.trabalhe AND c.iniciada_em >= %s
               AND NOT EXISTS (SELECT 1 FROM atendimento.candidaturas k WHERE k.bsuid = c.bsuid)
             GROUP BY c.bsuid ORDER BY 2 DESC""", (DESDE,)).fetchall():
        c = con.execute("SELECT * FROM atendimento.conversas WHERE id = %s", (r["conversa_id"],)).fetchone()
        if not c["wa_id"] or internos.e_interno(con, c["wa_id"]):
            continue
        ultima = con.execute("""SELECT max(recebido_em) AS em FROM atendimento.eventos_meta
                                 WHERE tipo = 'mensagem' AND (bsuid = %s OR corpo->'msg'->>'from' = %s)""",
                             (c["bsuid"], c["wa_id"])).fetchone()["em"]
        ja = con.execute("SELECT 1 FROM atendimento.enviadas WHERE para = %s AND resumo = %s LIMIT 1",
                         (c["wa_id"], RESUMO)).fetchone()
        aberta = con.execute("SELECT 1 FROM atendimento.conversas WHERE bsuid = %s AND situacao = 'em_curso' LIMIT 1",
                             (c["bsuid"],)).fetchone()
        v = olivia._vaga_da_pessoa(con, c)
        if v is not None and not v["aberta"]:
            v = None
        caso = "sem_vaga" if v is None else ("ficha" if v["modo"] == "ficha_ou_curriculo" else "curriculo")
        lingua = olivia._lingua_da_conversa(con, c)
        na_janela = ultima is not None and agora - ultima < JANELA
        # dono, 17/11/2026 ("a OlivIA precisa aprender a esperar tambem"): o recontato das 09:46 alcancou
        # quem tinha dito "ja envio" as 08:30. Quem falou ha menos de ESPERA nao e recontatado.
        cedo = ultima is not None and agora - ultima < ESPERA
        estado = ("ja recebeu o recontato" if ja else "em conversa agora" if aberta
                  else "fora da janela" if not na_janela else "falou ha pouco" if cedo else "mandar")
        lista.append({"wa_id": c["wa_id"], "conversa_id": c["id"], "ultima": ultima, "caso": caso, "lingua": lingua,
                      "estado": estado, "texto": TEXTOS[(caso, lingua)].format(vaga=titulo(v, lingua) if v else "")})
    return lista


def main() -> int:
    mandar = "--mandar" in sys.argv
    so = next((sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x == "--so"), "")
    so = {n.strip() for n in so.split(",") if n.strip()}
    cfg = config.carregar()
    agora = datetime.now(timezone.utc)
    with conexao(cfg) as con:
        lista = candidatos(con, agora)
    if so:
        lista = [x for x in lista if x["wa_id"] in so]
    a_mandar = [x for x in lista if x["estado"] == "mandar"]
    print("Candidatos sem candidatura desde %s: %d; a mandar agora: %d" % (DESDE, len(lista), len(a_mandar)))
    for x in lista:
        quando = x["ultima"].astimezone(motor.FUSO).strftime("%d/%m %H:%M") if x["ultima"] else "-"
        print("  %-14s ultima %s  %-9s %s  [%s]" % (x["wa_id"], quando, x["caso"], x["lingua"], x["estado"]))
        if x["estado"] == "mandar":
            print("      -> %s" % x["texto"])
    if not mandar:
        print("Nada foi mandado. Para mandar: o mesmo comando com --mandar")
        return 0
    from backend.saida import SaidaMeta
    from backend.texto_enviado import guardar_no_banco
    saida = SaidaMeta(cfg.meta_phone_id, cfg.meta_token, guardar=guardar_no_banco(cfg))
    for x in a_mandar:
        try:
            w = saida.texto(x["wa_id"], x["texto"])
        except Exception as falha:   # noqa: BLE001 -- um numero que falha nao para os outros
            print("  %s: NAO SAIU (%s)" % (x["wa_id"], type(falha).__name__))
            continue
        with conexao(cfg) as con:
            motor._registrar(con, x["conversa_id"], x["wa_id"], "texto", RESUMO, w)
        print("  %s: %s" % (x["wa_id"], "MANDADO" if w else "calado (a Meta nao aceitou)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
