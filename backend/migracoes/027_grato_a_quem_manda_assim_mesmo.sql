-- #1098 (dono, 22/10/2026, lendo a conversa do 1o candidato real): quem toca "Nao atendo todos" e
-- depois "Mandar curriculo" recebia "Otimo! Mande aqui o seu curriculo em PDF", o texto de quem atende
-- a todos. O dono: "Grato, talvez, de otimo". O pedido do PDF ganha a versao desse caminho.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
INSERT INTO atendimento.respostas_da_vaga (chave, descricao, texto, para_ia, ordem) VALUES
    ('pedir_pdf_assim', '', E'Grato! Mande aqui o seu *currículo em PDF*.\n\nAo enviar, você autoriza a Renascer a guardar o currículo e a usar uma ferramenta de análise para a pré-triagem; a decisão é sempre de uma pessoa da equipe.', false, 3);
