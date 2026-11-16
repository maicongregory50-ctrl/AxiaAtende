"""O AUDIO de quem e da casa vira texto, NA MAQUINA (#1238, dono 03/11/2026: "mais a transcricao de audio").

O CAMINHO:
1. `receber` (o motor, para interno com a chave `audio.transcrever` ligada): baixa o audio da Meta para
   `<campo_pasta>/audio/<dia>/<wamid>.ogg` e grava a linha em `atendimento.audios`. NAO responde: a resposta
   vem com a transcricao, do fio onde o texto entrar.
2. `laco` (uma thread propria do recepcionista, ao lado do trabalhador; o motor nunca espera): um audio por
   vez, na CPU, com o modelo carregado uma vez (faster-whisper large-v3-turbo, int8). Transcrito, o texto
   entra na corrente por um EVENTO SINTETICO em `eventos_meta` -- `chave_meta = <wamid>:transcrito`, tipo
   texto, corpo "(audio) " + texto, o mesmo `from` e a mesma hora do audio --, e o trabalhador o trata como
   qualquer texto da pessoa (o roteador inclusive). Nada no motor muda para isso.
3. O `.ogg` some 7 dias depois de transcrito (`limpar`, na rotina do minuto); o texto fica no banco.

O AUDIO DE FORA (#1520, D10, dono 16/11/2026: "Precisamos adicionar audio, ja temos a ferramenta"): o de
quem a OlivIA atende (nao e da casa, nem cliente da carteira, nem consultor) entra na MESMA fila, marcado
`de_fora`, so com as tres chaves ligadas -- `OLIVIA_FALA`, `audio.transcrever` e `audio.de_fora` (nasce
`false`) -- o modelo presente e o numero abaixo de `audio.de_fora_por_dia` em 24 h. A lingua e detectada
(portugues ou espanhol); o da casa passa na frente. Quando a transcricao do de fora falha, passa do teto de
duracao ou sai vazia, o evento entra com `NAO_OUVI`, para a pessoa nao ficar sem resposta. Fora disso, o
de fora continua com a linha fixa de quem nao le audio. O cliente da carteira e o consultor ficam de fora.

O QUE NAO FAZ: o SOM nunca sai da maquina (o modelo e local, pela conta LocalService do recepcionista); o
TEXTO transcrito de quem e de fora entra na chamada da OlivIA, como o texto que ele digita. Sem modelo no
disco, sem a biblioteca, chave desligada, erro ou audio acima de `audio.maximo_s`, no audio DA CASA: o
comportamento de sempre (ignorado, linha no log), e a linha em `audios` guarda o `erro`.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import internos
from .banco import conexao

MODELO = "faster-whisper-large-v3-turbo"
GUARDAR = timedelta(days=7)
MARCA = "(áudio) "
NAO_OUVI = "[não foi possível ouvir o áudio]"   # #1520: o de fora que nao deu para transcrever
ESPERA_S = 3.0
DE_FORA_POR_DIA = 6

# O que o /saude mostra. Zera a cada subida do recepcionista.
estado = {"modelo_presente": None, "ultimo_transcrito_em": None, "ultimo_erro": None}


def _ajuste(con, chave, padrao):
    r = con.execute("SELECT valor FROM atendimento.ajustes WHERE chave = %s", (chave,)).fetchone()
    return padrao if r is None else r["valor"]


def ligado(con) -> bool:
    return _ajuste(con, "audio.transcrever", False) is True


def de_fora_ligado(con) -> bool:
    """#1520: a chave do audio de quem e de fora (`audio.de_fora`, nasce false)."""
    return _ajuste(con, "audio.de_fora", False) is True


def de_fora_por_dia(con) -> int:
    try:
        return int(_ajuste(con, "audio.de_fora_por_dia", DE_FORA_POR_DIA) or DE_FORA_POR_DIA)
    except (TypeError, ValueError):
        return DE_FORA_POR_DIA


def maximo_s(con) -> int:
    try:
        return int(_ajuste(con, "audio.maximo_s", 180) or 180)
    except (TypeError, ValueError):
        return 180


