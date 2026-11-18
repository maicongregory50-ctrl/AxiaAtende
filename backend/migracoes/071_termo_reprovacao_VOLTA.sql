-- #1542 -- a VOLTA da 071. Antes: TERMO_REPROVACAO_ATIVO=false no .env.recepcionista e a chave do ERP
-- (REPROVACAO_ENVIA_WHATSAPP) desligada. O modelo na Meta fica (modelo nao se apaga); aqui sai so o cadastro.
-- O que ja foi devolvido ao ERP (estado e ciencia) fica la.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM casa.mudancas WHERE nome = '071_termo_reprovacao.sql';
DELETE FROM atendimento.modelos WHERE uso = 'termo_reprovacao';
DROP TABLE atendimento.termos_reprovacao;
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_variaveis;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_variaveis CHECK (variaveis <@ ARRAY[
    'primeiro_nome', 'nome', 'assunto', 'peca', 'n_avisos', 'n_imagens', 'responsavel',
    'aviso1', 'aviso2', 'aviso3',
    'vaga', 'candidato', 'declarou', 'req1', 'req2', 'req3', 'req4', 'resumo']::text[]);
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao_do_uso CHECK (
    (uso = 'convite' AND botao = 'quero_nao_quero')
    OR (uso = 'direta' AND botao IN ('falar_responsavel', 'parar_e_falar', 'parar_e_chamar'))
    OR (uso LIKE 'aviso%' AND botao = 'nenhum')
    OR (uso = 'curriculo' AND botao = 'triagem')
    OR (uso = 'reabertura' AND botao = 'ver'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_botao;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_botao
    CHECK (botao IN ('nenhum', 'quero_nao_quero', 'falar_responsavel', 'triagem', 'ver', 'parar_e_falar',
                     'parar_e_chamar'));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_categoria_do_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_categoria_do_uso CHECK (
    (uso IN ('convite', 'direta') AND categoria = 'MARKETING')
    OR ((uso LIKE 'aviso%' OR uso IN ('curriculo', 'reabertura')) AND categoria IN ('UTILITY', 'MARKETING')));
ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro',
                   'aviso_lote_do_representante', 'curriculo', 'reabertura', 'aviso_auditoria_estoque',
                   'aviso_integracao_recusada', 'aviso_painel_classe1', 'aviso_olivia_resumo',
                   'aviso_vaga_visita', 'aviso_arquivo_sem_antivirus', 'aviso_arquivo_ameaca'));
