-- VOLTA da 047 (#1205). Nunca e aplicada junto com a ida. Antes dela, volte o codigo (a SaidaMeta
-- grava na tabela) ou ponha o ajuste enviadas.guardar_texto em false. Perde-se o texto guardado; os
-- envios e as conversas nao sao tocados (o resumo de `enviadas` continua).
BEGIN;

DROP TABLE atendimento.enviadas_texto;
DELETE FROM atendimento.ajustes WHERE chave = 'enviadas.guardar_texto';
DELETE FROM casa.mudancas WHERE nome = '047_texto_do_envio.sql';

DO $$ BEGIN RAISE NOTICE '047 VOLTA OK: sem o texto do envio'; END $$;

COMMIT;
