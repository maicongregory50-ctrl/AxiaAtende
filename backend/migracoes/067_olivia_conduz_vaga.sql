-- #1525 -- a OlivIA conduz a conversa da vaga: a ficha de contato para quem nao tem curriculo
-- (spec e plano em docs/specs/2026-11-16-olivia-conduz-a-vaga-ficha-e-curriculo*.md, D1 a D9).
-- A chave `olivia.conduz_vaga` NASCE DESLIGADA: com ela false, tudo o que esta migracao cria e inerte.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- D3: o modo da vaga. "Ficha ou curriculo" aceita a ficha de cinco perguntas; "Curriculo obrigatorio",
-- so arquivo. O padrao e o mais estreito; a Auxiliar de producao (id 2) aceita ficha.
ALTER TABLE atendimento.vagas
    ADD COLUMN modo text NOT NULL DEFAULT 'curriculo'
        CONSTRAINT vagas_modo CHECK (modo IN ('ficha_ou_curriculo', 'curriculo'));
UPDATE atendimento.vagas SET modo = 'ficha_ou_curriculo' WHERE id = 2;

-- O rascunho da ficha (os cinco campos e a lingua, enquanto a pessoa responde), a lingua da conversa
-- (o toque unico sai nela) e a hora do toque unico (D4 e D6: um por conversa, nunca outro).
ALTER TABLE atendimento.conversas
    ADD COLUMN ficha jsonb,
    ADD COLUMN lingua text CONSTRAINT conversas_lingua CHECK (lingua IN ('pt', 'es')),
    ADD COLUMN vaga_lembrada_em timestamptz;

-- A ficha e uma candidatura sem arquivo (D5): `tipo_arquivo = 'ficha'`, os campos em `ficha`, sem `pdf`.
-- `quer_visita` (D7): a pessoa aceitou vir conhecer a empresa; a Fran combina o dia.
ALTER TABLE atendimento.candidaturas
    ADD COLUMN ficha jsonb,
    ADD COLUMN quer_visita boolean NOT NULL DEFAULT false;
ALTER TABLE atendimento.candidaturas DROP CONSTRAINT candidaturas_tipo_arquivo;
ALTER TABLE atendimento.candidaturas ADD CONSTRAINT candidaturas_tipo_arquivo
    CHECK (tipo_arquivo IN ('pdf', 'imagem', 'ficha'));

-- A chave e os dois tempos (horas). Liga e desliga sem restart por scripts/olivia.py.
INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('olivia.conduz_vaga', 'false'::jsonb),
    ('olivia.vaga_toque_h', '2'::jsonb),
    ('olivia.ficha_parcial_h', '4'::jsonb)
ON CONFLICT DO NOTHING;

-- Os textos de cadastro da ficha, em portugues e em espanhol. PROVISORIOS: o texto que vale e o do dono
-- (passo 18 do plano), e `scripts/olivia.py ligar-vaga` RECUSA ligar enquanto sobrar a marca
-- [TEXTO DO DONO]. A marca sai na troca do texto. {falta}: o que ainda falta da ficha.
INSERT INTO atendimento.respostas_da_vaga (chave, descricao, texto, para_ia, ordem) VALUES
    ('ficha_aviso', 'aviso antes da primeira pergunta da ficha (pt)',
     '[TEXTO DO DONO] Vou te fazer cinco perguntas rápidas. As respostas vão para a equipe de seleção da Renascer e ficam guardadas por 12 meses. Pode ser?', false, 40),
    ('ficha_aviso_es', 'aviso antes da primeira pergunta da ficha (es)',
     '[TEXTO DO DONO] Te voy a hacer cinco preguntas rápidas. Las respuestas van al equipo de selección de Renascer y se guardan por 12 meses. ¿Está bien?', false, 41),
    ('toque_ficha_falta', 'o toque unico: ficha comecada (pt)',
     '[TEXTO DO DONO] Faltou só {falta} para eu passar a sua ficha à equipe.', false, 42),
    ('toque_ficha_falta_es', 'o toque unico: ficha comecada (es)',
     '[TEXTO DO DONO] Solo faltó {falta} para pasar tu ficha al equipo.', false, 43),
    ('toque_convite', 'o toque unico: nada respondido, vaga que aceita ficha (pt)',
     '[TEXTO DO DONO] Não quer deixar a sua ficha? São cinco perguntas rápidas.', false, 44),
    ('toque_convite_es', 'o toque unico: nada respondido, vaga que aceita ficha (es)',
     '[TEXTO DO DONO] ¿No quieres dejar tu ficha? Son cinco preguntas rápidas.', false, 45),
    ('toque_curriculo', 'o toque unico: vaga de curriculo obrigatorio (pt)',
     '[TEXTO DO DONO] Ainda dá tempo de mandar o seu currículo. Pode ser uma foto.', false, 46),
    ('toque_curriculo_es', 'o toque unico: vaga de curriculo obrigatorio (es)',
     '[TEXTO DO DONO] Todavía puedes enviar tu currículum. Puede ser una foto.', false, 47),
    ('ficha_falta', 'a frase do que ainda falta, no lugar da promessa recusada (pt)',
     '[TEXTO DO DONO] Para eu passar a sua ficha à equipe, ainda falta {falta}.', false, 48),
    ('ficha_falta_es', 'a frase do que ainda falta, no lugar da promessa recusada (es)',
     '[TEXTO DO DONO] Para pasar tu ficha al equipo, todavía falta {falta}.', false, 49);

