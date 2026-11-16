-- #1520, etapa B -- a VOLTA da 066. O que ja foi transcrito fica como texto em eventos_meta e em audios.texto.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

DELETE FROM casa.mudancas WHERE nome = '066_audio_de_fora.sql';
DELETE FROM atendimento.ajustes WHERE chave IN ('audio.de_fora', 'audio.de_fora_por_dia');
ALTER TABLE atendimento.audios DROP COLUMN de_fora;