def achar_modelo(pasta: Path, ambiente: str = "producao") -> Path | None:
    """A pasta com o `model.bin`: a propria, uma de dentro, ou o `snapshots\\<hash>` da copia do cache do
    Hugging Face. Fora de producao procura tambem no cache do perfil de quem roda (o ensaio da sessao)."""
    bases = [Path(pasta)]
    if ambiente != "producao":
        bases.append(Path.home() / ".cache" / "huggingface" / "hub")
    for base in bases:
        if not base.is_dir():
            continue
        if (base / "model.bin").is_file():
            return base
        for padrao in ("*/model.bin", "*/snapshots/*/model.bin", "snapshots/*/model.bin"):
            achados = sorted(p for p in base.glob(padrao) if "whisper" in str(p).lower() or padrao.startswith("snap"))
            if achados:
                return achados[0].parent
    return None


class Whisper:
    """O transcritor de verdade. So o recepcionista (e o `scripts/audio.py ensaiar`) o carrega: o teste
    injeta um falso e nao toca no modelo."""
    modelo = MODELO

    def __init__(self, pasta: Path):
        from faster_whisper import WhisperModel   # so aqui: sem a biblioteca, o laco loga e dorme
        self._m = WhisperModel(str(pasta), device="cpu", compute_type="int8")

    def __call__(self, caminho: Path, maximo: int, lingua: str | None = "pt"):
        """(texto, duracao_s); texto None quando o audio passa de `maximo` segundos (nada e transcrito).
        `lingua` None (#1520, o audio de fora): o modelo detecta (portugues ou espanhol)."""
        segmentos, info = self._m.transcribe(decodificar(caminho), language=lingua, vad_filter=True)
        if info.duration > maximo:
            return None, info.duration
        return " ".join(s.text.strip() for s in segmentos).strip(), info.duration


# ── 1. a chegada (o motor) ───────────────────────────────────────────────────────────────────────────

def decodificar(caminho: Path):
    """O audio em 16 kHz mono float32, decodificado aqui e nao pelo `decode_audio` do faster-whisper:
    o 1.2.1 passa `metadata_errors` ao `av.open`, e o av 15+ nao aceita mais (TypeError no 1o audio
    real, 04/11/2026, #1238)."""
    import av
    import numpy as np
    pedacos = []
    reamostra = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=16000)
    with av.open(str(caminho), mode="r") as c:
        for quadro in c.decode(audio=0):
            pedacos.extend(q.to_ndarray() for q in reamostra.resample(quadro))
        pedacos.extend(q.to_ndarray() for q in reamostra.resample(None))
    if not pedacos:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(pedacos, axis=1).reshape(-1).astype(np.float32) / 32768.0


