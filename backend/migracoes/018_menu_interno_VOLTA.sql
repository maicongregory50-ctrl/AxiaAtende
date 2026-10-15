-- Desfaz a 018 (#1031). Apaga a raiz interna, as duas opcoes dela e a chave do reconhecimento.
-- NADA de atendimento e apagado: conversa, material de campo e frase anotada ficam.
--
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py: "o _VOLTA.sql nunca e
-- aplicado sozinho; ele existe para a mao de quem desfaz"). Por isso ele abre e fecha a propria
-- transacao e apaga a linha de casa.mudancas.
--
-- E quase sempre NAO e isto que se quer: para neutralizar o comportamento basta
--     UPDATE atendimento.ajustes SET valor = 'false' WHERE chave = 'interno.ligado';
-- sem restart e sem deploy. Este arquivo e para quando se quer o banco limpo tambem, e nesse caso
-- o CODIGO JA DEVE TER SIDO REVERTIDO -- senao o motor procura uma raiz interna que nao existe.
BEGIN;

DELETE FROM atendimento.menu
 WHERE pai_id = (SELECT id FROM atendimento.menu WHERE chave = 'raiz_interna');
DELETE FROM atendimento.menu WHERE chave = 'raiz_interna';
DELETE FROM atendimento.ajustes WHERE chave = 'interno.ligado';

-- Os dois CHECK voltam ao que eram. So passam porque as linhas que usavam os verbos novos acabaram
-- de ser apagadas acima -- se sobrar alguma, o banco recusa aqui, e esta certo recusar.
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_acao;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_acao
    CHECK (acao IN ('menu', 'destino', 'encerrar'));

ALTER TABLE atendimento.menu DROP CONSTRAINT menu_pergunta_so_no_menu;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_pergunta_so_no_menu
    CHECK (acao = 'menu' OR pergunta = '');

DELETE FROM casa.mudancas WHERE nome = '018_menu_interno.sql';

COMMIT;
