"""Os modelos de mensagem na Meta, a partir do CADASTRO (`atendimento.modelos`). #950, G4.

    python -m backend.modelos_meta --ver                      so leitura: os nossos modelos na Meta e a situacao
    python -m backend.modelos_meta --propor --imagem capa.jpg manda para aprovacao os do cadastro que a Meta ainda nao tem
    python -m backend.modelos_meta --propor --documento exemplo.pdf   o mesmo, para o modelo com PDF no cabecalho (#1098)
    python -m backend.modelos_meta --propor --so informativo_ao_comprador --imagem capa.png   so este (043)

Roda em janela elevada, com AXIAATENDE_AMBIENTE=producao e AXIAATENDE_PROCESSO=recepcionista (le o
token do .env.recepcionista; o token nunca e impresso). `--imagem` e o exemplo de cabecalho que a
Meta exige dos modelos com imagem: qualquer JPG de peca serve, ele nao vai a cliente nenhum.

REGRAS (spec, "Cuidado com a Meta"):
- so cria modelo que a Meta NAO tem com aquele nome e idioma. Modelo recusado nao se reenvia daqui:
  a Utilidade recusada vira Marketing UMA vez, por decisao do dono, nunca por insistencia;
- nada de editar ou apagar modelo, e nada no numero (registro, PIN, nome exibido).
"""
import argparse
import json
import mimetypes
import sys
from pathlib import Path

import httpx

from . import config, migracoes
from .banco import conexao

#: O texto dos botoes (a Meta aceita ate 25 caracteres). O sistema reconhece o toque pelo
#: `payload` do envio, nunca pelo texto, entao mudar o texto aqui nao muda o que o toque faz.
BOTOES_CONVITE = ("Quero receber", "Não quero receber")
BOTAO_FALAR = "Falar com meu atendimento"
#: O informativo ao comprador (043): a saida do cliente, ao lado do link de falar.
BOTAO_PARAR = "Não quero mais receber"
#: #1098: o modelo da Fran. As duas respostas voltam com a carga do envio (vaga:certa:<id>); o
#: terceiro e o link para conversar com o candidato, pelo NOSSO endereco (/falar/v<id>-<assinatura>).
BOTOES_TRIAGEM = ("Triagem certa", "Triagem errada")
BOTAO_CANDIDATO = "Conversar com o candidato"
#: #1188: o botao da reabertura dos avisos internos; volta com a carga `reabrir:<numero>`.
BOTAO_VER = "Ver"
#: O endereco publico do recepcionista (Funnel 443). O botao da direta termina em {{1}} = o codigo.
ENDERECO_FALAR = "https://serverrenascer.taild57672.ts.net/falar/"
LIMITE_BOTAO = 25

#: Um exemplo por fonte de variavel: a Meta exige exemplo para cada {{n}}. Dados de mentira.
EXEMPLOS = {
    "primeiro_nome": "João", "nome": "Agro Exemplo", "assunto": "soja", "peca": "a peça da semana",
    "n_imagens": "6", "responsavel": "o Maicon",
    "n_avisos": "3",   # #1188, a reabertura dos avisos internos
    # #1098: o curriculo para a Fran (candidato ficticio, o mesmo da maquete)
    "vaga": "Vaga Comercial", "candidato": "João Exemplo (49 9 0000-0000)",
    "declarou": "atende a todos os requisitos",
    "req1": "Agronomia com pós: consta (Agronomia UFSC, pós em Produção Vegetal)",
    "req2": "2 anos com sementes: não consta no currículo",
    "req3": "Vivência comercial: consta (3 anos em revenda de insumos)",
    "req4": "Mora em Maravilha ou vizinha: não (Cascavel, PR)",
    "resumo": "perfil comercial e técnico; o currículo não mostra experiência com sementes.",
}
EXEMPLOS_AVISO = {
    "aviso_recusa": ["Agro Exemplo", "5475 · Chapecó", "https://wa.me/5549999999999"],
    "aviso_sem_atendimento": ["João (5549999999999)", "Comercial › SC, com Maicon",
                              "https://wa.me/5549999999999"],
    "aviso_avaliacao_ruim": ["João (5549999999999)", "Comercial › SC, com Maicon",
                             "https://wa.me/5549999999999"],
    "aviso_endereco_fora": ["atende.exemplo.com.br", "11/10 14:32"],
    "aviso_endereco_voltou": ["atende.exemplo.com.br", "11/10 14:50", "18 min"],
    "aviso_plano_sem_registro": ["7", "14/10/2026"],     # #926, o Controle do plano
    # #1142: o resumo do lote ao representante -- {{2}} e contado na hora ("1 cliente seu")
    "aviso_lote_do_representante": ["Djeison", "3 clientes seus", "o plantio do Trigo Mourisco"],
    "aviso_auditoria_estoque": ["Matriz", "13/10/2026"],     # #350, a auditoria de estoque
}


