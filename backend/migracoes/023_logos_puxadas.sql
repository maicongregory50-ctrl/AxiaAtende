-- #1037 (dono, 19/10/2026): a logo de cliente chega ao marketing. A outra metade do #1036.
--
-- A 020 deixou a logo guardada com `puxada_em` nulo, "esperando o marketing puxar" -- e nenhuma
-- rota a entregava. Agora o publicador do marketing puxa (rotas_logos.py), diz o que fez com ela
-- e a recepcionista avisa quem mandou, so dentro das 24 h (a janela da Meta), no molde do aviso
-- do canal de campo (`aviso_catalogo`, `aviso_catalogo_em`).
--
-- `resultado`: o que o marketing fez -- `parceira_nova` (cliente novo, conferido no ERP, virou
-- parceira PENDENTE) ou `a_conferir` (espera o dono na Caixa). Nada aqui autoriza nada.
-- `aviso`: `enviado` ou `fora_da_janela` (nada sai: seria modelo pago); nulo = ainda nao tratado.
--
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.logos_de_cliente
    ADD COLUMN resultado text
        CONSTRAINT logos_resultado CHECK (resultado IN ('parceira_nova', 'a_conferir')),
    ADD COLUMN aviso text
        CONSTRAINT logos_aviso CHECK (aviso IN ('enviado', 'fora_da_janela')),
    ADD COLUMN aviso_em timestamptz;
