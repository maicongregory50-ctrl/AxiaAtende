-- Desfaz a 055 (#1248): as duas colunas saem. O aviso que voltou a fila nao volta ao erro (o texto do
-- erro antigo nao foi guardado); se ainda nao saiu, sai na volta seguinte como qualquer aviso.
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). O CODIGO JA DEVE TER
-- SIDO REVERTIDO antes dele -- senao envio.mandar_avisos procura colunas que nao existem.
BEGIN;

ALTER TABLE atendimento.avisos DROP COLUMN tentativa_em, DROP COLUMN tentativas;

DELETE FROM casa.mudancas WHERE nome = '055_aviso_tenta_de_novo.sql';

COMMIT;
