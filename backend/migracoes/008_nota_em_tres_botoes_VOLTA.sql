-- Desfaz a 008 (nota em tres botoes, #969). Nenhuma nota e apagada: 3, 2 e 1 cabem na escala antiga.
-- Os avisos de nota ruim saem da fila (ja foram mandados ou ficaram com erro) e o modelo sai do
-- cadastro; na Meta ele continua existindo, sem uso. O motor antigo volta a mandar a lista de cinco.
BEGIN;
DELETE FROM atendimento.avisos WHERE tipo = 'avaliacao_ruim';
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo CHECK (tipo IN ('recusa', 'sem_atendimento'));
DELETE FROM atendimento.modelos WHERE uso = 'aviso_avaliacao_ruim';
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento'));
DELETE FROM casa.mudancas WHERE nome = '008_nota_em_tres_botoes.sql';
COMMIT;
