-- #1238 -- o ROTEADOR com contexto por contato (a OlivIA escolhe o assunto do texto de quem e da casa) e a
-- TRANSCRICAO LOCAL de audio de interno. Spec e plano: docs/specs/2026-11-03-roteador-com-contexto-por-contato*.md.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py. Nenhuma linha existente muda; as chaves
-- nascem DESLIGADAS.

-- O registro de decisao: uma linha por texto que passou pelo roteador. So o roteador escreve aqui.
-- `candidatos` = os assuntos oferecidos a OlivIA (na ordem numerada do retrato); `desfazer` = o estado do
-- fio ANTES de o texto entrar nele, para a correcao escrita voltar atras sem adivinhar.
CREATE TABLE atendimento.roteador (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wamid           text NOT NULL CONSTRAINT roteador_um_por_mensagem UNIQUE,
    wa_id           text NOT NULL,
    texto           text NOT NULL DEFAULT '',          -- guardado ate o toque, na duvida
    candidatos      jsonb NOT NULL DEFAULT '[]'::jsonb,
    destino         text,                              -- 'chamado:12', 'foto:340', ... ou nulo (nenhum)
    destino_certo   text,                              -- so na correcao
    sinal           text NOT NULL DEFAULT 'nenhum' CONSTRAINT roteador_sinal
                    CHECK (sinal IN ('citacao', 'nomeado', 'proximidade', 'botao', 'correcao', 'nenhum')),
    confianca       text CONSTRAINT roteador_confianca CHECK (confianca IN ('alta', 'baixa')),
    aplicado        boolean NOT NULL DEFAULT false,
    desfazer        jsonb,
    corrigido_em    timestamptz,
    corrigido_para  text,
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX roteador_pessoa ON atendimento.roteador (wa_id, criado_em DESC);

-- O audio de interno: baixado pelo recepcionista, transcrito na maquina (faster-whisper), e o texto entra
-- na corrente por um evento sintetico em `eventos_meta`. O arquivo some 7 dias depois (`apagado_em`).
CREATE TABLE atendimento.audios (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wamid           text NOT NULL CONSTRAINT audios_um_por_mensagem UNIQUE,
    wa_id           text,
    bsuid           text,
    arquivo         text,                              -- relativo a campo_pasta
    mime            text NOT NULL DEFAULT '',
    duracao_s       numeric(8, 1),
    recebido_em     timestamptz NOT NULL DEFAULT now(),
    transcrito_em   timestamptz,
    texto           text,
    erro            text NOT NULL DEFAULT '',
    apagado_em      timestamptz
);
CREATE INDEX audios_a_transcrever ON atendimento.audios (id)
    WHERE transcrito_em IS NULL AND erro = '' AND arquivo IS NOT NULL;

-- A carencia da correcao escrita: a resposta encaminhada pelo roteador a um chamado so vai ao ERP
-- depois desta hora. Nula = na hora (tudo o que ja existe, e o que veio por citacao ou botao).
ALTER TABLE atendimento.pendencias_mensagens ADD COLUMN entregar_apos timestamptz;

-- O transcritor e local: custo zero, e a tela Custos mostra a duracao transcrita. As duas reguas de
-- servico ganham 'local'.
ALTER TABLE atendimento.uso_ia DROP CONSTRAINT uso_ia_servico;
ALTER TABLE atendimento.uso_ia ADD CONSTRAINT uso_ia_servico CHECK (servico IN ('claude', 'gemini', 'local'));
ALTER TABLE atendimento.precos DROP CONSTRAINT precos_servico;
ALTER TABLE atendimento.precos ADD CONSTRAINT precos_servico CHECK (servico IN ('meta', 'claude', 'gemini', 'local'));
INSERT INTO atendimento.precos (servico, item, vale_desde, por_milhao_entrada, por_milhao_saida)
VALUES ('local', 'faster-whisper-large-v3-turbo', '2026-11-03', 0, 0);

-- nascem DESLIGADAS: liga o dono, depois do ensaio (plano, passo 17)
INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('roteador.ligado', 'false'::jsonb),
    ('roteador.carencia_minutos', '3'::jsonb),
    ('audio.transcrever', 'false'::jsonb),
    ('audio.maximo_s', '180'::jsonb)
ON CONFLICT (chave) DO NOTHING;

DO $$
BEGIN
    IF to_regclass('atendimento.roteador') IS NULL OR to_regclass('atendimento.audios') IS NULL
       OR NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'roteador.ligado')
       OR NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'audio.transcrever') THEN
        RAISE EXCEPTION '054: o roteador e o audio nao nasceram.';
    END IF;
    RAISE NOTICE '054 OK: roteador e audio, desligados';
END $$;
