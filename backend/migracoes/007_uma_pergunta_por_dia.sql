-- #969, etapa 2: a pergunta "recebeu o atendimento?" sai UMA vez por pessoa por dia, 4h30 depois da
-- ULTIMA mensagem dela (dono, 10/10/2026: tres conversas simuladas no mesmo dia deram tres
-- perguntas). Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- `pergunta_da`: a conversa que levou a pergunta. Ela mesma, quando a pergunta saiu nela; outra
-- conversa do mesmo dia, quando ficou coberta por aquela pergunta (sem mensagem nova); NULL com
-- `pergunta_feita_em` preenchida = nao se perguntou (passou da janela de 24h da Meta).
ALTER TABLE atendimento.conversas
    ADD COLUMN pergunta_da bigint REFERENCES atendimento.conversas (id);

-- As que ja foram perguntadas: cada uma levou a propria pergunta.
UPDATE atendimento.conversas SET pergunta_da = id WHERE pergunta_feita_em IS NOT NULL;

-- E so em horario comercial (dono, 10/10/2026): seg a sab, 08-11 e 14-17. Sabado entra para quem
-- chamou sexta a tarde nao perder a janela de 24h da Meta ate segunda.
INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('pergunta_janela', '{"dias": [1, 2, 3, 4, 5, 6], "faixas": [["08:00", "11:00"], ["14:00", "17:00"]]}'::jsonb)
ON CONFLICT (chave) DO NOTHING;
