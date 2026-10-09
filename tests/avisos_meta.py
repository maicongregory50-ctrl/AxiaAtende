"""Avisos da Meta no formato da Cloud API (com o `user_id`, o BSUID, que o PyWa 4.5 exige)."""

NUMERO = "5549999990000"
BSUID = "BR.teste.1"


def aviso(mensagens=(), statuses=(), numero=NUMERO, bsuid=BSUID, nome="Teste"):
    valor = {"messaging_product": "whatsapp",
             "metadata": {"display_phone_number": "554936640121", "phone_number_id": "725888737278277"}}
    if mensagens:
        valor["contacts"] = [{"profile": {"name": nome}, "wa_id": numero, "user_id": bsuid}]
        valor["messages"] = list(mensagens)
    if statuses:
        valor["statuses"] = list(statuses)
    return {"object": "whatsapp_business_account",
            "entry": [{"id": "1442233593867052", "changes": [{"field": "messages", "value": valor}]}]}


def texto(wamid, corpo, numero=NUMERO):
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "text", "text": {"body": corpo}}


def toque(wamid, id_opcao, titulo="x", numero=NUMERO, lista=False):
    tipo = "list_reply" if lista else "button_reply"
    return {"from": numero, "id": wamid, "timestamp": "1760040000", "type": "interactive",
            "context": {"from": "554936640121", "id": "wamid.nosso"},
            "interactive": {"type": tipo, tipo: {"id": id_opcao, "title": titulo}}}


def status(wamid, situacao, numero=NUMERO):
    return {"id": wamid, "status": situacao, "timestamp": "1760040000", "recipient_id": numero}
