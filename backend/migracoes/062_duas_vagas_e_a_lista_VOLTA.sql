-- #1474 -- a VOLTA da 062: as duas vagas e a resposta da lista saem. RECUSA se ja ha curriculo
-- para alguma das duas (apagar candidatura e decisao de gente, nao de rollback). A Comercial NAO
-- e reaberta: fechar vaga e gesto do dono (o botao Fechar vaga), e a volta nao o desfaz.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DO $$
DECLARE
    n BIGINT;
BEGIN
    SELECT count(*) INTO n FROM atendimento.candidaturas c
      JOIN atendimento.vagas v ON v.id = c.vaga_id
     WHERE v.titulo IN ('Vaga Auxiliar de produção', 'Vaga Operador de empilhadeira');
    IF n > 0 THEN
        RAISE EXCEPTION '062 VOLTA: ha % curriculo(s) para as vagas que sairiam; nao se apaga candidatura por rollback.', n;
    END IF;
END $$;

UPDATE atendimento.conversas SET vaga_id = NULL
 WHERE vaga_id IN (SELECT id FROM atendimento.vagas
                    WHERE titulo IN ('Vaga Auxiliar de produção', 'Vaga Operador de empilhadeira'));
DELETE FROM atendimento.vagas WHERE titulo IN ('Vaga Auxiliar de produção', 'Vaga Operador de empilhadeira');
DELETE FROM atendimento.respostas_da_vaga WHERE chave = 'pergunta_menu_varias';
DELETE FROM casa.mudancas WHERE nome = '062_duas_vagas_e_a_lista.sql';
