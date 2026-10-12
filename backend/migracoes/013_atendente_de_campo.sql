-- #970, decisao 14 do dono (12/10/2026): o atendente de campo ganha um OBJETIVO, classificar a foto,
-- em vez de um roteiro fixo. O que ele fecha (bastidor, produto, fase, data) mora aqui; o marketing
-- aplica no catalogo quando fecha, mesmo horas depois. Sem BEGIN nem COMMIT.

ALTER TABLE atendimento.material_de_campo
    ADD COLUMN classe_bastidor    text,          -- o que o dialogo fechou (listas fechadas)
    ADD COLUMN classe_produto     text,
    ADD COLUMN classe_fase        text,
    ADD COLUMN lida_em            timestamptz,   -- a frase foi lida pela IA de texto
    ADD COLUMN pergunta_n         integer NOT NULL DEFAULT 0,   -- perguntas de classificacao ja feitas ao grupo (max 3)
    ADD COLUMN retomar_em         timestamptz,   -- quando voltar a perguntar o que ficou sem resposta
    ADD COLUMN retomada           boolean NOT NULL DEFAULT false,
    ADD COLUMN fechado_em         timestamptz,   -- a classificacao fechou (completa ou com o que deu)
    ADD COLUMN desistiu_em        timestamptz,   -- ninguem respondeu nem na retomada
    ADD COLUMN classe_aplicada_em timestamptz;   -- o marketing aplicou no catalogo

ALTER TABLE atendimento.material_de_campo DROP CONSTRAINT material_pergunta;
ALTER TABLE atendimento.material_de_campo ADD CONSTRAINT material_pergunta
    CHECK (pergunta_pendente IN ('legenda', 'data', 'qual_dia', 'bastidor', 'produto', 'fase'));

-- A lista de produtos do portfolio do marketing, para a IA de texto e para casar o que a pessoa
-- escreve. O publicador do marketing a manda (POST /campo/portfolio) e a mantem em dia.
INSERT INTO atendimento.ajustes (chave, valor) VALUES ('campo.produtos', '[]'::jsonb)
ON CONFLICT (chave) DO NOTHING;
