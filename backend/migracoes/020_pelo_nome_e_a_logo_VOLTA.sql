-- Desfaz a 020 (#1036). Devolve a pergunta do menu da casa ao texto LITERAL de 15/10/2026 (o que a
-- migracao 018 gravou) e APAGA a tabela das logos.
--
-- ATENCAO -- ESTE E O UNICO _VOLTA DESTE PROJETO QUE DESTROI DADO QUE NAO EXISTIA ANTES. As logos
-- ja colhidas morrem com a tabela, e os arquivos ficam orfaos na pasta de midia. ANTES DE RODAR:
--     \copy (SELECT * FROM atendimento.logos_de_cliente) TO 'logos-salvas.csv' CSV HEADER
-- e guarde a pasta dos arquivos. Nenhuma outra coisa de atendimento e apagada: conversa, material de
-- campo e frase anotada ficam.
--
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py: "o _VOLTA.sql nunca e
-- aplicado sozinho; ele existe para a mao de quem desfaz"). Por isso abre a propria transacao e
-- apaga a linha de casa.mudancas. O CODIGO JA DEVE TER SIDO REVERTIDO antes dele.
BEGIN;

UPDATE atendimento.menu
   SET pergunta = 'Você é da equipe. O que precisa?'
 WHERE chave = 'raiz_interna';

DROP TABLE atendimento.logos_de_cliente;

DELETE FROM casa.mudancas WHERE nome = '020_pelo_nome_e_a_logo.sql';

COMMIT;
