-- Desfaz a 022 (#1048): apaga a linha do cadastro de bastidores.
--
-- NADA de atendimento e apagado, e nenhuma peca e tocada: as que ficaram com classe nova (`estoque`,
-- `estrutura`, `produto-embalagem`, `manejo`) CONTINUAM com ela -- `classe_bastidor` e texto livre,
-- sem CHECK, entao o valor segue legivel. O que elas perdem e o rotulo vindo do cadastro.
--
-- E QUASE SEMPRE NAO E ISTO QUE SE QUER: reverter so o CODIGO ja basta na pratica. Com a linha no
-- banco e o codigo antigo, `campo.BASTIDORES` volta a ser a verdade e a linha e simplesmente
-- IGNORADA -- nenhum efeito, nenhum erro. Este arquivo e para quem quer o banco limpo tambem.
--
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py: "o _VOLTA.sql nunca e
-- aplicado sozinho; ele existe para a mao de quem desfaz"). Por isso abre a propria transacao e
-- apaga a linha de casa.mudancas. O CODIGO JA DEVE TER SIDO REVERTIDO antes dele -- senao
-- `bastidores(con)` cai na semente de cinco, e as quatro novas ficam sem rotulo.
BEGIN;

DELETE FROM atendimento.ajustes WHERE chave = 'campo.bastidores';

DELETE FROM casa.mudancas WHERE nome = '022_bastidores_em_cadastro.sql';

COMMIT;
