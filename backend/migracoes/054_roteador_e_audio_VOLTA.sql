-- Desfaz a 054 (#1238): o roteador e o audio saem, com as chaves e a carencia. As respostas que ja
-- entraram nos chamados ficam (sao do autor); o texto ja transcrito que entrou na corrente fica em
-- eventos_meta.
--
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). O CODIGO JA DEVE TER
-- SIDO REVERTIDO antes dele -- senao o motor e as telas procuram tabela e coluna que nao existem.
BEGIN;

DROP TABLE atendimento.roteador;
DROP TABLE atendimento.audios;
ALTER TABLE atendimento.pendencias_mensagens DROP COLUMN entregar_apos;

DELETE FROM atendimento.uso_ia WHERE servico = 'local';
DELETE FROM atendimento.precos WHERE servico = 'local';
ALTER TABLE atendimento.uso_ia DROP CONSTRAINT uso_ia_servico;
ALTER TABLE atendimento.uso_ia ADD CONSTRAINT uso_ia_servico CHECK (servico IN ('claude', 'gemini'));
ALTER TABLE atendimento.precos DROP CONSTRAINT precos_servico;
ALTER TABLE atendimento.precos ADD CONSTRAINT precos_servico CHECK (servico IN ('meta', 'claude', 'gemini'));

DELETE FROM atendimento.ajustes
 WHERE chave IN ('roteador.ligado', 'roteador.carencia_minutos', 'audio.transcrever', 'audio.maximo_s');

DELETE FROM casa.mudancas WHERE nome = '054_roteador_e_audio.sql';

COMMIT;
