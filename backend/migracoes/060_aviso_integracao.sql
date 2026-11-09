-- #1337 -- uma API externa do ERP passou a recusar (#1280): o aviso vai ao WhatsApp do dono, pelo mesmo
-- caminho da auditoria de estoque (049). O ERP deixa o aviso PENDENTE em /atendimento/integracoes-avisos;
-- as telas (backend/auditoria_erp.py, agora em CANAIS) gravam uma linha em avisos por destino do ajuste
-- `integracoes_para` e devolvem ENVIADO ou FALHOU. Spec e plano em
-- docs/specs/2026-11-09-aviso-de-api-recusando-no-whatsapp*.md.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- O CHECK e REESCRITO INTEIRO (a licao da 033): os nove de antes + o da integracao.
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada'));

-- O uso e "aviso_" + tipo: e por ele que envio.modelo_do_uso acha o texto do aviso.
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada'));

-- O texto vem PRONTO do ERP ({{1}}). Com o porteiro ligado sai como texto (dentro da janela) ou no Ver
-- da reabertura (fora dela): o modelo e so CADASTRO. So se o porteiro for desligado ele precisa da Meta:
-- `python -m backend.modelos_meta --propor --so aviso_integracao`.
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('aviso_integracao', 'UTILITY', 'aviso_integracao_recusada', false, ARRAY['aviso1'], 'nenhum',
     'Aviso do AxiaGestão: {{1}}');

-- Quem recebe: so o dono (o mesmo destino que abre o aviso do "nao quero", e o primeiro da auditoria).
INSERT INTO atendimento.ajustes (chave, valor)
SELECT 'integracoes_para', to_jsonb(ARRAY[(valor)::text::int])
  FROM atendimento.ajustes WHERE chave = 'avisado_no_nao'
ON CONFLICT DO NOTHING;

-- A correlacao com o ERP passa a ser por CANAL: o id 7 da auditoria e o id 7 da integracao sao avisos
-- diferentes. As linhas de hoje sao todas da auditoria (o DEFAULT as preenche antes da PK nova).
ALTER TABLE atendimento.avisos_auditoria_erp ADD COLUMN canal text NOT NULL DEFAULT 'auditoria_estoque';
ALTER TABLE atendimento.avisos_auditoria_erp DROP CONSTRAINT avisos_auditoria_erp_pkey;
ALTER TABLE atendimento.avisos_auditoria_erp ADD CONSTRAINT avisos_auditoria_erp_pkey PRIMARY KEY (canal, erp_aviso_id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'avisos_tipo'
                    AND pg_get_constraintdef(oid) LIKE '%auditoria_estoque%'
                    AND pg_get_constraintdef(oid) LIKE '%integracao_recusada%') THEN
        RAISE EXCEPTION '060: o CHECK de tipo do aviso perdeu tipos.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'modelos_uso'
                    AND pg_get_constraintdef(oid) LIKE '%aviso_auditoria_estoque%'
                    AND pg_get_constraintdef(oid) LIKE '%aviso_integracao_recusada%') THEN
        RAISE EXCEPTION '060: o CHECK de uso do modelo perdeu usos.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM atendimento.modelos WHERE nome = 'aviso_integracao') THEN
        RAISE EXCEPTION '060: o modelo do aviso nao nasceu.';
    END IF;
    IF EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'avisado_no_nao')
       AND NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'integracoes_para') THEN
        RAISE EXCEPTION '060: o ajuste integracoes_para nao nasceu.';
    END IF;
    RAISE NOTICE '060 OK: o aviso de API externa recusando';
END $$;
