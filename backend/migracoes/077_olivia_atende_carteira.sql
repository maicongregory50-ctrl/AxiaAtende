-- #1754 (24/11/2026) -- A OlivIA atende o cliente da carteira na conversa do boletim. Spec e plano:
-- docs/specs/2026-11-24-olivia-atende-a-carteira-no-boletim*.md (D1 a D12). O modelo e a 076.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- D10: as culturas do boletim, do pedido do Marketing (campo opcional). Vazia: a OlivIA nao anota interesse,
-- so passa o representante. Escritor: envio.receber_pedido.
ALTER TABLE atendimento.envios ADD COLUMN culturas text[] NOT NULL DEFAULT '{}';

-- D1: o toque em "Quero saber mais" (e a conversa que entrou por texto em ate 7 dias) e a resposta `saber`.
-- O ERP nao a conhece: eventos_erp.montar a traduz para `falar` ou `texto` (D9; medido no passo 2).
ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_resposta;
ALTER TABLE atendimento.envio_destinatarios ADD CONSTRAINT envio_dest_resposta
    CHECK (resposta IN ('quero', 'nao_quero', 'texto', 'falar', 'saber'));

-- Uma linha por conversa da carteira (D1, D5, D7). E a linha que diz que a conversa e do modo carteira: nasce
-- quando a conversa abre (o toque ou o texto), com a entrada e o papel do destinatario. Escritores: o toque
-- (envio.tratar_toque), a entrada por texto (olivia.carteira) e as ferramentas dela (anotar_interesse e
-- passar_representante, por backend/interesse.py). `enviada_em` preenchida = a FICHA saiu ao responsavel da
-- linha do envio; e por ela que a fala "avisei quem cuida de voce" e permitida (D7).
CREATE TABLE atendimento.interesses (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    destinatario_id bigint NOT NULL REFERENCES atendimento.envio_destinatarios (id),
    conversa_id     bigint NOT NULL REFERENCES atendimento.conversas (id) ON DELETE CASCADE,
    entrada         text NOT NULL CONSTRAINT interesses_entrada CHECK (entrada IN ('toque', 'texto')),
    papel           text,
    culturas        text[] NOT NULL DEFAULT '{}',
    texto           text NOT NULL DEFAULT '',     -- o que o cliente escreveu, literal (o que foi na ficha)
    criado_em       timestamptz NOT NULL DEFAULT now(),
    anotado_em      timestamptz,
    enviada_em      timestamptz,
    enviada_como    text CONSTRAINT interesses_enviada_como CHECK (enviada_como IN ('texto', 'modelo')),
    wamid           text,
    erro            text NOT NULL DEFAULT '',
    CONSTRAINT interesses_uma_por_conversa UNIQUE (conversa_id),
    CONSTRAINT interesses_enviada CHECK ((enviada_em IS NULL) = (enviada_como IS NULL))
);
CREATE INDEX interesses_destinatario ON atendimento.interesses (destinatario_id);
CREATE INDEX interesses_criado_em ON atendimento.interesses (criado_em);

-- D11: a chave. NASCE DESLIGADA; liga e desliga por scripts/olivia.py ligar-carteira | desligar-carteira, sem
-- restart, e so o dono liga. Desligada: o toque "saber" responde com a linha do representante e o texto cai
-- no portao do cliente, como hoje.
INSERT INTO atendimento.ajustes (chave, valor) VALUES ('olivia.atende_carteira', 'false'::jsonb)
ON CONFLICT DO NOTHING;

-- A leitura da sessao (`axiaatende_ro`): o mesmo GRANT da 072, onde o privilegio padrao nao existir.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'axiaatende_ro') THEN
        GRANT SELECT ON atendimento.interesses TO axiaatende_ro;
    END IF;
END $$;

-- Conferencia dentro da transacao
DO $$
BEGIN
    IF to_regclass('atendimento.interesses') IS NULL THEN
        RAISE EXCEPTION '077: a tabela atendimento.interesses nao foi criada.';
    END IF;
    IF (SELECT valor FROM atendimento.ajustes WHERE chave = 'olivia.atende_carteira') IS DISTINCT FROM 'false'::jsonb THEN
        RAISE EXCEPTION '077: a chave olivia.atende_carteira nao nasceu desligada.';
    END IF;
END $$;
