"""O que SAI pelo WhatsApp. #950.

Uma interface so (`Saida`) e duas implementacoes: `SaidaMeta`, que fala com a Meta pelo PyWa, e a
falsa dos testes (`tests/saida_falsa.py`). O motor nunca sabe qual esta usando.

So o RECEPCIONISTA cria uma `SaidaMeta`: e o unico processo com o token (config.py). Cada envio
fica em `atendimento.enviadas` com o id que a Meta devolve; os status (entregue, lida, falhou)
chegam depois pelo webhook e atualizam a linha.

LIMITES DO WHATSAPP, conferidos aqui e nao no motor: ate 3 botoes por mensagem, titulo de botao
ate 20 caracteres; lista com ate 10 linhas, titulo da linha ate 24 e descricao ate 72.
"""
from dataclasses import dataclass

MAX_BOTOES = 3
MAX_LINHAS = 10


@dataclass(frozen=True)
class Opcao:
    id: str          # o que volta no toque (callback)
    titulo: str
    descricao: str = ""


class Saida:
    """O contrato. Cada metodo devolve o id da mensagem na Meta (wamid)."""

    def texto(self, para: str, texto: str) -> str:
        raise NotImplementedError

    def botoes(self, para: str, texto: str, opcoes: list[Opcao]) -> str:
        raise NotImplementedError

    def lista(self, para: str, texto: str, botao: str, opcoes: list[Opcao]) -> str:
        raise NotImplementedError

    def imagem(self, para: str, arquivo: str, legenda: str = "") -> str:
        raise NotImplementedError

    def modelo(self, para: str, nome: str, idioma: str, corpo: list[str],
               imagem: str | None = None, botoes: list[str] | None = None, url: str | None = None) -> str:
        """`botoes`: as cargas dos botoes de resposta rapida; `url`: o final do botao de link
        (o modelo aprovado termina em {{1}}; aqui vai o numero do responsavel)."""
        raise NotImplementedError


def conferir_botoes(opcoes: list[Opcao]) -> None:
    if not 1 <= len(opcoes) <= MAX_BOTOES:
        raise ValueError("botoes: de 1 a %d, vieram %d" % (MAX_BOTOES, len(opcoes)))
    for o in opcoes:
        if len(o.titulo) > 20:
            raise ValueError("titulo de botao passa de 20: %r" % o.titulo)


def conferir_lista(opcoes: list[Opcao]) -> None:
    if not 1 <= len(opcoes) <= MAX_LINHAS:
        raise ValueError("lista: de 1 a %d linhas, vieram %d" % (MAX_LINHAS, len(opcoes)))
    for o in opcoes:
        if len(o.titulo) > 24 or len(o.descricao) > 72:
            raise ValueError("linha de lista passa do limite: %r" % o.titulo)


class SaidaMeta(Saida):
    """A Meta de verdade, pelo PyWa 4.5.0. `sessao` e um httpx.Client: os testes passam um com
    transporte falso e nada sai da maquina."""

    def __init__(self, phone_id: str, token: str, sessao=None, versao: str | None = None):
        from pywa import WhatsApp   # so o recepcionista importa a Meta
        extra = {"api_version": versao} if versao else {}
        self._wa = WhatsApp(phone_id=phone_id, token=token, session=sessao, server=None,
                            verify_token=None, **extra)

    def __repr__(self):   # nunca o token
        return "SaidaMeta()"

    def texto(self, para, texto):
        return self._wa.send_message(to=para, text=texto, preview_url=True).id

    def botoes(self, para, texto, opcoes):
        from pywa.types import Button
        conferir_botoes(opcoes)
        return self._wa.send_message(
            to=para, text=texto, buttons=[Button(title=o.titulo, callback_data=o.id) for o in opcoes]).id

    def lista(self, para, texto, botao, opcoes):
        from pywa.types import Section, SectionList, SectionRow
        conferir_lista(opcoes)
        linhas = [SectionRow(title=o.titulo, callback_data=o.id, description=o.descricao or None)
                  for o in opcoes]
        return self._wa.send_message(
            to=para, text=texto,
            buttons=SectionList(button_title=botao, sections=[Section(title="Opções", rows=linhas)])).id

    def nota(self) -> str:
        """A nota de qualidade do numero na Meta (GREEN/YELLOW/RED), so leitura."""
        q = self._wa.get_business_phone_number().quality_rating
        return str(getattr(q, "value", q) or "UNKNOWN").upper()   # o PyWa pode devolver enum

    def imagem(self, para, arquivo, legenda=""):
        return self._wa.send_image(to=para, image=arquivo, caption=legenda or None).id

    def modelo(self, para, nome, idioma, corpo, imagem=None, botoes=None, url=None):
        # O modelo vai como JSON cru (a forma da Cloud API), sem depender da classe de modelo do
        # PyWa: o que se manda aqui e exatamente o que a documentacao da Meta mostra.
        componentes = []
        if imagem:
            midia = self._wa.upload_media(media=imagem, mime_type="image/jpeg")
            componentes.append({"type": "header",
                                "parameters": [{"type": "image", "image": {"id": midia.id}}]})
        if corpo:
            componentes.append({"type": "body",
                                "parameters": [{"type": "text", "text": t} for t in corpo]})
        for i, carga in enumerate(botoes or []):
            componentes.append({"type": "button", "sub_type": "quick_reply", "index": str(i),
                                "parameters": [{"type": "payload", "payload": carga}]})
        if url:
            componentes.append({"type": "button", "sub_type": "url", "index": "0",
                                "parameters": [{"type": "text", "text": url}]})
        from pywa.types.templates import TemplateLanguage   # o PyWa pede o idioma no tipo dele
        return self._wa.send_template(to=para, name=nome, language=TemplateLanguage(idioma),
                                      params=componentes).id
