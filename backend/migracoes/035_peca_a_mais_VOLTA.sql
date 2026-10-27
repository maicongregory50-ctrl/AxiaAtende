-- VOLTA da 035 (#1175). Nunca e aplicada junto com a ida.
--
-- O CODIGO JA DEVE TER SIDO REVERTIDO antes dela: senao `receber_pedido` grava numa coluna que nao
-- existe mais.
--
-- O QUE SE PERDE: a marca dos envios que o dono mandou alem do teto. A VOLTA CONTA e diz quantos
-- antes de apagar, para o registro; nao recusa, porque nenhuma linha fica invalida sem a coluna.
BEGIN;

DO $$
DECLARE
    marcados BIGINT;
BEGIN
    SELECT count(*) INTO marcados FROM atendimento.envios WHERE passa_do_teto;
    RAISE NOTICE 'VOLTA da 035: % envio(s) tinham a marca da peca a mais', marcados;
END $$;

ALTER TABLE atendimento.envios DROP COLUMN passa_do_teto;

DELETE FROM casa.mudancas WHERE nome = '035_peca_a_mais.sql';
COMMIT;
