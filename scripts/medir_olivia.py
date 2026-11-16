"""#1520, passo 16: a medicao da OlivIA que fala com quem e de fora. SO LEITURA, pelo papel `axiaatende_ro`
(o mesmo leitor de `ler_conversa.py`; a leitura fica no log do Postgres do papel).

    python -X utf8 scripts\\medir_olivia.py [--desde 2026-11-16] [--dias 7]

O que mede, no periodo:
- conversas em que a OlivIA falou; como o vigia as fechou (bem / sem saida / ainda sem leitura);
- frases recusadas pelo filtro, por motivo;
- audios de fora (recebidos, transcritos, com erro);
- o custo em `uso_ia` (conversa e leitura do arquivo, tokens e US$ pelo preco da tabela);
- a conversao da vaga de chao de fabrica (curriculos / conversas de vaga), contra os 4 de 30 de 13/11/2026
  (a linha de base da spec), e quantos curriculos vieram em foto.
"""
import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ler_conversa import conectar  # noqa: E402

BASE_CHAO = (4, 30)   # 13/11/2026: 4 curriculos em 30 conversas de vaga de chao de fabrica (spec, O universo medido)
BASE_VAGA = (11, 38)  # #1525, 16/11/2026: 11 curriculos em 38 conversas de vaga desde 12/11 (spec, O universo medido)


