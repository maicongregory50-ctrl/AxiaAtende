-- AxiaMarketing (dono, 29/10/2026) -- o informativo ao comprador: a comunicacao DIRETA com o boletim no
-- cabecalho, sem pedir de novo o aceite (ele veio no mutirao) e com a saida a mao do cliente.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- Por que um modelo novo: o convite da abertura do canal pedia "Quero receber" antes de mostrar o
-- boletim, e a capa tirou a atencao (o cliente principal: "passou batido, que numero e esse"); o
-- `epoca_de_plantio` o dono recusou ("parece uma oferta barata"). O informativo leva informacao para
-- subsidiar a compra, e o texto e FIXO: a imagem do cabecalho muda a cada envio sem nova aprovacao.
--
-- O botao novo, `parar_e_falar`: "Nao quero mais receber" (resposta rapida, a carga do convite
-- `envio:<id>:nao_quero`, que ja grava a recusa e avisa o responsavel) e "Falar com meu atendimento"
-- (o link do nosso endereco, o mesmo da direta).
--
-- O NOME e o TEXTO tem de ser os aprovados na Meta (`python -m backend.modelos_meta --propor`); modelo
-- aprovado nao se edita: texto novo e modelo novo.

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver', 'parar_e_falar'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao IN ('falar_responsavel', 'parar_e_falar'))
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver'));

-- O texto A, escolhido pelo dono em 29/10/2026.
INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('informativo_ao_comprador', 'MARKETING', 'direta', true, ARRAY['primeiro_nome'], 'parar_e_falar',
     'Olá, {{1}}! Aqui é a Sementes Renascer, com informação de mercado e de safra para apoiar as suas '
     'decisões de compra e mostrar um pouco mais do nosso trabalho.');

DO $$
BEGIN
    IF (SELECT count(*) FROM atendimento.modelos WHERE nome = 'informativo_ao_comprador') <> 1 THEN
        RAISE EXCEPTION '043: esperava UM informativo_ao_comprador.';
    END IF;
END $$;
