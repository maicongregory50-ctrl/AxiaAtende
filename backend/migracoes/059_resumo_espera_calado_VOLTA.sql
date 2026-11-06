-- Desfaz a 059 (#1271): a chave do resumo calado sai. O codigo sem a linha trata a chave como LIGADA:
-- para voltar ao porteiro do #1188 sem deploy, DESLIGUE a chave em vez de rodar este arquivo.
-- ESTE ARQUIVO NAO E APLICADO PELO SERVICO (regra 3 de backend/migracoes.py). O CODIGO JA DEVE TER
-- SIDO REVERTIDO antes dele.
BEGIN;

DELETE FROM atendimento.ajustes WHERE chave = 'resumo.espera_calado';

DELETE FROM casa.mudancas WHERE nome = '059_resumo_espera_calado.sql';

COMMIT;
