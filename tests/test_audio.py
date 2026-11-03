"""#1238, passos 8 e 9: o audio de interno vira texto na maquina. O transcritor e FALSO (nenhum modelo e
carregado); a Meta e a IA tambem."""
import threading
from datetime import timedelta

import pytest

from backend import audio, recepcionista as R
from backend.banco import conexao
from backend.motor import NAO_ABRO_ARQUIVO
from tests.saida_falsa import SaidaFalsa
from tests.test_campo import AGORA, CLIENTE, EQUIPE, canal, ligar, passo  # noqa: F401 -- `canal` e fixture
from tests.test_roteador import Aponta, chamado, entrou


def mensagem_de_audio(wamid, numero=EQUIPE):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "audio",
            "audio": {"id": "midia-" + wamid, "mime_type": "audio/ogg; codecs=opus", "voice": True}}


class Transcritor:
    modelo = "falso"

    def __init__(self, texto="o cliente quer o preço do centeio", duracao=12.0):
        self.texto, self.duracao, self.ouvidos = texto, duracao, []

    def __call__(self, caminho, maximo):
        self.ouvidos.append(caminho)
        if self.duracao > maximo:
            return None, self.duracao
        return self.texto, self.duracao


@pytest.fixture
def ligado(canal):
    ligar(canal)
    with conexao(canal) as con:
        con.execute("UPDATE atendimento.ajustes SET valor = 'true'::jsonb WHERE chave = 'audio.transcrever'")
    return canal


def audios(cfg):
    with conexao(cfg) as con:
        return [dict(r) for r in con.execute("SELECT * FROM atendimento.audios ORDER BY id").fetchall()]


def test_o_audio_de_interno_e_baixado_e_nada_e_respondido(ligado):
    s = SaidaFalsa()
    passo(ligado, s, mensagem_de_audio("wa1"))
    a = audios(ligado)
    assert len(a) == 1 and a[0]["arquivo"].startswith("audio/") and a[0]["arquivo"].endswith("wa1.ogg")
    assert (ligado.campo_pasta / a[0]["arquivo"]).read_bytes() == b"MIDIA:midia-wa1"
    assert s.enviadas == []


def test_o_audio_de_fora_continua_sem_leitura(ligado):
    s = SaidaFalsa()
    passo(ligado, s, mensagem_de_audio("wa2", numero=CLIENTE), numero=CLIENTE, bsuid="BR.cliente")
    assert audios(ligado) == [] and s.ultima[2] == NAO_ABRO_ARQUIVO


def test_chave_desligada_o_audio_de_interno_e_ignorado_como_hoje(canal):
    ligar(canal)
    s = SaidaFalsa()
    passo(canal, s, mensagem_de_audio("wa3"))
    assert audios(canal) == [] and s.enviadas == []


def test_download_falho_guarda_o_erro_e_segue_o_de_hoje(ligado):
    s = SaidaFalsa()
    s.baixar_falha = True
    passo(ligado, s, mensagem_de_audio("wa4"))
    a = audios(ligado)
    assert a[0]["arquivo"] is None and "nao entregou" in a[0]["erro"] and s.enviadas == []


def test_o_texto_transcrito_entra_na_corrente_e_chega_ao_chamado(ligado):
    s = SaidaFalsa()
    with conexao(ligado) as con:
        for chave, valor in (("pendencias.ligado", "true"), ("roteador.ligado", "true")):
            con.execute("UPDATE atendimento.ajustes SET valor = %s::jsonb WHERE chave = %s", (valor, chave))
    chamado(ligado)
    passo(ligado, s, mensagem_de_audio("wa5"))
    t = Transcritor()
    assert audio.transcrever_um(ligado, t, agora=AGORA) is True
    assert audio.transcrever_um(ligado, t, agora=AGORA) is False   # a fila esvaziou
    a = audios(ligado)[0]
    assert a["texto"] == "o cliente quer o preço do centeio" and a["duracao_s"] == 12
    with conexao(ligado) as con:
        ev = con.execute("SELECT corpo FROM atendimento.eventos_meta WHERE chave_meta = 'wa5:transcrito'").fetchone()
        uso = con.execute("SELECT * FROM atendimento.uso_ia WHERE servico = 'local'").fetchone()
    assert ev["corpo"]["msg"]["text"]["body"] == "(áudio) o cliente quer o preço do centeio"
    assert uso["funcao"] == "audio" and uso["entrada"] == 12
    ia = Aponta({"destino": "Chamado 1222", "sinal": "nomeado"})
    R.processar_pendentes(ligado, s, ia, agora=AGORA + timedelta(seconds=20),
                          campo=__import__("backend.campo", fromlist=["Campo"]).Campo(ligado.campo_pasta, ia))
    assert entrou(ligado)[0]["texto"] == "(áudio) o cliente quer o preço do centeio"
    assert s.ultima[2] == "Anotado no chamado 1222. ✓"


def test_audio_acima_do_maximo_nao_e_transcrito(ligado):
    passo(ligado, SaidaFalsa(), mensagem_de_audio("wa6"))
    audio.transcrever_um(ligado, Transcritor(duracao=400.0), agora=AGORA)
    a = audios(ligado)[0]
    assert a["transcrito_em"] is None and a["erro"].startswith("acima do maximo")
    with conexao(ligado) as con:
        assert con.execute("SELECT 1 FROM atendimento.eventos_meta WHERE chave_meta = 'wa6:transcrito'").fetchone() is None


def test_o_ogg_sai_7_dias_depois_e_o_texto_fica(ligado):
    passo(ligado, SaidaFalsa(), mensagem_de_audio("wa7"))
    audio.transcrever_um(ligado, Transcritor(), agora=AGORA)
    a = audios(ligado)[0]
    arquivo = ligado.campo_pasta / a["arquivo"]
    with conexao(ligado) as con:
        assert audio.limpar(ligado, con, AGORA + timedelta(days=6)) == 0
        assert audio.limpar(ligado, con, AGORA + timedelta(days=8)) == 1
    assert not arquivo.exists() and audios(ligado)[0]["texto"] and audios(ligado)[0]["apagado_em"] is not None


def test_sem_a_biblioteca_o_laco_loga_uma_vez_e_nao_morre(ligado, tmp_path, monkeypatch, capsys):
    (tmp_path / "modelo").mkdir()
    (tmp_path / "modelo" / "model.bin").write_bytes(b"x")
    from dataclasses import replace
    cfg = replace(ligado, audio_modelo_pasta=tmp_path / "modelo")

    def sem_biblioteca(pasta):
        raise ImportError("No module named 'faster_whisper'")
    monkeypatch.setattr(audio, "Whisper", sem_biblioteca)
    parar = threading.Event()
    t = threading.Thread(target=audio.laco, args=(cfg, parar), kwargs={"espera": 0.05})
    t.start()
    threading.Event().wait(0.5)
    parar.set()
    t.join(2)
    assert not t.is_alive()
    assert capsys.readouterr().out.count("faster-whisper nao instalado") == 1


def test_achar_modelo_na_copia_do_cache(tmp_path):
    snap = tmp_path / "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo" / "snapshots" / "abc"
    snap.mkdir(parents=True)
    (snap / "model.bin").write_bytes(b"x")
    assert audio.achar_modelo(tmp_path) == snap
    assert audio.achar_modelo(tmp_path / "nao_existe") is None
