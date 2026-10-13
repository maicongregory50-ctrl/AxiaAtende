-- Desfaz a 017 (#982). Nada de atendimento e apagado.
BEGIN;
ALTER TABLE atendimento.material_de_campo DROP COLUMN safra_dita;
DELETE FROM casa.mudancas WHERE nome = '017_safra_dita.sql';
COMMIT;
