-- VOLTA da 045 (#1203). Nunca e aplicada junto com a ida. Nao ha codigo a reverter (os botoes sao os
-- da 044). O historico fica; a volta recusa enquanto houver envio ATIVO com o modelo. Na Meta ele
-- continua, sem uso.
BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM atendimento.envios WHERE modelo = 'informativo_curto'
                AND situacao IN ('ativo', 'parado_nota')) THEN
        RAISE EXCEPTION 'VOLTA da 045: ha envio ativo com o informativo_curto; suspenda-o antes.';
    END IF;
END $$;

DELETE FROM atendimento.modelos WHERE nome = 'informativo_curto';
DELETE FROM casa.mudancas WHERE nome = '045_informativo_so_ola.sql';

DO $$ BEGIN RAISE NOTICE '045 VOLTA OK: o informativo_curto fora do cadastro'; END $$;

COMMIT;
