-- #1182 (AxiaMarketing) -- o modelo da abertura do canal com o comprador (dono, 28/10/2026). Spec:
-- C:\AxiaMarketing\docs\specs\2026-10-28-campanhas-por-trilha-e-a-abertura-do-canal.md (plano ao lado,
-- passo 7). Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- A PRIMEIRA MENSAGEM ao cliente da carteira: o aviso de que a Renascer passou a falar com ele por
-- aqui, com o primeiro pacote (a leitura de safra e uma arte util) depois do "Quero receber". E um
-- CONVITE, como o das revendas: os botoes gravam o aceite, e as imagens vao depois do toque, sem custo.
-- O marketing o manda a lista do comprador (so a quem disse sim no cadastro), como pedido `material`.
--
-- O NOME e o TEXTO tem de ser os aprovados na Meta (o dono cadastra o modelo la, uma vez, com este
-- nome): o AxiaAtende manda pelo nome, e a Meta recusa o que nao bate.

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('abertura_do_canal', 'MARKETING', 'convite', true, ARRAY['primeiro_nome'], 'quero_nao_quero',
     'Olá, {{1}}! A Sementes Renascer começou a falar com você por aqui, pelo WhatsApp. Como primeiro '
     'pacote, preparamos uma leitura da safra de inverno e uma dica para o momento. Toque em "Quero '
     'receber" e mandamos aqui na conversa.');
