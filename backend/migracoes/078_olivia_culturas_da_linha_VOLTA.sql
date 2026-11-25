-- #1754 -- a VOLTA da 078: sai a lista da linha e a coluna do pedido fora da linha. ANTES: o codigo revertido
-- e os dois processos reiniciados. PERDE o que foi pedido fora da linha (a ficha ja mandada fica no WhatsApp
-- de quem recebeu). Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.interesses DROP COLUMN fora_da_linha;
DELETE FROM atendimento.ajustes WHERE chave = 'olivia.culturas_da_linha';
DELETE FROM casa.mudancas WHERE nome = '078_olivia_culturas_da_linha.sql';
