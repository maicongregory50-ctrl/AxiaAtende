-- #1099 (dono, 22/10/2026): "as ultimas fotos subiram com o titulo da anterior, o atendimento nao
-- entendeu que era um novo lote". O grupo fechado recebia foto nova (o lote pela hora de CHEGADA) e a
-- frase valia pela chegada, nao pelo envio. Spec: docs/specs/2026-10-22-o-lote-novo-nao-entra-no-grupo-fechado.md
-- (a spec dizia 025; a 025, a 026 e a 027 entraram antes, no mesmo dia).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- A hora em que a pessoa MANDOU (`msg.timestamp` da Meta). Vazia nas linhas antigas: caem na chegada.
ALTER TABLE atendimento.material_de_campo ADD COLUMN enviado_em timestamptz;
ALTER TABLE atendimento.campo_frases ADD COLUMN enviado_em timestamptz;

-- A pergunta nova: "E do mesmo assunto da anterior?" (lote sem frase logo depois de outro fechado).
ALTER TABLE atendimento.material_de_campo DROP CONSTRAINT material_pergunta;
ALTER TABLE atendimento.material_de_campo ADD CONSTRAINT material_pergunta
    CHECK (pergunta_pendente IN ('legenda', 'data', 'qual_dia', 'bastidor', 'produto', 'fase', 'mesmo'));

-- A chave do rollback sem deploy: 'false' devolve o lote e a frase a regra de chegada de antes.
INSERT INTO atendimento.ajustes (chave, valor) VALUES ('campo.lote_pelo_envio', 'true'::jsonb);
