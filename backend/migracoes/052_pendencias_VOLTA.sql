-- #1222 -- a VOLTA da 052: o molde de pendencia sai, com as chaves. Os avisos de hoje ficam intocados, e
-- os comentarios que ja entraram no ERP pelo WhatsApp ficam no chamado (sao do autor). Sem BEGIN nem
-- COMMIT: a transacao e de backend/migracoes.py.

DROP TABLE atendimento.pendencias_mensagens;
DROP TABLE atendimento.pendencias;
DELETE FROM atendimento.ajustes WHERE chave IN ('pendencias.ligado', 'pendencias.juntar_minutos', 'pendencias.cursor');
DELETE FROM casa.mudancas WHERE nome = '052_pendencias.sql';
