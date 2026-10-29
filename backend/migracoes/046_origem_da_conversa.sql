-- #1204 (dono, 29/10/2026) -- a conversa diz quem a abriu. Ate aqui toda conversa nascia de uma mensagem
-- chegando, e a Recepcao a contava como "chegou". O scripts/portao_retroativo.py (#1189) abre conversa
-- SEM mensagem nova: em 29/10 09:28 a da COPERMAP apareceu como "so chegou / parou no meio", e quem
-- escreveu primeiro fomos nos. `origem` = 'mensagem' (o recepcionista) ou 'portao_retroativo' (o script).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.conversas
    ADD COLUMN origem text NOT NULL DEFAULT 'mensagem'
        CONSTRAINT conversas_origem CHECK (origem IN ('mensagem', 'portao_retroativo'));

-- As que ja existem, pela regra e nao por id: o portao saiu NO INSTANTE em que a conversa nasceu, e
-- nenhuma mensagem dessa pessoa foi processada naquele instante. No recepcionista os tres carimbos sao
-- o mesmo `momento` (processado_em = iniciada_em = enviada_em); no script nao ha evento.
UPDATE atendimento.conversas c SET origem = 'portao_retroativo'
 WHERE EXISTS (SELECT 1 FROM atendimento.enviadas e
                WHERE e.conversa_id = c.id AND e.resumo LIKE 'portao do cliente%' AND e.enviada_em = c.iniciada_em)
   AND NOT EXISTS (SELECT 1 FROM atendimento.eventos_meta m
                    WHERE m.tipo = 'mensagem' AND m.processado_em = c.iniciada_em
                      AND (m.bsuid = c.bsuid OR m.corpo->'msg'->>'from' = c.wa_id));

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM atendimento.conversas WHERE origem = 'portao_retroativo';
    RAISE NOTICE '046 OK: origem na conversa; % aberta(s) pelo portao retroativo', n;
END $$;
