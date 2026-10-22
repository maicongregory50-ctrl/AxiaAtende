-- Desfaz a 029 (#1098): a abertura volta a perguntar "Voce atende a esses requisitos?". Volta junto o
-- codigo anterior de backend/vaga.py (git), que e quem mostra os botoes da pergunta.
BEGIN;
UPDATE atendimento.respostas_da_vaga
   SET texto = E'{saudacao} Obrigado pelo interesse na *{vaga}* da Sementes Renascer 🌱\n\nO anúncio pede:\n{requisitos}\n\nVocê atende a esses requisitos?'
 WHERE chave = 'abertura';
DELETE FROM atendimento.respostas_da_vaga WHERE chave IN ('pergunta_menu', 'pedir_pdf_banco');
DELETE FROM casa.mudancas WHERE nome = '029_vaga_sem_autoavaliacao.sql';
COMMIT;
