-- #1722 (23/11/2026) -- A limpeza do que ficou pendurado na conversa da Fran em 23/11 (D4 da spec).
-- Spec e plano: docs/specs/2026-11-23-arquivo-e-texto-citando-chamado*.md. A 073 e do #1664.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- Duas linhas, guardadas pelo CONTEUDO e nao so pelo id: no banco de teste (5437) elas nao existem,
-- e a migracao passa sem tocar nada.
--   1. a mensagem 136 (a resposta do FGTS das 14:24, descartada) volta a `a_entregar`: a volta das
--      telas a leva ao chamado 1541 como comentario. A 135 (o mesmo texto, 14:23) fica descartada.
--   2. a logo 6 (o PDF do termo de rescisao, que citava a pergunta do 1541) fecha: sem pergunta
--      pendente, puxada (nao e oferecida ao AxiaMarketing como largada), resultado nulo (nao e
--      anunciada a quem mandou), sem caminho de arquivo. O arquivo no disco sai em passo proprio do plano.
--      O PDF NAO vai ao chamado (dono): nao e o que a pergunta pedia.

UPDATE atendimento.pendencias_mensagens
   SET estado = 'a_entregar'
 WHERE id = 136 AND estado = 'descartada' AND sentido = 'entrou'
   AND texto LIKE 'No caso da rescis%';

UPDATE atendimento.logos_de_cliente
   SET pergunta_pendente = NULL,
       puxada_em = now(),
       resultado = NULL,
       arquivo = NULL,
       erro = 'nao era logo: PDF devolvido ao chamado 1541 (#1722)'
 WHERE wamid = 'wamid.HBgMNTU0OTkxOTM4OTEwFQIAEhgWM0VCMDcxODJBMjI4MENEMTY0MjMxMwA='
   AND puxada_em IS NULL;

-- Conferencia dentro da transacao
DO $$
DECLARE
    logo integer;
    msg integer;
BEGIN
    SELECT count(*) INTO logo FROM atendimento.logos_de_cliente
     WHERE wamid = 'wamid.HBgMNTU0OTkxOTM4OTEwFQIAEhgWM0VCMDcxODJBMjI4MENEMTY0MjMxMwA='
       AND (pergunta_pendente IS NOT NULL OR puxada_em IS NULL);
    IF logo > 0 THEN
        RAISE EXCEPTION '074: a logo do PDF de 23/11 ainda espera o cliente ou ainda pode ser puxada.';
    END IF;
    SELECT count(*) INTO msg FROM atendimento.pendencias_mensagens
     WHERE id = 136 AND texto LIKE 'No caso da rescis%' AND estado = 'descartada';
    IF msg > 0 THEN
        RAISE EXCEPTION '074: a resposta do FGTS (136) continua descartada.';
    END IF;
    RAISE NOTICE '074 OK: logo do PDF fechada e resposta do FGTS a entregar (onde existiam).';
END $$;
