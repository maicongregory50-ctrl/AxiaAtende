-- VOLTA da 041 (#1193). Nunca e aplicada junto com a ida.
--
-- ANTES DELA: o codigo da busca das retomadas revertido e as telas reiniciadas (senao a busca grava
-- colunas que nao existem).
--
-- RECUSA se ja houver aceite de retomada gravado: e consentimento, e consentimento nao se apaga (regra 4).
-- Tirar as colunas apagaria a origem e quem registrou. Com retomada gravada, a volta fica so no codigo.
BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM atendimento.consentimentos WHERE origem = 'retomada') THEN
        RAISE EXCEPTION 'VOLTA da 041: ha aceite de retomada gravado; consentimento nao se apaga (regra 4).';
    END IF;
END $$;

DROP INDEX atendimento.consentimentos_retomada_ref;
ALTER TABLE atendimento.consentimentos
    DROP CONSTRAINT consentimentos_retomada,
    DROP COLUMN registrado_por,
    DROP COLUMN retomada_ref,
    DROP COLUMN origem;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'atendimento' AND table_name = 'consentimentos'
                  AND column_name IN ('origem', 'retomada_ref', 'registrado_por')) THEN
        RAISE EXCEPTION 'VOLTA da 041: as tres colunas deviam ter saido.';
    END IF;
    RAISE NOTICE 'VOLTA da 041 OK: as colunas da retomada fora.';
END $$;

DELETE FROM casa.mudancas WHERE nome = '041_consentimento_retomada.sql';
COMMIT;
