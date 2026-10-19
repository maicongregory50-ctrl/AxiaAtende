-- Desfaz a 023 (#1037): tira as tres colunas da devolucao do marketing.
--
-- A LOGO NAO E TOCADA: a linha, o arquivo e o `puxada_em` ficam. O que se perde e so o que o
-- marketing disse que fez com ela (`resultado`) e se quem mandou foi avisado (`aviso`, `aviso_em`).
--
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). Por isso abre a
-- propria transacao e apaga a linha de casa.mudancas. O CODIGO JA DEVE TER SIDO REVERTIDO antes
-- dele -- senao `logos.mandar_avisos` e a rota "puxada" procuram colunas que nao existem.
BEGIN;

ALTER TABLE atendimento.logos_de_cliente
    DROP COLUMN aviso_em,
    DROP COLUMN aviso,
    DROP COLUMN resultado;

DELETE FROM casa.mudancas WHERE nome = '023_logos_puxadas.sql';

COMMIT;
