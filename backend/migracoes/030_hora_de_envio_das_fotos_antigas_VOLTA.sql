-- Desfaz a 030 (#1099): as linhas de antes da 028 voltam sem a hora de envio (valem pela chegada).
-- A 028 entrou no reinicio da tarde de 22/10/2026; nada de campo chegou entre 15:17 e esse reinicio.
BEGIN;
UPDATE atendimento.material_de_campo SET enviado_em = NULL WHERE recebido_em < '2026-10-22 15:17:00-03';
UPDATE atendimento.campo_frases SET enviado_em = NULL WHERE recebido_em < '2026-10-22 15:17:00-03';
DELETE FROM casa.mudancas WHERE nome = '030_hora_de_envio_das_fotos_antigas.sql';
COMMIT;
