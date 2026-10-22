-- Desfaz a 026 (#1097). As conversas voltam a "parou no meio" com a retomada ja marcada, para a IA
-- nao rodar nelas agora; o CHECK volta ao da 025.
BEGIN;
UPDATE atendimento.conversas
   SET situacao = 'parou_no_meio', retomada_em = coalesce(retomada_em, now()),
       retomada_chave = coalesce(retomada_chave, 'volta da 026')
 WHERE situacao IN ('imagem_recebida', 'logo_recebida');
ALTER TABLE atendimento.conversas DROP CONSTRAINT conversas_situacao;
ALTER TABLE atendimento.conversas ADD CONSTRAINT conversas_situacao
    CHECK (situacao IN ('em_curso', 'com_link', 'parou_no_meio', 'encerrada', 'envio',
                        'curriculo_recebido', 'sem_curriculo'));
DELETE FROM casa.mudancas WHERE nome = '026_imagem_e_logo_recebida.sql';
COMMIT;
