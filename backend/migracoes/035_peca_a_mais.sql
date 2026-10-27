-- #1175 -- a peca a mais: o dono pode mandar alem do teto do comprador (dono, 27/10/2026, decisao 3:
-- "precisa permitir"). Spec: C:\AxiaMarketing\docs\specs\2026-10-27-tipo-da-campanha-e-a-campanha-no-centro.md
-- -- plano ao lado, passo 6.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- A MARCA E DO ENVIO, nao do destinatario: e a peca que o dono decidiu mandar mesmo assim, e ela vale
-- para todos da fila. Quem escreve e `receber_pedido`, a partir do pedido do marketing; quem le e o
-- laco do lote (`envio.mandar_lotes`), antes do teto. Nenhum envio de hoje muda: o padrao e false.

ALTER TABLE atendimento.envios ADD COLUMN passa_do_teto boolean NOT NULL DEFAULT false;
