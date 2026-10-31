-- #1223 -- a VOLTA da 050: o painel de custos sai inteiro. Perde o uso de IA registrado e os precos
-- lancados desde a subida (por isso e o ultimo passo do rollback). Sem BEGIN nem COMMIT: a transacao
-- e de backend/migracoes.py.

DROP TABLE atendimento.meta_conferencia;
DROP TABLE atendimento.meta_cobrado;
DROP TABLE atendimento.precos;
DROP TABLE atendimento.uso_ia;
DELETE FROM atendimento.ajustes WHERE chave = 'custos.conferir_meta';
DELETE FROM casa.mudancas WHERE nome = '050_custos.sql';
