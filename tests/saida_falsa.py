"""A Saida dos testes: guarda o que teria saido para a Meta e devolve wamids falsos."""
from itertools import count

from backend.saida import Saida, conferir_botoes, conferir_lista


class SaidaFalsa(Saida):
    def __init__(self):
        self.enviadas = []
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

    def modelo(self, para, nome, idioma, corpo, imagem=None, botoes=None):
        self.enviadas.append(("modelo", para, nome, list(corpo)))
        return self._id()

    @property
    def ultima(self):
        return self.enviadas[-1]


class IAFalsa:
    def __init__(self, resposta=None, falha=False):
        self.resposta, self.falha, self.perguntas = resposta, falha, []

    def classificar(self, texto, opcoes):
        self.perguntas.append(texto)
        if self.falha:
            raise TimeoutError("a IA demorou")
        return self.resposta
