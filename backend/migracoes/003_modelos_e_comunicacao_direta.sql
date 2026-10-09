-- #950, E1b (emenda do dono, 09/10/2026): os modelos da Meta como CADASTRO, os dois tipos de
-- envio (material por convite; comunicacao direta com o botao do responsavel, so para quem ja
-- aceitou) e as imagens por cliente (a versao de cada revenda).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- Um modelo aprovado na Meta, descrito para o sistema montar a mensagem sem codigo novo.
-- `variaveis`: o que vai em {{1}}, {{2}}..., na ordem, de uma lista FECHADA de fontes:
--   primeiro_nome, nome            o cliente
--   assunto, peca, n_imagens       o envio
--   responsavel                    quem atende aquele cliente (canal comercial do cadastro)
--   aviso1, aviso2, aviso3         as tres partes de um aviso interno
-- `botao`: nenhum | quero_nao_quero (o convite) | link_responsavel (o botao de link do modelo
-- termina em {{1}}, e o sistema poe ali o WhatsApp do responsavel: https://wa.me/<numero>).
CREATE TABLE atendimento.modelos (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome        text NOT NULL CONSTRAINT modelos_nome_unico UNIQUE
                CONSTRAINT modelos_nome_formato CHECK (nome ~ '^[a-z0-9_]+$'),
    categoria   text NOT NULL CONSTRAINT modelos_categoria CHECK (categoria IN ('MARKETING', 'UTILITY')),
    idioma      text NOT NULL DEFAULT 'pt_BR',
    uso         text NOT NULL CONSTRAINT modelos_uso
                CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento')),
    cabecalho_imagem boolean NOT NULL DEFAULT false,
    variaveis   text[] NOT NULL DEFAULT '{}' CONSTRAINT modelos_variaveis CHECK (variaveis <@ ARRAY[
                    'primeiro_nome', 'nome', 'assunto', 'peca', 'n_imagens', 'responsavel',
                    'aviso1', 'aviso2', 'aviso3']::text[]),
    botao       text NOT NULL DEFAULT 'nenhum' CONSTRAINT modelos_botao
                CHECK (botao IN ('nenhum', 'quero_nao_quero', 'link_responsavel')),
    texto       text NOT NULL DEFAULT '',     -- o corpo como foi aprovado, para a tela mostrar
    ativo       boolean NOT NULL DEFAULT true,
    criado_em   timestamptz NOT NULL DEFAULT now(),
    -- a Meta cobra a categoria declarada: convite e direta sao Marketing; aviso e Utilidade
    CONSTRAINT modelos_categoria_do_uso CHECK (
        (uso IN ('convite', 'direta') AND categoria = 'MARKETING')
        OR (uso LIKE 'aviso%' AND categoria IN ('UTILITY', 'MARKETING'))),
    CONSTRAINT modelos_botao_do_uso CHECK (
        (uso = 'convite' AND botao = 'quero_nao_quero')
        OR (uso = 'direta' AND botao = 'link_responsavel')
        OR (uso LIKE 'aviso%' AND botao = 'nenhum'))
);

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('pecas_da_revenda', 'MARKETING', 'convite', true, ARRAY['primeiro_nome', 'n_imagens'], 'quero_nao_quero',
     'Olá, {{1}}! A Sementes Renascer preparou {{2}} peças com a marca da sua loja, prontas para o Instagram e o status. Toque em "Quero receber" e mandamos as imagens aqui na conversa.'),
    ('epoca_de_plantio', 'MARKETING', 'direta', true, ARRAY['primeiro_nome', 'assunto', 'responsavel'], 'link_responsavel',
     '{{1}}, chegou a época de {{2}}. Para garantir a sua semente, fale com {{3}} pelo botão abaixo.'),
    ('aviso_recusa', 'UTILITY', 'aviso_recusa', false, ARRAY['aviso1', 'aviso2', 'aviso3'], 'nenhum',
     'Aviso da sua carteira: o cliente {{1}} ({{2}}) pediu para não receber as peças. Vale um contato direto: {{3}}. Obrigado.'),
    ('aviso_sem_atendimento', 'UTILITY', 'aviso_sem_atendimento', false, ARRAY['aviso1', 'aviso2', 'aviso3'], 'nenhum',
     'Aviso do atendimento: {{1}} disse que ainda não recebeu retorno sobre {{2}}. Contato: {{3}}. Obrigado.');

-- os dois tipos de envio
ALTER TABLE atendimento.envios
    ADD COLUMN tipo text NOT NULL DEFAULT 'material' CONSTRAINT envios_tipo CHECK (tipo IN ('material', 'direta')),
    ADD COLUMN assunto text NOT NULL DEFAULT '';

-- a versao de cada cliente (a peca da revenda com a logo dela); nulo = as do envio
ALTER TABLE atendimento.envio_destinatarios
    ADD COLUMN capa text,
    ADD COLUMN imagens jsonb,
    ADD COLUMN aceite_cadastro boolean NOT NULL DEFAULT false;   -- o aceite de marketing do #952

-- 'sem_aceite': a comunicacao direta nao vai a quem nunca aceitou
ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_situacao;
ALTER TABLE atendimento.envio_destinatarios ADD CONSTRAINT envio_dest_situacao
    CHECK (situacao IN ('aguardando', 'sem_responsavel', 'sem_whatsapp', 'sem_aceite', 'recusou_antes',
                        'ja_recebeu', 'convidado', 'falhou', 'nao_e_whatsapp'));
