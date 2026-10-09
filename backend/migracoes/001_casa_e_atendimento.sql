-- #950 -- a casa do atendimento: login, o menu da OlivIA, as conversas, o envio a carteira e o
-- consentimento. Spec: C:\AxiaMarketing\docs\specs\2026-10-09-axiaatende-recepcionista-e-envio.md
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

CREATE SCHEMA IF NOT EXISTS casa;
CREATE SCHEMA atendimento;

COMMENT ON SCHEMA casa IS 'usuarios, login e o registro das mudancas aplicadas';
COMMENT ON SCHEMA atendimento IS 'o menu, as conversas, o que entrou e saiu pela Meta, o envio e o consentimento';

-- ── casa (molde: AxiaMarketing 001) ─────────────────────────────────────────

CREATE TABLE casa.usuarios (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    login       text NOT NULL,
    nome        text NOT NULL,
    senha_hash  text NOT NULL,
    ativo       boolean NOT NULL DEFAULT true,
    criado_em   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT usuarios_login_minusculo CHECK (login = lower(login)),
    CONSTRAINT usuarios_login_unico UNIQUE (login)
);

-- A sessao guarda o sha256 do token, nunca o token: quem le a tabela nao entra por ninguem.
CREATE TABLE casa.sessoes (
    token_sha256 text PRIMARY KEY,
    usuario_id   integer NOT NULL REFERENCES casa.usuarios (id),
    criada_em    timestamptz NOT NULL DEFAULT now(),
    expira_em    timestamptz NOT NULL
);
CREATE INDEX sessoes_usuario ON casa.sessoes (usuario_id);

-- ── o menu: destinos e a arvore de perguntas ────────────────────────────────

-- Quem atende. O WhatsApp e so digitos, com 55 (vai no link wa.me). A tela Destinos edita.
CREATE TABLE atendimento.destinos (
    id            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome          text NOT NULL CONSTRAINT destinos_nome CHECK (btrim(nome) <> ''),
    whatsapp      text NOT NULL CONSTRAINT destinos_whatsapp CHECK (whatsapp ~ '^55[1-9][0-9]9?[0-9]{8}$'),
    ativo         boolean NOT NULL DEFAULT true,
    atualizado_em timestamptz NOT NULL DEFAULT now(),
    atualizado_por integer REFERENCES casa.usuarios (id)
);

-- A arvore do menu. Um no e uma opcao que a pessoa toca. Ou ele abre outra pergunta (acao
-- 'menu', com filhos), ou manda o link de alguem (acao 'destino'), ou encerra.
-- Ate 3 filhos o WhatsApp mostra botoes; mais de 3, lista (decisao do dono, 09/10/2026).
CREATE TABLE atendimento.menu (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pai_id      integer REFERENCES atendimento.menu (id),
    chave       text NOT NULL CONSTRAINT menu_chave_unica UNIQUE
                CONSTRAINT menu_chave_formato CHECK (chave ~ '^[a-z0-9_.]+$'),
    -- 20 e o limite do titulo de botao no WhatsApp (o da linha de lista e 24): o menor dos dois
    rotulo      text NOT NULL CONSTRAINT menu_rotulo CHECK (char_length(rotulo) BETWEEN 1 AND 20),
    descricao   text NOT NULL DEFAULT '' CONSTRAINT menu_descricao CHECK (char_length(descricao) <= 72),
    pergunta    text NOT NULL DEFAULT '',      -- o que se pergunta ao abrir os filhos
    acao        text NOT NULL CONSTRAINT menu_acao CHECK (acao IN ('menu', 'destino', 'encerrar')),
    destino_id  integer REFERENCES atendimento.destinos (id),
    texto_antes text NOT NULL DEFAULT '',      -- vai antes do link (ex.: o link da Fretebras)
    ordem       integer NOT NULL DEFAULT 0,
    ativo       boolean NOT NULL DEFAULT true,
    CONSTRAINT menu_destino_so_na_folha CHECK ((acao = 'destino') = (destino_id IS NOT NULL)),
    CONSTRAINT menu_pergunta_so_no_menu CHECK (acao = 'menu' OR pergunta = '')
);
CREATE INDEX menu_pai ON atendimento.menu (pai_id, ordem);

-- Textos e regras que o dono ajusta sem codigo: boas-vindas, horario, quem e avisado no "Nao".
CREATE TABLE atendimento.ajustes (
    chave  text PRIMARY KEY,
    valor  jsonb NOT NULL,
    atualizado_em timestamptz NOT NULL DEFAULT now()
);

-- ── o que entra e sai pela Meta ─────────────────────────────────────────────

