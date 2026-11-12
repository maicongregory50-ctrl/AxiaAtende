-- #1474 (12/11/2026) -- As duas vagas do #1253/#1399 do marketing abertas no Trabalhe conosco, a
-- Comercial fechada (dono, 12/11/2026: "Comercial fechada"), e a resposta da LISTA das vagas:
-- com mais de uma aberta, quem vem pelo menu escolhe a dele (backend/vaga.py, `vagas_abertas`).
-- Os textos e requisitos sao os dos cards de C:\AxiaMarketing\docs\pecas\vagas\2026-11-05-*.md
-- (dono, 11/11/2026). Os `anuncio_ids` ficam vazios ate o dono criar os anuncios no Gerenciador.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.vagas SET aberta = false, fechada_em = now() WHERE id = 1 AND aberta;

INSERT INTO atendimento.vagas (titulo, requisitos, regiao, beneficios, anuncio_ids) VALUES
    ('Vaga Auxiliar de produção',
     ARRAY['Não exige experiência'],
     'O trabalho é na nossa unidade, em Cunha Porã (SC), de segunda a sexta, das 7h30 às 11h30 e das 13h30 às 18h.',
     'salário atrativo, plano de saúde Unimed, vale-alimentação, auxílio-combustível e auxílio-educação',
     '{}'),
    ('Vaga Operador de empilhadeira',
     ARRAY['Curso de operador de empilhadeira (NR-11)'],
     'O trabalho é na nossa unidade, em Cunha Porã (SC), de segunda a sexta, das 7h30 às 11h30 e das 13h30 às 18h.',
     'salário atrativo, plano de saúde Unimed, vale-alimentação, auxílio-combustível e auxílio-educação',
     '{}');

INSERT INTO atendimento.respostas_da_vaga (chave, descricao, texto, para_ia, ordem) VALUES
    ('pergunta_menu_varias', '',
     E'{saudacao} Obrigado pelo interesse em trabalhar na Sementes Renascer 🌱\n\nNo momento temos mais de uma vaga aberta. Toque em *Ver as vagas* e escolha a sua — ou *Outras áreas*, se o seu currículo é para outra função.',
     false, 1);

-- Conferencia dentro da transacao
DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.vagas WHERE aberta) <> 2 THEN
        RAISE EXCEPTION '062: esperava DUAS vagas abertas (Auxiliar de producao e Operador de empilhadeira).';
    END IF;
    IF (SELECT count(*) FROM atendimento.respostas_da_vaga WHERE chave = 'pergunta_menu_varias') <> 1 THEN
        RAISE EXCEPTION '062: esperava UMA resposta pergunta_menu_varias.';
    END IF;
END $$;
