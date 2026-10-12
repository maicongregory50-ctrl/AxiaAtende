-- Desfaz a 013 (#970, o atendente de campo com objetivo). Nada de atendimento e apagado.
BEGIN;
ALTER TABLE atendimento.material_de_campo DROP CONSTRAINT material_pergunta;
UPDATE atendimento.material_de_campo SET pergunta_pendente = NULL
 WHERE pergunta_pendente IN ('bastidor', 'produto', 'fase');
ALTER TABLE atendimento.material_de_campo ADD CONSTRAINT material_pergunta
    CHECK (pergunta_pendente IN ('legenda', 'data', 'qual_dia'));
ALTER TABLE atendimento.material_de_campo
    DROP COLUMN classe_bastidor, DROP COLUMN classe_produto, DROP COLUMN classe_fase, DROP COLUMN lida_em,
    DROP COLUMN pergunta_n, DROP COLUMN retomar_em, DROP COLUMN retomada, DROP COLUMN fechado_em,
    DROP COLUMN desistiu_em, DROP COLUMN classe_aplicada_em;
DELETE FROM atendimento.ajustes WHERE chave = 'campo.produtos';
DELETE FROM casa.mudancas WHERE nome = '013_atendente_de_campo.sql';
COMMIT;
