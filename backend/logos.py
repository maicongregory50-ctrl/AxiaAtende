"""A LOGO DE CLIENTE que chega pelo WhatsApp. #1036, 15/10/2026.

O QUE ACONTECEU. As 15:27 de 15/10 o Benedito usou o menu da casa, tocou "Foto do campo" e mandou a
logo de um cliente em PDF. Recebeu SILENCIO -- documento nao e `midia` (so image e video sao), e para
quem e da casa a linha curta nao sai de proposito (decisao do dono em 12/10: "o que ele manda e
material, e a duvida fica no log"). A logo se perdeu duas vezes no mesmo dia, as 07:36 e as 15:27.

O QUE ESTE MODULO FAZ: colhe o arquivo, pergunta de qual cliente e (o codigo do ERP) e o nome da
marca, e guarda. E so.

O QUE ELE NAO FAZ, E A LISTA IMPORTA:
- **nao aprova e nao autoriza**. O destino da logo e a tela Parceiras do AxiaMarketing (#886), onde a
  AUTORIZACAO DE USO trava a peca. E nem poderia: o banco de la tem o CHECK
  `parceiras_autorizada_com_documento`, que impede 'autorizada' sem arquivo de autorizacao e data de
  assinatura. A decisao do dono ("vira proposta, nunca aprovada") e a unica que aquele banco admite;
- **nao manda a logo a ninguem**;
- **nao chama o AxiaMarketing**. A linha fica aqui com `puxada_em` nulo e o MARKETING PUXA, pela rota
  e pela chave que ele ja usa para mandar o pedido de envio. E o padrao do #267: puxar mantem a seta
  na direcao que ela ja tinha, e nao nasce segredo novo;
- **nao e material de campo**, e por isso tem tabela e pasta proprias. Misturar poria uma logo no
  catalogo do marketing como foto de lavoura (medido em 15/10: 0 documentos em material_de_campo);
- **nao descarta logo sem codigo**. Sem o codigo do ERP ela FICA GUARDADA, visivel, para alguem
  completar. Descartar seria repetir em outra forma o defeito que este modulo conserta.

E PERGUNTA UMA VEZ SO. Depois de uma insistencia o fluxo para de perguntar e guarda o que tem -- e a
licao do teto do #1028, aplicada aqui antes de o defeito existir.
"""
import hashlib
import re
from datetime import datetime

from . import internos

# os quatro formatos que a tela Parceiras do marketing aceita (parceiras_logos_formato)
FORMATOS = {"application/pdf": "pdf", "image/svg+xml": "svg", "svg": "svg",
            "image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg"}

RECEBI = ("Recebi a logo{arquivo}. De qual cliente ela é? Me diga o *código dele no ERP* — é por ele "
          "que o marketing liga a parceira (o nome não serve).")
PERGUNTA_MARCA = ("Anotado, cliente {codigo}. E o *nome da marca*, como ela deve aparecer na arte?")
GUARDADA = ("Pronto: a logo de {marca} está guardada. A *autorização de uso* é na tela Parceiras — "
            "sem ela nenhuma arte sai com a marca do cliente, e eu não autorizo nada por aqui.")
SEM_CODIGO = ("Não achei um código aí. Me diga só os números do código do cliente no ERP; se não "
              "souber agora, deixo a logo guardada e alguém completa depois.")
GUARDADA_SEM_CLIENTE = ("Deixei a logo guardada sem o cliente. Ela não se perde: alguém completa "
                        "depois, na tela Parceiras.")


