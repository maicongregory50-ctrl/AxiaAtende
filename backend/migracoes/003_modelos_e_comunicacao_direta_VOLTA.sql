-- #950 -- desfaz a 003. So para a mao de quem desfaz, e so antes de existir envio direto.
BEGIN;
UPDATE atendimento.envio_destinatarios SET situacao = 'falhou' WHERE situacao = 'sem_aceite';
ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_situacao;
ALTER TABLE atendimento.envio_destinatarios ADD CONSTRAINT envio_dest_situacao
    CHECK (situacao IN ('aguardando', 'sem_responsavel', 'sem_whatsapp', 'recusou_antes',
                        'ja_recebeu', 'convidado', 'falhou', 'nao_e_whatsapp'));
ALTER TABLE atendimento.envio_destinatarios DROP COLUMN aceite_cadastro, DROP COLUMN imagens, DROP COLUMN capa;
ALTER TABLE atendimento.envios DROP COLUMN assunto, DROP COLUMN tipo;
DROP TABLE atendimento.modelos;
DELETE FROM casa.mudancas WHERE nome = '003_modelos_e_comunicacao_direta.sql';
COMMIT;
