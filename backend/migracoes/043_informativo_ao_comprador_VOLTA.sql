-- VOLTA da 043 (informativo ao comprador). Nunca e aplicada junto com a ida.
--
-- ANTES DELA: o codigo revertido (envio._mensagem e modelos_meta.componentes) e os dois processos
-- reiniciados. Envio que ja usou o modelo fica como esta: o historico (envios, destinatarios, a recusa
-- de quem tocou "Nao quero mais receber") nao e apagado; a volta recusa enquanto houver envio ATIVO
-- com ele. O modelo sai do cadastro; na Meta ele continua existindo, sem uso.
BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM atendimento.envios WHERE modelo = 'informativo_ao_comprador'
                AND situacao IN ('ativo', 'parado_nota')) THEN
        RAISE EXCEPTION 'VOLTA da 043: ha envio ativo com o informativo_ao_comprador; suspenda-o antes.';
    END IF;
END $$;

DELETE FROM atendimento.modelos WHERE nome = 'informativo_ao_comprador';

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao = 'falar_responsavel')
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver'));

DELETE FROM casa.mudancas WHERE nome = '043_informativo_ao_comprador.sql';

DO $$ BEGIN RAISE NOTICE '043 VOLTA OK: o informativo_ao_comprador fora do cadastro'; END $$;

COMMIT;
