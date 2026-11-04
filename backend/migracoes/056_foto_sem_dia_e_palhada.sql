-- #1097 (entrega 2, a ficha; dono, 22/10/2026): tres erros vistos na conversa do Willian em 21/10.
-- (1) "Nao" digitado a "E de hoje?" foi colado na legenda das tres pecas; (2) "Dessecada, apenas palhada"
-- virou pre-colheita porque a lista de fases nao tinha palhada; (3) "Nao sei" na data virou 21/10
-- (presumido), embora ele tenha dito que nao era de hoje.
-- `sem_dia`: a pessoa disse que nao sabe o dia (ou a data nao se entendeu): a foto entra SEM dia, e o
-- fechamento NAO presume o dia do envio. A fase `palhada` entra em campo.FASES (codigo), nao ha CHECK.
-- As tres fichas do Willian: legenda sem " · Nao", fase palhada, sem dia.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.material_de_campo
    ADD COLUMN sem_dia boolean NOT NULL DEFAULT false;

UPDATE atendimento.material_de_campo
   SET legenda = replace(legenda, ' · Não', ''),
       classe_fase = 'palhada',
       data_dita = NULL, data_presumida = false, sem_dia = true
 WHERE atv IN ('ATV-0774', 'ATV-0775', 'ATV-0776');
