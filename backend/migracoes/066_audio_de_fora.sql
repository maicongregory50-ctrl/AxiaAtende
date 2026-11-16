-- #1520, etapa B (D10, dono 16/11/2026): o audio de quem e de fora, transcrito na maquina pela mesma
-- transcricao da equipe (#1238), para a OlivIA responder ao que a pessoa falou. Plano: passos B1 a B8.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- O audio de fora fica marcado: a fila poe o da casa na frente, e quem nao ouviu recebe a marca.
ALTER TABLE atendimento.audios ADD COLUMN de_fora boolean NOT NULL DEFAULT false;

-- A chave NASCE DESLIGADA, e so vale com OLIVIA_FALA e audio.transcrever ligadas. Liga e desliga sem
-- restart por scripts/audio.py ligar-fora | desligar-fora. O teto por numero em 24 h segura quem mandar muitos.
INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('audio.de_fora', 'false'::jsonb),
    ('audio.de_fora_por_dia', '6'::jsonb)
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'atendimento'
                    AND table_name = 'audios' AND column_name = 'de_fora') THEN
        RAISE EXCEPTION '066: audios.de_fora nao nasceu.';
    END IF;
    IF (SELECT count(*) FROM atendimento.ajustes WHERE chave IN ('audio.de_fora', 'audio.de_fora_por_dia')) <> 2 THEN
        RAISE EXCEPTION '066: os ajustes do audio de fora nao nasceram.';
    END IF;
    RAISE NOTICE '066 OK: o audio de quem e de fora (chave desligada)';
END $$;
