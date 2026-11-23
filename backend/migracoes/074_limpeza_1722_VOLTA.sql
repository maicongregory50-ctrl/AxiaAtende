-- #1722 -- a VOLTA da 074 (ROLLBACK_PLAN 2 e 4 da spec). Sem BEGIN nem COMMIT: a transacao e de
-- backend/migracoes.py.
--   - a logo do PDF de 23/11 volta a esperar o cliente, sem `puxada_em` e sem `erro`. O caminho do
--     arquivo NAO volta: o arquivo foi apagado do disco, e nao deve voltar.
--   - a mensagem 136, SE ainda `a_entregar`, volta a `descartada`. Ja entregue, fica: o comentario no
--     chamado 1541 e historico e esta correto.
--   - sai o ajuste do aviso diario da chave desligada (gravado pelo codigo do #1722).

UPDATE atendimento.logos_de_cliente
   SET pergunta_pendente = 'erp_codigo', puxada_em = NULL, erro = ''
 WHERE wamid = 'wamid.HBgMNTU0OTkxOTM4OTEwFQIAEhgWM0VCMDcxODJBMjI4MENEMTY0MjMxMwA='
   AND erro = 'nao era logo: PDF devolvido ao chamado 1541 (#1722)';

UPDATE atendimento.pendencias_mensagens
   SET estado = 'descartada'
 WHERE id = 136 AND estado = 'a_entregar' AND texto LIKE 'No caso da rescis%';

DELETE FROM atendimento.ajustes WHERE chave = 'pendencias.arquivo_desligada_aviso_em';
DELETE FROM casa.mudancas WHERE nome = '074_limpeza_1722.sql';