def _nome_seguro(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", texto or "")[:120] or "sem_nome"


def aceita_de_fora(con, e, agora: datetime, olivia=None, envio=None) -> bool:
    """#1520 (B2): o audio de quem a OlivIA atende entra na fila? As tres chaves, o modelo nao ausente e o
    teto por numero em 24 h. Qualquer outro caso: False, e o motor segue para a linha fixa de hoje."""
    if olivia is None or not ligado(con) or not de_fora_ligado(con) or estado["modelo_presente"] is False:
        return False
    from . import olivia as olivia_mod
    if not olivia_mod.e_de_fora(con, e, agora, envio):
        return False
    n = con.execute("""SELECT count(*) AS n FROM atendimento.audios
                        WHERE de_fora AND wa_id = %s AND recebido_em > %s""",
                    (e.pessoa.wa_id, agora - timedelta(hours=24))).fetchone()["n"]
    if n >= de_fora_por_dia(con):
        print("audio: %s passou do teto de %d audios de fora em 24 h: a linha fixa" % (e.pessoa.wa_id, n), flush=True)
        return False
    return True


def receber(con, saida, e, agora: datetime, pasta: Path, olivia=None, envio=None, so_de_fora: bool = False) -> bool:
    """O audio de interno com a chave ligada -- ou, desde o #1520, o de quem a OlivIA atende com
    `audio.de_fora` ligada: baixado e na fila. True = tomado (nada mais responde agora). False = o
    caminho de hoje (chave desligada, teto, ou o download falhou -- a linha guarda o erro).
    `so_de_fora`: a chamada que o motor faz ANTES da conversa de vaga (o audio do candidato nao recebe
    "PDF ou foto"); o interno continua so na chamada de sempre."""
    a = getattr(e, "audio", None)
    if a is None or not ligado(con):
        return False
    interno = internos.e_interno(con, e.pessoa.wa_id)
    if interno and so_de_fora:
        return False
    de_fora = not interno
    if de_fora and not aceita_de_fora(con, e, agora, olivia, envio):
        return False
    if con.execute("SELECT 1 FROM atendimento.audios WHERE wamid = %s", (e.wamid,)).fetchone():
        return True   # o mesmo aviso de novo
    relativo, erro = "audio/%s/%s.ogg" % (agora.date().isoformat(), _nome_seguro(e.wamid)), ""
    try:
        saida.baixar(a.id, Path(pasta) / relativo)
    except Exception as falha:   # noqa: BLE001 -- o audio fica em eventos_meta; a linha diz o erro
        relativo, erro = None, ("%s: %s" % (type(falha).__name__, falha))[:300]
    con.execute("""INSERT INTO atendimento.audios (wamid, wa_id, bsuid, arquivo, mime, recebido_em, erro, de_fora)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (wamid) DO NOTHING""",
                (e.wamid, e.pessoa.wa_id, e.pessoa.bsuid, relativo, (a.mime or "")[:100], agora, erro, de_fora))
    print("audio: %s de %s%s: %s" % (e.wamid, e.pessoa.wa_id, " (de fora)" if de_fora else "",
                                     relativo or ("falhou -- " + erro)), flush=True)
    return relativo is not None


# ── 2. a transcricao (a thread do recepcionista) ─────────────────────────────────────────────────────

def _evento_sintetico(con, linha, texto: str) -> None:
    ev = con.execute("SELECT bsuid, corpo FROM atendimento.eventos_meta WHERE chave_meta = %s",
                     (linha["wamid"],)).fetchone()
    if ev is None:
        print("audio: o aviso de %s sumiu de eventos_meta; o texto fica so em audios" % linha["wamid"], flush=True)
        return
    original = (ev["corpo"] or {}).get("msg") or {}
    msg = {k: original[k] for k in ("from", "from_user_id", "timestamp") if k in original}
    msg.update(id=linha["wamid"], type="text", text={"body": MARCA + texto})
    con.execute("""INSERT INTO atendimento.eventos_meta (chave_meta, tipo, bsuid, corpo)
                   VALUES (%s, 'mensagem', %s, %s) ON CONFLICT (chave_meta) DO NOTHING""",
                (linha["wamid"] + ":transcrito", ev["bsuid"],
                 json.dumps({"contacts": (ev["corpo"] or {}).get("contacts") or [], "msg": msg})))


def transcrever_um(cfg, transcritor, agora: datetime | None = None) -> bool:
    """O proximo audio da fila. True = havia um (transcrito ou com erro); False = fila vazia."""
    with conexao(cfg) as con:
        # #1520 (B3): o da casa passa na frente do de fora (false vem antes de true)
        linha = con.execute("""SELECT * FROM atendimento.audios
                                WHERE transcrito_em IS NULL AND erro = '' AND arquivo IS NOT NULL
                                ORDER BY de_fora, id LIMIT 1""").fetchone()
        maximo = maximo_s(con)
    if linha is None:
        return False
    texto, duracao, erro = None, None, ""
    de_fora = bool(linha.get("de_fora"))
    try:   # FORA de transacao: a CPU trabalha segundos, e o banco nao fica preso por isso
        caminho = Path(cfg.campo_pasta) / linha["arquivo"]
        # o de fora sem lingua fixa (detectada: portugues ou espanhol); o da casa, "pt" como sempre
        texto, duracao = transcritor(caminho, maximo, lingua=None) if de_fora else transcritor(caminho, maximo)
        if texto is None:
            erro = "acima do maximo (%d s)" % maximo
    except Exception as falha:   # noqa: BLE001 -- um audio ruim nao trava a fila
        erro = ("%s: %s" % (type(falha).__name__, falha))[:300]
    momento = agora or datetime.now(timezone.utc)
    with conexao(cfg) as con:
        if erro:
            con.execute("UPDATE atendimento.audios SET erro = %s, duracao_s = %s WHERE id = %s",
                        (erro, duracao, linha["id"]))
            estado["ultimo_erro"] = "%s %s" % (momento.isoformat(), erro[:120])
            print("audio: %s: %s" % (linha["wamid"], erro), flush=True)
            if de_fora:   # #1520: a pessoa de fora nao fica sem resposta -- a OlivIA diz que nao ouviu
                _evento_sintetico(con, linha, NAO_OUVI)
            return True
        con.execute("UPDATE atendimento.audios SET transcrito_em = %s, texto = %s, duracao_s = %s WHERE id = %s",
                    (momento, texto, duracao, linha["id"]))
        if texto:
            _evento_sintetico(con, linha, texto)
        elif de_fora:
            _evento_sintetico(con, linha, NAO_OUVI)
        # o custo e zero; a duracao e o que mede a CPU (#1223, tela Custos)
        con.execute("""INSERT INTO atendimento.uso_ia (origem, servico, funcao, modelo, entrada, saida)
                       VALUES ('axiaatende', 'local', 'audio', %s, %s, %s)""",
                    (getattr(transcritor, "modelo", MODELO), int(round(duracao or 0)), len(texto or "")))
    estado["ultimo_transcrito_em"] = momento.isoformat()
    print("audio: %s transcrito (%.0f s, %d letras)" % (linha["wamid"], duracao or 0, len(texto or "")), flush=True)
    return True


def limpar(cfg, con, agora: datetime) -> int:
    """O `.ogg` sai 7 dias depois de transcrito (ou do erro); o texto fica."""
    feitos = 0
    for r in con.execute("""SELECT id, arquivo FROM atendimento.audios
                             WHERE apagado_em IS NULL AND arquivo IS NOT NULL
                               AND coalesce(transcrito_em, recebido_em) < %s
                               AND (transcrito_em IS NOT NULL OR erro <> '')
                             ORDER BY id LIMIT 50""", (agora - GUARDAR,)).fetchall():
        try:
            (Path(cfg.campo_pasta) / r["arquivo"]).unlink(missing_ok=True)
        except OSError as falha:
            print("audio: nao apaguei %s: %s" % (r["arquivo"], falha), flush=True)
            continue
        con.execute("UPDATE atendimento.audios SET apagado_em = %s WHERE id = %s", (agora, r["id"]))
        feitos += 1
    return feitos


def laco(cfg, parar, transcritor=None, espera: float = ESPERA_S) -> None:
    """A thread `transcritor` do recepcionista. Confere a chave a cada volta: desligada, solta o modelo
    (a memoria volta na proxima volta). Sem modelo no disco ou sem a biblioteca: loga UMA vez e dorme --
    nunca derruba o servico."""
    modelo, avisado = transcritor, None
    while not parar.wait(espera):
        try:
            with conexao(cfg) as con:
                on = ligado(con)
            if not on:
                if transcritor is None:
                    modelo = None
                continue
            if modelo is None:
                pasta = achar_modelo(cfg.audio_modelo_pasta, cfg.ambiente)
                estado["modelo_presente"] = pasta is not None
                if pasta is None:
                    if avisado != "sem modelo":
                        print("audio: sem modelo em %s: os audios esperam" % cfg.audio_modelo_pasta, flush=True)
                        avisado = "sem modelo"
                    continue
                try:
                    modelo = Whisper(pasta)
                except ImportError:
                    if avisado != "sem biblioteca":
                        print("audio: faster-whisper nao instalado no venv: os audios esperam", flush=True)
                        avisado = "sem biblioteca"
                    continue
                avisado = None
                print("audio: modelo carregado de %s" % pasta, flush=True)
            while not parar.is_set() and transcrever_um(cfg, modelo):
                pass
        except Exception as falha:   # noqa: BLE001 -- o laco nunca morre
            print("audio: %s: %s" % (type(falha).__name__, falha), flush=True)


def saude(cfg, con) -> dict:
    r = con.execute("""SELECT count(*) FILTER (WHERE transcrito_em IS NULL AND erro = '' AND arquivo IS NOT NULL) AS pendentes,
                              count(*) FILTER (WHERE transcrito_em IS NULL AND erro = '' AND arquivo IS NOT NULL
                                               AND de_fora) AS pendentes_de_fora,
                              max(transcrito_em) AS ultimo FROM atendimento.audios""").fetchone()
    presente = estado["modelo_presente"]
    if presente is None:
        presente = achar_modelo(cfg.audio_modelo_pasta, cfg.ambiente) is not None
    return {"ligado": ligado(con), "modelo_presente": presente, "pendentes": r["pendentes"],
            "ultimo_transcrito_em": r["ultimo"].isoformat() if r["ultimo"] else None,
            "ultimo_erro": estado["ultimo_erro"],
            # #1520: o audio de quem e de fora (a chave e a fila dele)
            "de_fora": de_fora_ligado(con), "pendentes_de_fora": r["pendentes_de_fora"]}
