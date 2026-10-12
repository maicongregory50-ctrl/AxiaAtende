-- #970, emenda da decisao 15 (12/10/2026, 14:25: cinco lembrancas de uma vez): UMA CONVERSA ABERTA
-- POR PESSOA. A foto que chega enquanto ha pergunta pendente entra na mesma conversa, mesmo depois
-- dos 10 minutos; o grupo deixa de ser "a janela de 10 min" e passa a ser este id (o do lider).
-- Sem BEGIN nem COMMIT.
ALTER TABLE atendimento.material_de_campo ADD COLUMN grupo_id integer;

-- o que ja existe: o grupo pela regra antiga (10 minutos a partir da primeira foto do numero)
UPDATE atendimento.material_de_campo m
   SET grupo_id = (SELECT min(a.id) FROM atendimento.material_de_campo a
                    WHERE a.wa_id = m.wa_id AND a.recebido_em <= m.recebido_em
                      AND a.recebido_em > m.recebido_em - interval '10 minutes');
UPDATE atendimento.material_de_campo SET grupo_id = id WHERE grupo_id IS NULL;
ALTER TABLE atendimento.material_de_campo ALTER COLUMN grupo_id SET NOT NULL;
CREATE INDEX material_de_campo_grupo ON atendimento.material_de_campo (grupo_id);
