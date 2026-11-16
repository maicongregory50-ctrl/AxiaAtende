-- #1525 -- a VOLTA da 067. RECUSA se ja ha candidatura em ficha (molde da 062): a ficha e dado de
-- candidato que a Fran ja recebeu, e apagar candidatura e decisao do dono, nao de rollback.
-- Os beneficios das vagas NAO voltam a dizer "salario atrativo": a OlivIA continua lendo o cadastro
-- mesmo sem a 067, e o filtro recusaria a frase.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DO $$
DECLARE
    n BIGINT;
BEGIN
    SELECT count(*) INTO n FROM atendimento.candidaturas WHERE tipo_arquivo = 'ficha';
    IF n > 0 THEN
        RAISE EXCEPTION '067 VOLTA: ha % ficha(s) gravada(s); nao se apaga candidatura por rollback.', n;
    END IF;
END $$;

DELETE FROM casa.mudancas WHERE nome = '067_olivia_conduz_vaga.sql';
DELETE FROM atendimento.avisos WHERE tipo = 'vaga_visita';
DELETE FROM atendimento.modelos WHERE uso = 'aviso_vaga_visita';
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada', 'painel_classe1', 'olivia_resumo'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1', 'aviso_olivia_resumo'));
DELETE FROM atendimento.respostas_da_vaga
 WHERE chave IN ('ficha_aviso', 'ficha_aviso_es', 'toque_ficha_falta', 'toque_ficha_falta_es', 'toque_convite',
                 'toque_convite_es', 'toque_curriculo', 'toque_curriculo_es', 'ficha_falta', 'ficha_falta_es');
DELETE FROM atendimento.ajustes WHERE chave IN ('olivia.conduz_vaga', 'olivia.vaga_toque_h', 'olivia.ficha_parcial_h');
ALTER TABLE atendimento.candidaturas DROP CONSTRAINT candidaturas_tipo_arquivo;
ALTER TABLE atendimento.candidaturas ADD CONSTRAINT candidaturas_tipo_arquivo
    CHECK (tipo_arquivo IN ('pdf', 'imagem'));
ALTER TABLE atendimento.candidaturas DROP COLUMN quer_visita, DROP COLUMN ficha;
ALTER TABLE atendimento.conversas DROP COLUMN vaga_lembrada_em, DROP COLUMN lingua, DROP COLUMN ficha;
ALTER TABLE atendimento.vagas DROP COLUMN modo;
