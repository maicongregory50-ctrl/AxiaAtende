-- #1248 (04/11/2026, 08:01): o Status do dia (3 imagens, PUB-0307) ao dono estourou o tempo no upload
-- para a Meta ("The read operation timed out") e o aviso ficou com `erro` -- e aviso com erro sai da fila
-- PARA SEMPRE: nao havia segunda tentativa. Agora a falha de rede (timeout, conexao) conta uma
-- tentativa e o aviso volta a fila 5 min depois, ate 3 vezes; so a terceira, ou um erro que nao e de
-- rede, vira `erro`. Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.avisos
    ADD COLUMN tentativas integer NOT NULL DEFAULT 0,   -- falhas de rede ate aqui
    ADD COLUMN tentativa_em timestamptz;                -- a ultima delas

-- O aviso de hoje que caiu por timeout volta a fila (uma vez; o erro antigo fica registrado em
-- tentativa_em = agora e tentativas = 1, para a conta das tres valer desde ja).
UPDATE atendimento.avisos
   SET erro = '', tentativas = 1, tentativa_em = now()
 WHERE enviado_em IS NULL AND nao_visto_em IS NULL
   AND erro ILIKE '%timed out%' AND criado_em > now() - interval '2 days';
