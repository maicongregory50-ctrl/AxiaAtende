-- #969: a nota da pesquisa em TRES botoes direto na tela (Bom, Normal, Ruim), no lugar da lista de
-- cinco, e a nota Ruim avisa o gestor como o "Nao" ja avisa (dono, 11/10/2026).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- `conversas.satisfacao` passa a guardar 3 (bom), 2 (normal), 1 (ruim). O CHECK de 1 a 5 fica: ele
-- cobre a escala nova, e nenhuma nota tinha sido gravada na escala antiga ate esta data.

-- O aviso da nota ruim: tipo novo na fila e o modelo de Utilidade dele (a Meta precisa aprovar:
-- `python -m backend.modelos_meta --propor`; ate la o aviso fica na fila com o erro e a nota na tela).
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim'));

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('aviso_avaliacao_ruim', 'UTILITY', 'aviso_avaliacao_ruim', false, ARRAY['aviso1', 'aviso2', 'aviso3'], 'nenhum',
     'Aviso do atendimento: {{1}} avaliou como ruim o atendimento sobre {{2}}. Contato: {{3}}. Obrigado.');
