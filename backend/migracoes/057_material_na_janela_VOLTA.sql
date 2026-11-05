-- Desfaz a 057 (#1267). Os destinatarios que receberam sem convite ficam como `convidado`, com as
-- imagens ja mandadas; so a marca sai.
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). O CODIGO JA DEVE TER
-- SIDO REVERTIDO antes dele -- senao envio.mandar_lotes grava numa coluna que nao existe.
BEGIN;
ALTER TABLE atendimento.envio_destinatarios DROP COLUMN sem_convite;
DELETE FROM casa.mudancas WHERE nome = '057_material_na_janela.sql';
COMMIT;
