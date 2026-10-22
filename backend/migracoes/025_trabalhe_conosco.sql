-- #1098 (dono, 22/10/2026): o TRABALHE CONOSCO ganha atendimento proprio. Quem chega pelo anuncio da
-- Vaga Comercial (Marketing, 20/10) cai direto na vaga, ve os requisitos, tira as duvidas com textos
-- aprovados e manda o curriculo, so em PDF. Cada curriculo vai sozinho ao WhatsApp da Fran com a
-- pre-triagem da IA; a decisao e dela, e ela diz se a triagem acertou.
-- Spec: docs/specs/2026-10-22-trabalhe-conosco-vaga-e-pre-triagem.md (caminho B).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- A vaga e CADASTRO, uma linha por vaga. `anuncio_ids` sao os `referral.source_id` da Meta: quem
-- chega por um deles, com a vaga aberta, nao ve o menu. `triagem_ligada` e o interruptor da spec.
CREATE TABLE atendimento.vagas (
    id             integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    titulo         text NOT NULL,
    requisitos     text[] NOT NULL DEFAULT '{}',
    regiao         text NOT NULL DEFAULT '',
    beneficios     text NOT NULL DEFAULT '',
    anuncio_ids    text[] NOT NULL DEFAULT '{}',
    aberta         boolean NOT NULL DEFAULT true,
    triagem_ligada boolean NOT NULL DEFAULT true,
    criada_em      timestamptz NOT NULL DEFAULT now(),
    fechada_em     timestamptz
);

INSERT INTO atendimento.vagas (titulo, requisitos, regiao, beneficios, anuncio_ids) VALUES
    ('Vaga Comercial',
     ARRAY['Formação em Agronomia, com pós-graduação',
           'Ao menos 2 anos de experiência com sementes',
           'Vivência na área comercial',
           'Morar em Maravilha (SC) ou cidade vizinha'],
     'A vaga é para quem mora em Maravilha (SC) ou numa cidade vizinha. O trabalho é na nossa unidade e em visitas comerciais e técnicas aos cooperantes multiplicadores de sementes da empresa, no RS, SC, PR, MS e GO.',
     'salário atrativo, plano de saúde Unimed, vale-alimentação, auxílio-combustível e auxílio-educação',
     ARRAY['120249624037810192']);

-- Os textos da conversa, aprovados pelo dono (maquete de 22/10 com o ajuste "so PDF"). `para_ia`:
-- as respostas entre as quais a IA escolhe (regra 3: ela so devolve a chave); as outras sao as
-- falas fixas da conversa, chamadas pelo motor. Marcadores: {saudacao} {vaga} {requisitos}
-- {regiao} {beneficios} {data}.
CREATE TABLE atendimento.respostas_da_vaga (
    chave     text PRIMARY KEY CONSTRAINT respostas_da_vaga_chave CHECK (chave ~ '^[a-z0-9_]+$'),
    descricao text NOT NULL DEFAULT '',
    texto     text NOT NULL,
    para_ia   boolean NOT NULL DEFAULT false,
    ordem     integer NOT NULL DEFAULT 0,
    ativo     boolean NOT NULL DEFAULT true
);

