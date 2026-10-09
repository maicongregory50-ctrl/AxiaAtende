-- #969, etapa 1: reconhecer quem chama e ja esta no cadastro do ERP. So REGISTRA: nada muda no que
-- a pessoa recebe (dono, 09/10/2026). Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- A agenda de numeros do cadastro, lida do ERP uma vez por dia (GET /atendimento/agenda, agente
-- ATENDIMENTO). Trocada inteira a cada leitura. So o que o atendimento precisa: nada de valor,
-- credito, salario ou documento.
CREATE TABLE atendimento.agenda (
    numero        text NOT NULL,                 -- 55 + DDD + 9 + oito digitos
    codigo        integer NOT NULL,              -- o codigo do cadastro no ERP
    nome          text NOT NULL DEFAULT '',
    papeis        text[] NOT NULL DEFAULT '{}',  -- equipe, representante, cliente, produtor, fornecedor
    contato_setor text NOT NULL DEFAULT '',      -- comercial, financeiro, fiscal
    contato_nome  text NOT NULL DEFAULT '',
    PRIMARY KEY (numero, codigo)
);

-- Cada leitura, certa ou errada: a tela diz "cadastro lido em ..." e o erro, se houve.
CREATE TABLE atendimento.agenda_leitura (
    id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lida_em timestamptz NOT NULL DEFAULT now(),
    linhas  integer,
    erro    text NOT NULL DEFAULT ''
);

-- O retrato do momento em que a conversa chegou (`erp_codigo` ja existe desde a 001).
-- `erp_cadastros`: quantos cadastros casaram com o numero. NULL = a agenda nao estava carregada;
-- 0 = fora do cadastro; 1 = reconhecido; 2+ = numero em mais de um cadastro (nada e escolhido).
ALTER TABLE atendimento.conversas
    ADD COLUMN erp_nome          text,
    ADD COLUMN erp_papeis        text[],
    ADD COLUMN erp_contato_setor text,
    ADD COLUMN erp_contato_nome  text,
    ADD COLUMN erp_cadastros     integer;
