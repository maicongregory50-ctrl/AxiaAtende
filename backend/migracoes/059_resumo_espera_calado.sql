-- #1271 (dono, 05/11/2026): "o representante recebe se tiver janela de 24h aberta, se nao, fica na fila
-- ate abrir". A chave do resumo do lote calado: ligada, o resumo fora da janela e guardado SEM a
-- reabertura paga e sem o "nao visto" de 7 dias, e os guardados saem juntos quando ele escreve.
-- Ausente conta como ligada (backend/envio.py, resumo_espera_calado). Desligar e o rollback:
--   UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'resumo.espera_calado';
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

INSERT INTO atendimento.ajustes (chave, valor) VALUES ('resumo.espera_calado', 'true'::jsonb)
ON CONFLICT (chave) DO NOTHING;
