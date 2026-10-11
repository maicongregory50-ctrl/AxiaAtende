-- Desfaz a 010 (o canal de campo, #970). O material ja buscado pelo marketing esta na Caixa ou no
-- catalogo de la; os arquivos em C:\Dados\AxiaAtende\campo nao sao apagados por aqui.
BEGIN;
DROP TABLE IF EXISTS atendimento.material_de_campo;
DELETE FROM atendimento.ajustes WHERE chave = 'campo.ligado';
DELETE FROM casa.mudancas WHERE nome = '010_canal_de_campo.sql';
COMMIT;
