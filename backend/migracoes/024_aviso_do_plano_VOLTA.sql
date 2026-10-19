-- Desfaz a 024 (o aviso do plano sem registro, #926). Nenhum atendimento e tocado: saem os avisos
-- do plano (enviados ou nao) e o modelo do cadastro (na Meta ele continua existindo, sem uso).
BEGIN;
DELETE FROM atendimento.avisos WHERE tipo = 'plano_sem_registro';
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou'));
DELETE FROM atendimento.modelos WHERE uso = 'aviso_plano_sem_registro';
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou'));
DELETE FROM casa.mudancas WHERE nome = '024_aviso_do_plano.sql';
COMMIT;
