-- #1142 -- a fila de envio por NUMERO, o papel do contato, e o resumo ao representante no lugar da
-- copia (dono, 26/10/2026).
-- Spec: docs/specs/2026-10-26-fila-por-numero-e-resumo-ao-representante.md -- plano ao lado, passo 1.
-- Pedido por: #1103 do AxiaMarketing; o par no ERP e o #1141, no ar desde 26/10.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- POR QUE (o problema, nao a solucao):
--   1. A fila e por CADASTRO (`envio_dest_um_por_cliente UNIQUE (envio_id, erp_codigo)`), e o
--      INSERT de `receber_pedido` tem `ON CONFLICT ... DO NOTHING`. Desde o #1141 o ERP entrega UMA
--      LINHA POR CONTATO do cliente (o comprador e o tecnico), e na camada COOPERATIVA os dois caem
--      no mesmo envio -- material diferente, mesma semana. Com a unicidade por cadastro, o segundo e
--      DESCARTADO EM SILENCIO. Nao e recusa: e sumir.
--   2. A copia ao responsavel manda, a cada convite, uma copia a quem atende o cliente. No material
--      as revendas o responsavel e o DONO (o marketing o poe como responsavel de toda revenda), e
--      foi assim que as artes da Agro Real e da Agro Simil chegaram ao WhatsApp dele em 23/10.
--      O manual de Envios, por outro lado, JA DIZIA o contrario -- "nao avisa o responsavel de quem
--      quis receber: so de quem recusou". A copia nunca entrou no manual; o codigo divergiu do que
--      estava escrito, e ninguem leu os dois lado a lado.
--
-- O QUE MUDA:
--   1. `envio_destinatarios.papel` (comprador | tecnico): quem e o contato no cliente. Nulo e o que
--      o pedido de antes manda -- nao se afirma o que ninguem disse.
--   2. `envio_destinatarios.responsavel_canal`: QUEM o responsavel e no ERP. E ele que decide a quem
--      o resumo vai, porque este projeto NAO SABE QUEM E O DONO (nao ha numero dele no config
--      daqui): quem sabe e o marketing, e passa a dizer.
--   3. A unicidade passa a ser por NUMERO, e e PARCIAL: quem nao tem celular valido grava
--      `whatsapp = ''`, e dois assim no mesmo envio e caso legitimo (`sem_whatsapp`) -- sem o
--      `WHERE` eles colidiriam. "Uma pessoa uma vez por envio" vira garantia do banco, e nao
--      cortesia de quem monta o pedido.
--   4. O aviso `lote_do_representante` e o modelo dele, para o resumo sair pelo caminho que JA
--      EXISTE (`atendimento.avisos` + `Envio.mandar_avisos`), como UTILITY, sem imagem e sem botao.
--
-- O QUE NAO MUDA: a classificacao do destinatario na chegada (as sete situacoes); o lote de 20 por
-- dia; `atendimento.consentimentos`, que e por numero e imutavel (regra 4); e o guarda de
-- `envio:<id>:copia` em `tratar_toque`, porque ha mensagens com esse botao na rua.
--
-- GALHOS: atendimento.envio_destinatarios (2 colunas, 1 unicidade), atendimento.avisos (1 CHECK),
-- atendimento.modelos (1 CHECK, 1 linha). A 031 esta reservada ao #1097; as mudancas entram pelo
-- nome, entao a ordem nao importa.

ALTER TABLE atendimento.envio_destinatarios
    ADD COLUMN papel text CONSTRAINT envio_dest_papel CHECK (papel IN ('comprador', 'tecnico')),
    ADD COLUMN responsavel_canal text CONSTRAINT envio_dest_resp_canal
        CHECK (responsavel_canal IN ('representante', 'corretor', 'dono', 'flutuante'));
COMMENT ON COLUMN atendimento.envio_destinatarios.papel IS
    'Quem e este contato no cliente (#1141): comprador (decide a compra) ou tecnico (vai ao produtor '
    'e recomenda). Nulo = o pedido nao disse. Vai ao ERP no evento (rel_contatos.envio_papel).';
COMMENT ON COLUMN atendimento.envio_destinatarios.responsavel_canal IS
    'O canal do responsavel no ERP (#1142): representante, corretor, dono ou flutuante. O resumo do '
    'lote vai SO a representante e corretor -- este projeto nao sabe qual numero e o do dono.';

