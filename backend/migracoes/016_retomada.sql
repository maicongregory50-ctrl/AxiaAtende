-- #989 (dono, 13/10/2026): a RETOMADA PELA OLIVIA. Trinta minutos depois de a conversa parar no
-- meio, a IA rele o que a pessoa escreveu e tocou, acha a opcao do menu que resolve e pergunta
-- "Pelo que entendi da nossa conversa, voce quer: X. E isso?" (Sim manda o link; Ver opcoes repete a
-- pergunta do ponto onde ela parou). Uma vez por conversa, so nas 24 h, nunca texto livre.
-- Sem BEGIN nem COMMIT.
ALTER TABLE atendimento.conversas
    ADD COLUMN retomada_em    timestamptz,   -- quando a OlivIA tentou (com ou sem mensagem: uma tentativa so)
    ADD COLUMN retomada_chave text;          -- o que ela propos (a chave do menu), ou o motivo de nao propor

INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('retomada', '"Pelo que entendi da nossa conversa, você quer: {opcao}. É isso?"'::jsonb)
ON CONFLICT (chave) DO NOTHING;
