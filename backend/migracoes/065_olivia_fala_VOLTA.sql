-- #1520 -- a VOLTA da 065. A imagem ja recebida fica como candidatura (a Fran ja a viu); so a coluna
-- que diz "foto" sai. Os avisos do resumo saem (o CHECK antigo nao os aceita), e o modelo e o preco tambem.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM casa.mudancas WHERE nome = '065_olivia_fala.sql';
UPDATE atendimento.respostas_da_vaga
   SET texto = 'Precisamos do seu currículo em PDF. Mande o arquivo PDF aqui mesmo.' WHERE chave = 'so_pdf';
DELETE FROM atendimento.avisos WHERE tipo = 'olivia_resumo';
DELETE FROM atendimento.modelos WHERE uso = 'aviso_olivia_resumo';
DELETE FROM atendimento.precos WHERE servico = 'claude' AND item = 'claude-sonnet-5-5' AND criado_por IS NULL;
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada', 'painel_classe1'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1'));
ALTER TABLE atendimento.candidaturas DROP COLUMN tipo_arquivo;
ALTER TABLE atendimento.conversas DROP COLUMN saida, DROP COLUMN conduzida_por;
