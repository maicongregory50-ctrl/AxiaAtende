-- #1036, emenda do dono em 15/10/2026, minutos depois de ver a frase em producao: "vamos tirar o
-- 'voce e da equipe', ele sabe que e".
--
-- A frase nasceu na 020 como "Olá, {nome}! Você é da equipe — o que precisa?". Dizer a alguem da
-- casa que ele e da casa nao informa nada: ele ja sabe, e saber disso e justamente a razao de ele
-- estar vendo este menu e nao o do cliente.
--
-- ESTA MIGRACAO PODE SER UM NO-OP EM PRODUCAO, e e de proposito: o texto e CADASTRO, e o dono o
-- trocou a mao no mesmo minuto com um UPDATE -- sem restart e sem deploy, que e o que o desenho da
-- 020 existe para permitir. Ela esta aqui para que uma INSTALACAO NOVA e o git nao discordem do que
-- esta no ar. Mudanca aplicada nao se edita (regra 2 de backend/migracoes.py), entao corrigir a 020
-- seria derrubar o servico pelo sha256: o conserto e mudanca nova, e esta e ela.
--
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.menu
   SET pergunta = 'Olá, {nome}! O que precisa?'
 WHERE chave = 'raiz_interna';