-- A unicidade por numero. CONTA ANTES e recusa com o numero: em producao isto nao foi medido (o
-- banco pede o segredo, e a sessao de agente nao o le), e falhar no CREATE UNIQUE INDEX diria que
-- "ha duplicata" sem dizer quantas nem onde.
DO $$
DECLARE
    repetidos BIGINT;
    exemplo   TEXT;
BEGIN
    SELECT count(*), min(format('envio %s, numero %s (%s vezes)', envio_id, whatsapp, n))
      INTO repetidos, exemplo
      FROM (SELECT envio_id, whatsapp, count(*) AS n
              FROM atendimento.envio_destinatarios
             WHERE whatsapp <> ''
             GROUP BY envio_id, whatsapp HAVING count(*) > 1) x;
    IF repetidos > 0 THEN
        RAISE EXCEPTION '033: % par(es) (envio, numero) repetido(s) -- a unicidade nova nao cabe. '
                        'O primeiro: %. Junte ou apague os repetidos antes de aplicar.',
                        repetidos, exemplo;
    END IF;
END $$;

ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_um_por_cliente;
CREATE UNIQUE INDEX envio_dest_um_por_numero
    ON atendimento.envio_destinatarios (envio_id, whatsapp) WHERE whatsapp <> '';
COMMENT ON INDEX atendimento.envio_dest_um_por_numero IS
    'Uma pessoa uma vez por envio (#1142). PARCIAL de proposito: quem nao tem celular valido grava '
    'whatsapp vazio, e dois desses no mesmo envio e caso legitimo (situacao sem_whatsapp).';

ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'lote_do_representante'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo'));

-- O modelo do resumo. O TEXTO FINAL E O QUE A META APROVAR: esta linha e a proposta, e e por ela
-- que o dono pede a aprovacao (categoria Utilidade -- aviso interno, a quem trabalha aqui).
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('aviso_lote_do_representante', 'UTILITY', 'aviso_lote_do_representante', false,
     ARRAY['aviso1', 'aviso2', 'aviso3'], 'nenhum',
     'Olá, {{1}}. {{2}} acabaram de receber a nossa mensagem sobre {{3}}. O que cada um respondeu '
     'aparece no Relacionamento, no sistema.');

-- ── Conferencia dentro da transacao ─────────────────────────────────────────
DO $$
DECLARE
    n BIGINT;
BEGIN
    IF (SELECT count(*) FROM atendimento.envio_destinatarios
         WHERE papel IS NOT NULL OR responsavel_canal IS NOT NULL) <> 0 THEN
        RAISE EXCEPTION '033: as duas colunas devia nascer nulas em toda linha.';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'envio_dest_um_por_cliente') THEN
        RAISE EXCEPTION '033: a unicidade por cadastro devia ter saido.';
    END IF;
    SELECT count(*) INTO n FROM pg_indexes
     WHERE schemaname = 'atendimento' AND indexname = 'envio_dest_um_por_numero'
       AND indexdef LIKE '%WHERE (whatsapp%';
    IF n <> 1 THEN
        RAISE EXCEPTION '033: esperava o indice parcial por numero, achei %.', n;
    END IF;
    IF (SELECT count(*) FROM atendimento.modelos WHERE uso = 'aviso_lote_do_representante') <> 1 THEN
        RAISE EXCEPTION '033: esperava UM modelo do resumo.';
    END IF;
    RAISE NOTICE '033 OK: papel e responsavel_canal (nulos), a unicidade por numero (parcial), e o '
                 'modelo aviso_lote_do_representante.';
END $$;

-- Conferencia esperada (o EFEITO, nao a ausencia de erro):
--   SELECT indexname, indexdef FROM pg_indexes
--    WHERE schemaname = 'atendimento' AND indexname = 'envio_dest_um_por_numero';
--   SELECT conname FROM pg_constraint WHERE conname = 'envio_dest_um_por_cliente';   -- vazio
--   SELECT nome, categoria, uso FROM atendimento.modelos WHERE uso LIKE 'aviso_lote%';
--   -- A JUSANTE: o proximo pedido do marketing grava os dois campos, e a tela Envios continua
--   -- listando os destinatarios de sempre.
--
-- ROLLBACK: 033_fila_por_numero_e_resumo_VOLTA.sql -- ela conta os avisos do tipo novo e os pares
-- (envio, cadastro) repetidos ANTES de desfazer, porque os dois impedem a volta.
