-- #1381 -- o arquivo (PDF ou Word) que vai junto da resposta do chamado ao WhatsApp do autor.
-- A linha que o ERP manda em /demandas/whatsapp/saida passa a trazer `anexo` quando o evento tem
-- arquivo; a volta do ERP (backend/pendencias_erp.py) o baixa para envios_pasta\chamados e grava aqui
-- {"arquivo", "nome", "media_type"}; o recepcionista (backend/pendencias.py) o manda logo depois do
-- texto. Spec e plano em docs/specs/2026-11-11-anexo-na-resposta-do-chamado*.md.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.pendencias_mensagens ADD COLUMN anexo jsonb;

-- A chave que desliga so o documento (o texto continua saindo). Nasce ligada.
INSERT INTO atendimento.ajustes (chave, valor) VALUES ('pendencias.anexo_ligado', 'true'::jsonb)
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                    AND table_name = 'pendencias_mensagens' AND column_name = 'anexo') THEN
        RAISE EXCEPTION '061: a coluna anexo nao nasceu.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM atendimento.ajustes WHERE chave = 'pendencias.anexo_ligado') THEN
        RAISE EXCEPTION '061: o ajuste pendencias.anexo_ligado nao nasceu.';
    END IF;
    RAISE NOTICE '061 OK: o anexo na resposta do chamado';
END $$;
