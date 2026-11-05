-- #1169 (dono, 05/11/2026): segurar o envio a carteira pela tela Envios -- por envio (Suspender, Religar)
-- e o "segurar tudo". O estado `suspenso` existe desde a 001 e o despacho de lotes ja o ignora; aqui
-- entram QUEM e QUANDO (o registro que o script do #1203 nao deixava) e a chave geral, desligada.
-- `suspenso_por`: o login de quem clicou; 'segurar tudo' quando o envio parou porque a chave geral foi
-- ligada (e volta sozinho quando ela desliga); 'chegou no segurar tudo' quando o pedido nasceu com a
-- chave ligada (fica suspenso ate alguem religar, decisao do dono); 'script:<usuario>' pelo script.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.envios
    ADD COLUMN suspenso_por text,
    ADD COLUMN suspenso_em timestamptz;

INSERT INTO atendimento.ajustes (chave, valor) VALUES ('envio.segurar', '{"ligado": false}'::jsonb)
ON CONFLICT (chave) DO NOTHING;
