-- Desfaz a 028 (#1099). A pergunta "mesmo" em aberto e limpa ANTES de o CHECK voltar (o grupo segue
-- para a proxima pergunta no laco do minuto, ou fecha).
BEGIN;
UPDATE atendimento.material_de_campo SET pergunta_pendente = NULL, retomar_em = NULL WHERE pergunta_pendente = 'mesmo';
ALTER TABLE atendimento.material_de_campo DROP CONSTRAINT material_pergunta;
ALTER TABLE atendimento.material_de_campo ADD CONSTRAINT material_pergunta
    CHECK (pergunta_pendente IN ('legenda', 'data', 'qual_dia', 'bastidor', 'produto', 'fase'));
ALTER TABLE atendimento.material_de_campo DROP COLUMN enviado_em;
ALTER TABLE atendimento.campo_frases DROP COLUMN enviado_em;
DELETE FROM atendimento.ajustes WHERE chave = 'campo.lote_pelo_envio';
DELETE FROM casa.mudancas WHERE nome = '028_lote_pelo_envio.sql';
COMMIT;
