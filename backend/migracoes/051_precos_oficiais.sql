-- #1223 -- os precos oficiais da Meta e do Gemini, lancados pela sessao a pedido do dono (31/10/2026:
-- "vamos buscar as tabelas oficiais dos dois servicos e ja preencher"). Antes, a tela dizia "sem preco".
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py. `criado_por` nulo: a tela mostra "(semente)".
--
-- META, por mensagem, em USD (a conta e faturada em USD: a propria Meta respondeu `currency = USD`).
--   marketing 0,0625 e utility 0,0068: CONFERIDOS na conferencia de 31/10/2026 (pricing_analytics da
--   conta 1442233593867052): 28/10 39 x marketing = US$ 2,4375; 29/10 29 = US$ 1,8125; 30/10 61 = US$ 3,8125;
--   28/10 2 x utility = US$ 0,0136. A documentacao da Meta (developers.facebook.com/docs/whatsapp/pricing)
--   cita 0,68 c para utilidade e autenticacao no Brasil, e a tabela vigente e a de 01/10/2026 (o Brasil
--   nao esta na lista de mudancas de outubro).
--   marketing_lite 0,0625: a Meta cobra a Marketing Messages Lite pela tarifa de marketing; nao conferido
--   na conta (so 2 mensagens em outubro). A conferencia diaria mostra se divergir.
--   authentication 0,0068: a mesma referencia da documentacao; a casa nao manda autenticacao hoje.
--
-- GEMINI, por milhao de tokens, em USD (ai.google.dev/gemini-api/docs/pricing, lido em 31/10/2026, nivel pago):
--   gemini-3.8-flash (o olhar sobre a foto): 0,75 / 3,75 ate 31/12/2026; 1,50 / 7,50 a partir de 01/01/2027
--     -- a segunda linha ja entra com a data, e a tela troca sozinha na virada.
--   gemini-2.5-flash-image (o editor): entrada 0,30; saida 30,00 (o preco do token de IMAGEM, que e o grosso
--     da saida: 1.290 tokens por imagem de ate 1024x1024 = US$ 0,039). O texto que vem junto sai pelo mesmo
--     preco, o que conta um pouco a mais, nunca a menos. Desligado pelo Google em 15/03/2027.
-- O `item` tem de bater com o modelo que o Google devolve em cada chamada (`modelVersion`); se vier outro
-- nome, a linha aparece "sem preco" e o preco se lanca na tela com aquele nome.

INSERT INTO atendimento.precos (servico, item, vale_desde, por_mensagem) VALUES
    ('meta', 'marketing',      '2026-10-01', 0.0625),
    ('meta', 'utility',        '2026-10-01', 0.0068),
    ('meta', 'marketing_lite', '2026-10-01', 0.0625),
    ('meta', 'authentication', '2026-10-01', 0.0068);

INSERT INTO atendimento.precos (servico, item, vale_desde, por_milhao_entrada, por_milhao_saida) VALUES
    ('gemini', 'gemini-3.8-flash',       '2026-10-01', 0.75, 3.75),
    ('gemini', 'gemini-3.8-flash',       '2027-01-01', 1.50, 7.50),
    ('gemini', 'gemini-2.5-flash-image', '2026-10-01', 0.30, 30.00);

DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.precos WHERE criado_por IS NULL AND servico IN ('meta', 'gemini')) < 7 THEN
        RAISE EXCEPTION '051: os precos oficiais nao entraram inteiros.';
    END IF;
    RAISE NOTICE '051 OK: os precos oficiais da Meta e do Gemini';
END $$;
