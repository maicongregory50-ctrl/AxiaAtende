-- #1182 (AxiaMarketing) -- desfaz a 037. O modelo `abertura_do_canal` JA ESTAVA APROVADO na Meta com o
-- texto da 036 (id 2661481667628841, conferido pelo dono com `modelos_meta --ver` em 28/10/2026), e o
-- proprio `--ver` aplicou a 037: o cadastro passou a ter um texto que a Meta nao conhece. Esta mudanca
-- devolve, letra por letra, o texto aprovado. Mudar o texto de novo e modelo NOVO (outro nome), com
-- aprovacao propria, nunca edicao deste. Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.modelos
   SET texto = 'Olá, {{1}}! A Sementes Renascer começou a falar com você por aqui, pelo WhatsApp. Como primeiro '
               'pacote, preparamos uma leitura da safra de inverno e uma dica para o momento. Toque em "Quero '
               'receber" e mandamos aqui na conversa.'
 WHERE nome = 'abertura_do_canal';
