-- Desfaz a 015 (#970). Nada de atendimento e apagado.
BEGIN;
ALTER TABLE atendimento.material_de_campo DROP COLUMN grupo_id;
DELETE FROM casa.mudancas WHERE nome = '015_grupo_da_conversa.sql';
COMMIT;
