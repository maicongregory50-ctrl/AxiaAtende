-- #950, G4: a Meta recusa modelo cujo corpo COMECA ou TERMINA numa variavel. O epoca_de_plantio
-- comecava em {{1}}; passa a comecar por "Olá, ", como o convite. As variaveis nao mudam.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
UPDATE atendimento.modelos
   SET texto = 'Olá, {{1}}! Chegou a época de {{2}}. Para garantir a sua semente, fale com {{3}} pelo botão abaixo.'
 WHERE nome = 'epoca_de_plantio'
   AND texto = '{{1}}, chegou a época de {{2}}. Para garantir a sua semente, fale com {{3}} pelo botão abaixo.';
