-- Desfaz a 009 (o vigia do endereco publico, #969). Nenhum atendimento e tocado: saem a linha do
-- vigia, os avisos dele que estavam na fila e os dois modelos do cadastro (na Meta eles continuam
-- existindo, sem uso). O recepcionista antigo volta a nao conferir o endereco.
BEGIN;
DROP TABLE atendimento.vigia_endereco;
DELETE FROM atendimento.avisos WHERE tipo IN ('endereco_fora', 'endereco_voltou');
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim'));
DELETE FROM atendimento.modelos WHERE uso IN ('aviso_endereco_fora', 'aviso_endereco_voltou');
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim'));
DELETE FROM casa.mudancas WHERE nome = '009_vigia_do_endereco.sql';
COMMIT;
