-- VOLTA da 044 (#1203). Nunca e aplicada junto com a ida.
--
-- ANTES DELA: o codigo revertido (envio._mensagem, envio.tratar_toque e modelos_meta.componentes) e
-- os dois processos reiniciados. O historico fica (envios, destinatarios, as recusas e os toques de
-- falar); a volta recusa enquanto houver envio ATIVO com o modelo. Na Meta ele continua, sem uso.
BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM atendimento.envios WHERE modelo = 'informativo_renascer'
                AND situacao IN ('ativo', 'parado_nota')) THEN
        RAISE EXCEPTION 'VOLTA da 044: ha envio ativo com o informativo_renascer; suspenda-o antes.';
    END IF;
END $$;

DELETE FROM atendimento.modelos WHERE nome = 'informativo_renascer';

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao IN ('falar_responsavel', 'parar_e_falar'))
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver', 'parar_e_falar'));

DELETE FROM casa.mudancas WHERE nome = '044_informativo_sem_link.sql';

DO $$ BEGIN RAISE NOTICE '044 VOLTA OK: o informativo_renascer fora do cadastro'; END $$;

COMMIT;
