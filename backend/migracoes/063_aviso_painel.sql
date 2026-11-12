-- #1434 -- o aviso de classe 1 do painel da casa (revisao ativa do painel, #1411 no AxiaSecurity) vai
-- ao WhatsApp do dono pelo mesmo caminho dos canais de backend/auditoria_erp.py. A origem nao e o ERP:
-- e a pasta C:\Logs\Seguranca\revisao\avisos, que a revisao (SYSTEM) escreve. Spec e plano em
-- docs/specs/2026-11-12-aviso-do-painel-no-whatsapp*.md.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- O CHECK e REESCRITO INTEIRO (a licao da 033): os dez da 060 + o do painel.
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada', 'painel_classe1'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1'));

-- O texto vem PRONTO da revisao ({{1}}). Com o porteiro ligado sai como texto (dentro da janela) ou no
-- Ver da reabertura (fora dela): o modelo e so CADASTRO, como o aviso_integracao da 060.
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('aviso_painel', 'UTILITY', 'aviso_painel_classe1', false, ARRAY['aviso1'], 'nenhum',
     'Aviso do painel da casa: {{1}}');

-- Quem recebe: o mesmo de integracoes_para (o dono).
INSERT INTO atendimento.ajustes (chave, valor)
SELECT 'painel_para', valor FROM atendimento.ajustes WHERE chave = 'integracoes_para'
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'avisos_tipo'
                    AND pg_get_constraintdef(oid) LIKE '%integracao_recusada%'
                    AND pg_get_constraintdef(oid) LIKE '%painel_classe1%') THEN
        RAISE EXCEPTION '063: o CHECK de tipo do aviso perdeu tipos.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'modelos_uso'
                    AND pg_get_constraintdef(oid) LIKE '%aviso_integracao_recusada%'
                    AND pg_get_constraintdef(oid) LIKE '%aviso_painel_classe1%') THEN
        RAISE EXCEPTION '063: o CHECK de uso do modelo perdeu usos.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM atendimento.modelos WHERE nome = 'aviso_painel') THEN
        RAISE EXCEPTION '063: o modelo do aviso do painel nao nasceu.';
    END IF;
    IF EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'integracoes_para')
       AND NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'painel_para') THEN
        RAISE EXCEPTION '063: o ajuste painel_para nao nasceu.';
    END IF;
    RAISE NOTICE '063 OK: o aviso do painel da casa';
END $$;
