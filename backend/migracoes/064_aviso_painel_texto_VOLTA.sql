-- #1434 -- a VOLTA da 064: o texto do aviso_painel volta ao da 063.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM casa.mudancas WHERE nome = '064_aviso_painel_texto.sql';
UPDATE atendimento.modelos SET texto = 'Aviso do painel da casa: {{1}}' WHERE nome = 'aviso_painel';
