-- Desfaz a 019 (#1027). Devolve as SETE descricoes aos VALORES LITERAIS de 15/10/2026, lidos do
-- banco antes de a 019 ser escrita -- inclusive as cinco que estavam VAZIAS. Nao e um "apague
-- generico": e o estado de antes, copiado.
--
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py: "o _VOLTA.sql nunca e
-- aplicado sozinho; ele existe para a mao de quem desfaz"). Por isso abre a propria transacao e
-- apaga a linha de casa.mudancas.
--
-- Nada de atendimento e apagado: conversa, material de campo e frase anotada ficam.
BEGIN;

UPDATE atendimento.menu SET descricao = 'Cotar sementes'             WHERE chave = 'comercial';
UPDATE atendimento.menu SET descricao = 'Atendimento a fornecedores' WHERE chave = 'fornecedores';
UPDATE atendimento.menu SET descricao = ''                           WHERE chave = 'comercial.produtor';
UPDATE atendimento.menu SET descricao = ''                           WHERE chave = 'comercial.revenda';
UPDATE atendimento.menu SET descricao = ''                           WHERE chave = 'comercial.corretor';
UPDATE atendimento.menu SET descricao = ''                           WHERE chave = 'fornecedores.ja';
UPDATE atendimento.menu SET descricao = ''                           WHERE chave = 'fornecedores.ainda';

DELETE FROM casa.mudancas WHERE nome = '019_direcao_do_pedido.sql';

COMMIT;
