"""A troca do dia (#950, Fases G5 e H): o app do AxiaAtende passa a OUVIR a conta do WhatsApp.

    python -m backend.troca --ver        so leitura: quem ouve a conta e o estado do numero
    python -m backend.troca --assinar    o app do AxiaAtende passa a ouvir a conta (POST subscribed_apps)

Roda em janela elevada, com AXIAATENDE_AMBIENTE=producao e AXIAATENDE_PROCESSO=recepcionista (le o
token do .env.recepcionista; o token nunca e impresso).

POR QUE NAO HA REDIRECIONAMENTO POR NUMERO AQUI (documentacao da Meta lida em 09/10/2026): o
redirecionamento de avisos ("override") vale por APLICATIVO. O app do Opa continuaria recebendo e
respondendo. Entao a troca e:
  1. este app ouve a conta (`--assinar`), com o recepcionista EM ESCUTA (ATENDE_RESPONDE=false);
  2. no dia: o dono desliga o robo da OlivIA no painel do Opa e liga ATENDE_RESPONDE=true;
  3. a volta: religar o robo no Opa e ATENDE_RESPONDE=false. Nada aqui tira o app do Opa da conta.

NUNCA, em nenhum comando: registrar ou desregistrar o numero, PIN, nome exibido, migracao de conta
(spec, "Cuidado com a Meta").
"""
import argparse
import json
import sys

import httpx

from . import config


def _cliente(cfg) -> httpx.Client:
    if not cfg.meta_token:
        raise SystemExit("falta o META_TOKEN no .env.recepcionista (rode como administrador, em producao)")
    return httpx.Client(base_url="%s/v%s" % (cfg.meta_url, cfg.meta_versao.lstrip("v")),
                        headers={"Authorization": "Bearer " + cfg.meta_token}, timeout=20)


def ver(cfg, http=None) -> dict:
    """So GET: os apps que ouvem a conta e o numero (nome, situacao, nota, configuracao de avisos)."""
    with (http or _cliente(cfg)) as c:
        apps = c.get("/%s/subscribed_apps" % cfg.meta_conta_wa).json()
        numero = c.get("/%s" % cfg.meta_phone_id,
                       params={"fields": "display_phone_number,verified_name,status,quality_rating,webhook_configuration"}).json()
    return {"apps": apps, "numero": numero}


def assinar(cfg, http=None) -> dict:
    """O app do AxiaAtende passa a ouvir a conta. Nao mexe na assinatura de ninguem mais."""
    with (http or _cliente(cfg)) as c:
        return c.post("/%s/subscribed_apps" % cfg.meta_conta_wa).json()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ver", action="store_true")
    g.add_argument("--assinar", action="store_true")
    a = ap.parse_args(argv)
    cfg = config.carregar()
    r = ver(cfg) if a.ver else assinar(cfg)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
