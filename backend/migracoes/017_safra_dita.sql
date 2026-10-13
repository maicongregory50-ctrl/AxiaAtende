-- #982 (dono, 13/10/2026): a SAFRA como resposta a "E de hoje?". A safra N e de 01/07/(N-1) a
-- 30/06/N (padrao da casa). Quem responde "safra 2025" (ou "2025", "24/25") da a safra, nao o dia:
-- a foto entra no catalogo SEM dia presumido e com a safra dita. Sem BEGIN nem COMMIT.
ALTER TABLE atendimento.material_de_campo ADD COLUMN safra_dita smallint;
