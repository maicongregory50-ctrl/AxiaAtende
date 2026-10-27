-- VOLTA da 034 (#1163). Nunca e aplicada junto com a ida.
--
-- O CODIGO JA DEVE TER SIDO REVERTIDO antes dela: senao o laco do lote grava uma situacao que o
-- CHECK antigo recusa.
--
-- O QUE IMPEDE A VOLTA: linhas ja com `teto_do_mes`. O CHECK antigo as recusa, e ela CONTA e
-- RECUSA dizendo quantas (molde da VOLTA da 033), sem mudar a situacao de ninguem sozinha: passar um
-- comprador segurado a `aguardando` o faria RECEBER, e isso e decisao do dono, nao do rollback.
BEGIN;

DO $$
DECLARE
    segurados BIGINT;
BEGIN
    SELECT count(*) INTO segurados FROM atendimento.envio_destinatarios WHERE situacao = 'teto_do_mes';
    IF segurados > 0 THEN
        RAISE EXCEPTION 'VOLTA da 034: ha % destinatario(s) em teto_do_mes; o CHECK antigo os recusa. '
                        'Guarde-os e decida o que fazer com cada um antes:  \copy (SELECT * FROM '
                        'atendimento.envio_destinatarios WHERE situacao = ''teto_do_mes'') TO ''teto.csv'' CSV HEADER',
                        segurados;
    END IF;
END $$;

ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_situacao;
ALTER TABLE atendimento.envio_destinatarios ADD CONSTRAINT envio_dest_situacao
    CHECK (situacao IN ('aguardando', 'sem_responsavel', 'sem_whatsapp', 'sem_aceite', 'recusou_antes',
                        'ja_recebeu', 'convidado', 'falhou', 'nao_e_whatsapp'));

DELETE FROM casa.mudancas WHERE nome = '034_teto_do_comprador.sql';
COMMIT;
