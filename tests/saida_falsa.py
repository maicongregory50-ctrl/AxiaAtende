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

    def imagem(self, para, arquivo, legenda="", opcoes=None):
        if opcoes:
            conferir_botoes(opcoes)
        self.enviadas.append(("imagem", para, arquivo, [(o.id, o.titulo) for o in opcoes or []]))
        self.legendas = getattr(self, "legendas", []) + [legenda]   # #1520: a legenda da foto a Fran
        return self._id()

    def contato(self, para, nome, whatsapp, empresa="Sementes Renascer"):
        self.enviadas.append(("contato", para, nome, [whatsapp]))
        return self._id()

    def tamanho_da_midia(self, media_id):
        return getattr(self, "tamanhos", {}).get(media_id)

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

    def link(self, para, texto, rotulo, url):
        from backend.saida import LIMITE_LINK
        assert len(rotulo) <= LIMITE_LINK, rotulo
        self.enviadas.append(("link", para, texto, [(rotulo, url)]))
        return self._id()

    def documento(self, para, dados, nome, legenda="", opcoes=None, mime_type="application/pdf"):
        if opcoes:
            conferir_botoes(opcoes)
        self.enviadas.append(("documento", para, legenda, [(o.id, o.titulo) for o in opcoes or []]))
        self.documentos = getattr(self, "documentos", []) + [(para, dados, nome)]
        self.mimes = getattr(self, "mimes", []) + [mime_type]
        return self._id()

    @property
    def ultima(self):
        return self.enviadas[-1]


class IAFalsa:
    def __init__(self, resposta=None, falha=False, campo=None):
        self.resposta, self.falha, self.perguntas = resposta, falha, []
        self.campo, self.frases = campo, []   # #970: o que `ler_campo` devolve, e as frases lidas
        self.bastidores_vistos = []           # #1048: as chaves que o cadastro entregou ao modelo

    def ler_visita(self, texto, ficha, motivos, hoje, candidatos=()):
        """#1090 etapa 3: `visita` e o dict devolvido (ou uma lista, um por leitura). #1439: guarda os
        candidatos vistos e a ficha de cada leitura."""
        self.visitas = getattr(self, "visitas", []) + [texto]
        self.candidatos_vistos = getattr(self, "candidatos_vistos", []) + [[c["codigo"] for c in candidatos]]
        self.fichas_vistas = getattr(self, "fichas_vistas", []) + [ficha.get("nome")]
        if self.falha:
            return None
        v = getattr(self, "visita", None)
        if isinstance(v, list):
            return v.pop(0) if v else None
        return v

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

    def rotear(self, retrato):
        """#1238: `self.roteador` e o dicionario devolvido (ou uma lista, um por chamada); `self.retratos`
        guarda o que ela viu. Sem `roteador`, "nenhum"."""
        self.retratos = getattr(self, "retratos", []) + [retrato]
        nenhum = {"destino": "nenhum", "confianca": None, "sinal": "nenhum", "destino_certo": "nenhum"}
        if self.falha:
            return nenhum
        r = getattr(self, "roteador", None)
        if isinstance(r, list):
            r = r.pop(0) if r else None
        return dict(nenhum, **r) if r else nenhum

    def escolher_pendencia(self, texto, pendencias):
        """#1222: `self.pendencia` e o id devolvido (None = "nenhuma")."""
        self.pendencias_vistas = getattr(self, "pendencias_vistas", []) + [[p["id"] for p in pendencias]]
        if self.falha:
            return None
        return getattr(self, "pendencia", None)

    def conversar(self, sistema, extra, mensagens, ferramentas):
        """#1520: a OlivIA que fala. `self.conversa` e a lista de turnos, um por chamada, na ordem: cada um
        {"texto": "...", "ferramentas": [("nome", {entrada}), ...]}. Lista vazia = turno sem fala nem
        ferramenta (o laco para). `self.chamadas` guarda o que ela viu em cada chamada."""
        import copy
        self.chamadas = getattr(self, "chamadas", []) + [{
            "sistema": sistema, "extra": extra, "mensagens": copy.deepcopy(mensagens),
            "ferramentas": [f["name"] for f in ferramentas]}]
        if self.falha:
            return None
        turnos = getattr(self, "conversa", [])
        t = turnos.pop(0) if turnos else {}
        n = len(self.chamadas)
        chamadas = [{"id": "fer_%d_%d" % (n, i), "nome": nome, "entrada": dict(entrada)}
                    for i, (nome, entrada) in enumerate(t.get("ferramentas", []))]
        conteudo = ([{"type": "text", "text": t["texto"]}] if t.get("texto") else []) + [
            {"type": "tool_use", "id": c["id"], "name": c["nome"], "input": c["entrada"]} for c in chamadas]
        return {"texto": t.get("texto", ""), "ferramentas": chamadas, "conteudo": conteudo}

    def descrever_arquivo(self, dados, mime):
        """#1520: o que `ler_arquivo_recebido` devolve (`self.arquivo`); guarda o mime lido."""
        self.arquivos_lidos = getattr(self, "arquivos_lidos", []) + [mime]
        return getattr(self, "arquivo", "É um currículo.")

    def classificar(self, texto, opcoes):
        self.perguntas.append(texto)
        self.opcoes = getattr(self, "opcoes", []) + [[o["chave"] for o in opcoes]]   # #988: o que ela viu
        if self.falha:
            raise TimeoutError("a IA demorou")
        return self.resposta
