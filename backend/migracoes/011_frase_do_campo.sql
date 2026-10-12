-- #970, decisao 13 do dono (12/10/2026): colaborador e representante do cadastro so recebem o menu
-- se pedirem ("menu"). O que escrevem fora disso e a FRASE da proxima foto (a legenda escrita antes
-- de mandar a foto, o jeito mais comum no celular) e fica guardado aqui ate a foto chegar.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

CREATE TABLE atendimento.campo_frases (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wa_id       text NOT NULL,
    texto       text NOT NULL,
    recebido_em timestamptz NOT NULL,
    usada_em    timestamptz,                    -- quando virou legenda de uma foto
    avisado     boolean NOT NULL DEFAULT false  -- a linha "anotado; para falar com alguem, escreva menu" ja foi
);
CREATE INDEX campo_frases_wa_id ON atendimento.campo_frases (wa_id, recebido_em DESC);
