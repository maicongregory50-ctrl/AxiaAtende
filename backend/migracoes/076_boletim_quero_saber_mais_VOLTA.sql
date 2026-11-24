-- #1754 -- a VOLTA da 076: sai o cadastro do modelo e os CHECK voltam a lista da 071. Nunca e aplicada junto
-- com a ida. ANTES: a VOLTA da 077 (se aplicada), o codigo revertido e os dois processos reiniciados. RECUSA
-- enquanto houver envio ATIVO com o modelo. Na Meta o modelo continua, sem uso (apaga-lo la e ato do dono).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM atendimento.envios WHERE modelo = 'boletim_quero_saber_mais'
                AND situacao IN ('ativo', 'parado_nota')) THEN
        RAISE EXCEPTION 'VOLTA da 076: ha envio ativo com o boletim_quero_saber_mais; suspenda-o antes.';
    END IF;
END $$;

DELETE FROM atendimento.modelos WHERE nome = 'boletim_quero_saber_mais';

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao IN ('falar_responsavel', 'parar_e_falar', 'parar_e_chamar'))
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver')
    OR (uso = 'termo_reprovacao' AND botao = 'ciente'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver', 'parar_e_falar',
                     'parar_e_chamar', 'ciente'));
DELETE FROM casa.mudancas WHERE nome = '076_boletim_quero_saber_mais.sql';
