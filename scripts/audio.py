"""#1238: liga, desliga ou mostra a TRANSCRICAO LOCAL de audio da equipe (a chave `audio.transcrever`), e
ENSAIA um arquivo: transcreve na janela e imprime o texto e o tempo (a medicao de CPU que a spec deixou "a
conferir"). Em producao, janela elevada:

    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\audio.py ver|ligar|desligar

O ensaio nao toca no banco e roda em qualquer ambiente:

    .\\.venv\\Scripts\\python.exe scripts\\audio.py ensaiar C:\\caminho\\do\\audio.ogg

Precisa do `faster-whisper` no venv e do modelo: em producao em `C:\\Dados\\AxiaAtende\\modelos`; fora de
producao tambem no cache do Hugging Face de quem roda.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import audio, config  # noqa: E402
from backend.banco import conexao  # noqa: E402


def ensaiar(cfg, arquivo: str) -> int:
    pasta = audio.achar_modelo(cfg.audio_modelo_pasta, cfg.ambiente)
    if pasta is None:
        print("modelo: NAO ACHEI em %s" % cfg.audio_modelo_pasta)
        return 1
    print("modelo: %s" % pasta)
    t0 = time.perf_counter()
    try:
        w = audio.Whisper(pasta)
    except ImportError:
        print("faster-whisper nao instalado neste venv")
        return 1
    carga = time.perf_counter() - t0
    t1 = time.perf_counter()
    texto, duracao = w(Path(arquivo), 10 ** 6)
    gasto = time.perf_counter() - t1
    print("carga do modelo: %.1f s" % carga)
    print("audio: %.1f s; transcricao: %.1f s (%.2f s por segundo de audio)" % (duracao, gasto, gasto / max(duracao, 0.1)))
    print("texto: %s" % texto)
    return 0


def main() -> int:
    args = sys.argv[1:] or ["ver"]
    acao = args[0]
    if acao not in ("ver", "ligar", "desligar", "ensaiar") or (acao == "ensaiar" and len(args) < 2):
        print("uso: audio.py ver|ligar|desligar | ensaiar <arquivo>")
        return 2
    cfg = config.carregar()
    if acao == "ensaiar":
        return ensaiar(cfg, args[1])
    with conexao(cfg) as con:
        if acao != "ver":
            con.execute("""UPDATE atendimento.ajustes SET valor = %s::jsonb, atualizado_em = now()
                            WHERE chave = 'audio.transcrever'""", ("true" if acao == "ligar" else "false",))
        s = audio.saude(cfg, con)
        n = con.execute("""SELECT count(*) FILTER (WHERE transcrito_em IS NOT NULL) AS transcritos,
                                  count(*) FILTER (WHERE erro <> '') AS com_erro,
                                  coalesce(sum(duracao_s) FILTER (WHERE transcrito_em IS NOT NULL), 0) AS segundos
                             FROM atendimento.audios""").fetchone()
    pasta = audio.achar_modelo(cfg.audio_modelo_pasta, cfg.ambiente)
    try:
        import faster_whisper  # noqa: F401
        biblioteca = "instalado"
    except ImportError:
        biblioteca = "NAO instalado"
    print("transcricao de audio: %s (ambiente %s)" % ("LIGADA" if s["ligado"] else "desligada", cfg.ambiente))
    print("modelo: %s" % (pasta or "NAO ACHEI em %s" % cfg.audio_modelo_pasta))
    print("faster-whisper: %s" % biblioteca)
    print("na fila: %d; transcritos: %d (%.0f min); com erro: %d"
          % (s["pendentes"], n["transcritos"], float(n["segundos"]) / 60, n["com_erro"]))
    print("ultimo transcrito: %s" % (s["ultimo_transcrito_em"] or "nenhum"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
