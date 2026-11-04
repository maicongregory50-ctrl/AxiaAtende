-- Desfaz a 056 (#1097): as tres fichas do Willian voltam ao que eram e a coluna sai. Outra foto que
-- tenha ficado sem dia passa a ter o dia do envio (o que o fechamento presumiria), para o catalogo nao
-- ficar com dia vazio sem a regra que o explica.
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). O CODIGO JA DEVE TER
-- SIDO REVERTIDO antes dele -- senao campo._fechar procura uma coluna que nao existe.
BEGIN;

UPDATE atendimento.material_de_campo
   SET legenda = legenda || ' · Não', classe_fase = 'pre-colheita',
       data_dita = '2026-10-21', data_presumida = true
 WHERE atv IN ('ATV-0774', 'ATV-0775', 'ATV-0776');
UPDATE atendimento.material_de_campo
   SET data_dita = (recebido_em AT TIME ZONE 'America/Sao_Paulo')::date, data_presumida = true
 WHERE sem_dia AND data_dita IS NULL AND safra_dita IS NULL;
UPDATE atendimento.material_de_campo SET classe_fase = NULL WHERE classe_fase = 'palhada';

ALTER TABLE atendimento.material_de_campo DROP COLUMN sem_dia;

DELETE FROM casa.mudancas WHERE nome = '056_foto_sem_dia_e_palhada.sql';

COMMIT;