-- Todo aviso recebido, cru, pela chave da Meta. A Meta reenvia por ate 7 dias: o UNIQUE e o que
-- impede responder duas vezes a mesma mensagem.
CREATE TABLE atendimento.eventos_meta (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave_meta   text NOT NULL CONSTRAINT eventos_meta_chave_unica UNIQUE,  -- wamid, ou wamid:status
    tipo         text NOT NULL CONSTRAINT eventos_meta_tipo CHECK (tipo IN ('mensagem', 'status', 'outro')),
    bsuid        text,
    recebido_em  timestamptz NOT NULL DEFAULT now(),
    corpo        jsonb NOT NULL,
    processado_em timestamptz,
    erro         text NOT NULL DEFAULT ''
);
CREATE INDEX eventos_meta_pendentes ON atendimento.eventos_meta (recebido_em) WHERE processado_em IS NULL;

-- A conversa de uma pessoa com a OlivIA. A chave da pessoa e o BSUID (`user_id` da Meta, A3 do
-- plano): quem usa nome de usuario pode chegar sem numero.
CREATE TABLE atendimento.conversas (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bsuid           text NOT NULL,
    wa_id           text,                       -- o numero, quando a Meta manda
    nome_perfil     text NOT NULL DEFAULT '',
    erp_codigo      integer,                    -- quando o numero casa com um cliente conhecido
    iniciada_em     timestamptz NOT NULL DEFAULT now(),
    ultimo_toque_em timestamptz NOT NULL DEFAULT now(),
    no_atual_id     integer REFERENCES atendimento.menu (id),
    caminho         text[] NOT NULL DEFAULT '{}',      -- os rotulos tocados, na ordem
    destino_id      integer REFERENCES atendimento.destinos (id),
    link_em         timestamptz,
    situacao        text NOT NULL DEFAULT 'em_curso' CONSTRAINT conversas_situacao
                    CHECK (situacao IN ('em_curso', 'com_link', 'parou_no_meio', 'encerrada', 'envio')),
    -- a IA para quem escreve: o que ela propos e se a pessoa confirmou (Sim = acerto)
    ia_proposta_id  integer REFERENCES atendimento.menu (id),
    ia_confirmou    boolean,
    -- a pergunta das 4h30 ("recebeu o atendimento?")
    pergunta_em     timestamptz,
    pergunta_feita_em timestamptz,
    recebeu         boolean,
    satisfacao      smallint CONSTRAINT conversas_satisfacao CHECK (satisfacao BETWEEN 1 AND 5),
    aviso_nao_em    timestamptz
);
CREATE INDEX conversas_pessoa ON atendimento.conversas (bsuid, iniciada_em DESC);
CREATE INDEX conversas_pergunta ON atendimento.conversas (pergunta_em) WHERE pergunta_feita_em IS NULL;
-- uma conversa aberta por pessoa
CREATE UNIQUE INDEX conversas_uma_aberta ON atendimento.conversas (bsuid) WHERE situacao = 'em_curso';

-- Tudo o que sai, com o id que a Meta devolve; os status (entregue, lida, falhou) chegam depois.
CREATE TABLE atendimento.enviadas (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wamid       text CONSTRAINT enviadas_wamid_unico UNIQUE,   -- nulo quando a Meta recusou na hora
    conversa_id bigint REFERENCES atendimento.conversas (id),
    para        text NOT NULL,                  -- wa_id ou bsuid
    tipo        text NOT NULL CONSTRAINT enviadas_tipo
                CHECK (tipo IN ('texto', 'botoes', 'lista', 'imagem', 'modelo')),
    resumo      text NOT NULL DEFAULT '',
    enviada_em  timestamptz NOT NULL DEFAULT now(),
    status      text NOT NULL DEFAULT 'aceita' CONSTRAINT enviadas_status
                CHECK (status IN ('aceita', 'enviada', 'entregue', 'lida', 'falhou')),
    status_em   timestamptz,
    erro        text NOT NULL DEFAULT ''
);

-- ── o envio a carteira ──────────────────────────────────────────────────────

