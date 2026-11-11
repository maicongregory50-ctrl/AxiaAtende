-- #1381 -- a VOLTA da 061: a coluna do anexo e a chave saem. Os arquivos ja baixados em
-- envios_pasta\chamados ficam no disco (a original esta no ERP).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM casa.mudancas WHERE nome = '061_anexo_na_pendencia.sql';
DELETE FROM atendimento.ajustes WHERE chave = 'pendencias.anexo_ligado';
ALTER TABLE atendimento.pendencias_mensagens DROP COLUMN anexo;
