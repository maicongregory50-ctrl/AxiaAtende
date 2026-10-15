-- #1036 (dono, 15/10/2026): duas coisas no mesmo chamado, por decisao dele.
--
-- 1. PELO NOME. A pergunta do menu da casa (nascido hoje no #1031) dizia "Voce e da equipe. O que
--    precisa?" -- impessoal, tendo o nome na mao. Ela passa a trazer `{nome}`, que
--    `mostrar_menu_interno` formata com `primeiro_nome()` (que tambem resolve a caixa alta do ERP:
--    "BENEDITO  VASKEVICZ" -> "Benedito"). O TEXTO CONTINUA CADASTRO e o nome continua codigo: a
--    frase segue editavel sem deploy, e o codigo tolera a ausencia do marcador.
--
-- 2. A LOGO DE CLIENTE. As 15:27 de hoje o Benedito mandou a logo de um cliente em PDF e recebeu
--    SILENCIO -- documento nao e midia (motor.py cria e.midia so para image e video), e para quem e
--    da casa a linha curta nao sai de proposito (12/10). A logo se perdeu duas vezes (07:36 e
--    15:27, o mesmo arquivo).
--
--    A logo passa a ser colhida aqui e a ESPERAR SER PUXADA pelo AxiaMarketing, cuja tela Parceiras
--    (#886) e o destino: ela guarda a logo, o contato e a AUTORIZACAO QUE TRAVA A PECA. Nada aqui
--    aprova nada -- e o banco de la concorda, porque `parceiras_autorizada_com_documento` e um CHECK
--    que impede 'autorizada' sem arquivo de autorizacao e data de assinatura.
--
--    NAO e material de campo, e por isso tem tabela propria: misturar poria uma logo no catalogo do
--    marketing como foto de lavoura. Medido em 15/10: 0 documentos em material_de_campo.
--
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.menu
   SET pergunta = 'Olá, {nome}! Você é da equipe — o que precisa?'
 WHERE chave = 'raiz_interna';

CREATE TABLE atendimento.logos_de_cliente (
    id bigserial PRIMARY KEY,
    -- quem mandou
    bsuid text NOT NULL,
    wa_id text,
    enviada_por text NOT NULL DEFAULT '',          -- o nome de quem e da casa, como o cadastro diz
    -- o arquivo. `wamid` UNICO: o mesmo aviso repetido pela Meta nao cria duas logos
    wamid text NOT NULL CONSTRAINT logos_wamid_unico UNIQUE,
    nome_arquivo text NOT NULL DEFAULT '',         -- o original ("Logo rigo sem..pdf" e informacao)
    arquivo text,                                  -- relativo a pasta de midia; NULL se o download falhou
    sha256 text CONSTRAINT logos_sha256 CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'),
    mime text NOT NULL DEFAULT '',
    -- os quatro que a tela Parceiras do marketing aceita (parceiras_logos_formato)
    formato text CONSTRAINT logos_formato CHECK (formato IS NULL OR formato IN ('pdf', 'svg', 'png', 'jpg')),
    -- de quem e a logo. NULO e estado legitimo: sem o codigo ela FICA GUARDADA, nunca e descartada
    erp_codigo integer CONSTRAINT logos_erp_codigo CHECK (erp_codigo IS NULL OR erp_codigo > 0),
    nome_marca text NOT NULL DEFAULT '',
    -- o dialogo de duas perguntas. A maquina do canal de campo nao serve: ela pende de uma linha de
    -- material_de_campo, e usa-la obrigaria a criar peca de campo para uma logo.
    pergunta_pendente text
        CONSTRAINT logos_pergunta_pendente CHECK (pergunta_pendente IN ('erp_codigo', 'nome_marca')),
    insistiu boolean NOT NULL DEFAULT false,       -- uma insistencia so (a licao do teto do #1028)
    recebida_em timestamptz NOT NULL DEFAULT now(),
    completada_em timestamptz,
    -- o AxiaMarketing PUXA (padrao #267: a seta nao se inverte, e nao nasce segredo novo)
    puxada_em timestamptz,
    erro text NOT NULL DEFAULT ''
);

CREATE INDEX logos_a_puxar ON atendimento.logos_de_cliente (recebida_em) WHERE puxada_em IS NULL;
CREATE INDEX logos_pendente_por_pessoa ON atendimento.logos_de_cliente (bsuid, id DESC)
    WHERE pergunta_pendente IS NOT NULL;
