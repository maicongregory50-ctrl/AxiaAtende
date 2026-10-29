-- #1128 -- o pedido de CT-e da Logistica do ERP: a ficha do frete vai ao WhatsApp do destino "Logistica"
-- (dono, 29/10/2026). Spec e plano: C:\AxiaGestao\docs\specs\2026-10-29-logistica-fretes*.md (passo 8).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- DOIS PROCESSOS, como o envio do marketing: o das TELAS (que tem o segredo do ERP e nao fala com a Meta)
-- busca o pedido no ERP, baixa a ficha para `envios_pasta` e grava a linha; o RECEPCIONISTA (o unico que
-- fala com a Meta e nao le o ERP) manda o PDF com a linha de texto, SO com a janela de 24 h aberta (sem
-- modelo: decisao do dono), e grava enviado ou o erro; as TELAS devolvem o estado ao ERP.

CREATE TABLE atendimento.pedidos_cte (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    erp_pedido_id  integer NOT NULL UNIQUE,      -- axia.fretes_pedidos_cte.id no ERP
    frete_numero   text NOT NULL,
    texto          text NOT NULL,                -- a legenda do PDF, montada pelo ERP
    arquivo        text NOT NULL,                -- o PDF em envios_pasta
    para_nome      text NOT NULL DEFAULT '',
    para_whatsapp  text NOT NULL DEFAULT '',
    criado_em      timestamptz NOT NULL DEFAULT now(),
    enviado_em     timestamptz,
    wamid          text NOT NULL DEFAULT '',
    erro           text NOT NULL DEFAULT '',
    devolvido_em   timestamptz                   -- quando o estado voltou ao ERP
);
CREATE INDEX pedidos_cte_a_mandar ON atendimento.pedidos_cte (id) WHERE enviado_em IS NULL AND erro = '';
