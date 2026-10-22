-- #1097 (dono, 22/10/2026): "precisa finalizar na tela pra mim, nao pode ser parou no meio, Imagem
-- Recebida, talvez". Quem e da equipe toca "Foto do campo" (no `texto`, #1031): o menu diz a linha e
-- para, a foto (ou a logo de cliente) e tomada pelo canal de campo SEM tocar na conversa, e 30 min
-- depois ela virava "parou no meio" -- com a retomada da IA gasta em "sem opcao".
-- Agora a conversa fecha com o que chegou. Spec: docs/specs/2026-10-22-a-conversa-da-equipe-termina-com-o-que-chegou.md
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- A lista inteira: a da 025 (#1098, o Trabalhe conosco) e os dois valores novos.
ALTER TABLE atendimento.conversas DROP CONSTRAINT conversas_situacao;
ALTER TABLE atendimento.conversas ADD CONSTRAINT conversas_situacao
    CHECK (situacao IN ('em_curso', 'com_link', 'parou_no_meio', 'encerrada', 'envio',
                        'curriculo_recebido', 'sem_curriculo', 'imagem_recebida', 'logo_recebida'));

-- As conversas de antes, pela mesma regra do motor: a ultima escolha foi uma opcao `texto` do menu
-- interno, e nas 24 h seguintes chegou a logo (logo_recebida) ou a foto (imagem_recebida). Em
-- 22/10/2026 sao cinco: 37 e 40 (logo), 46, 56 e 107 (foto; a 107 e a do Willian).
UPDATE atendimento.conversas c
   SET situacao = CASE WHEN EXISTS (SELECT 1 FROM atendimento.logos_de_cliente l
                                     WHERE l.wa_id = c.wa_id
                                       AND l.recebida_em BETWEEN c.iniciada_em AND c.iniciada_em + interval '24 hours')
                       THEN 'logo_recebida' ELSE 'imagem_recebida' END
  FROM atendimento.menu n
 WHERE n.id = c.no_atual_id AND n.acao = 'texto'
   AND c.situacao IN ('em_curso', 'parou_no_meio')
   AND (EXISTS (SELECT 1 FROM atendimento.logos_de_cliente l
                 WHERE l.wa_id = c.wa_id AND l.recebida_em BETWEEN c.iniciada_em AND c.iniciada_em + interval '24 hours')
        OR EXISTS (SELECT 1 FROM atendimento.material_de_campo m
                    WHERE m.wa_id = c.wa_id AND m.recebido_em BETWEEN c.iniciada_em AND c.iniciada_em + interval '24 hours'));
