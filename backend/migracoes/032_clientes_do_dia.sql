-- #1090 etapa 3, entrega 1 (23/10/2026): "Meus clientes" -- o consultor recebe um cliente por vez no
-- WhatsApp da Renascer, conta por escrito como foi, a OlivIA monta o registro e ele confere.
-- Spec: C:\AxiaGestao\docs\specs\2026-10-23-relacionamento-etapa3-visita-pelo-whatsapp.md
--
-- QUEM ESCREVE O QUE:
--   clientes_fila / clientes_motivos: o processo das TELAS (copia do ERP a cada 10 min; o recepcionista
--     nao tem o segredo do ERP -- R4).
--   clientes_registros: o RECEPCIONISTA (a conversa) e as TELAS (o envio ao ERP: gravado/recusado).
--   clientes_consultores: esta migracao (o dono, pela linha dele em Destinos) e, depois, a mao.
--
-- A 031 esta reservada ao #1097 (entrega 2); as mudancas entram pelo nome, entao a ordem nao importa.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

CREATE TABLE atendimento.clientes_consultores (
    wa_id        text PRIMARY KEY CONSTRAINT clientes_consultores_wa CHECK (wa_id ~ '^55[1-9][0-9]9?[0-9]{8}$'),
    comercial_id integer NOT NULL,                       -- o cadastro comercial no ERP (o responsavel)
    nome         text NOT NULL,
    ativo        boolean NOT NULL DEFAULT true,
    criado_em    timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE atendimento.clientes_consultores IS
    'Quem esta no piloto do "Meus clientes" (#1090 etapa 3): o numero e o cadastro comercial no ERP.';

-- A fila do consultor como o ERP a calculou (ordem do Relacionamento), com a ficha de cada cliente.
CREATE TABLE atendimento.clientes_fila (
    comercial_id integer NOT NULL,
    codigo       integer NOT NULL,                       -- o cliente no ERP (stakeholder)
    posicao      integer NOT NULL,
    ficha        jsonb NOT NULL,
    copiada_em   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (comercial_id, codigo)
);

CREATE TABLE atendimento.clientes_motivos (
    id         integer PRIMARY KEY,                      -- o id do motivo no ERP
    nome       text NOT NULL,
    pede_texto boolean NOT NULL DEFAULT false
);

-- Um registro = um cliente oferecido ao consultor. O estado anda:
--   aberto -> (le e pergunta) -> conferir -> confirmado -> gravado | recusado (volta a aberto)
--   aberto|conferir -> depois (o cliente volta amanha) | descartado (parou por hoje)
CREATE TABLE atendimento.clientes_registros (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wa_id          text NOT NULL,                        -- o consultor (clientes_consultores)
    para           text NOT NULL,                        -- o numero como a Meta o mandou: e por ele que se responde
    comercial_id   integer NOT NULL,
    codigo         integer NOT NULL,
    ficha          jsonb NOT NULL,
    estado         text NOT NULL DEFAULT 'aberto' CONSTRAINT clientes_registros_estado
                   CHECK (estado IN ('aberto', 'conferir', 'confirmado', 'gravado', 'recusado', 'depois', 'descartado')),
    textos         text NOT NULL DEFAULT '',             -- o que ele escreveu, junto
    ultimo_texto_em timestamptz,
    lido           boolean NOT NULL DEFAULT true,        -- false = chegou texto que a IA ainda nao leu
    proposta       jsonb NOT NULL DEFAULT '{}'::jsonb,   -- o registro montado (os campos da tela do ERP)
    pergunta       text,                                 -- o campo que falta e foi perguntado
    erro           text,                                 -- a frase do ERP, quando recusou
    erp_id         integer,
    avisado        boolean NOT NULL DEFAULT false,       -- gravado/recusado ja foi dito a ele
    criado_em      timestamptz NOT NULL DEFAULT now(),
    confirmado_em  timestamptz,
    gravado_em     timestamptz
);
CREATE INDEX clientes_registros_wa ON atendimento.clientes_registros (wa_id, criado_em DESC);
CREATE INDEX clientes_registros_estado ON atendimento.clientes_registros (estado) WHERE estado IN ('confirmado', 'gravado', 'recusado');

-- A opcao no menu da casa. So quem esta em clientes_consultores a ve (motor.mostrar_menu_interno).
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_acao;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_acao
    CHECK (acao IN ('menu', 'destino', 'encerrar', 'texto', 'menu_cliente', 'vaga', 'clientes'));

INSERT INTO atendimento.menu (pai_id, chave, rotulo, descricao, pergunta, acao, texto_antes, ordem)
SELECT id, 'interna.clientes', '📋 Meus clientes', 'Um cliente da sua fila por vez; você conta como foi', '',
       'clientes', '', 3
  FROM atendimento.menu WHERE chave = 'raiz_interna';

INSERT INTO atendimento.ajustes (chave, valor) VALUES ('clientes.ligado', 'true'::jsonb)
    ON CONFLICT (chave) DO NOTHING;

-- O piloto: o dono (MAICON GREGORY, comercial 42 no ERP), pela linha dele em Destinos. Se nao houver
-- exatamente uma, nada entra -- e o passo vira da mao (INSERT com o numero dele).
INSERT INTO atendimento.clientes_consultores (wa_id, comercial_id, nome)
SELECT d.whatsapp, 42, d.nome
  FROM atendimento.destinos d
 WHERE d.ativo AND d.nome ILIKE 'maicon%'
   AND (SELECT count(*) FROM atendimento.destinos WHERE ativo AND nome ILIKE 'maicon%') = 1;
