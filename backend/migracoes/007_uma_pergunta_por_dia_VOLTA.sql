-- Desfaz a 007 (uma pergunta por dia, #969). Nenhum atendimento e apagado: so a coluna que liga a
-- conversa a pergunta do dia. O motor antigo volta a perguntar uma vez por conversa.
BEGIN;
ALTER TABLE atendimento.conversas DROP COLUMN pergunta_da;
DELETE FROM atendimento.ajustes WHERE chave = 'pergunta_janela';
DELETE FROM casa.mudancas WHERE nome = '007_uma_pergunta_por_dia.sql';
COMMIT;
