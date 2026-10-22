"""A Saida dos testes: guarda o que teria saido para a Meta e devolve wamids falsos."""
from itertools import count

from backend.saida import Saida, conferir_botoes, conferir_lista


class SaidaFalsa(Saida):
    def __init__(self):
        self.enviadas = []
        self.modelos = []
        self._n = count(1)

    def _id(self):
        return "wamid.saida.%d" % next(self._n)

    def texto(self, para, texto):
        self.enviadas.append(("texto", para, texto, []))
        return self._id()

    def botoes(self, para, texto, opcoes):
        conferir_botoes(opcoes)
        self.enviadas.append(("botoes", para, texto, [(o.id, o.titulo) for o in opcoes]))
        return self._id()

    def lista(self, para, texto, botao, opcoes):
        conferir_lista(opcoes)
        self.enviadas.append(("lista", para, texto, [(o.id, o.titulo) for o in opcoes]))
        return self._id()

    def imagem(self, para, arquivo, legenda=""):
        self.enviadas.append(("imagem", para, arquivo, []))
        return self._id()

    def contato(self, para, nome, whatsapp, empresa="Sementes Renascer"):
        self.enviadas.append(("contato", para, nome, [whatsapp]))
        return self._id()

    def baixar(self, media_id, destino):
        from pathlib import Path
        if getattr(self, "baixar_falha", False):
            raise RuntimeError("a Meta nao entregou a midia")
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"MIDIA:" + media_id.encode())
        self.baixadas = getattr(self, "baixadas", []) + [(media_id, str(destino))]
        return str(destino)

    def modelo(self, para, nome, idioma, corpo, imagem=None, botoes=None, url=None, documento=None):
        if getattr(self, "modelo_falha", None):
            raise RuntimeError(self.modelo_falha)
        self.enviadas.append(("modelo", para, nome, list(corpo)))
        self.modelos.append({"para": para, "nome": nome, "corpo": list(corpo), "imagem": imagem,
                             "botoes": botoes, "url": url, "documento": documento})
        return self._id()

    def documento(self, para, dados, nome, legenda="", opcoes=None):
        if opcoes:
            conferir_botoes(opcoes)
        self.enviadas.append(("documento", para, legenda, [(o.id, o.titulo) for o in opcoes or []]))
        self.documentos = getattr(self, "documentos", []) + [(para, dados, nome)]
        return self._id()

    @property
    def ultima(self):
        return self.enviadas[-1]


class IAFalsa:
    def __init__(self, resposta=None, falha=False, campo=None):
        self.resposta, self.falha, self.perguntas = resposta, falha, []
        self.campo, self.frases = campo, []   # #970: o que `ler_campo` devolve, e as frases lidas
        self.bastidores_vistos = []           # #1048: as chaves que o cadastro entregou ao modelo

    def ler_campo(self, texto, produtos, bastidores=None):
        self.frases.append(texto)
        self.bastidores_vistos.append([b["chave"] for b in (bastidores or [])])
        if self.falha:
            raise TimeoutError("a IA demorou")
        if isinstance(self.campo, list):   # uma leitura por frase, na ordem
            return self.campo.pop(0) if self.campo else None
        return self.campo

    def triar(self, pdf, vaga):
        """#1098: a pre-triagem; `self.triagem` e o que ela devolve (None = a IA nao respondeu)."""
        self.triados = getattr(self, "triados", []) + [(pdf, vaga["titulo"])]
        if self.falha:
            raise TimeoutError("a IA demorou")
        return getattr(self, "triagem", None)

    def classificar(self, texto, opcoes):
        self.perguntas.append(texto)
        self.opcoes = getattr(self, "opcoes", []) + [[o["chave"] for o in opcoes]]   # #988: o que ela viu
        if self.falha:
            raise TimeoutError("a IA demorou")
        return self.resposta
