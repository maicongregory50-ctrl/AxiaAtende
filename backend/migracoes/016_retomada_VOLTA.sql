-- Desfaz a 016 (#989). As conversas retomadas ficam como estao; nada de atendimento e apagado.
BEGIN;
ALTER TABLE atendimento.conversas DROP COLUMN retomada_em, DROP COLUMN retomada_chave;
DELETE FROM atendimento.ajustes WHERE chave = 'retomada';
DELETE FROM casa.mudancas WHERE nome = '016_retomada.sql';
COMMIT;
