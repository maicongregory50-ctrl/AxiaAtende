-- VOLTA da 037 (#1182). Nunca e aplicada junto com a ida.
--
-- Devolve o texto da 036. CUIDADO: se o modelo ja foi aprovado na Meta com o texto da 037, o texto do
-- cadastro tem de continuar igual ao da Meta; voltar aqui so faz sentido antes de mandar a Meta.
BEGIN;

UPDATE atendimento.modelos
   SET texto = 'Olá, {{1}}! A Sementes Renascer começou a falar com você por aqui, pelo WhatsApp. Como primeiro '
               'pacote, preparamos uma leitura da safra de inverno e uma dica para o momento. Toque em "Quero '
               'receber" e mandamos aqui na conversa.'
 WHERE nome = 'abertura_do_canal';

DELETE FROM casa.mudancas WHERE nome = '037_texto_da_abertura_do_canal.sql';
COMMIT;
