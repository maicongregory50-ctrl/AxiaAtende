-- #926, entrega 3 do Planejamento (o Controle, dono, 19/10/2026): o plano de marketing passou cinco
-- dias sem registro e nada lembrou. O Marketing confere uma vez por dia e PEDE o aviso por
-- POST /pedido/aviso; quem manda WhatsApp na casa e esta fila (decisao do #950).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- O aviso ao dono e o modelo de Utilidade dele (a Meta precisa aprovar:
-- `python -m backend.modelos_meta --propor`; sem o modelo aprovado o aviso fica na fila com o erro).
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou',
                    'plano_sem_registro'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou', 'aviso_plano_sem_registro'));

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('aviso_plano_sem_registro', 'UTILITY', 'aviso_plano_sem_registro', false, ARRAY['aviso1', 'aviso2'], 'nenhum',
     'O plano de marketing está há {{1}} dias sem registro (o último foi em {{2}}). Abra a sessão e rode /planejamento semana.');
