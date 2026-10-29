-- VOLTA da 039 (#1188). Nunca e aplicada junto com a ida.
--
-- ANTES DELA: a chave AXIAATENDE_PORTEIRO desligada no XML e o codigo revertido (senao o porteiro
-- grava colunas que nao existem).
--
-- O QUE ACONTECE COM OS AVISOS: nenhum e apagado. Os guardados e os nao vistos perdem o estado e
-- voltam a pendente (`enviado_em` nulo, `erro` vazio): o codigo antigo os manda na proxima volta, um
-- modelo por aviso. Quem nao quiser isso marca o `erro` deles antes de aplicar esta volta.
-- O modelo sai do cadastro; na Meta ele continua existindo, sem uso.
BEGIN;

DELETE FROM atendimento.modelos WHERE uso = 'reabertura';

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_variaveis;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_variaveis CHECK (variaveis <@ ARRAY[
    'primeiro_nome', 'nome', 'assunto', 'peca', 'n_imagens', 'responsavel',
    'aviso1', 'aviso2', 'aviso3',
    'vaga', 'candidato', 'declarou', 'req1', 'req2', 'req3', 'req4', 'resumo']::text[]);
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao = 'falar_responsavel')
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_categoria_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_categoria_do_uso CHECK (
    (uso IN ('convite', 'direta') AND categoria = 'MARKETING')
    OR ((uso LIKE 'aviso%' OR uso = 'curriculo') AND categoria IN ('UTILITY', 'MARKETING')));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo'));   -- a lista da 033, inteira

DROP INDEX atendimento.avisos_guardados;
ALTER TABLE atendimento.avisos
    DROP COLUMN reabertura_id,
    DROP COLUMN como,
    DROP COLUMN nao_visto_em,
    DROP COLUMN guardado_em;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'atendimento' AND table_name = 'avisos'
                  AND column_name IN ('guardado_em', 'nao_visto_em', 'como', 'reabertura_id')) THEN
        RAISE EXCEPTION 'VOLTA da 039: as quatro colunas deviam ter saido.';
    END IF;
    RAISE NOTICE 'VOLTA da 039 OK: as colunas fora, o modelo de reabertura fora.';
END $$;

DELETE FROM casa.mudancas WHERE nome = '039_porteiro_dos_avisos.sql';
COMMIT;
