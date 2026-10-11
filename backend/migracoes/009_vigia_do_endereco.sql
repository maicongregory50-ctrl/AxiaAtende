-- #969, etapa 3 (dono, 11/10/2026): o vigia do endereco publico. Em 09/10 o nome do Funnel sumiu do
-- DNS publico, a Meta ficou um dia e meio sem achar o recepcionista e nada avisou.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- Uma linha so: como o endereco esta, desde quando, e a ultima conferencia.
CREATE TABLE atendimento.vigia_endereco (
    unica        boolean PRIMARY KEY DEFAULT true CONSTRAINT vigia_endereco_unica CHECK (unica),
    situacao     text NOT NULL CONSTRAINT vigia_endereco_situacao CHECK (situacao IN ('no_ar', 'fora')),
    desde        timestamptz NOT NULL,
    falhas       smallint NOT NULL DEFAULT 0,       -- "nao existe" seguidos; dois = fora
    conferido_em timestamptz
);

-- Os dois avisos ao gestor e os modelos de Utilidade deles (a Meta precisa aprovar:
-- `python -m backend.modelos_meta --propor`; sem o modelo aprovado o aviso fica na fila com o erro).
ALTER TABLE atendimento.avisos DROP CONSTRAINT avisos_tipo;
ALTER TABLE atendimento.avisos ADD CONSTRAINT avisos_tipo
    CHECK (tipo IN ('recusa', 'sem_atendimento', 'avaliacao_ruim', 'endereco_fora', 'endereco_voltou'));

ALTER TABLE atendimento.modelos DROP CONSTRAINT modelos_uso;
ALTER TABLE atendimento.modelos ADD CONSTRAINT modelos_uso
    CHECK (uso IN ('convite', 'direta', 'aviso_recusa', 'aviso_sem_atendimento', 'aviso_avaliacao_ruim',
                   'aviso_endereco_fora', 'aviso_endereco_voltou'));

INSERT INTO atendimento.modelos (nome, categoria, uso, cabecalho_imagem, variaveis, botao, texto) VALUES
    ('aviso_endereco_fora', 'UTILITY', 'aviso_endereco_fora', false, ARRAY['aviso1', 'aviso2'], 'nenhum',
     'Aviso do atendimento: o endereço público {{1}} saiu do ar em {{2}}. As mensagens do WhatsApp não chegam até ele voltar. Obrigado.'),
    ('aviso_endereco_voltou', 'UTILITY', 'aviso_endereco_voltou', false, ARRAY['aviso1', 'aviso2', 'aviso3'], 'nenhum',
     'Aviso do atendimento: o endereço público {{1}} voltou ao ar em {{2}}, depois de {{3}} fora. Obrigado.');
