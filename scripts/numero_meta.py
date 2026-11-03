"""O numero da Renascer ainda esta na Meta? SO LEITURA (03/11/2026, dono: "diz que o WhatsApp da Renascer
nao existe mais", logo depois de cancelar o Opa Suite). Em producao, janela elevada:
    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\numero_meta.py
Faz dois GET na Graph API com o token do recepcionista e imprime so o estado: o numero (status, nome
exibido, qualidade, limite), os numeros da conta (WABA 1442233593867052) e os apps inscritos no webhook.
NAO registra, NAO desregistra, NAO muda nada (regra 1 do CLAUDE.md). Nunca imprime o token.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx  # noqa: E402

from backend import config  # noqa: E402

WABA = "1442233593867052"
CAMPOS_NUMERO = ("id,display_phone_number,verified_name,name_status,code_verification_status,status,"
                 "quality_rating,messaging_limit_tier,platform_type,is_official_business_account,"
                 "account_mode,throughput")


def main() -> int:
    cfg = config.carregar()
    if not cfg.meta_token:
        print("sem META_TOKEN no .env.recepcionista (rodar com AXIAATENDE_PROCESSO=recepcionista, elevado)")
        return 2
    base = "https://graph.facebook.com/%s" % cfg.meta_versao
    cab = {"Authorization": "Bearer " + cfg.meta_token}
    with httpx.Client(timeout=20) as c:
        for rotulo, url, params in (
                ("NUMERO %s" % cfg.meta_phone_id, "%s/%s" % (base, cfg.meta_phone_id), {"fields": CAMPOS_NUMERO}),
                ("NUMEROS DA CONTA %s" % WABA, "%s/%s/phone_numbers" % (base, WABA),
                 {"fields": "id,display_phone_number,verified_name,status,name_status,quality_rating,platform_type"}),
                ("APPS INSCRITOS NO WEBHOOK", "%s/%s/subscribed_apps" % (base, WABA), {}),
                ("CONTA", "%s/%s" % (base, WABA),
                 {"fields": "id,name,account_review_status,business_verification_status,ownership_type,on_behalf_of_business_info"})):
            try:
                r = c.get(url, params=params, headers=cab)
                corpo = r.json()
            except Exception as falha:  # noqa: BLE001
                print("== %s: %s: %s" % (rotulo, type(falha).__name__, falha))
                continue
            print("== %s (HTTP %d)" % (rotulo, r.status_code))
            print(json.dumps(corpo, ensure_ascii=False, indent=2))
    print("\nLeitura: status=CONNECTED e name_status=APPROVED e o numero vivo na Cloud API; status=DISCONNECTED/"
          "DELETED, ou erro 100/33 'Unsupported get request' no numero, e o numero fora da conta. Se a lista da "
          "conta nao trouxer o 49 3664 0121, alguem o removeu da WABA. Nada aqui muda nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
