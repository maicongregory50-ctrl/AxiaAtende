-- #1223 -- a VOLTA da 051: tira so as sementes da Meta e do Gemini (criado_por nulo). O que o dono lancou
-- na tela fica, e o Haiku da 050 tambem. Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM atendimento.precos WHERE criado_por IS NULL AND servico IN ('meta', 'gemini');
DELETE FROM casa.mudancas WHERE nome = '051_precos_oficiais.sql';
