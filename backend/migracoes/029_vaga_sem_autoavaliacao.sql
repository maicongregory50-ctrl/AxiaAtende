-- #1098 (dono, 22/10/2026, depois dos primeiros candidatos reais): a pergunta "Voce atende a esses
-- requisitos?" sai. Dos 10 que tocaram um botao, 8 disseram "Nao atendo todos" e 5 deles mandaram o
-- curriculo assim mesmo; a Fran marcou "Triagem certa" nas 4 que avaliou. O dono: "a gente faz a
-- triagem e analisa se o candidato atende; nao precisamos perguntar para ele se autoavaliar".
-- A abertura passa a pedir o PDF direto. E quem chega pelo MENU (e nao pelo anuncio) escolhe antes se
-- o curriculo e para a vaga aberta ou para outras areas (banco de curriculos, sem triagem): senao o
-- curriculo de quem procura armazem ia a Fran triado contra os requisitos comerciais.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
UPDATE atendimento.respostas_da_vaga
   SET texto = E'{saudacao} Obrigado pelo interesse na *{vaga}* da Sementes Renascer 🌱\n\nO anúncio pede:\n{requisitos}\n\nMande aqui o seu *currículo em PDF*.\n\nAo enviar, você autoriza a Renascer a guardar o currículo e a usar uma ferramenta de análise para a pré-triagem; a decisão é sempre de uma pessoa da equipe.'
 WHERE chave = 'abertura';

INSERT INTO atendimento.respostas_da_vaga (chave, descricao, texto, para_ia, ordem) VALUES
    ('pergunta_menu', '', E'{saudacao} Obrigado pelo interesse em trabalhar na Sementes Renascer 🌱\n\nNo momento temos aberta a *{vaga}*. O seu currículo é para ela ou para outras áreas?', false, 1),
    ('pedir_pdf_banco', '', E'Mande aqui o seu *currículo em PDF*: ele fica guardado para as próximas vagas.\n\nAo enviar, você autoriza a Renascer a guardar o currículo e a usar uma ferramenta de análise; a decisão é sempre de uma pessoa da equipe.', false, 3);
