-- #1099 (dono, 22/10/2026, 20:42): a foto mandada as 08:54:56 chegou 12 h depois e abriu lote novo
-- ("Recebi." e "O que esta acontecendo nessa foto?") em vez de entrar calada no album das 08:54. O
-- album e de antes da 028 e nao tinha a hora de envio: valia a de chegada (10:05), longe demais.
-- A hora de envio das linhas antigas sai do aviso da Meta, que ja esta guardado (`msg.timestamp`).
-- Nunca depois da chegada (o relogio do celular pode estar adiantado: a mesma regra de hora_de_envio).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
UPDATE atendimento.material_de_campo m
   SET enviado_em = least(to_timestamp((e.corpo->'msg'->>'timestamp')::bigint), m.recebido_em)
  FROM atendimento.eventos_meta e
 WHERE m.enviado_em IS NULL AND m.wamid IS NOT NULL
   AND e.chave_meta = m.wamid AND e.tipo = 'mensagem'
   AND (e.corpo->'msg'->>'timestamp') ~ '^[0-9]+$';

-- A frase nao guarda o wamid: casa pelo numero, pelo texto e pela chegada (o mesmo aviso).
UPDATE atendimento.campo_frases f
   SET enviado_em = least(to_timestamp((e.corpo->'msg'->>'timestamp')::bigint), f.recebido_em)
  FROM atendimento.eventos_meta e
 WHERE f.enviado_em IS NULL AND e.tipo = 'mensagem'
   AND e.corpo->'msg'->>'from' = f.wa_id
   AND e.corpo->'msg'->'text'->>'body' = f.texto
   AND e.recebido_em BETWEEN f.recebido_em - interval '5 minutes' AND f.recebido_em + interval '5 minutes'
   AND (e.corpo->'msg'->>'timestamp') ~ '^[0-9]+$';
