-- #1722 (24/11/2026) -- a logo 7: a ficha-FRT-2026-0003.pdf que o dono mandou as 07:34 de 24/11
-- DESLIZANDO o aviso da integracao do Bradesco (18/11) e que virou "Recebi a logo". Nao e logo: fecha
-- como a 074 fechou a logo 6 -- sem pergunta pendente, puxada (nao e oferecida ao AxiaMarketing como
-- largada), resultado nulo. O caminho do arquivo FICA (o arquivo continua no disco; apagar e do dono).
-- Guardada pelo wamid: no banco de teste (5437) a linha nao existe e a migracao passa sem tocar nada.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.logos_de_cliente
   SET pergunta_pendente = NULL,
       puxada_em = now(),
       resultado = NULL,
       erro = 'nao era logo: PDF deslizando o aviso da integracao (#1722)'
 WHERE wamid = 'wamid.HBgMNTU0OTkxNTA1NTY1FQIAEhgWM0VCMDUzRERFRDNEQzBDMjQyNTk3MQA='
   AND puxada_em IS NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM atendimento.logos_de_cliente
                WHERE wamid = 'wamid.HBgMNTU0OTkxNTA1NTY1FQIAEhgWM0VCMDUzRERFRDNEQzBDMjQyNTk3MQA='
                  AND (pergunta_pendente IS NOT NULL OR puxada_em IS NULL)) THEN
        RAISE EXCEPTION '075: a logo da ficha de 24/11 ainda espera o cliente ou ainda pode ser puxada.';
    END IF;
    RAISE NOTICE '075 OK: logo da ficha de 24/11 fechada (onde existia).';
END $$;