def _cliente(cfg) -> httpx.Client:
    if not cfg.meta_token:
        raise SystemExit("falta o META_TOKEN no .env.recepcionista (rode como administrador, em producao)")
    return httpx.Client(base_url="%s/v%s" % (cfg.meta_url, cfg.meta_versao.lstrip("v")),
                        headers={"Authorization": "Bearer " + cfg.meta_token}, timeout=60)


def cadastro(cfg) -> list[dict]:
    with conexao(cfg) as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM atendimento.modelos WHERE ativo ORDER BY id").fetchall()]


def componentes(m: dict, cabecalho: str | None = None, documento: str | None = None) -> list[dict]:
    """O modelo do cadastro na forma da Meta (POST message_templates)."""
    if m["texto"].strip().startswith("{{") or m["texto"].strip().endswith("}}"):
        raise ValueError("%s: a Meta recusa corpo que comeca ou termina numa variavel" % m["nome"])
    exemplos = (EXEMPLOS_AVISO[m["uso"]] if m["uso"] in EXEMPLOS_AVISO
                else [EXEMPLOS[v] for v in m["variaveis"]])
    saida = []
    if m["cabecalho_imagem"]:
        if not cabecalho:
            raise ValueError("%s tem imagem no cabecalho: passe --imagem" % m["nome"])
        saida.append({"type": "HEADER", "format": "IMAGE", "example": {"header_handle": [cabecalho]}})
    if m.get("cabecalho_documento"):
        if not documento:
            raise ValueError("%s tem documento no cabecalho: passe --documento" % m["nome"])
        saida.append({"type": "HEADER", "format": "DOCUMENT", "example": {"header_handle": [documento]}})
    corpo = {"type": "BODY", "text": m["texto"]}
    if exemplos:
        corpo["example"] = {"body_text": [exemplos]}
    saida.append(corpo)
    if m["botao"] == "quero_nao_quero":
        saida.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": t} for t in BOTOES_CONVITE]})
    elif m["botao"] == "falar_responsavel":
        # link para o NOSSO endereco: a Meta recusa link direto para o WhatsApp em modelo
        saida.append({"type": "BUTTONS", "buttons": [{
            "type": "URL", "text": BOTAO_FALAR, "url": ENDERECO_FALAR + "{{1}}",
            "example": [ENDERECO_FALAR + "1-0a1b2c3d4e5f6a7b"]}]})
    elif m["botao"] == "parar_e_falar":
        # a resposta rapida antes do link: a ordem e a do envio (as cargas primeiro, o link no fim)
        saida.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": BOTAO_PARAR}, {
            "type": "URL", "text": BOTAO_FALAR, "url": ENDERECO_FALAR + "{{1}}",
            "example": [ENDERECO_FALAR + "1-0a1b2c3d4e5f6a7b"]}]})
    elif m["botao"] == "parar_e_chamar":
        # 044: os dois sao resposta rapida -- botao de link faz o toque na foto abrir o link
        saida.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": t}
                                                     for t in (BOTAO_PARAR, BOTAO_FALAR)]})
    elif m["botao"] == "triagem":
        saida.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": t} for t in BOTOES_TRIAGEM] + [{
            "type": "URL", "text": BOTAO_CANDIDATO, "url": ENDERECO_FALAR + "{{1}}",
            "example": [ENDERECO_FALAR + "v1-0a1b2c3d4e5f6a7b"]}]})
    elif m["botao"] == "ver":
        saida.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": BOTAO_VER}]})
    for b in (c for c in saida if c["type"] == "BUTTONS"):
        for botao in b["buttons"]:
            assert len(botao["text"]) <= LIMITE_BOTAO, botao["text"]
    return saida


