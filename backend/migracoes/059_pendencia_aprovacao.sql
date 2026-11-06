-- #1276 (dono, 06/11/2026): o aviso de aprovação no WhatsApp. A pendência ganha o tipo `aprovacao`
-- (o pedido que espera a etapa que a pessoa aprova), sempre informativo: sai só com a janela aberta,
-- nunca chama a reabertura paga. A chave nasce DESLIGADA; liga depois da prova das telas do celular.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.pendencias DROP CONSTRAINT pendencias_tipo;
ALTER TABLE atendimento.pendencias ADD CONSTRAINT pendencias_tipo CHECK (tipo IN ('chamado', 'aprovacao'));

INSERT INTO atendimento.ajustes (chave, valor) VALUES ('pendencias.aprovacao.ligado', 'false'::jsonb)
ON CONFLICT (chave) DO NOTHING;
