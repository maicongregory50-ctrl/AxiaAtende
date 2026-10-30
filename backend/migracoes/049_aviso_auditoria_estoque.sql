-- #350 -- a auditoria de estoque do ERP venceu: o aviso vai ao WhatsApp de quem cuida dela (o dono e a
-- Fran, que responde pelo Financeiro; dono, 30/10/2026). O ERP deixa o aviso PENDENTE; as telas buscam
-- (backend/auditoria_erp.py), gravam uma linha em avisos por destino e devolvem o estado. Sai pelo
-- porteiro dos avisos (#1188): texto dentro da janela, reabertura fora dela. Spec e plano no ERP:
-- C:\AxiaGestao\docs\specs\2026-10-30-auditoria-quinzenal-de-estoque*.md (passo 6).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- O CHECK e REESCRITO INTEIRO (a licao da 033): os oito de antes + o da auditoria.
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque'));

-- O texto do aviso (com o porteiro ligado sai como texto; sem ele, este modelo precisaria da Meta:
-- `python -m backend.modelos_meta --propor --so aviso_auditoria_estoque`).
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('aviso_auditoria_estoque', 'UTILITY', 'aviso_auditoria_estoque', false, ARRAY['aviso1', 'aviso2'], 'nenhum',
     'A auditoria de estoque da {{1}} está vencida: a última lista foi gerada em {{2}}. Abra Relatórios → Auditoria de estoque no AxiaGestão.');

-- Quem recebe: uma LISTA de destinos (o dono, do ajuste do plano, e a Fran). Muda-se aqui sem mexer
-- nos outros avisos.
INSERT INTO atendimento.ajustes (chave, valor)
SELECT 'auditoria_estoque_para',
       to_jsonb(ARRAY(SELECT x FROM (
           SELECT (SELECT valor FROM atendimento.ajustes WHERE chave = 'avisado_no_nao')::text::int AS x
           UNION
           SELECT id FROM atendimento.destinos WHERE nome = 'Fran' AND ativo) s WHERE x IS NOT NULL ORDER BY x));

-- O vinculo com o ERP: um aviso de la vira uma linha em avisos por destino.
CREATE TABLE atendimento.avisos_auditoria_erp (
    erp_aviso_id  integer PRIMARY KEY,
    aviso_ids     bigint[] NOT NULL DEFAULT '{}',
    erro          text NOT NULL DEFAULT '',
    criado_em     timestamptz NOT NULL DEFAULT now(),
    devolvido_em  timestamptz
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'avisos_tipo'
                    AND pg_get_constraintdef(oid) LIKE '%status_do_dia%'
                    AND pg_get_constraintdef(oid) LIKE '%auditoria_estoque%') THEN
        RAISE EXCEPTION '049: o CHECK de tipo do aviso perdeu tipos.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'modelos_uso'
                    AND pg_get_constraintdef(oid) LIKE '%reabertura%'
                    AND pg_get_constraintdef(oid) LIKE '%aviso_auditoria_estoque%') THEN
        RAISE EXCEPTION '049: o CHECK de uso do modelo perdeu usos.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM atendimento.modelos WHERE uso = 'aviso_auditoria_estoque') THEN
        RAISE EXCEPTION '049: o modelo do aviso nao nasceu.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'auditoria_estoque_para') THEN
        RAISE EXCEPTION '049: o ajuste auditoria_estoque_para nao nasceu.';
    END IF;
    RAISE NOTICE '049 OK: o aviso da auditoria de estoque';
END $$;
