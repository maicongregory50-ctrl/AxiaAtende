-- #1434 -- o texto do modelo aviso_painel (063) terminava na variavel ({{1}}), e a Meta recusa corpo que
-- comeca ou termina numa variavel (modelos_meta). A 063 ja estava aplicada quando isso apareceu: o
-- conserto e esta mudanca nova, como manda backend/migracoes.py.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.modelos SET texto = 'Aviso do painel da casa: {{1}} O detalhe está no painel.'
 WHERE nome = 'aviso_painel';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM atendimento.modelos WHERE nome = 'aviso_painel' AND texto LIKE '%{{1}}') THEN
        RAISE EXCEPTION '064: o texto do aviso_painel ainda termina na variavel.';
    END IF;
    RAISE NOTICE '064 OK: o texto do aviso do painel';
END $$;
