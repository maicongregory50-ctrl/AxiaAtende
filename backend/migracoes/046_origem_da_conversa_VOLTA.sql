-- VOLTA da 046 (#1204). Nunca e aplicada junto com a ida. Antes dela, volte o codigo (o motor grava a
-- coluna ao abrir conversa). Perde-se so a marca de quem abriu: a conversa continua.
BEGIN;

ALTER TABLE atendimento.conversas DROP COLUMN origem;
DELETE FROM casa.mudancas WHERE nome = '046_origem_da_conversa.sql';

DO $$ BEGIN RAISE NOTICE '046 VOLTA OK: a conversa sem origem'; END $$;

COMMIT;
