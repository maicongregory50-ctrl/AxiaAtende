-- Desfaz a 004 (so o texto; o modelo ja enviado a Meta nao volta por aqui).
BEGIN;
UPDATE atendimento.modelos
   SET texto = '{{1}}, chegou a época de {{2}}. Para garantir a sua semente, fale com {{3}} pelo botão abaixo.'
 WHERE nome = 'epoca_de_plantio';
DELETE FROM casa.mudancas WHERE nome = '004_modelo_nao_comeca_por_variavel.sql';
COMMIT;
