-- #970 -- o canal de campo (spec C:\AxiaMarketing\docs\specs\2026-10-10-canal-de-campo-no-whatsapp.md,
-- etapa A). A foto ou o video que um colaborador ou representante do cadastro manda ao WhatsApp da
-- Renascer fica guardado aqui, com a legenda, a data dita, as perguntas feitas e o que o marketing
-- devolveu (buscado, catalogado, foi ao ar) e os avisos a quem mandou. Sem BEGIN nem COMMIT: a
-- transacao e de backend/migracoes.py.

CREATE TABLE atendimento.material_de_campo (
    id                     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bsuid                  text,
    wa_id                  text NOT NULL,
    erp_codigo             integer,
    erp_papel              text NOT NULL,              -- equipe | representante (o que casou)
    erp_nome               text NOT NULL DEFAULT '',
    wamid                  text NOT NULL UNIQUE,       -- a mensagem da Meta com a midia
    tipo                   text NOT NULL CONSTRAINT material_tipo CHECK (tipo IN ('foto', 'video')),
    mime                   text NOT NULL DEFAULT '',
    arquivo                text,                       -- relativo a pasta `campo` (NULL: nao baixou)
    legenda                text NOT NULL DEFAULT '',   -- a que veio na mensagem, ou a resposta
    legenda_perguntada_em  timestamptz,
    data_dita              date,                       -- "e de hoje?" Sim = o dia do envio; Outra data = o que disse
    data_presumida         boolean NOT NULL DEFAULT false,  -- nao respondeu: vale o dia do envio, marcado
    data_perguntada_em     timestamptz,
    pergunta_pendente      text CONSTRAINT material_pergunta CHECK (pergunta_pendente IN ('legenda', 'data', 'qual_dia')),
    recebido_em            timestamptz NOT NULL,
    buscado_em             timestamptz,                -- o marketing levou
    lote                   text,                       -- o lote na Caixa do marketing
    catalogado_em          timestamptz,
    atv                    text,
    foi_ao_ar_em           timestamptz,
    peca                   text,
    aviso_catalogo         text CONSTRAINT material_aviso_catalogo CHECK (aviso_catalogo IN ('enviado', 'fora_da_janela')),
    aviso_catalogo_em      timestamptz,
    aviso_ar               text CONSTRAINT material_aviso_ar CHECK (aviso_ar IN ('enviado', 'fora_da_janela')),
    aviso_ar_em            timestamptz,
    erro                   text NOT NULL DEFAULT ''
);

CREATE INDEX material_de_campo_pendentes ON atendimento.material_de_campo (buscado_em) WHERE buscado_em IS NULL;
CREATE INDEX material_de_campo_wa_id ON atendimento.material_de_campo (wa_id, recebido_em DESC);

-- A chave do canal (decisao 8 do dono): nasce DESLIGADA; liga-se no primeiro caso, com ele.
INSERT INTO atendimento.ajustes (chave, valor) VALUES ('campo.ligado', 'false'::jsonb)
ON CONFLICT (chave) DO NOTHING;