def _listar(c: httpx.Client, cfg) -> list[dict]:
    r = c.get("/%s/message_templates" % cfg.meta_conta_wa,
              params={"fields": "name,language,status,category,rejected_reason", "limit": 200}).json()
    return r.get("data", [])


def ver(cfg, http=None) -> list[dict]:
    """So GET: os modelos da conta, com a situacao e o motivo de recusa."""
    with (http or _cliente(cfg)) as c:
        return _listar(c, cfg)


def _subir_exemplo(c: httpx.Client, cfg, imagem: Path) -> str:
    """O exemplo de cabecalho (a imagem, ou o PDF do #1098) vai pelo envio em partes da Meta e
    volta como `h`."""
    app = c.get("/app", params={"fields": "id"}).json()["id"]
    tipo = mimetypes.guess_type(imagem.name)[0] or "image/jpeg"
    dados = imagem.read_bytes()
    sessao = c.post("/%s/uploads" % app, params={"file_name": imagem.name, "file_length": len(dados),
                                                  "file_type": tipo}).json()["id"]
    r = c.post("/%s" % sessao, content=dados,
               headers={"Authorization": "OAuth " + cfg.meta_token, "file_offset": "0"}).json()
    return r["h"]


def propor(cfg, imagem: Path | None = None, http=None, documento: Path | None = None,
           so: list[str] | None = None) -> list[dict]:
    """Manda para aprovacao os modelos do cadastro que a Meta ainda nao tem. Devolve o que fez.
    `so`: so estes nomes (043) -- os outros que faltam ficam como estao."""
    feitos = []
    with (http or _cliente(cfg)) as c:
        ja = {(t["name"], t["language"]) for t in _listar(c, cfg)}
        faltam = [m for m in cadastro(cfg) if (m["nome"], m["idioma"]) not in ja and (not so or m["nome"] in so)]
        cabecalho = None
        if any(m["cabecalho_imagem"] for m in faltam):
            if not imagem:
                raise SystemExit("um dos modelos tem imagem no cabecalho: passe --imagem <arquivo.jpg>")
            cabecalho = _subir_exemplo(c, cfg, imagem)
        exemplo_pdf = None
        if any(m.get("cabecalho_documento") for m in faltam):
            if not documento:
                raise SystemExit("um dos modelos tem documento no cabecalho: passe --documento <arquivo.pdf>")
            exemplo_pdf = _subir_exemplo(c, cfg, documento)
        for m in faltam:
            corpo = {"name": m["nome"], "language": m["idioma"], "category": m["categoria"],
                     "components": componentes(m, cabecalho, exemplo_pdf)}
            r = c.post("/%s/message_templates" % cfg.meta_conta_wa, json=corpo).json()
            feitos.append({"nome": m["nome"], "resposta": r})
    return feitos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ver", action="store_true")
    g.add_argument("--propor", action="store_true")
    ap.add_argument("--imagem", type=Path)
    ap.add_argument("--documento", type=Path)
    ap.add_argument("--so", action="append", help="propor so este modelo (repetivel)")
    a = ap.parse_args(argv)
    cfg = config.carregar()
    migracoes.aplicar(cfg)   # o texto do cadastro pode ter sido acertado por mudanca nova
    if a.ver:
        nossos = {m["nome"] for m in cadastro(cfg)}
        r = [t for t in ver(cfg) if t["name"] in nossos]
    else:
        r = propor(cfg, a.imagem, documento=a.documento, so=a.so)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
