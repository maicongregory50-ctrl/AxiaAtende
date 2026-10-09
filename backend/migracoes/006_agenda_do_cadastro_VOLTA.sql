-- Desfaz a 006 (o reconhecimento do cadastro, #969). Nenhum atendimento e apagado: so as colunas
-- do retrato do cadastro e a agenda.
BEGIN;
ALTER TABLE atendimento.conversas
    DROP COLUMN erp_nome, DROP COLUMN erp_papeis, DROP COLUMN erp_contato_setor,
    DROP COLUMN erp_contato_nome, DROP COLUMN erp_cadastros;
DROP TABLE atendimento.agenda_leitura;
DROP TABLE atendimento.agenda;
DELETE FROM casa.mudancas WHERE nome = '006_agenda_do_cadastro.sql';
COMMIT;
