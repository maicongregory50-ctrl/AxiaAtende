-- #1238 (dono, 03/11/2026): a logo de cliente passa a aceitar o NOME do cliente, resolvido pela agenda
-- do ERP; o codigo continua valendo. `cliente_dito` guarda o que a pessoa escreveu, inclusive quando a
-- agenda nao resolveu: a logo fica guardada sem codigo, mas com o nome dito, para alguem completar
-- na tela Parceiras do marketing (que o le em /logos/pendentes).
--
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.logos_de_cliente
    ADD COLUMN cliente_dito text NOT NULL DEFAULT '';
