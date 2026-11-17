-- #1589 -- a VOLTA da 070: a chave da conversa de venda sai. Sem ela o codigo le "desligada" (o padrao),
-- e quem quer comprar recebe os botoes do Comercial, como antes. Nao apaga conversa nenhuma.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM atendimento.ajustes WHERE chave = 'olivia.conduz_venda';
DELETE FROM casa.mudancas WHERE nome = '070_olivia_conduz_venda.sql';