def _nome_seguro(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", texto or "")[:120] or "sem_nome"


def _dizer(con, saida, para: str, texto: str) -> str:
    """Manda E REGISTRA em `atendimento.enviadas`, no molde de `campo._registrar`.

    NAO e detalhe: sem o registro, `scripts/ler_conversa.py` nao reconstroi o dialogo (so aparece o
    que a PESSOA mandou) e o aviso de status da Meta nao tem onde pousar. A casa ja pagou por isso
    uma vez -- o commit 71047bb do #981 fez exatamente este conserto para o canal de campo, depois
    de a primeira leitura mostrar a conversa sem as falas da OlivIA. O modulo novo repetiu o erro
    na primeira rodada em producao (15/10, 16:30) e este e o conserto.

    `ON CONFLICT (wamid) DO NOTHING` porque o wamid e unico em `enviadas`.
    """
    w = saida.texto(para, texto)
    con.execute("""INSERT INTO atendimento.enviadas (wamid, para, tipo, resumo)
                   VALUES (%s, %s, 'texto', %s) ON CONFLICT (wamid) DO NOTHING""",
                (w, para, ("logo: " + (texto or ""))[:200]))
    return w


def _formato(mime: str, nome_arquivo: str) -> str | None:
    f = FORMATOS.get((mime or "").split(";")[0].strip().lower())
    if f:
        return f
    ext = (nome_arquivo or "").rsplit(".", 1)[-1].lower()
    return ext if ext in ("pdf", "svg", "png", "jpg") else None


def pendente(con, bsuid: str):
    return con.execute("""SELECT * FROM atendimento.logos_de_cliente
                           WHERE bsuid = %s AND pergunta_pendente IS NOT NULL
                           ORDER BY id DESC LIMIT 1""", (bsuid,)).fetchone()


def receber(con, saida, e, agora: datetime, pasta) -> bool:
    """O documento de quem e da casa. True quando a logo foi tomada (e nada mais deve tratar isso).

    Fora daqui: documento de quem NAO e da casa, que segue para a linha de arquivo do #1027.
    """
    d = getattr(e, "documento", None)
    if d is None:
        return False
    quem = internos.quem_e(con, e.pessoa.wa_id)
    if not quem or not internos.ligado(con):
        return False   # de fora: a linha de arquivo do #1027 responde
    formato = _formato(d.mime, d.nome_arquivo)
    if formato is None:
        return False   # arquivo que o marketing nao aceita: cai na linha de arquivo, que explica

    # `wamid` e UNICO: o mesmo aviso repetido pela Meta nao cria duas logos
    if con.execute("SELECT 1 FROM atendimento.logos_de_cliente WHERE wamid = %s", (e.wamid,)).fetchone():
        return True

    arquivo, erro = None, ""
    try:
        relativo = "logos/%s/%s_%s.%s" % (agora.date().isoformat(), _nome_seguro(e.wamid),
                                          _nome_seguro(d.nome_arquivo.rsplit(".", 1)[0]), formato)
        destino = pasta / relativo
        saida.baixar(d.id, destino)
        arquivo = relativo
    except Exception as falha:   # noqa: BLE001 -- a logo fica em eventos_meta; a linha diz o erro
        erro = ("%s: %s" % (type(falha).__name__, falha))[:300]

    sha = None
    if arquivo:
        try:
            sha = hashlib.sha256((pasta / arquivo).read_bytes()).hexdigest()
        except OSError:
            sha = None

    con.execute("""INSERT INTO atendimento.logos_de_cliente
                       (bsuid, wa_id, enviada_por, wamid, nome_arquivo, arquivo, sha256, mime,
                        formato, pergunta_pendente, recebida_em, erro)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'erp_codigo', %s, %s)""",
                (e.pessoa.bsuid, e.pessoa.wa_id, quem.get("nome") or "", e.wamid,
                 d.nome_arquivo[:200], arquivo, sha, d.mime[:100], formato, agora, erro))
    nome = (" *%s*" % d.nome_arquivo) if d.nome_arquivo else ""
    _dizer(con, saida, e.pessoa.para, RECEBI.format(arquivo=nome))
    print("logos: logo de %s por %s (%s): %s" % (formato, quem.get("nome"), e.pessoa.wa_id,
                                                 arquivo or ("falhou -- " + erro)), flush=True)
    return True


def responder(con, saida, e, agora: datetime) -> bool:
    """A resposta a pergunta da logo. True quando foi tratada aqui.

    PRECISA vir ANTES de `campo.texto_de_interno` no motor: depois dele, "7687" viraria a frase da
    proxima foto do canal de campo, e a logo ficaria para sempre sem cliente. E DEPOIS de
    `campo.responder`, para nao roubar a resposta de uma pergunta de foto que ja estava aberta.
    """
    texto = (e.texto or "").strip()
    if not texto or e.toque:
        return False
    linha = pendente(con, e.pessoa.bsuid)
    if not linha:
        return False
    # quem pede menu escapa da pergunta, e a logo FICA guardada
    if internos.pede_menu(texto):
        con.execute("UPDATE atendimento.logos_de_cliente SET pergunta_pendente = NULL WHERE id = %s",
                    (linha["id"],))
        return False

    if linha["pergunta_pendente"] == "erp_codigo":
        digitos = re.sub(r"\D", "", texto)
        if not digitos or len(digitos) > 9:
            if linha["insistiu"]:
                con.execute("""UPDATE atendimento.logos_de_cliente
                                  SET pergunta_pendente = NULL WHERE id = %s""", (linha["id"],))
                _dizer(con, saida, e.pessoa.para, GUARDADA_SEM_CLIENTE)
                return True
            con.execute("UPDATE atendimento.logos_de_cliente SET insistiu = true WHERE id = %s",
                        (linha["id"],))
            _dizer(con, saida, e.pessoa.para, SEM_CODIGO)
            return True
        con.execute("""UPDATE atendimento.logos_de_cliente
                          SET erp_codigo = %s, pergunta_pendente = 'nome_marca', insistiu = false
                        WHERE id = %s""", (int(digitos), linha["id"]))
        _dizer(con, saida, e.pessoa.para, PERGUNTA_MARCA.format(codigo=int(digitos)))
        return True

    # nome_marca: o que a pessoa escrever vale, e o dialogo termina aqui
    con.execute("""UPDATE atendimento.logos_de_cliente
                      SET nome_marca = %s, pergunta_pendente = NULL, completada_em = %s
                    WHERE id = %s""", (texto[:120], agora, linha["id"]))
    _dizer(con, saida, e.pessoa.para, GUARDADA.format(marca=texto[:120]))
    return True
