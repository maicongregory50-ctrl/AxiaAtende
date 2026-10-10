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
