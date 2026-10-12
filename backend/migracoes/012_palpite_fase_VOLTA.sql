-- Desfaz a 012 (#970).
BEGIN;
ALTER TABLE atendimento.material_de_campo DROP COLUMN palpite_fase;
DELETE FROM casa.mudancas WHERE nome = '012_palpite_fase.sql';
COMMIT;
