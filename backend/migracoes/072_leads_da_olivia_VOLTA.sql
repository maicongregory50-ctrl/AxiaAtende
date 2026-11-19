-- #1660 -- a VOLTA da 072: a ficha do produtor e a chave do piloto saem. Sem a chave o codigo le "desligada"
-- (o padrao) e a OlivIA volta a so receber e direcionar (#1589). PERDE as fichas guardadas: e o ultimo passo
-- do ROLLBACK_PLAN da spec, depois do revert do codigo.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DROP TABLE atendimento.leads;
DELETE FROM atendimento.ajustes WHERE chave IN ('olivia.qualifica_produtor', 'olivia.qualifica_estados');
DELETE FROM casa.mudancas WHERE nome = '072_leads_da_olivia.sql';
