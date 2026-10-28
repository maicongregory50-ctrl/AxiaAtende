-- VOLTA da 036 (#1182). Nunca e aplicada junto com a ida.
--
-- O CODIGO DO MARKETING JA DEVE TER SIDO REVERTIDO antes dela: senao a tela continua oferecendo o
-- modelo e o pedido e recusado aqui.
--
-- O QUE IMPEDE A VOLTA: envio ja feito com o modelo. Tirar o modelo de um envio em curso deixaria o
-- lote sem texto; ela CONTA e RECUSA dizendo quantos, sem mudar envio de ninguem sozinha.
BEGIN;

DO $$
DECLARE
    com_ele BIGINT;
BEGIN
    SELECT count(*) INTO com_ele FROM atendimento.envios WHERE modelo = 'abertura_do_canal';
    IF com_ele > 0 THEN
        RAISE EXCEPTION 'VOLTA da 036: ha % envio(s) com o modelo abertura_do_canal; decida cada um antes',
                        com_ele;
    END IF;
END $$;

DELETE FROM atendimento.modelos WHERE nome = 'abertura_do_canal';

DELETE FROM casa.mudancas WHERE nome = '036_modelo_abertura_do_canal.sql';
COMMIT;
