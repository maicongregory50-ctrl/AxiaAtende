-- #950 (decisao do dono, 09/10/2026): a Meta recusa botao de modelo com link direto para o WhatsApp
-- ("Os botoes nao podem conter links diretos para o WhatsApp"). O botao "Falar com meu atendimento"
-- passa a abrir o NOSSO endereco (/falar/<codigo>), que anota o toque (resposta 'falar') e manda
-- para o WhatsApp do responsavel na hora: um toque so, do modelo a conversa.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
UPDATE atendimento.modelos SET botao = 'falar_responsavel' WHERE botao = 'link_responsavel';
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel'));
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao = 'falar_responsavel')
    OR (uso LIKE 'aviso%' AND botao = 'nenhum'));

ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_resposta;
ALTER TABLE atendimento.envio_destinatarios ADD CONSTRAINT envio_dest_resposta
    CHECK (resposta IN ('quero', 'nao_quero', 'texto', 'falar'));
