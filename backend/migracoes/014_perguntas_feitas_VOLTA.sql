-- Desfaz a 014 (#970, decisao 15). Nada de atendimento e apagado.
BEGIN;
ALTER TABLE atendimento.material_de_campo DROP COLUMN perguntas_feitas;
DELETE FROM casa.mudancas WHERE nome = '014_perguntas_feitas.sql';
COMMIT;
