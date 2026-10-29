-- #1193 -- a retomada: o cliente que tinha recusado volta a receber depois de falar com uma pessoa
-- (dono, 29/10/2026). Spec e plano: C:\AxiaGestao\docs\specs\2026-10-29-relacionamento-parar-e-retomar*.md
-- (passo 7). Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- A REGRA 4 NAO MUDA DE FORCA: consentimento nao se altera nem se apaga (o gatilho continua). A retomada
-- e um consentimento NOVO, por cima: um aceite com origem 'retomada', gravado quando a busca traz do ERP
-- a retomada que uma pessoa registrou (axia.rel_retomadas). Como o envio e a tela Quem recebe leem o
-- ULTIMO consentimento do numero, o aceite novo vence a recusa antiga; uma recusa ainda mais nova vence
-- o aceite. Nao ha wamid (nao veio da Meta): fica vazio, e quem e quando ficam em registrado_por e em.
--
-- ADD COLUMN com padrao nao dispara o gatilho de linha (UPDATE/DELETE): as linhas de hoje ficam 'toque'.

ALTER TABLE atendimento.consentimentos
    ADD COLUMN origem text NOT NULL DEFAULT 'toque'
        CONSTRAINT consentimentos_origem CHECK (origem IN ('toque', 'retomada')),
    ADD COLUMN retomada_ref bigint,
    ADD COLUMN registrado_por text,
    ADD CONSTRAINT consentimentos_retomada CHECK (
        (origem = 'toque' AND retomada_ref IS NULL)
        OR (origem = 'retomada' AND retomada_ref IS NOT NULL AND tipo = 'aceite' AND registrado_por IS NOT NULL));
-- a mesma retomada do ERP duas vezes grava uma
CREATE UNIQUE INDEX consentimentos_retomada_ref ON atendimento.consentimentos (retomada_ref)
    WHERE retomada_ref IS NOT NULL;
