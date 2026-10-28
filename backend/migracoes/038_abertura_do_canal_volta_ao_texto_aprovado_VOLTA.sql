-- VOLTA da 038 (#1182). Nunca e aplicada junto com a ida.
--
-- NAO APLIQUE enquanto o modelo aprovado na Meta tiver o texto da 036: a volta poe no cadastro o texto
-- da 037, que a Meta nao conhece. Existe so pela regra de toda mudanca ter a sua volta.
BEGIN;

UPDATE atendimento.modelos
   SET texto = 'Olá, {{1}}! Aqui é a Sementes Renascer, agora também pelo WhatsApp. Daqui para frente '
               'vamos mandar por aqui informação útil de safra: o clima, a oferta de semente e o que vem '
               'pela frente. Para começar, preparamos um boletim da safra de inverno. Quer receber?'
 WHERE nome = 'abertura_do_canal';

DELETE FROM casa.mudancas WHERE nome = '038_abertura_do_canal_volta_ao_texto_aprovado.sql';
COMMIT;
