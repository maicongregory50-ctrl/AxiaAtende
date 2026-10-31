-- #1223 -- o painel de custos das APIs pagas (Claude, Meta, Gemini), por funcao. Spec e plano:
-- docs/specs/2026-10-31-olivia-e-o-painel-de-custos*.md.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- A Meta NAO ganha registro novo aqui: a quantidade cobrada ja vem em `eventos_meta` (o `pricing` de
-- cada aviso de status) e o modelo de cada envio ja esta em `enviadas_texto.modelo` (#1205). O que
-- nasce e o que faltava: o uso de IA por chamada, os precos com vigencia e o que a Meta diz ter cobrado.
-- O `axiaatende_ro` le as tabelas novas pelo ALTER DEFAULT PRIVILEGES de servicos/criar_leitura.ps1.

-- Uma linha por chamada a modelo pago. `origem` diz QUEM chamou: o recepcionista daqui grava direto
-- (id_origem nulo); o AxiaMarketing empurra o dele por /pedido/uso-ia, com o id da linha de la, e o
-- UNIQUE faz o mesmo lote mandado duas vezes virar uma linha so.
CREATE TABLE atendimento.uso_ia (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    em          timestamptz NOT NULL DEFAULT now(),
    origem      text NOT NULL CONSTRAINT uso_ia_origem CHECK (origem IN ('axiaatende', 'axiamarketing')),
    id_origem   bigint,
    servico     text NOT NULL CONSTRAINT uso_ia_servico CHECK (servico IN ('claude', 'gemini')),
    funcao      text NOT NULL CONSTRAINT uso_ia_funcao CHECK (btrim(funcao) <> ''),
    modelo      text NOT NULL,
    entrada     integer NOT NULL DEFAULT 0 CONSTRAINT uso_ia_entrada CHECK (entrada >= 0),
    saida       integer NOT NULL DEFAULT 0 CONSTRAINT uso_ia_saida CHECK (saida >= 0),
    CONSTRAINT uso_ia_da_origem UNIQUE (origem, id_origem)
);
CREATE INDEX uso_ia_em ON atendimento.uso_ia (em);

-- O preco por item, com a data em que passou a valer. Preco novo e LINHA nova: o antigo continua
-- valendo para os dias de antes. Meta: `item` e a categoria que a Meta cobra (marketing, utility,
-- marketing_lite...), por mensagem. Claude e Gemini: `item` e o modelo, por milhao de tokens.
CREATE TABLE atendimento.precos (
    id                  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    servico             text NOT NULL CONSTRAINT precos_servico CHECK (servico IN ('meta', 'claude', 'gemini')),
    item                text NOT NULL CONSTRAINT precos_item CHECK (btrim(item) <> ''),
    vale_desde          date NOT NULL,
    por_mensagem        numeric(12, 6),
    por_milhao_entrada  numeric(12, 6),
    por_milhao_saida    numeric(12, 6),
    moeda               text NOT NULL DEFAULT 'USD' CONSTRAINT precos_moeda CHECK (moeda ~ '^[A-Z]{3}$'),
    criado_por          integer REFERENCES casa.usuarios (id),
    criado_em           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT precos_um_por_dia UNIQUE (servico, item, vale_desde),
    CONSTRAINT precos_forma CHECK (
        (servico = 'meta' AND por_mensagem IS NOT NULL AND por_mensagem >= 0)
        OR (servico <> 'meta' AND por_milhao_entrada IS NOT NULL AND por_milhao_saida IS NOT NULL
            AND por_milhao_entrada >= 0 AND por_milhao_saida >= 0))
);

-- Semente: o preco de tabela do Haiku 5.5 registrado em backend/ia.py (06/10/2026). Meta e Gemini
-- nascem SEM preco, de proposito: quem preenche e o dono, e ate la a tela diz "sem preco", nunca 0.
INSERT INTO atendimento.precos (servico, item, vale_desde, por_milhao_entrada, por_milhao_saida)
VALUES ('claude', 'claude-haiku-5-5', '2026-10-06', 0.10, 0.50);

-- O que a Meta diz ter cobrado, por dia e categoria (a conferencia diaria, backend/custos_meta.py).
CREATE TABLE atendimento.meta_cobrado (
    dia        date NOT NULL,
    categoria  text NOT NULL,
    volume     integer NOT NULL DEFAULT 0,
    custo      numeric(14, 6) NOT NULL DEFAULT 0,
    moeda      text NOT NULL DEFAULT '',
    lido_em    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (dia, categoria)
);

-- Como foi a leitura de cada dia. `sem_acesso` e `erro` existem para a tela nunca mostrar zero onde
-- ninguem conseguiu ler.
CREATE TABLE atendimento.meta_conferencia (
    dia       date PRIMARY KEY,
    situacao  text NOT NULL CONSTRAINT meta_conferencia_situacao CHECK (situacao IN ('ok', 'sem_acesso', 'erro')),
    detalhe   text NOT NULL DEFAULT '',
    lido_em   timestamptz NOT NULL DEFAULT now()
);

-- A chave da conferencia: em `false`, o recepcionista para de perguntar a Meta, sem restart.
INSERT INTO atendimento.ajustes (chave, valor) VALUES ('custos.conferir_meta', 'true'::jsonb);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM atendimento.precos WHERE servico = 'claude' AND item = 'claude-haiku-5-5') THEN
        RAISE EXCEPTION '050: o preco do Haiku nao nasceu.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'custos.conferir_meta') THEN
        RAISE EXCEPTION '050: o ajuste custos.conferir_meta nao nasceu.';
    END IF;
    RAISE NOTICE '050 OK: uso de IA, precos e a conferencia da Meta';
END $$;
