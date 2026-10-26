-- VOLTA da 033 (#1142). Nunca e aplicada junto com a ida.
--
-- O QUE SE PERDE: o papel de cada destinatario, o canal do responsavel, e os avisos de resumo ja
-- gravados (o tipo sai do CHECK, entao eles nao podem ficar). O que NAO se toca:
-- `atendimento.consentimentos` (regra 4 deste projeto -- aceite e recusa ficam, inclusive num
-- rollback) e as mensagens ja enviadas.
--
-- O CODIGO JA DEVE TER SIDO REVERTIDO antes dela: senao `receber_pedido` grava colunas que nao
-- existem e o `ON CONFLICT` por numero nao acha indice nenhum.
--
-- DUAS COISAS IMPEDEM A VOLTA, e por isso ela CONTA as duas antes de mexer:
--   1. avisos de `lote_do_representante` ja gravados -- o CHECK antigo os recusa;
--   2. dois destinatarios do MESMO cadastro no mesmo envio (o caso que a 033 passou a permitir) --
--      a unicidade antiga, por cadastro, nao cabe neles.
-- Falhar no meio do ALTER diria "violou a restricao" sem dizer quantos nem quais.
BEGIN;

DO $$
DECLARE
    avisos    BIGINT;
    repetidos BIGINT;
    exemplo   TEXT;
BEGIN
    SELECT count(*) INTO avisos FROM atendimento.avisos WHERE tipo = 'lote_do_representante';
    IF avisos > 0 THEN
        RAISE EXCEPTION 'VOLTA da 033: ha % aviso(s) de lote_do_representante gravado(s); o CHECK '
                        'antigo os recusa. Guarde-os e apague antes:  \copy (SELECT * FROM '
                        'atendimento.avisos WHERE tipo = ''lote_do_representante'') TO ''avisos.csv'' CSV HEADER',
                        avisos;
    END IF;
    SELECT count(*), min(format('envio %s, cadastro %s (%s vezes)', envio_id, erp_codigo, n))
      INTO repetidos, exemplo
      FROM (SELECT envio_id, erp_codigo, count(*) AS n
              FROM atendimento.envio_destinatarios
             GROUP BY envio_id, erp_codigo HAVING count(*) > 1) x;
    IF repetidos > 0 THEN
        RAISE EXCEPTION 'VOLTA da 033: % par(es) (envio, cadastro) repetido(s) -- a unicidade antiga '
                        'nao cabe. O primeiro: %. Isso e o comprador E o tecnico do mesmo cliente no '
                        'mesmo envio, que a 033 passou a permitir: decida qual fica.', repetidos, exemplo;
    END IF;
END $$;

DELETE FROM atendimento.modelos WHERE uso = 'aviso_lote_do_representante';

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro', 'curriculo'));

ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento'));

DROP INDEX atendimento.envio_dest_um_por_numero;
ALTER TABLE atendimento.envio_destinatarios
    ADD CONSTRAINT envio_dest_um_por_cliente UNIQUE (envio_id, erp_codigo);

ALTER TABLE atendimento.envio_destinatarios
    DROP CONSTRAINT envio_dest_resp_canal,
    DROP CONSTRAINT envio_dest_papel;
ALTER TABLE atendimento.envio_destinatarios
    DROP COLUMN responsavel_canal,
    DROP COLUMN papel;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'envio_dest_um_por_cliente') THEN
        RAISE EXCEPTION 'VOLTA da 033: a unicidade por cadastro devia ter voltado.';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'atendimento' AND table_name = 'envio_destinatarios'
                  AND column_name IN ('papel', 'responsavel_canal')) THEN
        RAISE EXCEPTION 'VOLTA da 033: as duas colunas devia ter saido.';
    END IF;
    RAISE NOTICE 'VOLTA da 033 OK: a unicidade por cadastro de volta, as colunas fora, o modelo fora.';
END $$;

DELETE FROM casa.mudancas WHERE nome = '033_fila_por_numero_e_resumo.sql';
COMMIT;
