"""#1528: o chamado no WhatsApp -- a VOLTA COM ARQUIVO. Quem recebeu uma pergunta de chamado devolve o
documento (PDF, Word, Excel ou foto) pelo WhatsApp, e ele entra no chamado no ERP.
Spec e plano: docs/specs/2026-11-16-chamado-no-whatsapp-a-volta-com-arquivo*.md (D1 a D5).

ESTE MODULO E DO RECEPCIONISTA (Meta e banco, nunca o ERP), como `pendencias.py`. A ida ao ERP e das
TELAS (`pendencias_erp.levar_arquivos`); a tabela `pendencias_mensagens` e a fila entre os dois.

O CAMINHO (D1, D3):
- o arquivo que CITA uma mensagem de chamado com pergunta aberta (a pessoa deslizou): entra direto;
- o arquivo SEM citar, de quem tem uma RAJADA aberta (o anterior chegou ha menos de 5 min): entra nela;
- o documento SEM citar, de quem tem chamado com pergunta aberta: "E para o Chamado N?" (Sim, Outro
  chamado, Outro assunto). A FOTO sem citar de quem e do canal de campo continua material de campo, sem
  pergunta (as 14 fotos do universo medido da spec);
- a rajada fecha com 5 min de silencio, com o decimo arquivo, ou na hora com um texto da pessoa em
  seguida (o texto vira o do comentario e nao passa pelo roteador).

O QUE NUNCA ACONTECE AQUI: decidir se o arquivo presta. Quem decide e o ERP, pelo conteudo e pelo
antivirus (D4, regras 2 e 3). Aqui so os limites que se conferem antes de baixar (10 MB, 10 por vez, 20
por dia), a copia no transito e o sha256. Nenhuma IA abre o arquivo (regra 6).
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from psycopg.types.json import Jsonb

from .envio import com_nove
from .saida import Opcao

MAX_BYTES = 10 * 1024 * 1024
PASTA: Path | None = None    # <envios_pasta>\chamados_volta; o recepcionista a poe ao subir
EXT_FOTO = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

NAO_ESPERA = "Este chamado não espera resposta: o arquivo não entrou."
GRANDE = "Não aceitei '%s': passou de 10 MB."
TETO_RAJADA = "Não aceitei '%s': são até 10 arquivos de uma vez. Mande os outros daqui a 5 minutos."
TETO_DIA = "Não aceitei '%s': passou de 20 arquivos hoje."
NAO_BAIXOU = "Não consegui receber '%s'. Mande de novo, por favor."
RECUSA = "Não aceitei '%s': %s."
SEM_ANTIVIRUS = ("Recebi '%s', mas o nosso verificador de segurança está fora do ar e não posso aceitar arquivo "
                 "sem conferir. O suporte já foi avisado. Guardei o arquivo e aviso aqui quando ele entrar; não "
                 "precisa mandar de novo.")
AV_EXPIROU = ("O verificador não voltou e o arquivo '%s' não entrou no chamado %s. O suporte está cuidando; "
              "mande de novo mais tarde.")
NAO_ANOTOU = "Não consegui anotar os arquivos no chamado %s. Mande de novo mais tarde, por favor."


def _ajuste(con, chave, padrao):
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (chave,)).fetchone()
    return padrao if r is None else r["valor"]


def ligado(con) -> bool:
    return _ajuste(con, "pendencias.arquivo_volta", False) is True


def _minutos(con) -> timedelta:
    return timedelta(minutes=int(_ajuste(con, "pendencias.rajada_minutos", 5) or 5))


def arquivo_da_mensagem(e) -> dict | None:
    """O que se sabe do arquivo antes de baixar. Documento (qualquer um: o ERP decide o tipo) ou foto;
    video, audio e figurinha nao voltam (spec, Fora)."""
    if e.documento is not None:
        return {"media_id": e.documento.id, "mime": e.documento.mime or "",
                "nome": (Path((e.documento.nome_arquivo or "").replace("\\", "/")).name or "documento")[:200],
                "tipo": "documento"}
    if e.midia is not None and e.midia.tipo == "foto":
        mime = (e.midia.mime or "image/jpeg").split(";")[0].strip().lower()
        return {"media_id": e.midia.id, "mime": mime, "nome": "foto-%s%s" % (e.wamid[-6:], EXT_FOTO.get(mime, ".jpg")),
                "tipo": "foto"}
    return None


def _enviada(con, w, para, resumo):
    con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'texto', %s)",
                (w, para, resumo[:200]))


def _dizer(con, saida, para, texto, resumo):
    _enviada(con, saida.texto(para, texto), para, resumo)


def _do_campo(con, numero: str) -> bool:
    """Quem usa o canal de campo: para essa pessoa, foto sem deslizar e foto de campo (spec, D1)."""
    from . import campo
    return campo.ligado(con) and campo.quem_e(con, numero) is not None


def _rajada_aberta(con, numero: str, agora: datetime):
    return con.execute("""SELECT m.* FROM atendimento.pendencias_mensagens m
                            JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                           WHERE p.para_whatsapp = %s AND m.estado = 'rajada' AND m.entregar_apos > %s
                           ORDER BY m.id DESC LIMIT 1""", (com_nove(numero), agora)).fetchone()


def _cheia_recente(con, numero: str, agora: datetime) -> bool:
    """A rajada que fechou pelo teto (10) ha menos de 5 min: o 11o arquivo e recusado, nao abre outra."""
    teto = int(_ajuste(con, "pendencias.rajada_teto", 10) or 10)
    r = con.execute("""SELECT count(a.*) AS n, max(a.criado_em) AS ultima
                         FROM atendimento.pendencias_mensagens m
                         JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                         JOIN atendimento.pendencias_mensagens a ON a.rajada_id = m.id
                        WHERE p.para_whatsapp = %s AND m.classe = 'resposta' AND m.sentido = 'entrou'
                          AND m.id = (SELECT max(m2.rajada_id) FROM atendimento.pendencias_mensagens m2
                                        JOIN atendimento.pendencias p2 ON p2.id = m2.pendencia_id
                                       WHERE p2.para_whatsapp = %s AND m2.rajada_id IS NOT NULL)""",
                    (com_nove(numero), com_nove(numero))).fetchone()
    return bool(r and r["n"] >= teto and r["ultima"] and agora - r["ultima"] < _minutos(con))


def _do_dia(con, numero: str, agora: datetime) -> int:
    return con.execute("""SELECT count(*) AS n FROM atendimento.pendencias_mensagens m
                            JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                           WHERE p.para_whatsapp = %s AND m.classe = 'arquivo' AND m.sentido = 'entrou'
                             AND m.estado NOT IN ('escolher', 'descartada') AND m.criado_em > %s""",
                       (com_nove(numero), agora - timedelta(hours=24))).fetchone()["n"]


def _linha(con, pendencia_id: int, a: dict, estado: str, agora: datetime, rajada_id=None) -> int:
    return con.execute("""INSERT INTO atendimento.pendencias_mensagens
                              (pendencia_id, sentido, classe, texto, estado, arquivo, rajada_id, criado_em)
                          VALUES (%s, 'entrou', 'arquivo', %s, %s, %s, %s, %s) RETURNING id""",
                       (pendencia_id, a["nome"][:4000], estado, Jsonb(a), rajada_id, agora)).fetchone()["id"]


def _recusar_aqui(con, saida, para, p, a, motivo, frase, agora, mid=None) -> None:
    """A recusa que nao precisa do ERP (limite, Meta). Fica o rastro (regra 5), e a frase sai na hora."""
    a = dict(a, motivo=motivo, texto=frase, avisado=True)
    if mid:
        con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'arquivo_recusado', arquivo = %s WHERE id = %s",
                    (Jsonb(a), mid))
    else:
        _linha(con, p["id"], a, "arquivo_recusado", agora)
    _dizer(con, saida, para, frase, "pendencia %d: arquivo recusado (%s)" % (p["id"], motivo))


def _cabeca(con, p, numero: str, agora: datetime):
    """A rajada aberta deste chamado, ou uma nova. A rajada aberta de OUTRO chamado fecha aqui."""
    cab = _rajada_aberta(con, numero, agora)
    if cab and cab["pendencia_id"] == p["id"]:
        return cab
    if cab:
        con.execute("UPDATE atendimento.pendencias_mensagens SET entregar_apos = %s WHERE id = %s", (agora, cab["id"]))
    return con.execute("""INSERT INTO atendimento.pendencias_mensagens
                              (pendencia_id, sentido, classe, texto, estado, entregar_apos, criado_em)
                          VALUES (%s, 'entrou', 'resposta', '', 'rajada', %s, %s) RETURNING *""",
                       (p["id"], agora + _minutos(con), agora)).fetchone()


def entrar(con, saida, para: str, numero: str, p, a: dict, agora: datetime, mid: int | None = None) -> bool:
    """O arquivo vai a pendencia `p`: limites, download para o transito, sha256, e a rajada."""
    if int(_do_dia(con, numero, agora)) >= int(_ajuste(con, "pendencias.arquivo_dia_teto", 20) or 20):
        _recusar_aqui(con, saida, para, p, a, "teto_dia", TETO_DIA % a["nome"], agora, mid)
        return True
    if _cheia_recente(con, numero, agora):
        _recusar_aqui(con, saida, para, p, a, "teto_rajada", TETO_RAJADA % a["nome"], agora, mid)
        return True
    tamanho = None
    try:
        tamanho = saida.tamanho_da_midia(a["media_id"])
    except Exception:  # noqa: BLE001 -- sem o tamanho declarado, confere-se o real depois de baixar
        tamanho = None
    if tamanho and tamanho > MAX_BYTES:
        _recusar_aqui(con, saida, para, p, a, "tamanho", GRANDE % a["nome"], agora, mid)
        return True
    if PASTA is None:
        raise RuntimeError("arquivo_volta.PASTA nao foi posta pelo recepcionista")
    destino = PASTA / (uuid.uuid4().hex + (Path(a["nome"]).suffix.lower()[:8] or ".bin"))
    try:
        dados = Path(saida.baixar(a["media_id"], destino)).read_bytes()
    except Exception as falha:  # noqa: BLE001 -- a Meta nao entregou: a pessoa manda de novo
        print("arquivo_volta: baixar %s: %s" % (a["media_id"], falha), flush=True)
        destino.unlink(missing_ok=True)
        _recusar_aqui(con, saida, para, p, a, "baixar", NAO_BAIXOU % a["nome"], agora, mid)
        return True
    if len(dados) > MAX_BYTES or not dados:
        destino.unlink(missing_ok=True)
        _recusar_aqui(con, saida, para, p, a, "tamanho", GRANDE % a["nome"], agora, mid)
        return True
    cab = _cabeca(con, p, numero, agora)
    a = dict(a, caminho=str(destino), tamanho=len(dados), sha256=hashlib.sha256(dados).hexdigest())
    if mid:
        con.execute("""UPDATE atendimento.pendencias_mensagens SET pendencia_id = %s, estado = 'arquivo_a_validar',
                              arquivo = %s, rajada_id = %s WHERE id = %s""", (p["id"], Jsonb(a), cab["id"], mid))
    else:
        _linha(con, p["id"], a, "arquivo_a_validar", agora, cab["id"])
    n = con.execute("SELECT count(*) AS n FROM atendimento.pendencias_mensagens WHERE rajada_id = %s",
                    (cab["id"],)).fetchone()["n"]
    fecha = agora if n >= int(_ajuste(con, "pendencias.rajada_teto", 10) or 10) else agora + _minutos(con)
    con.execute("UPDATE atendimento.pendencias_mensagens SET entregar_apos = %s WHERE id = %s", (fecha, cab["id"]))
    return True


def tratar(con, saida, e, agora: datetime) -> bool:
    """Chamado de `pendencias.tratar`, depois dos toques. True = tratado aqui."""
    if not ligado(con):
        return False
    from . import pendencias as P
    numero, para = e.pessoa.wa_id or "", e.pessoa.para
    a = arquivo_da_mensagem(e)
    if a is None:
        # o texto logo depois dos arquivos fecha a rajada e vira o texto do comentario (D3)
        if e.texto and not e.toque:
            cab = _rajada_aberta(con, numero, agora)
            if cab is None:
                return False
            if e.contexto and not con.execute(
                    """SELECT 1 FROM atendimento.pendencias_mensagens WHERE wamid = %s AND sentido = 'saiu'
                         AND pendencia_id = %s""", (e.contexto, cab["pendencia_id"])).fetchone():
                con.execute("UPDATE atendimento.pendencias_mensagens SET entregar_apos = %s WHERE id = %s",
                            (agora, cab["id"]))
                return False   # citou outro assunto: a rajada fecha calada e o texto segue o caminho dele
            con.execute("UPDATE atendimento.pendencias_mensagens SET texto = %s, entregar_apos = %s WHERE id = %s",
                        (e.texto[:4000], agora, cab["id"]))
            return True
        return False
    if con.execute("SELECT 1 FROM atendimento.pendencias_mensagens WHERE arquivo->>'wamid' = %s",
                   (e.wamid,)).fetchone():
        return True   # a Meta reenviou o aviso
    a.update(wamid=e.wamid, quem=(e.pessoa.nome or "")[:80])
    if e.contexto:
        alvo = [dict(r) for r in con.execute(
            """SELECT DISTINCT p.* FROM atendimento.pendencias_mensagens m
                 JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                WHERE m.wamid = %s AND m.sentido = 'saiu' AND p.tipo = 'chamado'""", (e.contexto,)).fetchall()]
        alvo = [p for p in alvo if p["para_whatsapp"] == com_nove(numero)]
        if not alvo:
            return False   # citou outra coisa, ou e de outro numero: nada baixado (regra 1)
        esperando = [p for p in alvo if p["espera"] == "resposta"]
        if not esperando:
            _dizer(con, saida, para, NAO_ESPERA, "pendencia %d: arquivo sem pergunta aberta" % alvo[0]["id"])
            return True
        return entrar(con, saida, para, numero, esperando[0], a, agora)
    cab = _rajada_aberta(con, numero, agora)
    if cab is not None:
        p = P.pendencia(con, cab["pendencia_id"], numero)
        if p and p["espera"] == "resposta":
            return entrar(con, saida, para, numero, p, a, agora)
    pend = [p for p in P.pendencias_da_pessoa(con, numero) if p["espera"] == "resposta" and p["tipo"] == "chamado"]
    if not pend:
        return False
    if a["tipo"] == "foto" and _do_campo(con, numero):
        return False   # foto de campo continua foto de campo (spec, D1)
    p = pend[0]
    mid = _linha(con, p["id"], a, "escolher", agora)
    opcoes = [Opcao("pend:sim:%d" % mid, "Sim")]
    if len(pend) > 1:
        opcoes.append(Opcao("pend:lista:%d" % mid, "Outro chamado"))
    opcoes.append(Opcao("pend:outro:%d" % mid, "Outro assunto"))
    w = saida.botoes(para, "É para o %s?" % P.rotulo(p), opcoes)
    con.execute("INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo) VALUES (%s, %s, 'botoes', %s)",
                (w, para, "pendencia %d: arquivo e para?" % p["id"]))
    return True


def escolhido(con, saida, para: str, numero: str, m, p, agora: datetime) -> None:
    """A pessoa tocou Sim (ou escolheu o chamado na lista) para o arquivo guardado em `m`."""
    a = dict(m["arquivo"] or {})
    if p is None or p["espera"] != "resposta":
        con.execute("UPDATE atendimento.pendencias_mensagens SET estado = 'descartada' WHERE id = %s", (m["id"],))
        _dizer(con, saida, para, NAO_ESPERA, "pendencia: arquivo sem pergunta aberta")
        return
    entrar(con, saida, para, numero, p, a, agora, mid=m["id"])


def entrada_guardada(con, m, pessoa):
    """O "Outro assunto" do arquivo: a mensagem original, relida do aviso da Meta, segue a corrente de
    sempre (a logo, o campo...). Sem o aviso, None."""
    from . import motor
    wamid = (m["arquivo"] or {}).get("wamid")
    ev = con.execute("""SELECT corpo FROM atendimento.eventos_meta WHERE tipo = 'mensagem'
                          AND corpo->'msg'->>'id' = %s ORDER BY id DESC LIMIT 1""", (wamid,)).fetchone() if wamid else None
    if not ev:
        return None
    corpo = ev["corpo"] or {}
    e = motor.ler_mensagem({"contacts": corpo.get("contacts") or []}, corpo.get("msg") or {})
    e.pessoa = pessoa
    return e


# ── o que sai: as frases que dependem do ERP ────────────────────────────────

def mandar(con, saida, agora: datetime) -> int:
    """A volta do minuto (RECEPCIONISTA): a recusa que o ERP deu, o aviso de "sem antivirus" a pessoa, e a
    confirmacao da rajada que o ERP gravou. Roda mesmo com a chave desligada: o que ja estava no caminho
    termina (spec, ROLLBACK_PLAN 2)."""
    feitas = 0
    for m in con.execute("""SELECT m.id, m.estado, m.arquivo, p.referencia, p.para_whatsapp FROM atendimento.pendencias_mensagens m
                              JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                             WHERE m.classe = 'arquivo' AND (
                                   (m.estado = 'arquivo_recusado' AND coalesce(m.arquivo->>'avisado', '') = '')
                                OR (m.estado = 'arquivo_a_validar' AND m.arquivo ? 'av_desde'
                                    AND coalesce(m.arquivo->>'av_avisado', '') = ''))
                             ORDER BY m.id""").fetchall():
        a = dict(m["arquivo"] or {})
        if m["estado"] == "arquivo_recusado":
            frase = (AV_EXPIROU % (a.get("nome"), m["referencia"]) if a.get("motivo") == "antivirus_expirou"
                     else RECUSA % (a.get("nome"), (a.get("texto") or "não foi aceito").rstrip(".")))
            marca = {"avisado": True}
        else:
            frase, marca = SEM_ANTIVIRUS % a.get("nome"), {"av_avisado": True}
        try:
            _dizer(con, saida, m["para_whatsapp"], frase, "pendencia: arquivo %s" % m["estado"])
        except Exception as falha:  # noqa: BLE001 -- tenta na volta seguinte
            print("arquivo_volta: frase da mensagem %d: %s" % (m["id"], falha), flush=True)
            continue
        con.execute("UPDATE atendimento.pendencias_mensagens SET arquivo = arquivo || %s WHERE id = %s",
                    (Jsonb(marca), m["id"]))
        feitas += 1
    for c in con.execute("""SELECT m.id, m.arquivo, p.referencia, p.para_whatsapp FROM atendimento.pendencias_mensagens m
                              JOIN atendimento.pendencias p ON p.id = m.pendencia_id
                             WHERE m.estado = 'confirmar' ORDER BY m.id""").fetchall():
        info = dict(c["arquivo"] or {})
        if info.get("erro"):
            frase = NAO_ANOTOU % c["referencia"]
        else:
            nomes = [r["arquivo"]["nome"] for r in con.execute(
                """SELECT arquivo FROM atendimento.pendencias_mensagens WHERE rajada_id = %s AND estado = 'entregue'
                    ORDER BY id""", (c["id"],)).fetchall()]
            recusados = con.execute("""SELECT count(*) AS n FROM atendimento.pendencias_mensagens
                                        WHERE rajada_id = %s AND estado = 'arquivo_recusado'""", (c["id"],)).fetchone()["n"]
            if nomes:
                frase = "Anotado no chamado %s: %d %s. ✓" % (c["referencia"], len(nomes),
                                                            "arquivo" if len(nomes) == 1 else "arquivos")
                if recusados:
                    frase += "\nEntraram: %s." % ", ".join(nomes)
            else:
                frase = "Anotado no chamado %s. ✓" % c["referencia"]
        try:
            _dizer(con, saida, c["para_whatsapp"], frase, "pendencia: arquivos anotados")
        except Exception as falha:  # noqa: BLE001
            print("arquivo_volta: confirmacao %d: %s" % (c["id"], falha), flush=True)
            continue
        con.execute("UPDATE atendimento.pendencias_mensagens SET estado = %s WHERE id = %s",
                    ("erro" if info.get("erro") else "entregue", c["id"]))
        feitas += 1
    return feitas
