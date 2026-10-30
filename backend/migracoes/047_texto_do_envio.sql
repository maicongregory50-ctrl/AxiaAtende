-- #1205 (dono, 30/10/2026) -- o texto exato do que nos mandamos. Ate aqui `enviadas` guardava so o
-- resumo ("menu principal", "ia retomou fornecedores.ainda"), e a janela da conversa na Recepcao
-- mostraria o resumo em vez do que o cliente leu. Um escritor so: a `SaidaMeta`, depois de a Meta
-- aceitar o envio (backend/texto_enviado.py). A chave e o `wamid`, o mesmo que `enviadas` grava.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

CREATE TABLE atendimento.enviadas_texto (
    wamid      text PRIMARY KEY,
    tipo       text NOT NULL,                  -- texto | botoes | lista | link | contato | imagem | documento | modelo
    texto      text NOT NULL DEFAULT '',       -- o corpo como saiu (no modelo, vazio: o corpo e o de `modelos`)
    opcoes     jsonb,                          -- botoes, linhas da lista, link: o que a pessoa viu para tocar
    modelo     text,                           -- o nome do modelo, quando foi modelo
    variaveis  text[],                         -- as variaveis do modelo, na ordem {{1}}, {{2}}...
    legenda    text NOT NULL DEFAULT '',       -- imagem e documento: a legenda e o nome do arquivo
    gravado_em timestamptz NOT NULL DEFAULT now()
);

-- A chave da captura: `false` para de gravar no proximo envio, sem restart (ROLLBACK 1 da spec).
INSERT INTO atendimento.ajustes (chave, valor) VALUES ('enviadas.guardar_texto', 'true'::jsonb);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'enviadas.guardar_texto') THEN
        RAISE EXCEPTION '047: o ajuste enviadas.guardar_texto nao nasceu.';
    END IF;
    RAISE NOTICE '047 OK: enviadas_texto e a chave da captura';
END $$;
