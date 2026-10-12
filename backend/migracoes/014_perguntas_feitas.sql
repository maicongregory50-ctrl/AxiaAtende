-- #970, decisao 15 do dono (12/10/2026, no segundo caso): a lista e do agente, nao de quem manda a
-- foto -- as perguntas sao abertas e a IA de texto as encaixa; cada pergunta e feita UMA vez, e a
-- foto entra no catalogo quando a conversa fecha. Aqui mora o que ja foi perguntado ao grupo.
-- Sem BEGIN nem COMMIT.
ALTER TABLE atendimento.material_de_campo
    ADD COLUMN perguntas_feitas text[] NOT NULL DEFAULT '{}';
