-- #1528 -- o chamado no WhatsApp: a VOLTA COM ARQUIVO. Quem recebeu uma pergunta de chamado devolve o
-- documento (PDF, Word, Excel, foto) pelo WhatsApp, e ele entra no chamado no ERP, validado duas vezes.
-- Spec e plano: docs/specs/2026-11-16-chamado-no-whatsapp-a-volta-com-arquivo*.md.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py. A 067 e do #1525.
--
-- O QUE MUDA em `pendencias_mensagens` (o que volta, sentido 'entrou'):
--   classe 'arquivo': um arquivo que a pessoa mandou. `arquivo` (jsonb) guarda o que se sabe dele:
--     media_id, wamid, nome, mime, tamanho, caminho (a copia no transito), sha256, anexo_id (o ERP
--     aceitou), motivo/texto (o ERP recusou), avisado (a frase ja saiu), av_desde (o antivirus fora).
--   estados novos:
--     arquivo_a_validar -- baixado, esperando o ERP (as TELAS levam a POST /demandas/whatsapp/{id}/arquivo)
--     arquivo_validado  -- o ERP aceitou e devolveu o anexo_id; espera a rajada fechar
--     arquivo_recusado  -- o ERP recusou (ou o antivirus nao voltou em 1 h); a copia ja foi apagada
--     rajada            -- a CABECA da rajada (classe 'resposta'): o texto que acompanha os arquivos.
--                          Fecha quando `entregar_apos` passa (5 min de silencio, o decimo arquivo, ou
--                          um texto da pessoa em seguida). As TELAS mandam a resposta com os anexo_ids.
--     confirmar         -- o ERP gravou o comentario com os arquivos; o RECEPCIONISTA manda
--                          "Anotado no chamado N: 3 arquivos" e passa a 'entregue'.
--   `rajada_id`: a cabeca a que o arquivo pertence.
-- Os ajustes nascem com a chave DESLIGADA (D4, regra 8): desligada, o arquivo segue os caminhos de hoje.

ALTER TABLE atendimento.pendencias_mensagens DROP CONSTRAINT pend_msg_classe;
ALTER TABLE atendimento.pendencias_mensagens ADD CONSTRAINT pend_msg_classe
    CHECK (classe IN ('informativo', 'pergunta', 'entrega', 'resposta', 'validacao', 'arquivo'));

ALTER TABLE atendimento.pendencias_mensagens DROP CONSTRAINT pend_msg_estado;
ALTER TABLE atendimento.pendencias_mensagens ADD CONSTRAINT pend_msg_estado
    CHECK (estado IN ('esperando', 'guardada', 'enviada', 'escolher', 'a_entregar', 'entregue', 'descartada',
                      'erro', 'arquivo_a_validar', 'arquivo_validado', 'arquivo_recusado', 'rajada',
                      'confirmar'));

ALTER TABLE atendimento.pendencias_mensagens ADD COLUMN arquivo jsonb;
ALTER TABLE atendimento.pendencias_mensagens ADD COLUMN rajada_id bigint
    REFERENCES atendimento.pendencias_mensagens (id);

DROP INDEX atendimento.pend_msg_estado;
CREATE INDEX pend_msg_estado ON atendimento.pendencias_mensagens (estado)
    WHERE estado IN ('esperando', 'guardada', 'escolher', 'a_entregar', 'arquivo_a_validar',
                     'arquivo_validado', 'arquivo_recusado', 'rajada', 'confirmar');
CREATE INDEX pend_msg_rajada ON atendimento.pendencias_mensagens (rajada_id) WHERE rajada_id IS NOT NULL;

-- Os dois avisos ao suporte (D4, regra 3): o antivirus fora (e a volta dele) e a ameaca acusada.
-- O CHECK e REESCRITO INTEIRO (a licao da 033): os da 067 (#1525) + os dois daqui.
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro', 'lote_do_representante', 'status_do_dia', 'auditoria_estoque',
                    'integracao_recusada', 'painel_classe1', 'olivia_resumo', 'vaga_visita',
                    'arquivo_sem_antivirus', 'arquivo_ameaca'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1', 'aviso_olivia_resumo',
                   'aviso_vaga_visita', 'aviso_arquivo_sem_antivirus', 'aviso_arquivo_ameaca'));

-- O texto vem pronto ({{1}}); a Meta recusa corpo que comeca ou termina numa variavel.
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('arquivo_sem_antivirus', 'UTILITY', 'aviso_arquivo_sem_antivirus', false, ARRAY['aviso1'], 'nenhum',
     'Volta com arquivo: {{1}} O detalhe está na tela Envios.'),
    ('arquivo_ameaca', 'UTILITY', 'aviso_arquivo_ameaca', false, ARRAY['aviso1'], 'nenhum',
     'Arquivo recusado por ameaça: {{1}} Vale conferir o celular da pessoa.');

INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('pendencias.arquivo_volta', 'false'::jsonb),
    ('pendencias.rajada_minutos', '5'::jsonb),
    ('pendencias.rajada_teto', '10'::jsonb),
    ('pendencias.arquivo_dia_teto', '20'::jsonb)
ON CONFLICT (chave) DO NOTHING;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                    AND table_name = 'pendencias_mensagens' AND column_name IN ('arquivo', 'rajada_id')
                   HAVING count(*) = 2) THEN
        RAISE EXCEPTION '068: as colunas do arquivo nao nasceram.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'avisos_tipo'
                    AND pg_get_constraintdef(oid) LIKE '%olivia_resumo%'
                    AND pg_get_constraintdef(oid) LIKE '%vaga_visita%'
                    AND pg_get_constraintdef(oid) LIKE '%arquivo_ameaca%') THEN
        RAISE EXCEPTION '068: o CHECK de tipo do aviso perdeu tipos.';
    END IF;
    IF (SELECT valor FROM atendimento.ajustes WHERE chave = 'pendencias.arquivo_volta') IS DISTINCT FROM 'false'::jsonb THEN
        RAISE EXCEPTION '068: a chave pendencias.arquivo_volta nao nasceu desligada.';
    END IF;
    RAISE NOTICE '068 OK: a volta com arquivo (estados, colunas, avisos, ajustes), desligada';
END $$;
