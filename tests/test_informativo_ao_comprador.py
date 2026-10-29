"""O informativo ao comprador (043, dono 29/10/2026): a direta com o boletim no cabecalho, o texto fixo
escolhido pelo dono, "Nao quero mais receber" (a recusa) e "Falar com meu atendimento" (o link)."""
from datetime import timedelta

from backend import modelos_meta
from backend.banco import conexao
from backend.envio import Envio
from tests.saida_falsa import SaidaFalsa
from tests.test_envio import QUINTA_10H, _tocar, cliente, destinatarios, ligado, pedir  # noqa: F401
from tests.test_envio_direto import direta, imagens  # noqa: F401

TEXTO = ("Olá, {{1}}! Aqui é a Sementes Renascer, com informação de mercado e de safra para apoiar as suas "
         "decisões de compra e mostrar um pouco mais do nosso trabalho.")


def informativo(imagens, clientes):
    return {**direta(imagens, clientes), "modelo": "informativo_ao_comprador", "assunto": "",
            "campanha": "Bom te ver de novo", "peca": "Boletim de safra nº 1"}


def test_o_informativo_vai_a_meta_com_a_imagem_o_texto_do_dono_e_os_dois_botoes(cfg):
    m = {x["nome"]: x for x in modelos_meta.cadastro(cfg)}["informativo_ao_comprador"]
    assert (m["categoria"], m["uso"], m["botao"]) == ("MARKETING", "direta", "parar_e_falar")
    c = modelos_meta.componentes(m, "4::h")
    assert c[0] == {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["4::h"]}}
    assert c[1]["text"] == TEXTO and c[1]["example"]["body_text"] == [["João"]]
    botoes = c[2]["buttons"]
    assert [(b["type"], b["text"]) for b in botoes] == [("QUICK_REPLY", "Não quero mais receber"),
                                                       ("URL", "Falar com meu atendimento")]
    assert botoes[1]["url"].endswith("/falar/{{1}}") and "wa.me" not in botoes[1]["url"]


def test_o_informativo_sai_com_o_boletim_a_recusa_e_o_link_sem_imagens_depois(ligado, imagens):
    pedir(ligado, informativo(imagens, [dict(cliente(1, 30, nome="JOAO DA SILVA",
                                                     resp=("Djeison de Oliveira", "5549999567572")),
                                             aceite_cadastro=True)]))
    s = SaidaFalsa()
    Envio(ler_nota=lambda: "GREEN").rotina(ligado, s, QUINTA_10H)
    m = next(x for x in s.modelos if x["para"] != "5549999567572")
    assert m["nome"] == "informativo_ao_comprador" and m["corpo"] == ["Joao"]
    assert m["imagem"] and m["botoes"] == ["envio:1:nao_quero"] and m["url"].startswith("1-")
    assert destinatarios(ligado)[1]["imagens_total"] == 0


def test_nao_quero_mais_receber_e_a_recusa_de_sempre(ligado, imagens):
    pedir(ligado, informativo(imagens, [dict(cliente(1, 30, resp=("Djeison de Oliveira", "5549999567572")),
                                             aceite_cadastro=True)]))
    s, env = SaidaFalsa(), Envio(ler_nota=lambda: "GREEN")
    env.rotina(ligado, s, QUINTA_10H)
    numero = destinatarios(ligado)[1]["whatsapp"]
    _tocar(ligado, s, env, numero, "nao_quero", QUINTA_10H + timedelta(hours=1))
    assert s.ultima[0] == "texto" and "não vai mais receber" in s.ultima[2]
    with conexao(ligado) as con:
        assert con.execute("SELECT tipo FROM atendimento.consentimentos").fetchone()["tipo"] == "recusa"
    env.rotina(ligado, s, QUINTA_10H + timedelta(hours=1, minutes=1))
    assert s.ultima[0] == "modelo" and s.ultima[1] == "5549999567572" and s.ultima[2] == "aviso_recusa"


def test_propor_so_o_informativo_deixa_os_outros_que_faltam(cfg, tmp_path):
    from dataclasses import replace
    from tests.test_modelos_meta import cliente_falso
    imagem = tmp_path / "boletim.png"
    imagem.write_bytes(b"\x89PNG")
    pedidos = []
    feitos = modelos_meta.propor(replace(cfg, meta_token="t"), imagem, http=cliente_falso(pedidos),
                                 so=["informativo_ao_comprador"])
    assert [f["nome"] for f in feitos] == ["informativo_ao_comprador"]
    assert len([p for p in pedidos if p.method == "POST" and p.url.path.endswith("/message_templates")]) == 1


# ── 044: o informativo sem botao de link ─────────────────────────────────────

def renascer(imagens, clientes):
    return {**informativo(imagens, clientes), "modelo": "informativo_renascer"}


def test_o_informativo_renascer_tem_as_duas_respostas_rapidas_e_nenhum_link(cfg):
    m = {x["nome"]: x for x in modelos_meta.cadastro(cfg)}["informativo_renascer"]
    assert (m["uso"], m["botao"], m["texto"]) == ("direta", "parar_e_chamar", TEXTO)
    botoes = modelos_meta.componentes(m, "4::h")[2]["buttons"]
    assert [(b["type"], b["text"]) for b in botoes] == [("QUICK_REPLY", "Não quero mais receber"),
                                                       ("QUICK_REPLY", "Falar com meu atendimento")]


def _manda(ligado, imagens, resp=("Djeison de Oliveira", "5549999567572")):
    pedir(ligado, renascer(imagens, [dict(cliente(1, 30, resp=resp), aceite_cadastro=True)]))
    s, env = SaidaFalsa(), Envio(ler_nota=lambda: "GREEN")
    env.rotina(ligado, s, QUINTA_10H)
    return s, env, destinatarios(ligado)[1]["whatsapp"]


def test_o_informativo_renascer_sai_sem_link(ligado, imagens):
    s, _, numero = _manda(ligado, imagens)
    m = next(x for x in s.modelos if x["para"] == numero)
    assert m["botoes"] == ["envio:1:nao_quero", "envio:1:falar"] and m["url"] is None and m["imagem"]


def test_falar_com_meu_atendimento_anota_e_responde_com_o_representante(ligado, imagens):
    s, env, numero = _manda(ligado, imagens)
    _tocar(ligado, s, env, numero, "falar", QUINTA_10H + timedelta(hours=1))
    assert s.ultima[0] == "texto" and s.ultima[1] == numero
    assert "Djeison" in s.ultima[2] and "https://wa.me/5549999567572" in s.ultima[2]
    d = destinatarios(ligado)[1]
    assert d["resposta"] == "falar" and d["resposta_em"] is not None
    # e ainda pode sair depois: o "falar" nao fecha a recusa
    _tocar(ligado, s, env, numero, "nao_quero", QUINTA_10H + timedelta(hours=2), wamid="w2")
    assert destinatarios(ligado)[1]["resposta"] == "nao_quero" and "não vai mais receber" in s.ultima[2]


def test_falar_sem_numero_do_representante_responde_sem_link(ligado, imagens):
    s, env, numero = _manda(ligado, imagens, resp=("Djeison de Oliveira", "5549999567572"))
    with conexao(ligado) as con:
        con.execute("UPDATE atendimento.envio_destinatarios SET responsavel_whatsapp = ''")
    _tocar(ligado, s, env, numero, "falar", QUINTA_10H + timedelta(hours=1))
    assert s.ultima[2] == Envio.SEM_REPRESENTANTE
