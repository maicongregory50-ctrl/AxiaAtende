-- #1664 -- a VOLTA da 073: os quatro ajustes do cooperante saem. Sem eles o codigo le a chave desligada (o
-- padrao) e o produtor que responde a um aviso volta ao portao do cliente, como antes. E o ultimo passo do
-- ROLLBACK_PLAN da spec, depois do revert do codigo. Nada se perde: as respostas ficam em `enviadas`.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM atendimento.ajustes
 WHERE chave IN ('cooperante.resposta_padrao', 'cooperante.dias', 'cooperante.texto', 'cooperante.destino');
DELETE FROM casa.mudancas WHERE nome = '073_resposta_ao_cooperante.sql';
