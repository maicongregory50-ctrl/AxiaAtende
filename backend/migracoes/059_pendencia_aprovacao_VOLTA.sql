-- Desfaz a 059 (#1276): as pendencias de aprovacao e as mensagens delas saem, o tipo volta a ser so
-- `chamado`, e a chave sai.
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). O CODIGO JA DEVE TER
-- SIDO REVERTIDO antes dele -- senao a volta das telas procura a chave e grava o tipo que nao existe.
BEGIN;

DELETE FROM atendimento.pendencias_mensagens
 WHERE pendencia_id IN (SELECT id FROM atendimento.pendencias WHERE tipo = 'aprovacao');
DELETE FROM atendimento.pendencias WHERE tipo = 'aprovacao';
ALTER TABLE atendimento.pendencias DROP CONSTRAINT pendencias_tipo;
ALTER TABLE atendimento.pendencias ADD CONSTRAINT pendencias_tipo CHECK (tipo IN ('chamado'));
DELETE FROM atendimento.ajustes WHERE chave = 'pendencias.aprovacao.ligado';

DELETE FROM casa.mudancas WHERE nome = '059_pendencia_aprovacao.sql';

COMMIT;
