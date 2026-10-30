-- #1207 -- o Status do dia: as artes do Stories chegam ao WhatsApp do dono pelo porteiro dos avisos
-- (dono, 30/10/2026: "vir somente a legenda da ultima foto, sem mais nenhum texto adicional"; "eu ja
-- tenho janela aberta, teria que ser texto"). O Marketing pede pela porta do pedido (/pedido/aviso),
-- e o aviso sai como IMAGENS: sem texto nenhum, so a ultima com a legenda. Fora da janela, a mesma
-- reabertura dos avisos internos (#1188). Spec e plano no Marketing:
-- C:\AxiaMarketing\docs\specs\2026-10-30-stories-e-status-com-o-carrossel-completo*.md (passo 1).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.avisos
    ADD COLUMN imagens text[] NOT NULL DEFAULT '{}',   -- os arquivos, na ordem (so o status_do_dia)
    ADD COLUMN legenda text NOT NULL DEFAULT '';       -- vai na ultima imagem, como esta

-- O CHECK e REESCRITO INTEIRO (a licao da 033): os sete de antes + o status do dia.
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia'));
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_status_com_imagens
    CHECK (tipo <> 'status_do_dia' OR cardinality(imagens) BETWEEN 1 AND 10);

-- Quem recebe o Status: nasce o mesmo de quem recebe o aviso do plano (o dono); muda-se aqui sem
-- mexer no outro.
INSERT INTO atendimento.ajustes (chave, valor)
SELECT 'status_do_dia_para', valor FROM atendimento.ajustes WHERE chave = 'avisado_no_nao';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                    AND table_name = 'avisos' AND column_name IN ('imagens', 'legenda')
                   HAVING count(*) = 2) THEN
        RAISE EXCEPTION '048: as colunas imagens e legenda nao nasceram.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'avisos_tipo'
                    AND pg_get_constraintdef(oid) LIKE '%lote_do_representante%'
                    AND pg_get_constraintdef(oid) LIKE '%status_do_dia%') THEN
        RAISE EXCEPTION '048: o CHECK de tipo do aviso perdeu tipos.';
    END IF;
    IF EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'avisado_no_nao')
       AND NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'status_do_dia_para') THEN
        RAISE EXCEPTION '048: o ajuste status_do_dia_para nao nasceu.';
    END IF;
    RAISE NOTICE '048 OK: o status do dia nos avisos';
END $$;
