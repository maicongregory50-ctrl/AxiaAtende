-- Desfaz a 021 (#1036): devolve a frase ao texto que a 020 gravou. Nada de atendimento e apagado.
--
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). E para a mao de quem
-- desfaz, e por isso abre a propria transacao e apaga a linha de casa.mudancas.
--
-- Quase sempre nao e isto que se quer: para trocar a frase basta um UPDATE, sem restart e sem
-- deploy -- o texto e cadastro.
BEGIN;

UPDATE atendimento.menu
   SET pergunta = 'Olá, {nome}! Você é da equipe — o que precisa?'
 WHERE chave = 'raiz_interna';

DELETE FROM casa.mudancas WHERE nome = '021_ele_sabe_que_e_da_equipe.sql';

COMMIT;
