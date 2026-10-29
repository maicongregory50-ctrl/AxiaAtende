-- VOLTA da 042 (#1128). Nunca e aplicada junto com a ida.
--
-- ANTES DELA: o codigo do pedido de CT-e revertido (logistica_erp.py, a volta das telas e a chamada no
-- recepcionista) e os dois processos reiniciados.
--
-- O historico do que foi mandado fica no ERP (axia.fretes_pedidos_cte, com o estado e o wamid); aqui era a
-- fila de passagem. Pedido ainda nao devolvido ao ERP fica PENDENTE la, sem efeito.
BEGIN;

DROP TABLE atendimento.pedidos_cte;
DELETE FROM casa.mudancas WHERE nome = '042_pedido_de_cte.sql';

DO $$ BEGIN RAISE NOTICE '042 VOLTA OK: atendimento.pedidos_cte removida'; END $$;

COMMIT;
