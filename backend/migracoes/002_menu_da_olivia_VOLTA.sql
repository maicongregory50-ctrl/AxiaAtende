-- #950 -- desfaz a 002 (a semente do menu). So para a mao de quem desfaz, e so antes da troca do
-- dia: depois dela, as conversas apontam para o menu e para os destinos.
-- Um DELETE so para o menu: a chave estrangeira do pai e conferida no fim do comando.
BEGIN;
DELETE FROM atendimento.ajustes;
DELETE FROM atendimento.menu;
DELETE FROM atendimento.destinos;
DELETE FROM casa.mudancas WHERE nome = '002_menu_da_olivia.sql';
COMMIT;
