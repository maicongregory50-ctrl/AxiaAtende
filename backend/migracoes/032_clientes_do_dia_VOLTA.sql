-- Desfaz a 032 (#1090 etapa 3). Os contatos que ja foram ao ERP ficam la (sao contatos de pessoa).
BEGIN;

DELETE FROM atendimento.menu WHERE chave = 'interna.clientes';
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_acao;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_acao
    CHECK (acao IN ('menu', 'destino', 'encerrar', 'texto', 'menu_cliente', 'vaga'));
DELETE FROM atendimento.ajustes WHERE chave = 'clientes.ligado';

DROP TABLE IF EXISTS atendimento.clientes_registros;
DROP TABLE IF EXISTS atendimento.clientes_motivos;
DROP TABLE IF EXISTS atendimento.clientes_fila;
DROP TABLE IF EXISTS atendimento.clientes_consultores;

DELETE FROM casa.mudancas WHERE nome = '032_clientes_do_dia.sql';

COMMIT;
