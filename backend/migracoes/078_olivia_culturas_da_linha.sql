-- #1754, emenda de 25/11/2026 (D13, D14): a lista fechada de anotar_interesse passa a ser a LINHA INTEIRA da
-- Renascer, num ajuste, e nao as culturas do envio (que viram so o destaque "do boletim"). O que o cliente
-- pede fora da linha vai literal, numa coluna propria do interesse. Lista conferida pelo dono em 25/11/2026,
-- tirada de docs/olivia/base-da-empresa.md ("Os produtos"), pela especie; troca-se por scripts/olivia.py.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

INSERT INTO atendimento.ajustes (chave, valor) VALUES ('olivia.culturas_da_linha', '[
  "Aveia preta", "Aveia branca", "Aveia ucraniana", "Azevém", "Capim sudão", "Centeio", "Milheto",
  "Nabo forrageiro", "Trigo mourisco", "Ervilha forrageira", "Ervilhaca", "Tremoço branco", "Feijão guandu",
  "Crotalária", "Misturas AVR (adubação verde)", "Misturas FR (pastagem)"
]'::jsonb)
ON CONFLICT DO NOTHING;

ALTER TABLE atendimento.interesses ADD COLUMN fora_da_linha text[] NOT NULL DEFAULT '{}';

-- Conferencia dentro da transacao
DO $$
BEGIN
    IF jsonb_array_length((SELECT valor FROM atendimento.ajustes WHERE chave = 'olivia.culturas_da_linha')) < 1 THEN
        RAISE EXCEPTION '078: a lista olivia.culturas_da_linha nao nasceu.';
    END IF;
    IF NOT (SELECT valor FROM atendimento.ajustes WHERE chave = 'olivia.culturas_da_linha') ? 'Centeio' THEN
        RAISE EXCEPTION '078: o centeio ficou fora da linha.';
    END IF;
END $$;
