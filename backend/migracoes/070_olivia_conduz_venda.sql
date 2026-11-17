-- #1589 (17/11/2026) -- A chave da conversa de quem quer comprar: a OlivIA conversa, identifica (nome,
-- produtor/revenda/corretor, o que procura) e entrega o contato do representante certo sem o botao de
-- confirmacao. Degrau 2 da escada da spec docs/specs/2026-11-17-olivia-conversa-de-venda.md.
-- NASCE DESLIGADA, e so vale com OLIVIA_FALA ligada. Liga e desliga sem restart por
-- scripts/olivia.py ligar-venda | desligar-venda.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

INSERT INTO atendimento.ajustes (chave, valor) VALUES ('olivia.conduz_venda', 'false'::jsonb)
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.ajustes WHERE chave = 'olivia.conduz_venda') <> 1 THEN
        RAISE EXCEPTION '070: o ajuste olivia.conduz_venda nao ficou gravado.';
    END IF;
END $$;
