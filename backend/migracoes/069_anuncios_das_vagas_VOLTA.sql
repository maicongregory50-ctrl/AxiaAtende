-- #1525 -- a VOLTA da 069: as duas vagas voltam a ficar sem anuncio ligado (quem clica no anuncio volta a
-- ser recebido pela pergunta geral). Nao apaga conversa nem candidatura.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.vagas SET anuncio_ids = '{}'
 WHERE titulo IN ('Vaga Operador de empilhadeira', 'Vaga Auxiliar de produção')
   AND anuncio_ids <@ ARRAY['120250019686590192', '120250019668190192'];
DELETE FROM casa.mudancas WHERE nome = '069_anuncios_das_vagas.sql';
