-- Desfaz a 005. So antes de existir toque 'falar' gravado (ele vira 'texto').
BEGIN;
UPDATE atendimento.envio_destinatarios SET resposta = 'texto' WHERE resposta = 'falar';
ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_resposta;
ALTER TABLE atendimento.envio_destinatarios ADD CONSTRAINT envio_dest_resposta
    CHECK (resposta IN ('quero', 'nao_quero', 'texto'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
UPDATE atendimento.modelos SET botao = 'link_responsavel' WHERE botao = 'falar_responsavel';
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'link_responsavel'));
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao = 'link_responsavel')
    OR (uso LIKE 'aviso%' AND botao = 'nenhum'));
DELETE FROM casa.mudancas WHERE nome = '005_direta_por_toque.sql';
COMMIT;