def medir(con, desde: datetime) -> dict:
    con.execute("SET TRANSACTION READ ONLY")
    falou = """(c.conduzida_por = 'olivia' OR EXISTS (SELECT 1 FROM atendimento.enviadas e
                 WHERE e.conversa_id = c.id AND e.resumo LIKE 'olivia:%%'))"""
    c = con.execute("""SELECT count(*) AS n,
                              count(*) FILTER (WHERE c.saida = 'bem') AS bem,
                              count(*) FILTER (WHERE c.saida = 'sem_saida') AS sem_saida,
                              count(*) FILTER (WHERE c.saida IS NULL) AS sem_leitura
                         FROM atendimento.conversas c WHERE c.iniciada_em >= %s AND """ + falou, (desde,)).fetchone()
    recusadas = con.execute("""SELECT substr(resumo, length('olivia: recusada: ') + 1) AS motivo, count(*) AS n FROM atendimento.enviadas
                                WHERE resumo LIKE 'olivia: recusada%%' AND enviada_em >= %s GROUP BY 1 ORDER BY 2 DESC""",
                            (desde,)).fetchall()
    falas = con.execute("""SELECT count(*) AS n FROM atendimento.enviadas
                            WHERE resumo LIKE 'olivia: fala%%' AND enviada_em >= %s""", (desde,)).fetchone()["n"]
    audios = con.execute("""SELECT count(*) AS n, count(*) FILTER (WHERE transcrito_em IS NOT NULL) AS transcritos,
                                   count(*) FILTER (WHERE erro <> '') AS com_erro
                              FROM atendimento.audios WHERE de_fora AND recebido_em >= %s""", (desde,)).fetchone()
    custo = con.execute("""SELECT u.funcao, u.modelo, count(*) AS chamadas, sum(u.entrada) AS entrada, sum(u.saida) AS saida,
                                  sum((u.entrada * p.por_milhao_entrada + u.saida * p.por_milhao_saida) / 1000000) AS usd
                             FROM atendimento.uso_ia u
                             LEFT JOIN LATERAL (SELECT por_milhao_entrada, por_milhao_saida FROM atendimento.precos
                                                 WHERE servico = u.servico AND item = u.modelo
                                                   AND vale_desde <= (u.em AT TIME ZONE 'America/Sao_Paulo')::date
                                                 ORDER BY vale_desde DESC LIMIT 1) p ON true
                            WHERE u.funcao IN ('conversa', 'leitura_arquivo') AND u.em >= %s
                            GROUP BY 1, 2 ORDER BY 1""", (desde,)).fetchall()
    # O papel de leitura NAO le `candidaturas` (o curriculo mora la, #981/#1098): o curriculo conta pela
    # situacao da conversa, e a foto pelo envio a Fran como imagem (`enviadas`, tipo imagem).
    chao = con.execute("""SELECT count(*) AS conversas,
                                 count(*) FILTER (WHERE c.situacao = 'curriculo_recebido') AS curriculos,
                                 (SELECT count(*) FROM atendimento.enviadas e
                                   WHERE e.tipo = 'imagem' AND e.resumo LIKE 'curriculo %% para a fran'
                                     AND e.enviada_em >= %s) AS em_foto
                            FROM atendimento.conversas c
                            JOIN atendimento.vagas v ON v.id = c.vaga_id
                           WHERE c.trabalhe AND c.iniciada_em >= %s
                             AND (v.titulo ILIKE '%%produ%%' OR v.titulo ILIKE '%%empilhadeira%%')""",
                       (desde, desde)).fetchone()
    # #1525: a conversa da vaga conduzida por ela. A ficha conta pelo envio a Fran (`enviadas`, "ficha N para a
    # fran" / "ficha incompleta N ..."): o papel de leitura nao le `candidaturas.ficha`, de proposito.
    vaga = con.execute("""SELECT count(*) AS conversas,
                                 count(*) FILTER (WHERE c.situacao = 'curriculo_recebido') AS com_candidatura,
                                 count(*) FILTER (WHERE c.vaga_lembrada_em IS NOT NULL) AS tocadas,
                                 count(*) FILTER (WHERE c.vaga_lembrada_em IS NOT NULL AND c.ultimo_toque_em > c.vaga_lembrada_em)
                                     AS responderam_ao_toque
                            FROM atendimento.conversas c
                           WHERE c.trabalhe AND c.iniciada_em >= %s""", (desde,)).fetchone()
    envios = con.execute("""SELECT count(*) FILTER (WHERE resumo ~ '^ficha [0-9]+ para a fran') AS fichas,
                                   count(*) FILTER (WHERE resumo ~ '^ficha incompleta [0-9]+ para a fran') AS incompletas,
                                   count(*) FILTER (WHERE resumo ~ '^curriculo [0-9]+ para a fran') AS curriculos
                              FROM atendimento.enviadas WHERE enviada_em >= %s""", (desde,)).fetchone()
    visita = con.execute("""SELECT count(*) AS n FROM atendimento.candidaturas
                             WHERE quer_visita AND recebida_em >= %s""", (desde,)).fetchone()["n"]
    return {"conversas": dict(c), "falas": falas, "recusadas": [dict(r) for r in recusadas], "audios": dict(audios),
            "custo": [dict(r) for r in custo], "chao": dict(chao),
            "vaga": dict(vaga, **dict(envios), quer_visita=visita)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", help="AAAA-MM-DD (padrao: --dias atras)")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--dsn", help=argparse.SUPPRESS)
    a = ap.parse_args()
    desde = (datetime.combine(date.fromisoformat(a.desde), datetime.min.time(), tzinfo=timezone(timedelta(hours=-3)))
             if a.desde else datetime.now(timezone.utc) - timedelta(days=a.dias))
    con = conectar(a.dsn)
    m = medir(con, desde)
    c = m["conversas"]
    print("OlivIA desde %s" % desde.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"))
    print("conversas em que ela falou: %d (bem %d, sem saída %d, ainda sem leitura do vigia %d); falas: %d"
          % (c["n"], c["bem"], c["sem_saida"], c["sem_leitura"], m["falas"]))
    print("frases recusadas: %s" % (", ".join("%s %d" % (r["motivo"], r["n"]) for r in m["recusadas"]) or "nenhuma"))
    au = m["audios"]
    print("áudios de fora: %d (transcritos %d, com erro %d)" % (au["n"], au["transcritos"], au["com_erro"]))
    total = 0.0
    for r in m["custo"]:
        usd = float(r["usd"] or 0)
        total += usd
        print("custo %s (%s): %d chamadas, %d tokens de entrada, %d de saída, US$ %.4f%s"
              % (r["funcao"], r["modelo"], r["chamadas"], r["entrada"], r["saida"], usd,
                 "" if r["usd"] is not None else " (sem preço)"))
    print("custo total: US$ %.4f (entrada contada cheia: o cache da Anthropic sai mais barato)" % total)
    ch = m["chao"]
    taxa = (ch["curriculos"] / ch["conversas"]) if ch["conversas"] else 0
    print("vaga de chão de fábrica: %d currículos (%d em foto) em %d conversas = %.0f%%; linha de base 13/11: %d de %d = %.0f%%"
          % (ch["curriculos"], ch["em_foto"], ch["conversas"], taxa * 100, BASE_CHAO[0], BASE_CHAO[1],
             100 * BASE_CHAO[0] / BASE_CHAO[1]))
    v = m["vaga"]
    chegaram = v["fichas"] + v["incompletas"] + v["curriculos"]
    print("conversas de vaga (#1525): %d; à Fran: %d fichas completas, %d incompletas, %d currículos = %d "
          "(%.0f%%); linha de base 16/11: %d de %d = %.0f%%"
          % (v["conversas"], v["fichas"], v["incompletas"], v["curriculos"], chegaram,
             100 * chegaram / v["conversas"] if v["conversas"] else 0, BASE_VAGA[0], BASE_VAGA[1],
             100 * BASE_VAGA[0] / BASE_VAGA[1]))
    print("toques únicos: %d mandados, %d com resposta depois; quer visitar a empresa: %d"
          % (v["tocadas"], v["responderam_ao_toque"], v["quer_visita"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
