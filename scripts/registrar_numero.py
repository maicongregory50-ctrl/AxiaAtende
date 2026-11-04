"""Registra o numero na Cloud API (o passo que tira o status PENDING). ATO DO DONO, uma vez, na janela
elevada, com o PIN de dois passos na mao -- o sistema NUNCA faz isto sozinho (regra 1 do CLAUDE.md), e por
isso o script exige o PIN e a palavra "sim" na linha de comando. #1242, 04/11/2026.
    cd C:\\AxiaAtende
    $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
    .\\.venv\\Scripts\\python.exe scripts\\registrar_numero.py --pin 123456 --sim
O PIN: se o numero JA TEM verificacao em duas etapas, tem de ser o PIN dela (errado = recusa, e a Meta
limita a 10 tentativas em 72 h). Se NAO tem, o PIN informado passa a ser o PIN do numero: guarde-o.
Nunca imprime o token. Depois, scripts\\numero_meta.py deve mostrar status CONNECTED.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx  # noqa: E402

from backend import config  # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    if "--sim" not in args or "--pin" not in args:
        print("uso: registrar_numero.py --pin <6 digitos> --sim   (sem --sim nao faz nada)")
        return 2
    pin = args[args.index("--pin") + 1]
    if not (pin.isdigit() and len(pin) == 6):
        print("o PIN tem 6 digitos")
        return 2
    cfg = config.carregar()
    if not cfg.meta_token:
        print("sem META_TOKEN (rodar elevado, com AXIAATENDE_PROCESSO=recepcionista)")
        return 2
    url = "%s/%s/%s/register" % (config.META_URL, cfg.meta_versao, cfg.meta_phone_id)
    print("registrando o numero %s (phone_id %s) ..." % ("49 3664-0121", cfg.meta_phone_id))
    with httpx.Client(timeout=30) as c:
        r = c.post(url, json={"messaging_product": "whatsapp", "pin": pin},
                   headers={"Authorization": "Bearer " + cfg.meta_token})
    print("HTTP %d" % r.status_code)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    if r.status_code == 200:
        print("\nRegistrado. Confira com scripts\\numero_meta.py (status CONNECTED) e mande um 'oi' ao numero.")
    else:
        print("\nRecusado. Erro 133005/136025 = PIN errado (nao insista: 10 tentativas em 72 h); "
              "133016 = tentativas demais, espere; 133015 = numero excluido ha pouco, espere 5 min.")
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
