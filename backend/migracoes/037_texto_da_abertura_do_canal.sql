-- #1182 (AxiaMarketing) -- o texto da abertura do canal, reescrito com o dono em 28/10/2026, ANTES de o
-- modelo ir a Meta: a primeira mensagem diz ola, diz o que vai chegar por aqui daqui para frente
-- (informacao util de safra) e pergunta se ele quer o primeiro boletim. Sem prometer "sem oferta": a
-- oferta de novembro chega pelo mesmo canal. Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- O NOME continua o mesmo; o texto tem de ser o que a Meta aprovar. `python -m backend.modelos_meta
-- --propor` aplica esta mudanca antes de mandar.

UPDATE atendimento.modelos
   SET texto = 'Olá, {{1}}! Aqui é a Sementes Renascer, agora também pelo WhatsApp. Daqui para frente '
               'vamos mandar por aqui informação útil de safra: o clima, a oferta de semente e o que vem '
               'pela frente. Para começar, preparamos um boletim da safra de inverno. Quer receber?'
 WHERE nome = 'abertura_do_canal';
