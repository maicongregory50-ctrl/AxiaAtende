-- Desfaz a 058 (#1169): a chave e as duas colunas saem. O envio que ficou `suspenso` continua suspenso
-- (o estado ja existia), e o script do #1203 continua religando.
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). O CODIGO JA DEVE TER
-- SIDO REVERTIDO antes dele -- senao segurar.py procura colunas que nao existem.
BEGIN;

DELETE FROM atendimento.ajustes WHERE chave = 'envio.segurar';
ALTER TABLE atendimento.envios DROP COLUMN suspenso_em, DROP COLUMN suspenso_por;

DELETE FROM casa.mudancas WHERE nome = '058_segurar_envio.sql';

COMMIT;
