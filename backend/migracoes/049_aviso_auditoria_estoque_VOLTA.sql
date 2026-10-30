-- #350 -- a VOLTA da 049: os avisos da auditoria saem (o CHECK antigo nao os aceita), o modelo, o
-- ajuste e o vinculo com o ERP tambem. Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DROP TABLE atendimento.avisos_auditoria_erp;
DELETE FROM casa.mudancas WHERE nome = '049_aviso_auditoria_estoque.sql';
DELETE FROM atendimento.ajustes WHERE chave = 'auditoria_estoque_para';
DELETE FROM atendimento.avisos WHERE tipo = 'auditoria_estoque';
DELETE FROM atendimento.modelos WHERE uso = 'aviso_auditoria_estoque';
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura'));
