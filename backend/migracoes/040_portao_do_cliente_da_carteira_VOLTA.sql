-- Desfaz a 040 (#1189). Antes, desligar o portao (ajuste portao.ligado = false) ou reverter o codigo:
-- sem a raiz_carteira o portao nao tem menu para mostrar. NADA de atendimento e apagado.
-- Nao e aplicado pelo servico (regra 3 de backend/migracoes.py): abre e fecha a propria transacao.
BEGIN;

UPDATE atendimento.conversas SET no_atual_id = NULL, ia_proposta_id = NULL
 WHERE no_atual_id IN (SELECT id FROM atendimento.menu WHERE chave LIKE 'carteira.%' OR chave = 'raiz_carteira')
    OR ia_proposta_id IN (SELECT id FROM atendimento.menu WHERE chave LIKE 'carteira.%' OR chave = 'raiz_carteira');
DELETE FROM atendimento.menu WHERE pai_id = (SELECT id FROM atendimento.menu WHERE chave = 'raiz_carteira');
DELETE FROM atendimento.menu WHERE chave = 'raiz_carteira';
DELETE FROM atendimento.ajustes WHERE chave = 'portao.ligado';
DELETE FROM casa.mudancas WHERE nome = '040_portao_do_cliente_da_carteira.sql';

COMMIT;
