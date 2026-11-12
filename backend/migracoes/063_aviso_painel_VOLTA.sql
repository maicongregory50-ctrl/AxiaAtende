-- #1434 -- a VOLTA da 063: os avisos do painel saem (o CHECK antigo nao os aceita), o modelo, o ajuste e
-- as correlacoes do canal do painel tambem.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM casa.mudancas WHERE nome = '063_aviso_painel.sql';
DELETE FROM atendimento.avisos_auditoria_erp WHERE canal = 'painel_classe1';
DELETE FROM atendimento.ajustes WHERE chave = 'painel_para';
DELETE FROM atendimento.avisos WHERE tipo = 'painel_classe1';
DELETE FROM atendimento.modelos WHERE uso = 'aviso_painel_classe1';
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada'));
