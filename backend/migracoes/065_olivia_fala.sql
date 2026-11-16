-- #1520 -- a OlivIA anonima fala (spec e plano em docs/specs/2026-11-14-a-olivia-anonima-fala*.md).
-- Tres colunas, o tipo de aviso do vigia (com o modelo dele no cadastro) e o preco do Sonnet.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- Quem conduz a conversa: o menu (o caminho de sempre) ou a OlivIA (texto proprio ao anonimo).
ALTER TABLE atendimento.conversas
    ADD COLUMN conduzida_por text NOT NULL DEFAULT 'menu'
        CONSTRAINT conversas_conduzida_por CHECK (conduzida_por IN ('menu', 'olivia')),
    -- Como terminou aos olhos do vigia das 23:40 (D6). Nula enquanto ninguem olhou.
    ADD COLUMN saida text CONSTRAINT conversas_saida CHECK (saida IN ('bem', 'sem_saida'));

-- D5: o curriculo em foto entra nas mesmas colunas `pdf_*`, e esta coluna diz o que e.
ALTER TABLE atendimento.candidaturas
    ADD COLUMN tipo_arquivo text NOT NULL DEFAULT 'pdf'
        CONSTRAINT candidaturas_tipo_arquivo CHECK (tipo_arquivo IN ('pdf', 'imagem'));

-- D5: a foto passa a servir. A linha de quem manda Word, audio ou figurinha na vaga diz isso.
UPDATE atendimento.respostas_da_vaga
   SET texto = 'Precisamos do seu currículo em PDF ou em foto. Mande aqui mesmo.'
 WHERE chave = 'so_pdf';

-- O resumo do vigia ao dono. O CHECK e REESCRITO INTEIRO (a licao da 033): os onze da 063 + o da OlivIA.
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada', 'painel_classe1', 'olivia_resumo'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1', 'aviso_olivia_resumo'));

-- O texto vem pronto do vigia ({{1}}); a Meta recusa corpo que comeca ou termina numa variavel.
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('olivia_resumo', 'UTILITY', 'aviso_olivia_resumo', false, ARRAY['aviso1'], 'nenhum',
     'Resumo da OlivIA: {{1}} O detalhe está na tela Recepção.');

-- D8: a conversa e do Sonnet 5.5. Preco de tabela em 03/11/2026: US$ 2 por milhao de entrada, 10 de saida.
INSERT INTO atendimento.precos (servico, item, vale_desde, por_milhao_entrada, por_milhao_saida)
VALUES ('claude', 'claude-sonnet-5-5', '2026-11-03', 2.00, 10.00)
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                    AND table_name = 'conversas' AND column_name IN ('conduzida_por', 'saida')
                   HAVING count(*) = 2) THEN
        RAISE EXCEPTION '065: as colunas da conversa nao nasceram.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                    AND table_name = 'candidaturas' AND column_name = 'tipo_arquivo') THEN
        RAISE EXCEPTION '065: tipo_arquivo nao nasceu.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'avisos_tipo'
                    AND pg_get_constraintdef(oid) LIKE '%painel_classe1%'
                    AND pg_get_constraintdef(oid) LIKE '%olivia_resumo%') THEN
        RAISE EXCEPTION '065: o CHECK de tipo do aviso perdeu tipos.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM atendimento.modelos WHERE nome = 'olivia_resumo') THEN
        RAISE EXCEPTION '065: o modelo do resumo da OlivIA nao nasceu.';
    END IF;
    RAISE NOTICE '065 OK: a OlivIA fala (conduzida_por, saida, tipo_arquivo, aviso e preco)';
END $$;
