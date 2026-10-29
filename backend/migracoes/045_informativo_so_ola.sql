-- #1203 (dono, 29/10/2026) -- o informativo com uma linha so. Na prova do `informativo_renascer` (044) a
-- foto abriu inteira, mas o texto debaixo dela repetia o que a arte ja diz ("a arte ja e o texto que a
-- gente quer mandar, a gente construiu cuidadosamente aquele texto"). Fica o ola com o nome e o que e.
-- Os mesmos botoes da 044 (`parar_e_chamar`). Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('informativo_curto', 'MARKETING', 'direta', true, ARRAY['primeiro_nome'], 'parar_e_chamar',
     'Olá, {{1}}! Informativo da Sementes Renascer.');

DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.modelos WHERE nome = 'informativo_curto') <> 1 THEN
        RAISE EXCEPTION '045: esperava UM informativo_curto.';
    END IF;
END $$;
