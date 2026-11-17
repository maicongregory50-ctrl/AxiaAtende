-- #1525 (17/11/2026) -- Os dois anuncios das vagas, que o dono criou no Gerenciador da Meta em 12/11,
-- ligados cada um a sua vaga. A 062 deixou `anuncio_ids` vazio "ate o dono criar os anuncios", e ninguem
-- voltou: desde 12/11, 51 mensagens chegaram com o `referral` desses dois anuncios e nenhuma foi
-- reconhecida como de vaga (`vaga.vaga_aberta(con, anuncio)` casa pelo id). A pessoa ouvia "vagas de
-- trabalho, comprar sementes ou outro assunto?" em vez de ser recebida na vaga.
-- Qual e de qual: o dono confirmou o 120250019686590192 como o da empilhadeira; o outro e o do auxiliar.
-- O que as pessoas escolheram depois bate: 18 de 19 do primeiro foram a Empilhadeira, 12 de 15 do segundo
-- ao Auxiliar. As publicacoes: instagram.com/p/DfpsTafg9Mf/ (empilhadeira) e /p/DfpsGZnAIp5/ (auxiliar).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

UPDATE atendimento.vagas SET anuncio_ids = ARRAY['120250019686590192']
 WHERE titulo = 'Vaga Operador de empilhadeira';
UPDATE atendimento.vagas SET anuncio_ids = ARRAY['120250019668190192']
 WHERE titulo = 'Vaga Auxiliar de produção';

-- Conferencia dentro da transacao
DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.vagas WHERE '120250019686590192' = ANY(anuncio_ids)
                                                 AND titulo = 'Vaga Operador de empilhadeira') <> 1 THEN
        RAISE EXCEPTION '069: o anuncio da empilhadeira nao ficou na vaga Operador de empilhadeira.';
    END IF;
    IF (SELECT count(*) FROM atendimento.vagas WHERE '120250019668190192' = ANY(anuncio_ids)
                                                 AND titulo = 'Vaga Auxiliar de produção') <> 1 THEN
        RAISE EXCEPTION '069: o anuncio do auxiliar nao ficou na vaga Auxiliar de producao.';
    END IF;
END $$;
