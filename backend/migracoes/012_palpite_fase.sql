-- #970 (dono, 12/10/2026): o palpite do marketing passa a trazer tambem a FASE da lavoura (lista
-- fechada do catalogo de la), para a foto entrar classificada. Sem BEGIN nem COMMIT.
ALTER TABLE atendimento.material_de_campo ADD COLUMN palpite_fase text;
