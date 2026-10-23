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
EMPRESA = "Sementes Renascer"
MAX_LINHAS = 10
LIMITE_LINK = 20   # #1090: o rotulo do botao de link (cta_url) na Meta


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

    def contato(self, para: str, nome: str, whatsapp: str, empresa: str = EMPRESA) -> str:
        """O cartao de contato de quem atende: a pessoa toca em Conversar, ou salva o contato."""
        raise NotImplementedError

    def modelo(self, para: str, nome: str, idioma: str, corpo: list[str],
               imagem: str | None = None, botoes: list[str] | None = None, url: str | None = None,
               documento: tuple[bytes, str] | None = None) -> str:
        """`botoes`: as cargas dos botoes de resposta rapida; `url`: o final do botao de link
        (o modelo aprovado termina em {{1}}; aqui vai o numero do responsavel). O botao de link vem
        DEPOIS das respostas no modelo, e o indice dele e o numero de respostas (#1098: o modelo da
        Fran tem duas respostas e o link no indice 2). `documento`: (bytes, nome do arquivo), o PDF
        do cabecalho (#1098)."""
        raise NotImplementedError

    def link(self, para: str, texto: str, rotulo: str, url: str) -> str:
        """#1090 etapa 3: o texto com UM botao de link (mensagem interativa `cta_url`). A Meta nao deixa
        botao de resposta na mesma mensagem, e o rotulo tem ate 20 caracteres. So dentro das 24 h."""
        raise NotImplementedError

    def documento(self, para: str, dados: bytes, nome: str, legenda: str = "",
                  opcoes: list[Opcao] | None = None) -> str:
        """#1098: um PDF, com a legenda e ate 3 botoes (mensagem interativa com o documento no
        cabecalho). So dentro da janela de 24 h de quem recebe; fora dela, e modelo."""
        raise NotImplementedError

    def baixar(self, media_id: str, destino) -> str:
        """#970: baixa a midia que a pessoa mandou (o id vem no aviso da Meta) para `destino`
        (Path), com o mesmo token. Devolve o caminho gravado. A URL da Meta vale 5 minutos."""
        raise NotImplementedError


def wa_id_do_whatsapp(numero: str) -> str:
    """O id do WhatsApp de um celular brasileiro e o numero ANTIGO, sem o 9 (o seu chega assim nos
    avisos da Meta: 554991505565). O cartao de contato com o id errado nao mostra "Conversar", so
    "Convidar" (ensaio de 09/10/2026, cartao do Benedito)."""
    n = "".join(c for c in (numero or "") if c.isdigit())
    if len(n) == 13 and n.startswith("55") and n[4] == "9":
        return n[:4] + n[5:]
    return n


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

    def link(self, para, texto, rotulo, url):
        from pywa.types import URLButton
        if len(rotulo) > LIMITE_LINK:
            raise ValueError("rotulo do link com mais de %d caracteres: %r" % (LIMITE_LINK, rotulo))
        return self._wa.send_message(to=para, text=texto, buttons=URLButton(title=rotulo, url=url)).id

    def contato(self, para, nome, whatsapp, empresa=EMPRESA):
        from pywa.types import Contact
        partes = nome.split()
        cartao = Contact(name=Contact.Name(formatted_name=nome, first_name=partes[0],
                                           last_name=" ".join(partes[1:]) or None),
                         phones=[Contact.Phone(phone="+" + whatsapp, wa_id=wa_id_do_whatsapp(whatsapp), type="WORK")],
                         org=Contact.Org(company=empresa))
        return self._wa.send_contact(to=para, contact=cartao).id

    def nota(self) -> str:
        """A nota de qualidade do numero na Meta (GREEN/YELLOW/RED), so leitura."""
        q = self._wa.get_business_phone_number().quality_rating
        return str(getattr(q, "value", q) or "UNKNOWN").upper()   # o PyWa pode devolver enum

    def imagem(self, para, arquivo, legenda=""):
        return self._wa.send_image(to=para, image=arquivo, caption=legenda or None).id

    def baixar(self, media_id, destino):
        from pathlib import Path
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        url = self._wa.get_media_url(media_id).url
        self._wa.download_media(url=url, path=str(destino.parent), filename=destino.name)
        return str(destino)

    def documento(self, para, dados, nome, legenda="", opcoes=None):
        from pywa.types import Button
        if opcoes:
            conferir_botoes(opcoes)
        return self._wa.send_document(
            to=para, document=dados, filename=nome, caption=legenda or None, mime_type="application/pdf",
            buttons=[Button(title=o.titulo, callback_data=o.id) for o in opcoes] if opcoes else None).id

    def modelo(self, para, nome, idioma, corpo, imagem=None, botoes=None, url=None, documento=None):
        # O modelo vai como JSON cru (a forma da Cloud API), sem depender da classe de modelo do
        # PyWa: o que se manda aqui e exatamente o que a documentacao da Meta mostra.
        componentes = []
        if imagem:
            midia = self._wa.upload_media(media=imagem, mime_type="image/jpeg")
            componentes.append({"type": "header",
                                "parameters": [{"type": "image", "image": {"id": midia.id}}]})
        if documento:
            dados, arquivo = documento
            midia = self._wa.upload_media(media=dados, mime_type="application/pdf", filename=arquivo)
            componentes.append({"type": "header", "parameters": [
                {"type": "document", "document": {"id": midia.id, "filename": arquivo}}]})
        if corpo:
            componentes.append({"type": "body",
                                "parameters": [{"type": "text", "text": t} for t in corpo]})
        for i, carga in enumerate(botoes or []):
            componentes.append({"type": "button", "sub_type": "quick_reply", "index": str(i),
                                "parameters": [{"type": "payload", "payload": carga}]})
        if url:
            componentes.append({"type": "button", "sub_type": "url", "index": str(len(botoes or [])),
                                "parameters": [{"type": "text", "text": url}]})
        from pywa.types.templates import TemplateLanguage   # o PyWa pede o idioma no tipo dele
        return self._wa.send_template(to=para, name=nome, language=TemplateLanguage(idioma),
                                      params=componentes).id