INSERT INTO atendimento.respostas_da_vaga (chave, descricao, texto, para_ia, ordem) VALUES
    ('abertura', '', E'{saudacao} Obrigado pelo interesse na *{vaga}* da Sementes Renascer 🌱\n\nO anúncio pede:\n{requisitos}\n\nVocê atende a esses requisitos?', false, 1),
    ('nao_atende', '', E'Obrigado pela sinceridade. Esta vaga pede os quatro requisitos.\n\nSe quiser, mande o seu currículo assim mesmo: ele fica guardado para as próximas vagas.', false, 2),
    ('pedir_pdf', '', E'Ótimo! Mande aqui o seu *currículo em PDF*.\n\nAo enviar, você autoriza a Renascer a guardar o currículo e a usar uma ferramenta de análise para a pré-triagem; a decisão é sempre de uma pessoa da equipe.', false, 3),
    ('recebido', '', E'Recebemos o seu currículo ✅\n\nEstamos fazendo uma *pré-triagem* dos candidatos. Os pré-selecionados recebem o nosso retorno por aqui, com mais informações sobre a vaga e as próximas etapas.\n\nObrigado por querer fazer parte do time!', false, 4),
    ('so_pdf', '', 'Precisamos do seu currículo em PDF. Mande o arquivo PDF aqui mesmo.', false, 5),
    ('sem_vaga', '', E'No momento não temos vaga aberta.\n\nSe quiser, mande o seu currículo em PDF: ele fica guardado para as próximas vagas.', false, 6),
    ('recebemos_nao', '', 'Ainda não chegou nenhum currículo seu. Pode mandar aqui mesmo, em PDF.', false, 7),
    ('regiao', 'pergunta para que região ou cidade é a vaga, onde vai trabalhar', '{regiao}', true, 10),
    ('recebemos', 'pergunta se o currículo dela chegou, se receberam', 'Recebemos, sim ✅ (em {data}). Os pré-selecionados recebem retorno por aqui.', true, 11),
    ('apresentacao', 'se apresenta por texto (formação, experiência) sem mandar arquivo', 'Anotei 👍 Falta só o currículo: mande o arquivo em PDF aqui mesmo.', true, 12),
    ('sem_pdf', 'diz que não tem currículo, não tem PDF, ou pergunta se pode mandar foto ou Word', 'Precisamos do seu currículo em PDF. Se ele estiver no Word, salve como PDF e mande aqui.', true, 13),
    ('salario', 'pergunta salário, remuneração ou benefícios', 'Oferecemos {beneficios}. Os valores são conversados com os pré-selecionados.', true, 14),
    ('retorno', 'pergunta quando vão dar retorno, prazo, próximas etapas', 'Estamos fazendo a pré-triagem de todos os currículos. Os pré-selecionados recebem retorno por aqui.', true, 15),
    ('pessoa', 'quer falar com uma pessoa, um humano, alguém da empresa', 'Pode falar com a {nome}, do nosso time:', true, 16),
    ('outro_assunto', 'o assunto não é a vaga (comprar semente, fornecedor, outro assunto)', '', true, 17);

-- A candidatura: um PDF recebido. O PDF fica NO BANCO (bytea) e nao em C:\Dados: so o banco tem
-- backup (R2, spec "Conformidade com a casa"). `apagar_em` = recebida + 12 meses (decisao 5 do
-- dono); vencido, a rotina apaga o PDF, o texto, a triagem, o nome e o numero, e ficam a vaga, as
-- datas, a situacao e o retorno da Fran.
CREATE TABLE atendimento.candidaturas (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vaga_id          integer REFERENCES atendimento.vagas (id),
    conversa_id      bigint REFERENCES atendimento.conversas (id),
    bsuid            text,
    wa_id            text,
    nome_perfil      text NOT NULL DEFAULT '',
    declarou         text CONSTRAINT candidaturas_declarou CHECK (declarou IN ('todos', 'nem_todos')),
    texto            text NOT NULL DEFAULT '',     -- o que a pessoa escreveu na conversa (vai a Fran)
    wamid            text CONSTRAINT candidaturas_wamid UNIQUE,   -- a Meta reenvia: o repetido nao entra
    pdf              bytea,
    pdf_nome         text NOT NULL DEFAULT '',
    pdf_sha256       text NOT NULL DEFAULT '',
    pdf_bytes        integer,
    recebida_em      timestamptz NOT NULL DEFAULT now(),
    triagem          jsonb,
    triagem_em       timestamptz,
    triagem_erro     text NOT NULL DEFAULT '',
    fran_para        text,                         -- o WhatsApp para onde foi (o destino do no, a Fran)
    fran_wamid       text,
    fran_em          timestamptz,
    fran_erro        text NOT NULL DEFAULT '',
    fran_tentativa_em timestamptz,
    feedback         text CONSTRAINT candidaturas_feedback CHECK (feedback IN ('certa', 'errada')),
    feedback_texto   text NOT NULL DEFAULT '',
    feedback_em      timestamptz,
    espera_comentario boolean NOT NULL DEFAULT false,
    apagar_em        timestamptz NOT NULL,
    apagada_em       timestamptz
);
CREATE INDEX candidaturas_a_enviar ON atendimento.candidaturas (id) WHERE fran_em IS NULL AND apagada_em IS NULL;
CREATE INDEX candidaturas_pessoa ON atendimento.candidaturas (bsuid, recebida_em DESC);

-- A conversa de vaga: marcada pela vaga. Ela termina como "Curriculo recebido" ou "Sem curriculo",
-- nunca "parou no meio" (os leitores de decisao -- marcar_paradas, retomar_paradas, a pergunta das
-- 4h30 -- nao leem estes dois valores, de proposito).
-- `trabalhe` marca a conversa (com ou sem vaga aberta: sem vaga, o curriculo fica para as proximas);
-- `vaga_declarou` guarda o botao "atendo todos / nao atendo todos" ate o PDF chegar.
ALTER TABLE atendimento.conversas ADD COLUMN trabalhe boolean NOT NULL DEFAULT false;
ALTER TABLE atendimento.conversas ADD COLUMN vaga_id integer REFERENCES atendimento.vagas (id);
ALTER TABLE atendimento.conversas ADD COLUMN vaga_declarou text
    CONSTRAINT conversas_vaga_declarou CHECK (vaga_declarou IN ('todos', 'nem_todos'));
