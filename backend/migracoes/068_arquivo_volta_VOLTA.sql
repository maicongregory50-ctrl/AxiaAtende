-- #1528 -- a VOLTA da 068. Desfazer o CODIGO e desligar a chave (pendencias.arquivo_volta = false), que e
-- o passo 1 do ROLLBACK_PLAN da spec; esta volta e o passo 3. O arquivo que ja entrou no chamado fica no
-- ERP: aqui saem so as linhas do transito e da rajada, que o CHECK antigo nao aceita.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM casa.mudancas WHERE nome = '068_arquivo_volta.sql';
UPDATE atendimento.pendencias_mensagens SET rajada_id = NULL WHERE rajada_id IS NOT NULL;
DELETE FROM atendimento.pendencias_mensagens WHERE classe = 'arquivo' OR estado IN ('rajada', 'confirmar');
DELETE FROM atendimento.avisos WHERE tipo IN ('arquivo_sem_antivirus', 'arquivo_ameaca');
DELETE FROM atendimento.modelos WHERE uso IN ('aviso_arquivo_sem_antivirus', 'aviso_arquivo_ameaca');
DELETE FROM atendimento.ajustes WHERE chave IN ('pendencias.arquivo_volta', 'pendencias.rajada_minutos',
                                                 'pendencias.rajada_teto', 'pendencias.arquivo_dia_teto');
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada', 'painel_classe1', 'olivia_resumo', 'vaga_visita'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1', 'aviso_olivia_resumo',
                   'aviso_vaga_visita'));
DROP INDEX atendimento.pend_msg_rajada;
DROP INDEX atendimento.pend_msg_estado;
CREATE INDEX pend_msg_estado ON atendimento.pendencias_mensagens (estado)
    WHERE estado IN ('esperando', 'guardada', 'escolher', 'a_entregar');
ALTER TABLE atendimento.pendencias_mensagens DROP COLUMN rajada_id, DROP COLUMN arquivo;
ALTER TABLE atendimento.pendencias_mensagens DROP CONSTRAINT pend_msg_estado;
ALTER TABLE atendimento.pendencias_mensagens ADD CONSTRAINT pend_msg_estado
    CHECK (estado IN ('esperando', 'guardada', 'enviada', 'escolher', 'a_entregar', 'entregue', 'descartada', 'erro'));
ALTER TABLE atendimento.pendencias_mensagens DROP CONSTRAINT pend_msg_classe;
ALTER TABLE atendimento.pendencias_mensagens ADD CONSTRAINT pend_msg_classe
    CHECK (classe IN ('informativo', 'pergunta', 'entrega', 'resposta', 'validacao'));

DO $$ BEGIN RAISE NOTICE '068 VOLTA OK: a volta com arquivo saiu'; END $$;
