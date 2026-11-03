-- Desfaz a 053 (#1238): tira o nome dito do cliente. A logo, o arquivo e o codigo ficam.
--
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). O CODIGO JA DEVE TER
-- SIDO REVERTIDO antes dele -- senao logos.responder e logos.a_puxar procuram uma coluna que nao existe.
BEGIN;

ALTER TABLE atendimento.logos_de_cliente DROP COLUMN cliente_dito;

DELETE FROM casa.mudancas WHERE nome = '053_logo_pelo_nome.sql';

COMMIT;
