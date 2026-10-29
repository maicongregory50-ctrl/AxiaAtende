"""A prova do envio: o MESMO pacote de um envio da carteira, a um numero so (o do dono).

Copia o envio (modelo, capa, imagens, peca, assunto) para um envio NOVO, `<pedido_ref>-prova-<hora>`,
com uma linha so: o numero dado. A capa e as imagens sao as de um cliente que ja recebeu (os mesmos
arquivos da pasta de envios). O responsavel e o mesmo daquele cliente, para o texto sair igual, mas
com o canal `dono`: o resumo do lote nao vai ao representante.

O que fica diferente, de proposito:
- `erp_codigo = 0`: o ERP ignora (nao e cliente), o Relacionamento nao ganha linha;
- a campanha leva "PROVA - " na frente (a tela Envios a separa; o texto do modelo nao a usa);
- lote de 1, e passa do teto.
Sai pelo laco de sempre do recepcionista: so de segunda a sexta, das 9h30 as 17h, com a nota verde.

Sem `--gravar`, SO MOSTRA. Em producao, janela elevada:

    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\prova_do_envio.py
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\prova_do_envio.py --envio <id> --numero 55DDD9XXXXXXXX
    C:\\AxiaAtende\\.venv\\Scripts\\python.exe C:\\AxiaAtende\\scripts\\prova_do_envio.py --envio <id> --numero 55DDD9XXXXXXXX --gravar
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.banco import conexao  # noqa: E402
from backend.envio import (CELULAR, DIAS_DA_JANELA, FUSO, JANELA_FIM, JANELA_INICIO,  # noqa: E402
                           so_digitos)


def listar(con, busca: str):
    for e in con.execute(
            """SELECT e.id, e.pedido_ref, e.tipo, e.campanha, e.peca, e.modelo, e.situacao, e.aprovado_em,
                      count(d.*) FILTER (WHERE d.convite_em IS NOT NULL) AS convidados
                 FROM atendimento.envios e LEFT JOIN atendimento.envio_destinatarios d ON d.envio_id = e.id
                WHERE e.campanha ILIKE %s OR e.peca ILIKE %s OR e.pedido_ref ILIKE %s
                GROUP BY e.id ORDER BY e.id""", ("%" + busca + "%",) * 3).fetchall():
        print("envio %(id)s  %(pedido_ref)s  %(tipo)s  modelo=%(modelo)s  %(situacao)s  convidados=%(convidados)s"
              % e)
        print("    campanha: %(campanha)s  |  peca: %(peca)s  |  aprovado em %(aprovado_em)s" % e)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--busca", default="bom te ver")
    a.add_argument("--envio", type=int)
    a.add_argument("--numero")
    a.add_argument("--nome", default="Maicon Gregory")
    a.add_argument("--gravar", action="store_true")
    args = a.parse_args()
    cfg = config.carregar()
    print("ambiente:", cfg.ambiente if hasattr(cfg, "ambiente") else "?")
    with conexao(cfg) as con:
        if not args.envio:
            listar(con, args.busca)
            print("\nescolha o envio com --envio <id> e diga o numero com --numero")
            return
        numero = so_digitos(args.numero or "")
        if not CELULAR.match(numero):
            sys.exit("numero %r nao e celular no formato 55 + DDD + 9 + 8 digitos" % args.numero)
        e = con.execute("SELECT * FROM atendimento.envios WHERE id = %s", (args.envio,)).fetchone()
        if not e:
            sys.exit("envio %s nao existe" % args.envio)
        m = con.execute("""SELECT * FROM atendimento.envio_destinatarios
                            WHERE envio_id = %s AND convite_em IS NOT NULL ORDER BY posicao LIMIT 1""",
                        (e["id"],)).fetchone()
        if not m:
            sys.exit("envio %s ainda nao mandou a ninguem: nao ha o pacote de um cliente para copiar" % e["id"])
        capa = m["capa"] or e["capa"]
        imagens = m["imagens"] if m["imagens"] is not None else e["imagens"]
        print("\no pacote do envio %s (%s), copiado do cliente %s (%s):" % (e["id"], e["pedido_ref"],
                                                                             m["erp_codigo"], m["nome"]))
        print("  modelo:", e["modelo"], "| tipo:", e["tipo"], "| peca:", e["peca"], "| assunto:", e["assunto"])
        for rotulo, c in [("capa", capa)] + [("imagem %d" % i, c) for i, c in enumerate(imagens, 1)]:
            print("  %-9s %s  %s" % (rotulo, c, "ok" if c and Path(c).is_file() else "ARQUIVO NAO ENCONTRADO"))
        print("  responsavel no texto: %s (canal dono: sem resumo ao representante)" % m["responsavel_nome"])
        print("  para: %s (%s)" % (args.nome, numero))
        agora = datetime.now(FUSO)
        dentro = agora.weekday() in DIAS_DA_JANELA and JANELA_INICIO <= agora.time() < JANELA_FIM
        print("  janela de envio:", "aberta agora" if dentro else "FECHADA: sai no proximo dia util, 9h30")
        if not args.gravar:
            print("\nso mostrei. Para gravar, repita com --gravar")
            return
        ref = "%s-prova-%s" % (e["pedido_ref"], agora.strftime("%Y%m%d%H%M"))
        novo = con.execute(
            """INSERT INTO atendimento.envios (pedido_ref, tipo, campanha, peca, assunto, modelo, capa, imagens,
                                               aprovado_por, aprovado_em, lote_tamanho, passa_do_teto)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, now(), 1, true) RETURNING id""",
            (ref, e["tipo"], "PROVA - " + e["campanha"], e["peca"], e["assunto"], e["modelo"], e["capa"],
             json.dumps(e["imagens"]), "prova do dono (script)")).fetchone()["id"]
        con.execute(
            """INSERT INTO atendimento.envio_destinatarios
                   (envio_id, erp_codigo, nome, whatsapp, posicao, responsavel_nome, responsavel_whatsapp,
                    situacao, capa, imagens, aceite_cadastro, papel, responsavel_canal)
               VALUES (%s, 0, %s, %s, 1, %s, %s, 'aguardando', %s, %s::jsonb, true, NULL, 'dono')""",
            (novo, args.nome, numero, m["responsavel_nome"], m["responsavel_whatsapp"], m["capa"],
             json.dumps(m["imagens"]) if m["imagens"] is not None else None))
        print("\ngravado: envio %s (%s). Sai na proxima volta do recepcionista (1 min), dentro da janela." % (novo, ref))


if __name__ == "__main__":
    main()