ALTER TABLE atendimento.conversas DROP CONSTRAINT conversas_situacao;
ALTER TABLE atendimento.conversas ADD CONSTRAINT conversas_situacao
    CHECK (situacao IN ('em_curso', 'com_link', 'parou_no_meio', 'encerrada', 'envio',
                        'curriculo_recebido', 'sem_curriculo'));

-- O curriculo vai a Fran como documento (dentro da janela dela): um tipo a mais no registro do que sai.
ALTER TABLE atendimento.enviadas DROP CONSTRAINT enviadas_tipo;
ALTER TABLE atendimento.enviadas ADD CONSTRAINT enviadas_tipo
    CHECK (tipo IN ('texto', 'botoes', 'lista', 'imagem', 'modelo', 'documento'));

-- O no "Trabalhe conosco" passa a abrir a conversa da vaga. O destino (a Fran) FICA: e o "falar com
-- uma pessoa" da vaga, e a tela Destinos continua trocando-o.
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_acao;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_acao
    CHECK (acao IN ('menu', 'destino', 'encerrar', 'texto', 'menu_cliente', 'vaga'));
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_destino_so_na_folha;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_destino_so_na_folha
    CHECK ((acao IN ('destino', 'vaga')) = (destino_id IS NOT NULL));
UPDATE atendimento.menu SET acao = 'vaga' WHERE chave = 'trabalhe';

-- O modelo da Fran (Utilidade): o PDF no cabecalho, a triagem em variaveis de UMA linha (a Meta
-- recusa quebra de linha em variavel), "Triagem certa" / "Triagem errada" e o link para conversar
-- com o candidato (o NOSSO endereco /falar/v<id>: a Meta recusa wa.me direto em modelo).
ALTER TABLE atendimento.modelos ADD COLUMN cabecalho_documento boolean NOT NULL DEFAULT false;
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro', 'curriculo'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_categoria_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_categoria_do_uso CHECK (
    (uso IN ('convite', 'direta') AND categoria = 'MARKETING')
    OR ((uso LIKE 'aviso%' OR uso = 'curriculo') AND categoria IN ('UTILITY', 'MARKETING')));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao = 'falar_responsavel')
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_variaveis;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_variaveis CHECK (variaveis <@ ARRAY[
    'primeiro_nome', 'nome', 'assunto', 'peca', 'n_imagens', 'responsavel',
    'aviso1', 'aviso2', 'aviso3',
    'vaga', 'candidato', 'declarou', 'req1', 'req2', 'req3', 'req4', 'resumo']::text[]);

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, cabecalho_documento, variaveis, botao, texto) VALUES
    ('curriculo_para_fran', 'UTILITY', 'curriculo', false, true,
     ARRAY['vaga', 'candidato', 'declarou', 'req1', 'req2', 'req3', 'req4', 'resumo'], 'triagem',
     E'Novo currículo · {{1}}\nCandidato: {{2}}\nDisse nos botões: {{3}}\n\nPré-triagem (IA):\n{{4}}\n{{5}}\n{{6}}\n{{7}}\nResumo: {{8}}\n\nA decisão é sua. A triagem acertou?');

-- A leitura da sessao (`axiaatende_ro`, #981) recebe toda tabela nova pelo privilegio padrao do
-- schema. Do curriculo ela le tudo MENOS o arquivo: o PDF e dado pessoal com finalidade unica (a
-- pre-triagem), e ninguem precisa dele fora do recepcionista e da Fran. No banco de teste o papel
-- nao existe, e o bloco nao faz nada.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'axiaatende_ro') THEN
        REVOKE SELECT ON atendimento.candidaturas FROM axiaatende_ro;
        GRANT SELECT (id, vaga_id, conversa_id, bsuid, wa_id, nome_perfil, declarou, texto, wamid,
                      pdf_nome, pdf_sha256, pdf_bytes, recebida_em, triagem, triagem_em, triagem_erro,
                      fran_para, fran_wamid, fran_em, fran_erro, fran_tentativa_em, feedback, feedback_texto,
                      feedback_em, espera_comentario, apagar_em, apagada_em)
            ON atendimento.candidaturas TO axiaatende_ro;
    END IF;
END $$;