-- D8: os beneficios do cadastro entram no que a OlivIA pode falar, e a palavra "salario" e recusada
-- pelo filtro de saida. O texto das vagas abertas perde o "salario atrativo" (o dono confirma antes de ligar).
UPDATE atendimento.vagas
   SET beneficios = 'plano de saúde Unimed, vale-alimentação, auxílio-combustível e auxílio-educação'
 WHERE aberta AND beneficios = 'salário atrativo, plano de saúde Unimed, vale-alimentação, auxílio-combustível e auxílio-educação';

-- D7: a visita marcada DEPOIS de a candidatura ter ido a Fran vira um aviso de uma linha a ela.
-- Os CHECKs sao REESCRITOS INTEIROS (a licao da 033): os da 065 + o da visita.
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada', 'painel_classe1', 'olivia_resumo', 'vaga_visita'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1', 'aviso_olivia_resumo',
                   'aviso_vaga_visita'));
-- A Meta recusa corpo que comeca ou termina numa variavel.
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('vaga_visita', 'UTILITY', 'aviso_vaga_visita', false, ARRAY['aviso1'], 'nenhum',
     'O candidato {{1}} quer visitar a empresa. Combine o dia com ele.');

-- A leitura da sessao (`axiaatende_ro`) tem SELECT por coluna em candidaturas (025): ganha so
-- `quer_visita`. A FICHA, como o arquivo, nao entra. No banco de teste o papel nao existe.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'axiaatende_ro') THEN
        GRANT SELECT (quer_visita) ON atendimento.candidaturas TO axiaatende_ro;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                    AND table_name = 'conversas' AND column_name IN ('ficha', 'lingua', 'vaga_lembrada_em')
                   HAVING count(*) = 3) THEN
        RAISE EXCEPTION '067: as colunas da conversa nao nasceram.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                    AND table_name = 'candidaturas' AND column_name IN ('ficha', 'quer_visita')
                   HAVING count(*) = 2) THEN
        RAISE EXCEPTION '067: as colunas da candidatura nao nasceram.';
    END IF;
    IF (SELECT count(*) FROM atendimento.ajustes
         WHERE chave IN ('olivia.conduz_vaga', 'olivia.vaga_toque_h', 'olivia.ficha_parcial_h')) <> 3 THEN
        RAISE EXCEPTION '067: os ajustes da conducao da vaga nao nasceram.';
    END IF;
    IF (SELECT valor FROM atendimento.ajustes WHERE chave = 'olivia.conduz_vaga') <> 'false'::jsonb THEN
        RAISE EXCEPTION '067: a chave olivia.conduz_vaga tem de nascer false.';
    END IF;
    IF (SELECT count(*) FROM atendimento.respostas_da_vaga WHERE chave LIKE 'ficha_%' OR chave LIKE 'toque_%') <> 10 THEN
        RAISE EXCEPTION '067: esperava DEZ textos da ficha (cinco chaves, pt e es).';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'avisos_tipo'
                    AND pg_get_constraintdef(oid) LIKE '%olivia_resumo%'
                    AND pg_get_constraintdef(oid) LIKE '%vaga_visita%') THEN
        RAISE EXCEPTION '067: o CHECK de tipo do aviso perdeu tipos.';
    END IF;
    RAISE NOTICE '067 OK: a OlivIA conduz a vaga (modo, ficha, lingua, toque, visita; chave desligada)';
END $$;
