-- #1542 (etapa 3, passo 5) -- o TERMO DE REPROVACAO DE LOTE do ERP vai ao WhatsApp Legal do produtor, com o
-- PDF no cabecalho e o botao "Recebi e estou ciente". Plano:
-- C:\AxiaGestao\docs\specs\2026-11-18-termo-de-reprovacao-do-lote-etapa3-plano.md
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py. A 070 e do #1589.
--
-- `termos_reprovacao`: uma linha por pedido de envio do ERP (`reprovacoes_lote_envios.id`). As TELAS a
-- gravam (busca de 1 min) com o PDF baixado; o RECEPCIONISTA manda o modelo, guarda o wamid, o estado da
-- Meta e o toque; as TELAS devolvem ao ERP o estado e a ciencia (`*_devolvido*`).
--
-- O modelo `termo_reprovacao_lote` (Utilidade, PDF no cabecalho, formato do #1098). O texto cita o contrato
-- e pede so a confirmacao do recebimento; nao fala em concordancia (dono, 18/11/2026: o produtor ja
-- concordou no contrato, e dizer "nao e concordancia" soaria como concessao). O toque e reconhecido pela
-- carga `termo:ciente:<id>`, nunca pelo texto do botao.

CREATE TABLE atendimento.termos_reprovacao (
    id                   bigserial PRIMARY KEY,
    erp_envio_id         integer NOT NULL CONSTRAINT termos_reprovacao_envio_unico UNIQUE,
    erp_termo_id         integer NOT NULL,
    numero_termo         text NOT NULL,
    produtor_nome        text NOT NULL DEFAULT '',
    lotes                text NOT NULL DEFAULT '',
    valor                text NOT NULL DEFAULT '',
    vencimento           text NOT NULL DEFAULT '',
    para_whatsapp        text NOT NULL,
    arquivo              text NOT NULL DEFAULT '',
    estado               text NOT NULL DEFAULT 'a_enviar' CONSTRAINT termos_reprovacao_estado
                         CHECK (estado IN ('a_enviar', 'enviada', 'entregue', 'lida', 'falhou')),
    erro                 text NOT NULL DEFAULT '',
    wamid                text NOT NULL DEFAULT '',
    criado_em            timestamptz NOT NULL DEFAULT now(),
    enviado_em           timestamptz,
    estado_em            timestamptz,
    estado_devolvido     text NOT NULL DEFAULT '',     -- o ultimo estado que o ERP ja recebeu
    ciencia_em           timestamptz,
    ciencia_numero       text,
    ciencia_wamid        text,
    ciencia_devolvida_em timestamptz,
    ciencia_recusada     text                          -- o ERP recusou (numero diferente): nao tenta de novo
);
CREATE INDEX termos_reprovacao_a_enviar ON atendimento.termos_reprovacao (id) WHERE estado = 'a_enviar';
CREATE INDEX termos_reprovacao_wamid ON atendimento.termos_reprovacao (wamid) WHERE wamid <> '';

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1', 'aviso_olivia_resumo',
                   'aviso_vaga_visita', 'aviso_arquivo_sem_antivirus', 'aviso_arquivo_ameaca',
                   'termo_reprovacao'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_categoria_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_categoria_do_uso CHECK (
    (uso IN ('convite', 'direta') AND categoria = 'MARKETING')
    OR ((uso LIKE 'aviso%' OR uso IN ('curriculo', 'reabertura')) AND categoria IN ('UTILITY', 'MARKETING'))
    OR (uso = 'termo_reprovacao' AND categoria = 'UTILITY'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver', 'parar_e_falar',
                     'parar_e_chamar', 'ciente'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao IN ('falar_responsavel', 'parar_e_falar', 'parar_e_chamar'))
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver')
    OR (uso = 'termo_reprovacao' AND botao = 'ciente'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_variaveis;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_variaveis CHECK (variaveis <@ ARRAY[
    'primeiro_nome', 'nome', 'assunto', 'peca', 'n_avisos', 'n_imagens', 'responsavel',
    'aviso1', 'aviso2', 'aviso3',
    'vaga', 'candidato', 'declarou', 'req1', 'req2', 'req3', 'req4', 'resumo',
    'produtor', 'numero_termo', 'lotes', 'valor', 'vencimento']::text[]);

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, cabecalho_documento, variaveis, botao, texto) VALUES
    ('termo_reprovacao_lote', 'UTILITY', 'termo_reprovacao', false, true,
     ARRAY['produtor', 'numero_termo', 'lotes', 'valor', 'vencimento'], 'ciente',
     E'Olá, {{1}}. Segue o termo de reprovação {{2}}, do lote {{3}}, com a cobrança do beneficiamento de '
     'R$ {{4}}, prevista na Cláusula Sexta, item 4, do contrato. O valor será compensado no encontro de '
     'contas; o vencimento é {{5}}.' || E'\n\n' || 'Toque no botão abaixo para confirmar que recebeu este termo.');

DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.modelos WHERE nome = 'termo_reprovacao_lote' AND ativo) <> 1 THEN
        RAISE EXCEPTION '071: o modelo termo_reprovacao_lote nao ficou no cadastro.';
    END IF;
    IF to_regclass('atendimento.termos_reprovacao') IS NULL THEN
        RAISE EXCEPTION '071: atendimento.termos_reprovacao nao existe.';
    END IF;
END $$;