-- Um pedido do AxiaMarketing, aprovado pelo dono la (trava D7 do #923).
CREATE TABLE atendimento.envios (
    id           integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pedido_ref   text NOT NULL CONSTRAINT envios_pedido_unico UNIQUE,  -- a publicacao do Marketing
    campanha     text NOT NULL,
    peca         text NOT NULL,
    modelo       text NOT NULL,                 -- o modelo da Meta (ex.: pecas_da_revenda)
    capa         text NOT NULL,                 -- a imagem do cabecalho do convite
    imagens      jsonb NOT NULL,                -- as que vao depois do "Quero receber"
    aprovado_por text NOT NULL,
    aprovado_em  timestamptz NOT NULL,
    recebido_em  timestamptz NOT NULL DEFAULT now(),
    lote_tamanho integer NOT NULL DEFAULT 20 CONSTRAINT envios_lote CHECK (lote_tamanho BETWEEN 1 AND 20),
    situacao     text NOT NULL DEFAULT 'ativo' CONSTRAINT envios_situacao
                 CHECK (situacao IN ('ativo', 'parado_nota', 'concluido', 'suspenso'))
);

-- Cada cliente do pedido, na ordem de faturamento (Top 20, Top 50, Top 100: dono, 09/10/2026).
CREATE TABLE atendimento.envio_destinatarios (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    envio_id         integer NOT NULL REFERENCES atendimento.envios (id),
    erp_codigo       integer NOT NULL,
    nome             text NOT NULL,
    cidade           text NOT NULL DEFAULT '',
    uf               text NOT NULL DEFAULT '',
    whatsapp         text NOT NULL DEFAULT '',  -- so digitos, com 55; vazio = sem celular valido
    faturamento      numeric NOT NULL DEFAULT 0,
    posicao          integer NOT NULL,          -- 1 = o maior faturamento
    -- o responsavel vem do canal comercial do cadastro no ERP (#952); vazio = nao envia
    responsavel_nome text NOT NULL DEFAULT '',
    responsavel_whatsapp text NOT NULL DEFAULT '',
    sugestao_vendedor text NOT NULL DEFAULT '', -- o vendedor do ultimo pedido, so como sugestao
    situacao         text NOT NULL DEFAULT 'aguardando' CONSTRAINT envio_dest_situacao
                     CHECK (situacao IN ('aguardando', 'sem_responsavel', 'sem_whatsapp', 'recusou_antes',
                                         'ja_recebeu', 'convidado', 'falhou', 'nao_e_whatsapp')),
    lote             integer,
    convite_wamid    text,
    convite_em       timestamptz,
    entregue_em      timestamptz,
    lido_em          timestamptz,
    resposta         text CONSTRAINT envio_dest_resposta CHECK (resposta IN ('quero', 'nao_quero', 'texto')),
    resposta_texto   text NOT NULL DEFAULT '',
    resposta_em      timestamptz,
    imagens_enviadas integer NOT NULL DEFAULT 0,
    imagens_total    integer NOT NULL DEFAULT 0,
    aviso_recusa_em  timestamptz,
    erro             text NOT NULL DEFAULT '',
    CONSTRAINT envio_dest_um_por_cliente UNIQUE (envio_id, erp_codigo)
);
CREATE INDEX envio_dest_fila ON atendimento.envio_destinatarios (envio_id, situacao, posicao);
CREATE INDEX envio_dest_wamid ON atendimento.envio_destinatarios (convite_wamid);

-- A leitura da nota de qualidade do numero, uma por dia: o proximo lote so sai com GREEN.
CREATE TABLE atendimento.nota_qualidade (
    lida_em  timestamptz PRIMARY KEY DEFAULT now(),
    nota     text NOT NULL CONSTRAINT nota_valor CHECK (nota IN ('GREEN', 'YELLOW', 'RED', 'UNKNOWN'))
);

-- ── consentimento: NUNCA SE APAGA ───────────────────────────────────────────

-- O toque em "Quero receber" (aceite) ou "Nao quero receber" (recusa), com a prova da Meta.
-- E a prova do consentimento: nem rollback a apaga (regra 4 do CLAUDE.md).
CREATE TABLE atendimento.consentimentos (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    whatsapp   text NOT NULL,
    bsuid      text NOT NULL DEFAULT '',
    erp_codigo integer,
    tipo       text NOT NULL CONSTRAINT consentimentos_tipo CHECK (tipo IN ('aceite', 'recusa')),
    em         timestamptz NOT NULL DEFAULT now(),
    wamid      text NOT NULL,                   -- a mensagem do toque
    envio_id   integer REFERENCES atendimento.envios (id)
);
CREATE INDEX consentimentos_numero ON atendimento.consentimentos (whatsapp, em DESC);

CREATE FUNCTION atendimento.consentimento_imutavel() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'consentimento nao se altera nem se apaga (#950, regra 4)';
END $$;
CREATE TRIGGER consentimentos_imutaveis BEFORE UPDATE OR DELETE ON atendimento.consentimentos
    FOR EACH ROW EXECUTE FUNCTION atendimento.consentimento_imutavel();
CREATE TRIGGER consentimentos_sem_truncate BEFORE TRUNCATE ON atendimento.consentimentos
    FOR EACH STATEMENT EXECUTE FUNCTION atendimento.consentimento_imutavel();

-- ── avisos internos (Utilidade) ─────────────────────────────────────────────

CREATE TABLE atendimento.avisos (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo        text NOT NULL CONSTRAINT avisos_tipo CHECK (tipo IN ('recusa', 'sem_atendimento')),
    para_nome   text NOT NULL,
    para_whatsapp text NOT NULL,
    sobre       text NOT NULL,                  -- o que o aviso diz, em uma linha
    criado_em   timestamptz NOT NULL DEFAULT now(),
    enviado_em  timestamptz,
    wamid       text,
    erro        text NOT NULL DEFAULT ''
);
