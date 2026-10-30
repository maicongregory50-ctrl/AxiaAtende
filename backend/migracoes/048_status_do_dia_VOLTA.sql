-- #1207 -- a VOLTA da 048: os avisos do status do dia saem (o CHECK antigo nao os aceita), e a tabela
-- volta a ser a da 039. Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM atendimento.ajustes WHERE chave = 'status_do_dia_para';
DELETE FROM atendimento.avisos WHERE tipo = 'status_do_dia';
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_status_com_imagens;
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante'));
ALTER TABLE atendimento.avisos DROP COLUMN imagens, DROP COLUMN legenda;
