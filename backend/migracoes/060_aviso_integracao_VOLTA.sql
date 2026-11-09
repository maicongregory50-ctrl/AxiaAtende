-- #1337 -- a VOLTA da 060: os avisos de integracao saem (o CHECK antigo nao os aceita), o modelo, o
-- ajuste e as correlacoes do canal novo tambem; a PK da correlacao volta a ser so o id do ERP.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM casa.mudancas WHERE nome = '060_aviso_integracao.sql';
DELETE FROM atendimento.avisos_auditoria_erp WHERE canal <> 'auditoria_estoque';
ALTER TABLE atendimento.avisos_auditoria_erp DROP CONSTRAINT avisos_auditoria_erp_pkey;
ALTER TABLE atendimento.avisos_auditoria_erp DROP COLUMN canal;
ALTER TABLE atendimento.avisos_auditoria_erp ADD CONSTRAINT avisos_auditoria_erp_pkey PRIMARY KEY (erp_aviso_id);
DELETE FROM atendimento.ajustes WHERE chave = 'integracoes_para';
DELETE FROM atendimento.avisos WHERE tipo = 'integracao_recusada';
DELETE FROM atendimento.modelos WHERE uso = 'aviso_integracao_recusada';
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque'));
