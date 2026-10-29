-- #1203 (dono, 29/10/2026) -- o informativo SEM botao de link. Na prova do `informativo_ao_comprador`
-- (043) o toque na FOTO abriu o link do "Falar com meu atendimento": com botao de link no modelo, o
-- WhatsApp leva a imagem do cabecalho para ele, e o boletim nao abria inteiro. O dono: "cada botao
-- ganha sua funcao e a imagem deixa de ser um link".
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- O botao novo, `parar_e_chamar`: as DUAS respostas rapidas. "Nao quero mais receber" e a recusa de
-- sempre; "Falar com meu atendimento" (`envio:<id>:falar`) volta ao recepcionista, que anota o toque e
-- responde com a linha do representante (envio.tratar_toque). O mesmo texto A da 043; botao faz parte
-- do modelo aprovado, entao e modelo novo, com outro nome. A 043 fica no cadastro, sem uso.

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver', 'parar_e_falar',
                     'parar_e_chamar'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao IN ('falar_responsavel', 'parar_e_falar', 'parar_e_chamar'))
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver'));

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('informativo_renascer', 'MARKETING', 'direta', true, ARRAY['primeiro_nome'], 'parar_e_chamar',
     'Olá, {{1}}! Aqui é a Sementes Renascer, com informação de mercado e de safra para apoiar as suas '
     'decisões de compra e mostrar um pouco mais do nosso trabalho.');

DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.modelos WHERE nome = 'informativo_renascer') <> 1 THEN
        RAISE EXCEPTION '044: esperava UM informativo_renascer.';
    END IF;
END $$;
