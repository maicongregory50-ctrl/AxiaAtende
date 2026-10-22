-- Desfaz a 025 (o Trabalhe conosco, #1098). O no "Trabalhe conosco" volta a mandar o cartao da Fran.
-- AS TABELAS vagas, candidaturas e respostas_da_vaga FICAM: sao curriculos com consentimento e o
-- retorno da Fran; apaga-las e decisao do dono, por arquivo proprio (spec, ROLLBACK 4). Por isso a
-- coluna conversas.vaga_id tambem fica (a candidatura aponta a conversa).
BEGIN;
UPDATE atendimento.conversas SET situacao = 'encerrada'
 WHERE situacao IN ('curriculo_recebido', 'sem_curriculo');
UPDATE atendimento.conversas SET situacao = 'encerrada'
 WHERE situacao = 'em_curso' AND vaga_id IS NOT NULL;
ALTER TABLE atendimento.conversas DROP CONSTRAINT conversas_situacao;
ALTER TABLE atendimento.conversas ADD CONSTRAINT conversas_situacao
    CHECK (situacao IN ('em_curso', 'com_link', 'parou_no_meio', 'encerrada', 'envio'));

UPDATE atendimento.menu SET acao = 'destino' WHERE acao = 'vaga';
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_destino_so_na_folha;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_destino_so_na_folha
    CHECK ((acao = 'destino') = (destino_id IS NOT NULL));
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_acao;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_acao
    CHECK (acao IN ('menu', 'destino', 'encerrar', 'texto', 'menu_cliente'));

DELETE FROM atendimento.modelos WHERE uso = 'curriculo';
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_variaveis;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_variaveis CHECK (variaveis <@ ARRAY[
    'primeiro_nome', 'nome', 'assunto', 'peca', 'n_imagens', 'responsavel',
    'aviso1', 'aviso2', 'aviso3']::text[]);
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao = 'falar_responsavel')
    OR (uso LIKE 'aviso%' AND botao = 'nenhum'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_categoria_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_categoria_do_uso CHECK (
    (uso IN ('convite', 'direta') AND categoria = 'MARKETING')
    OR (uso LIKE 'aviso%' AND categoria IN ('UTILITY', 'MARKETING')));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro'));
ALTER TABLE atendimento.modelos DROP COLUMN cabecalho_documento;
DELETE FROM casa.mudancas WHERE nome = '025_trabalhe_conosco.sql';
COMMIT;
