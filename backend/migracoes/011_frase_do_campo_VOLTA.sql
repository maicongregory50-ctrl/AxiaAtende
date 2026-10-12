-- Desfaz a 011 (#970, a frase antes da foto). Nada de atendimento e apagado.
BEGIN;
DROP TABLE IF EXISTS atendimento.campo_frases;
DELETE FROM casa.mudancas WHERE nome = '011_frase_do_campo.sql';
COMMIT;
