-- #1664 (19/11/2026) -- A resposta padrao ao produtor cooperante que responde a um aviso automatico do contrato.
-- Spec e plano: docs/specs/2026-11-19-resposta-padrao-ao-aviso-de-contrato*.md (D1 a D8). A 072 e do #1660.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- Quatro ajustes, nenhuma tabela nova (o codigo e backend/cooperante.py):
--   cooperante.resposta_padrao  a chave (D8); nasce DESLIGADA e liga por scripts/cooperante.py, sem restart
--   cooperante.dias             o prazo depois do aviso em que a mensagem do produtor recebe a resposta (D1)
--   cooperante.texto            o texto fixo, sem IA (D2), com {saudacao}, {nome} e {contato}
--   cooperante.destino          o id do destino (tela Destinos) que e o contato legal do contrato (D4)
INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('cooperante.resposta_padrao', 'false'::jsonb),
    ('cooperante.dias', '7'::jsonb),
    ('cooperante.texto', to_jsonb(
        '{saudacao}, {nome}! Essa mensagem foi um envio automático do nosso sistema, que passou a informar os '
        'andamentos do seu contrato de multiplicação de sementes. Aos poucos todas as etapas vão chegar por '
        'aqui. Eu não tenho os detalhes do seu contrato; quem atende na empresa é o {contato}. Segue o contato '
        'dele.'::text))
ON CONFLICT DO NOTHING;

DO $$
DECLARE
    d integer;
BEGIN
    SELECT id INTO d FROM atendimento.destinos WHERE nome = 'Maicon Gregory' ORDER BY id LIMIT 1;
    IF d IS NULL THEN
        RAISE EXCEPTION '073: o destino "Maicon Gregory" nao existe na tela Destinos; o contato do cooperante fica sem dono.';
    END IF;
    INSERT INTO atendimento.ajustes (chave, valor) VALUES ('cooperante.destino', to_jsonb(d))
    ON CONFLICT DO NOTHING;
END $$;

-- Conferencia dentro da transacao
DO $$
BEGIN
    IF (SELECT valor FROM atendimento.ajustes WHERE chave = 'cooperante.resposta_padrao') IS DISTINCT FROM 'false'::jsonb THEN
        RAISE EXCEPTION '073: a chave cooperante.resposta_padrao nao nasceu desligada.';
    END IF;
    IF (SELECT count(*) FROM atendimento.ajustes
         WHERE chave IN ('cooperante.dias', 'cooperante.texto', 'cooperante.destino')) <> 3 THEN
        RAISE EXCEPTION '073: os ajustes do cooperante nao ficaram completos.';
    END IF;
END $$;
