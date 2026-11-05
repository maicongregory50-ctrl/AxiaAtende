"""#1267 (dono, 05/11/2026): o material na janela aberta. Quem ja aceitou e mandou qualquer mensagem nas
ultimas 24 h recebe o envio seguinte como uma linha de texto e as imagens, sem o convite pago; fora disso,
o convite de sempre. Meta falsa: nada sai."""
from datetime import timedelta

from backend import recepcionista as R
from backend.banco import conexao
from backend.envio import TEXTO_NA_JANELA, Envio
from tests.avisos_meta import aviso
from tests.saida_falsa import SaidaFalsa
from tests.test_envio import QUINTA_10H, cliente, destinatarios, imagens, ligado, pedido, pedir  # noqa: F401


def _escreveu(cfg, numero, quando, wamid="wamid.oi"):
    """Uma mensagem de texto da pessoa, com a hora da mensagem em `quando` (#1237)."""
    msg = {"from": numero, "id": wamid, "timestamp": str(int(quando.timestamp())), "type": "text",
           "text": {"body": "oi"}}
    R.gravar(cfg, aviso([msg], numero=numero, bsuid="BR." + numero))


def _aceitou(cfg, numero):
    with conexao(cfg) as con:
        con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, tipo, em, wamid)
                       VALUES (%s, 'aceite', %s, 'wamid.aceite')""", (numero, QUINTA_10H - timedelta(days=1)))


def _lote(cfg, agora):
    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(cfg, s, agora)
    return s


def test_quem_aceitou_e_escreveu_ha_uma_hora_recebe_sem_convite(ligado, imagens):  # noqa: F811
    pedir(ligado, pedido(imagens, [cliente(1, 10)]))
    numero = destinatarios(ligado)[1]["whatsapp"]
    _aceitou(ligado, numero)
    _escreveu(ligado, numero, QUINTA_10H - timedelta(hours=1))
    s = _lote(ligado, QUINTA_10H)
    tipos = [x[0] for x in s.enviadas]
    assert "modelo" not in tipos                       # nenhum convite pago
    assert tipos[0] == "texto" and s.enviadas[0][2] == TEXTO_NA_JANELA
    assert tipos.count("imagem") == 3
    d = destinatarios(ligado)[1]
    assert d["sem_convite"] and d["situacao"] == "convidado" and d["resposta"] is None
    assert d["imagens_enviadas"] == 3 and d["convite_em"] is not None
    assert d["resposta_em"] == QUINTA_10H - timedelta(hours=1)   # a janela conta da mensagem dele


def test_quem_aceitou_mas_nao_escreve_ha_25h_recebe_o_convite(ligado, imagens):  # noqa: F811
    pedir(ligado, pedido(imagens, [cliente(1, 10)]))
    numero = destinatarios(ligado)[1]["whatsapp"]
    _aceitou(ligado, numero)
    _escreveu(ligado, numero, QUINTA_10H - timedelta(hours=25))
    s = _lote(ligado, QUINTA_10H)
    assert [x[0] for x in s.enviadas] == ["modelo"]
    assert not destinatarios(ligado)[1]["sem_convite"]


def test_quem_nunca_aceitou_recebe_o_convite_mesmo_com_a_janela_aberta(ligado, imagens):  # noqa: F811
    pedir(ligado, pedido(imagens, [cliente(1, 10)]))
    numero = destinatarios(ligado)[1]["whatsapp"]
    _escreveu(ligado, numero, QUINTA_10H - timedelta(hours=1))
    s = _lote(ligado, QUINTA_10H)
    assert [x[0] for x in s.enviadas] == ["modelo"]


def test_quem_recusou_por_ultimo_nao_recebe_sem_convite(ligado, imagens):  # noqa: F811
    pedir(ligado, pedido(imagens, [cliente(1, 10)]))
    numero = destinatarios(ligado)[1]["whatsapp"]
    _aceitou(ligado, numero)
    with conexao(ligado) as con:
        con.execute("""INSERT INTO atendimento.consentimentos (whatsapp, tipo, em, wamid)
                       VALUES (%s, 'recusa', %s, 'wamid.recusa')""", (numero, QUINTA_10H - timedelta(hours=2)))
    _escreveu(ligado, numero, QUINTA_10H - timedelta(hours=1))
    s = _lote(ligado, QUINTA_10H)
    assert "texto" not in [x[0] for x in s.enviadas]


def test_o_texto_que_falha_cai_no_convite(ligado, imagens):  # noqa: F811
    pedir(ligado, pedido(imagens, [cliente(1, 10)]))
    numero = destinatarios(ligado)[1]["whatsapp"]
    _aceitou(ligado, numero)
    _escreveu(ligado, numero, QUINTA_10H - timedelta(hours=1))
    s = SaidaFalsa()

    def recusa(para, texto):
        raise RuntimeError("(#131047) Re-engagement message")
    s.texto = recusa
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, QUINTA_10H)
    assert [x[0] for x in s.enviadas] == ["modelo"]
    assert not destinatarios(ligado)[1]["sem_convite"]
