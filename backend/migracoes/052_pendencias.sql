-- #1222 -- o molde de PENDENCIA: um assunto aberto com uma pessoa, e as mensagens dele (as que saem e as
-- que voltam). O chamado e o primeiro tipo; a triagem de curriculo, o cliente aberto e a pergunta de
-- foto entram depois como tipos novos, sem tabela nova (comentario #10540 do #1222).
-- Spec: docs/specs/2026-10-31-o-chamado-no-whatsapp.md. Sem BEGIN nem COMMIT: a transacao e de
-- backend/migracoes.py.
--
-- O VINCULO RESPOSTA x PENDENCIA e o `wamid`: a mensagem que sai guarda o id da Meta, e a resposta
-- citada traz esse id (`Entrada.contexto`). Uma mensagem pode levar blocos de varios chamados (a
-- juncao de 10 min), por isso o `wamid` NAO e unico aqui.
--
-- QUEM ESCREVE: as TELAS (a puxada do ERP: as mensagens que saem, e a entrega ao ERP das que voltam)
-- e o RECEPCIONISTA (o envio pela Meta e a leitura da resposta). Nenhum dos dois chama o outro: a
-- tabela e a fila entre eles, como `atendimento.avisos`.

CREATE TABLE atendimento.pendencias (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo            text NOT NULL CONSTRAINT pendencias_tipo CHECK (tipo IN ('chamado')),
    referencia      text NOT NULL,                       -- o numero do chamado
    titulo          text NOT NULL DEFAULT '',
    para_whatsapp   text NOT NULL,
    -- o que se espera da pessoa; nulo = nada (so informativo). E o que a OlivIA lista.
    espera          text CONSTRAINT pendencias_espera CHECK (espera IN ('resposta', 'validacao')),
    espera_desde    timestamptz,
    espera_evento   integer,                             -- o evento do ERP que pediu (pergunta/entrega)
    aguardando_motivo boolean NOT NULL DEFAULT false,    -- tocou "Nao ficou bom": o proximo texto e o motivo
    avisou_informativo boolean NOT NULL DEFAULT false,   -- a linha "e so um aviso" ja saiu uma vez
    aberta_em       timestamptz NOT NULL DEFAULT now(),
    ultima_em       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pendencias_uma_por_assunto UNIQUE (tipo, referencia, para_whatsapp)
);

CREATE TABLE atendimento.pendencias_mensagens (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pendencia_id    bigint NOT NULL REFERENCES atendimento.pendencias (id),
    sentido         text NOT NULL CONSTRAINT pend_msg_sentido CHECK (sentido IN ('saiu', 'entrou')),
    classe          text NOT NULL CONSTRAINT pend_msg_classe
                    CHECK (classe IN ('informativo', 'pergunta', 'entrega', 'resposta', 'validacao')),
    texto           text NOT NULL,
    resultado       text CONSTRAINT pend_msg_resultado CHECK (resultado IN ('entregue', 'nao_ficou_bom')),
    origem_evento_id integer CONSTRAINT pend_msg_origem_unica UNIQUE,   -- o evento do ERP (so as que saem)
    wamid           text,
    -- saiu:   esperando -> (guardada, fora da janela) -> enviada
    -- entrou: escolher (a pessoa ainda confirma de qual chamado) -> a_entregar -> entregue | erro
    --         descartada (resposta a um informativo, ou "Outro assunto")
    estado          text NOT NULL CONSTRAINT pend_msg_estado
                    CHECK (estado IN ('esperando', 'guardada', 'enviada', 'escolher', 'a_entregar',
                                      'entregue', 'descartada', 'erro')),
    criado_em       timestamptz NOT NULL DEFAULT now(),
    enviada_em      timestamptz,
    entregue_em     timestamptz,
    erro            text NOT NULL DEFAULT ''
);
CREATE INDEX pend_msg_wamid ON atendimento.pendencias_mensagens (wamid) WHERE wamid IS NOT NULL;
CREATE INDEX pend_msg_estado ON atendimento.pendencias_mensagens (estado)
    WHERE estado IN ('esperando', 'guardada', 'escolher', 'a_entregar');

-- nasce DESLIGADO: liga depois da prova com um numero da casa (spec, Impacto em producao)
INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('pendencias.ligado', 'false'::jsonb),
    ('pendencias.juntar_minutos', '10'::jsonb)
ON CONFLICT (chave) DO NOTHING;

DO $$
BEGIN
    IF to_regclass('atendimento.pendencias_mensagens') IS NULL
       OR NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'pendencias.ligado') THEN
        RAISE EXCEPTION '052: o molde de pendencia nao nasceu.';
    END IF;
    RAISE NOTICE '052 OK: o molde de pendencia (chamado no WhatsApp), desligado';
END $$;
