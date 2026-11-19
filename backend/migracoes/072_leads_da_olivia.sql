-- #1660 (19/11/2026) -- A OlivIA qualifica o produtor rural (piloto SC e RS) e entrega a ficha a quem atende.
-- Spec e plano: docs/specs/2026-11-19-olivia-qualifica-o-produtor-rural*.md (D1 a D10).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- Uma linha por conversa de qualificacao. Quem escreve: SO as duas ferramentas da OlivIA (`anotar_lead`
-- cria e atualiza; `fechar_lead` grava o resumo, `completa`, `faltou` e o resultado do envio da ficha).
-- `enviada_em` preenchida = a ficha SAIU para o destino da folha; e por ela que a fala "o consultor esta
-- recebendo o resumo" e permitida (D6). Apagada com 12 meses (D10), na rotina que apaga a ficha do candidato.
CREATE TABLE atendimento.leads (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversa_id   bigint NOT NULL REFERENCES atendimento.conversas (id) ON DELETE CASCADE,
    destino_id    integer REFERENCES atendimento.destinos (id) ON DELETE SET NULL,
    nome          text NOT NULL DEFAULT '',
    produto       text NOT NULL DEFAULT '',
    finalidade    text NOT NULL DEFAULT '',
    tamanho       text NOT NULL DEFAULT '',
    quando        text NOT NULL DEFAULT '',
    municipio     text NOT NULL DEFAULT '',
    uf            text NOT NULL DEFAULT '',
    resumo        text NOT NULL DEFAULT '',
    completa      boolean NOT NULL DEFAULT false,
    faltou        text[] NOT NULL DEFAULT '{}',
    criado_em     timestamptz NOT NULL DEFAULT now(),
    enviada_em    timestamptz,
    enviada_como  text CONSTRAINT leads_enviada_como CHECK (enviada_como IN ('texto', 'modelo')),
    wamid         text,
    erro          text NOT NULL DEFAULT '',
    CONSTRAINT leads_uma_por_conversa UNIQUE (conversa_id),
    CONSTRAINT leads_enviada CHECK ((enviada_em IS NULL) = (enviada_como IS NULL))
);
CREATE INDEX leads_criado_em ON atendimento.leads (criado_em);

-- D8 e D1: a chave do piloto (nasce DESLIGADA; liga por scripts/olivia.py ligar-qualifica, sem restart, e so
-- vale com olivia.conduz_venda ligada) e os estados do piloto, para ampliar sem codigo.
INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('olivia.qualifica_produtor', 'false'::jsonb),
    ('olivia.qualifica_estados', '["SC", "RS"]'::jsonb)
ON CONFLICT DO NOTHING;

-- A leitura da sessao (`axiaatende_ro`) ja recebe tabela nova pelo ALTER DEFAULT PRIVILEGES de
-- servicos/criar_leitura.ps1; o GRANT aqui garante o mesmo onde o privilegio padrao nao existir.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'axiaatende_ro') THEN
        GRANT SELECT ON atendimento.leads TO axiaatende_ro;
    END IF;
END $$;

-- Conferencia dentro da transacao
DO $$
BEGIN
    IF to_regclass('atendimento.leads') IS NULL THEN
        RAISE EXCEPTION '072: a tabela atendimento.leads nao foi criada.';
    END IF;
    IF (SELECT valor FROM atendimento.ajustes WHERE chave = 'olivia.qualifica_produtor') IS DISTINCT FROM 'false'::jsonb THEN
        RAISE EXCEPTION '072: a chave olivia.qualifica_produtor nao nasceu desligada.';
    END IF;
    IF (SELECT valor FROM atendimento.ajustes WHERE chave = 'olivia.qualifica_estados') IS DISTINCT FROM '["SC", "RS"]'::jsonb THEN
        RAISE EXCEPTION '072: os estados do piloto nao ficaram SC e RS.';
    END IF;
END $$;
