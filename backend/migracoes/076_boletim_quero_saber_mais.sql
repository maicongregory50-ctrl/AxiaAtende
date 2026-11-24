-- #1754 (24/11/2026) -- o modelo do boletim com "Quero saber mais". Spec e plano:
-- docs/specs/2026-11-24-olivia-atende-a-carteira-no-boletim*.md (D2). So o CADASTRO do modelo: a tabela de
-- interesses, a coluna das culturas e a chave vem na 077. Separada de proposito: o dono propoe o modelo a Meta
-- (`python -m backend.modelos_meta --propor --so boletim_quero_saber_mais`), e o `--propor` aplica as mudancas
-- pendentes antes de ler o cadastro -- a 076 entra em producao nessa hora, sozinha, sem mudar nada para ninguem.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- O botao novo, `saber_e_parar`: as DUAS respostas rapidas. "Quero saber mais" (`envio:<id>:saber`) volta ao
-- recepcionista (envio.tratar_toque): com a chave olivia.atende_carteira ligada, a saudacao, a versao maior e o
-- texto da parceria, e a OlivIA conversa; desligada, a linha do representante, como o "falar" de hoje. "Nao
-- quero receber" e a recusa de sempre. Sem "Falar com meu atendimento" (D2): quem quer a pessoa pede na conversa.
-- Cada constraint repete a lista INTEIRA de hoje (a da 071) com o valor novo.

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver', 'parar_e_falar',
                     'parar_e_chamar', 'ciente', 'saber_e_parar'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao IN ('falar_responsavel', 'parar_e_falar', 'parar_e_chamar', 'saber_e_parar'))
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver')
    OR (uso = 'termo_reprovacao' AND botao = 'ciente'));

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('boletim_quero_saber_mais', 'MARKETING', 'direta', true, ARRAY['primeiro_nome'], 'saber_e_parar',
     'Olá, {{1}}! Saiu o boletim de safra da Sementes Renascer, com a leitura do mercado de sementes para '
     'esta safra. Toque em "Quero saber mais" e mandamos o material completo aqui na conversa.');

DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.modelos WHERE nome = 'boletim_quero_saber_mais'
          AND botao = 'saber_e_parar' AND uso = 'direta' AND categoria = 'MARKETING') <> 1 THEN
        RAISE EXCEPTION '076: esperava UM boletim_quero_saber_mais (direta, MARKETING, saber_e_parar).';
    END IF;
END $$;
