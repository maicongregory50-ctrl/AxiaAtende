"""O boletim DIRETO a quem nao o recebeu: um envio novo, do tipo `direta`, a partir de um convite. #1203.

Nasceu do Bom te ver de novo (dono, 29/10/2026): o convite `abertura_do_canal` (envio 6) foi suspenso
e quem nao recebeu o Boletim de safra no 1 o recebe pelo `informativo_curto`, em duas levas -- os que
faltam (`--grupo faltam`, 30/10) e o reenvio a quem recebeu o convite e nao tocou (`--grupo reenvio`,
03/11). Quem ja esta numa leva anterior nao entra de novo; `--dividir N` reparte em N envios (cada
um manda 20 por dia). `--prova <numero>` manda so ao numero dado (com prova_agora.py, fora da janela).

Do envio de origem (o convite da abertura do canal), entra quem ainda NAO RECEBEU o boletim:
- `aguardando`: o convite nem saiu (o envio foi suspenso);
- `convidado` sem resposta: recebeu o convite e nao tocou em nada (entregue, lido ou nao).
Fica de fora quem tocou "Quero receber" (ja recebeu as imagens), quem tocou "Nao quero" ou recusou
antes, quem nao tem responsavel com WhatsApp (o botao "Falar com meu atendimento" nao teria para
onde ir) e quem RESPONDEU POR TEXTO -- estes sao listados, para o dono ler o que escreveram.

O envio novo e real: mesma campanha e o codigo do ERP de cada cliente (o Relacionamento recebe o
evento). Sai pelo laco de sempre: 20 por dia por envio, seg-sex 9h30-17h, nota verde, teto do
comprador (duas por mes; quem recebeu o convite em outubro tem uma).

Sem `--gravar`, SO MOSTRA. Em producao, janela elevada:

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\direto_do_envio.py --envio 6 --modelo informativo_curto --grupo reenvio
    ... o mesmo, com --gravar
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import CELULAR, FUSO, _ultimo_consentimento, modelo  # noqa: E402


def separar(con, envio_id: int):
    entram, fora = [], {}
    for d in con.execute("""SELECT * FROM atendimento.envio_destinatarios WHERE envio_id = %s
                             ORDER BY posicao""", (envio_id,)).fetchall():
        if d["situacao"] not in ("aguardando", "convidado"):
            motivo = "situacao %s" % d["situacao"]
        elif d["resposta"] == "quero":
            motivo = "tocou Quero receber (ja tem o boletim)"
        elif d["resposta"] == "nao_quero" or _ultimo_consentimento(con, d["whatsapp"]) == "recusa":
            motivo = "recusou"
        elif d["resposta"] == "texto":
            motivo = "respondeu por texto"
        elif d["resposta"]:
            motivo = "resposta %s" % d["resposta"]
        elif not d["responsavel_nome"] or not CELULAR.match(d["responsavel_whatsapp"] or ""):
            motivo = "sem responsavel com WhatsApp"
        else:
            entram.append(d)
            continue
        fora.setdefault(motivo, []).append(d)
    return entram, fora


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--envio", type=int, required=True, help="o envio de origem (o convite)")
    a.add_argument("--modelo", required=True, help="modelo de uso direta, aprovado na Meta")
    a.add_argument("--assunto", default="", help="o {{2}} do modelo, quando ele o usa")
    a.add_argument("--peca", default="Boletim de safra nº 1", help="o nome que o ERP e o representante leem")
    a.add_argument("--capa", help="a imagem do cabecalho; sem ela, a 1a imagem do pacote de origem")
    a.add_argument("--prova", help="manda SO a este numero (a prova), com o texto e o botao do primeiro cliente")
    a.add_argument("--nome", default="Maicon Gregory", help="o nome da prova")
    a.add_argument("--grupo", choices=("faltam", "reenvio", "todos"), default="todos",
                   help="faltam: o convite nem saiu; reenvio: recebeu o convite e nao tocou; todos: os dois")
    a.add_argument("--dividir", type=int, default=1,
                   help="em quantos envios dividir a lista (cada envio manda 20 por dia)")
    a.add_argument("--gravar", action="store_true")
    args = a.parse_args()
    cfg = config.carregar()
    print("ambiente:", cfg.ambiente)
    with conexao(cfg) as con:
        e = con.execute("SELECT * FROM atendimento.envios WHERE id = %s", (args.envio,)).fetchone()
        if not e:
            sys.exit("envio %s nao existe" % args.envio)
        m = modelo(con, args.modelo)
        if not m or m["uso"] != "direta":
            sys.exit("o modelo %r nao existe no cadastro ou nao e de uso direta" % args.modelo)
        if "assunto" in (m["variaveis"] or []) and not args.assunto:
            sys.exit("o modelo %s usa o assunto: diga --assunto" % m["nome"])
        capa = args.capa
        if not capa:
            ref = con.execute("""SELECT imagens FROM atendimento.envio_destinatarios
                                  WHERE envio_id = %s AND imagens IS NOT NULL ORDER BY posicao LIMIT 1""",
                              (e["id"],)).fetchone()
            capa = (ref["imagens"] if ref else e["imagens"] or [None])[0]
        print("\norigem: envio %s (%s), situacao %s" % (e["id"], e["pedido_ref"], e["situacao"]))
        if e["situacao"] in ("ativo", "parado_nota"):
            print("  ATENCAO: o envio de origem ainda esta ativo; suspenda-o antes, ou os aguardando recebem os dois")
        print("modelo: %s  |  peca: %s  |  assunto: %s" % (m["nome"], args.peca, args.assunto or "-"))
        print("texto:  %s" % m["texto"])
        print("capa:   %s  %s" % (capa, "ok" if capa and Path(capa).is_file() else "ARQUIVO NAO ENCONTRADO"))
        entram, fora = separar(con, e["id"])
        # quem ja esta num envio direto feito daqui (uma leva anterior) nao entra de novo
        ja = {r["whatsapp"] for r in con.execute(
            """SELECT d.whatsapp FROM atendimento.envio_destinatarios d JOIN atendimento.envios x ON x.id = d.envio_id
                WHERE x.pedido_ref LIKE %s AND x.pedido_ref NOT LIKE %s""",
            (e["pedido_ref"] + "-direto-%", e["pedido_ref"] + "-prova-%"))}
        for d in [d for d in entram if d["whatsapp"] in ja]:
            fora.setdefault("ja esta numa leva direta anterior", []).append(d)
        entram = [d for d in entram if d["whatsapp"] not in ja]
        so = {"faltam": "aguardando", "reenvio": "convidado"}.get(args.grupo)
        if so:
            for d in [d for d in entram if d["situacao"] != so]:
                fora.setdefault("de outro grupo (--grupo %s)" % args.grupo, []).append(d)
            entram = [d for d in entram if d["situacao"] == so]
        aguardando = sum(1 for d in entram if d["situacao"] == "aguardando")
        print("\nENTRAM: %d  (convite nao saiu: %d; recebeu o convite e nao tocou: %d)"
              % (len(entram), aguardando, len(entram) - aguardando))
        sem_entrega = [d for d in entram if d["situacao"] == "convidado" and not d["entregue_em"]]
        if sem_entrega:
            print("  destes, %d com o convite ainda SEM ENTREGA (podem receber os dois quando o aparelho voltar)"
                  % len(sem_entrega))
        n = max(1, args.dividir)
        print("  em %d envio(s), a 20 por dia cada: %d dia(s) uteis" % (n, -(-len(entram) // (20 * n))))
        if "responsavel" in (m["variaveis"] or []):
            nomes = {}
            for d in entram:
                nomes[d["responsavel_nome"]] = nomes.get(d["responsavel_nome"], 0) + 1
            print("  o responsavel, como sai no texto (\"fale com ...\"):")
            for n, q in sorted(nomes.items(), key=lambda x: -x[1]):
                print("    %-40s %d" % (n, q))
        for motivo, ds in sorted(fora.items()):
            print("FORA:   %-45s %d" % (motivo, len(ds)))
        for d in fora.get("respondeu por texto", []):
            print("        %s (%s): %r" % (d["nome"], d["erp_codigo"], d["resposta_texto"][:120]))
        if not capa or not Path(capa).is_file():
            sys.exit("\nsem a imagem do cabecalho nao grava")
        if not args.gravar:
            print("\nso mostrei. Para gravar, repita com --gravar")
            return
        if not entram:
            sys.exit("ninguem a mandar")
        agora = datetime.now(FUSO)
        ref = "%s-direto-%s-%s" % (e["pedido_ref"], args.grupo, agora.strftime("%Y%m%d%H%M%S"))
        campanha, lote, teto = e["campanha"], 20, False
        if args.prova:
            # a mesma mensagem, so ao numero da prova: codigo 0 (o ERP ignora), o responsavel do
            # primeiro cliente (o texto e o botao saem iguais), canal dono (sem resumo ao representante)
            numero = "".join(c for c in args.prova if c.isdigit())
            if not CELULAR.match(numero):
                sys.exit("numero %r nao e celular no formato 55 + DDD + 9 + 8 digitos" % args.prova)
            p = entram[0]
            entram = [{**p, "erp_codigo": 0, "nome": args.nome, "cidade": "", "uf": "", "whatsapp": numero,
                       "faturamento": 0, "posicao": 1, "papel": None, "responsavel_canal": "dono"}]
            ref, campanha, lote, teto = ref.replace("-direto-", "-prova-direto-"), "PROVA - " + campanha, 1, True
            print("PROVA: so para %s (%s); o responsavel no texto e o de %s: %s"
                  % (args.nome, numero, p["nome"], p["responsavel_nome"]))
        partes = [entram] if args.prova else [entram[k::n] for k in range(n)]
        for k, parte in enumerate(p for p in partes if p):
            ref_k = ref if len(partes) == 1 else "%s-%d" % (ref, k + 1)
            novo = con.execute(
                """INSERT INTO atendimento.envios (pedido_ref, tipo, campanha, peca, assunto, modelo, capa, imagens,
                                                   aprovado_por, aprovado_em, lote_tamanho, passa_do_teto)
                   VALUES (%s, 'direta', %s, %s, %s, %s, %s, '[]'::jsonb, %s, now(), %s, %s) RETURNING id""",
                (ref_k, campanha, args.peca, args.assunto, m["nome"], capa,
                 "dono (script, a partir do envio %s)" % e["id"], lote, teto)).fetchone()["id"]
            for d in parte:
                con.execute(
                    """INSERT INTO atendimento.envio_destinatarios
                           (envio_id, erp_codigo, nome, cidade, uf, whatsapp, faturamento, posicao,
                            responsavel_nome, responsavel_whatsapp, sugestao_vendedor, situacao,
                            aceite_cadastro, papel, responsavel_canal)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'aguardando', %s, %s, %s)""",
                    (novo, d["erp_codigo"], d["nome"], d["cidade"], d["uf"], d["whatsapp"], d["faturamento"],
                     d["posicao"], d["responsavel_nome"], d["responsavel_whatsapp"], d["sugestao_vendedor"],
                     d["aceite_cadastro"], d["papel"], d["responsavel_canal"]))
            print("gravado: envio %s (%s), %d clientes." % (novo, ref_k, len(parte)))
        print("\nSai no proximo lote, dentro da janela (seg-sex, 9h30-17h).")


if __name__ == "__main__":
    main()
