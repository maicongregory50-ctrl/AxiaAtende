-- #1188 -- a janela de 24 h: o porteiro dos avisos internos e o modelo de reabertura (dono, 28/10/2026).
-- Spec e plano: docs/specs/2026-10-28-a-janela-de-24h-e-o-porteiro-dos-avisos*.md (passo 2).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- O ESTADO DO AVISO, alem de enviado e erro (que ja existiam):
--   guardado_em    fora da janela da pessoa: esperando o toque em Ver da reabertura;
--   nao_visto_em   7 dias sem o toque: nao sai mais, e NAO SOME (a tela Envios mostra);
--   como           por onde saiu: 'modelo' (pago) ou 'texto' (de graca, dentro da janela); nulo ate sair;
--   reabertura_id  a mensagem de reabertura (atendimento.enviadas) que o guardou.
-- Com a chave AXIAATENDE_PORTEIRO desligada nada disso e preenchido, e o aviso sai como sempre.

ALTER TABLE atendimento.avisos
    ADD COLUMN guardado_em timestamptz,
    ADD COLUMN nao_visto_em timestamptz,
    ADD COLUMN como text CONSTRAINT avisos_como CHECK (como IN ('modelo', 'texto')),
    ADD COLUMN reabertura_id bigint REFERENCES atendimento.enviadas (id);
CREATE INDEX avisos_guardados ON atendimento.avisos (para_whatsapp)
    WHERE enviado_em IS NULL AND guardado_em IS NOT NULL AND nao_visto_em IS NULL;

-- Os CHECKs sao REESCRITOS INTEIROS (a licao da 033): cada lista carrega tudo o que ja existia.
-- usos: os da 033 (dez) + reabertura; botoes e variaveis: os da 025 + o novo.
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura'));
-- a reabertura e pedida como Utilidade; a Meta pode classifica-la como Marketing (regra 6)
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_categoria_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_categoria_do_uso CHECK (
    (uso IN ('convite', 'direta') AND categoria = 'MARKETING')
    OR ((uso LIKE 'aviso%' OR uso IN ('curriculo', 'reabertura')) AND categoria IN ('UTILITY', 'MARKETING')));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao = 'falar_responsavel')
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_variaveis;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_variaveis CHECK (variaveis <@ ARRAY[
    'primeiro_nome', 'nome', 'assunto', 'peca', 'n_avisos', 'n_imagens', 'responsavel',
    'aviso1', 'aviso2', 'aviso3',
    'vaga', 'candidato', 'declarou', 'req1', 'req2', 'req3', 'req4', 'resumo']::text[]);

-- O modelo, com o texto APROVADO PELO DONO em 28/10/2026. O nome e o texto tem de ser os aprovados na
-- Meta (`python -m backend.modelos_meta --propor`); modelo aprovado nao se edita: texto novo e modelo novo.
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('reabrir_avisos', 'UTILITY', 'reabertura', false, ARRAY['n_avisos'], 'ver',
     'Você tem {{1}} aviso(s) da Sementes Renascer. Toque em Ver para receber.');

-- ── Conferencia dentro da transacao ─────────────────────────────────────────
DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.modelos WHERE uso = 'reabertura') <> 1 THEN
        RAISE EXCEPTION '039: esperava UM modelo de reabertura.';
    END IF;
    IF (SELECT count(*) FROM atendimento.avisos
         WHERE guardado_em IS NOT NULL OR nao_visto_em IS NOT NULL OR como IS NOT NULL
            OR reabertura_id IS NOT NULL) <> 0 THEN
        RAISE EXCEPTION '039: as quatro colunas deviam nascer nulas em todo aviso.';
    END IF;
    -- o tipo do aviso NAO muda: a lista da 033 continua inteira
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'avisos_tipo'
                    AND pg_get_constraintdef(oid) LIKE '%lote_do_representante%'
                    AND pg_get_constraintdef(oid) LIKE '%plano_sem_registro%') THEN
        RAISE EXCEPTION '039: o CHECK de tipo do aviso perdeu tipos.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'modelos_uso'
                    AND pg_get_constraintdef(oid) LIKE '%curriculo%'
                    AND pg_get_constraintdef(oid) LIKE '%aviso_lote_do_representante%') THEN
        RAISE EXCEPTION '039: o CHECK de uso do modelo perdeu os usos que ja existiam.';
    END IF;
    RAISE NOTICE '039 OK: o estado do aviso (quatro colunas nulas) e o modelo reabrir_avisos.';
END $$;
