-- #950 -- desfaz a 001. SO PARA A MAO DE QUEM DESFAZ, e nunca em producao com consentimento
-- gravado: o consentimento e a prova do aceite e da recusa (regra 4 do CLAUDE.md). Antes de rodar
-- em producao, exportar atendimento.consentimentos (pg_dump -t) e guardar a copia.
BEGIN;
DROP SCHEMA atendimento CASCADE;
DROP TABLE casa.sessoes;
DROP TABLE casa.usuarios;
DELETE FROM casa.mudancas WHERE nome = '001_casa_e_atendimento.sql';
COMMIT;
