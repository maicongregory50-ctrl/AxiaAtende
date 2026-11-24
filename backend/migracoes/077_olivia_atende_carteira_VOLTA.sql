-- #1754 -- a VOLTA da 077: saem a tabela de interesses, a coluna das culturas e a chave; o CHECK da resposta
-- volta a lista da 005. ANTES: a chave desligada (scripts/olivia.py desligar-carteira), o codigo revertido e
-- os dois processos reiniciados. PERDE os interesses gravados (as fichas ja mandadas ficam no WhatsApp de quem
-- recebeu, e o que foi ao Relacionamento do ERP fica la). A resposta `saber` vira `falar` (o toque), que e
-- como ela ja saia para o ERP enquanto a conversa corria.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.envio_destinatarios SET resposta = 'falar' WHERE resposta = 'saber';
ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_resposta;
ALTER TABLE atendimento.envio_destinatarios ADD CONSTRAINT envio_dest_resposta
    CHECK (resposta IN ('quero', 'nao_quero', 'texto', 'falar'));
DROP TABLE atendimento.interesses;
ALTER TABLE atendimento.envios DROP COLUMN culturas;
DELETE FROM atendimento.ajustes WHERE chave = 'olivia.atende_carteira';
DELETE FROM casa.mudancas WHERE nome = '077_olivia_atende_carteira.sql';
