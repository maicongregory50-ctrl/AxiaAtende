-- #1163 -- o teto de duas mensagens por mes ao comprador (dono, 27/10/2026).
-- Spec: C:\AxiaMarketing\docs\specs\2026-10-27-cadencia-por-publico-e-teto-do-comprador.md -- plano ao
-- lado, passo 7. Pedido no #1103 do AxiaMarketing (spec de 26/10, linha 27: "Teto de duas mensagens
-- por mes por comprador"), que ficou em prosa e nao era aplicado em lugar nenhum.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.
--
-- POR QUE AQUI. Quem manda e o laco do lote (backend/envio.py), e e na hora de sair que se sabe o
-- mes: o envio em lotes de ate 20 por dia atravessa a virada. A situacao nova diz, na linha do
-- destinatario, que ele NAO recebeu esta porque ja tinha recebido duas no mes -- com o motivo
-- escrito, como as outras situacoes de "fora". Nenhuma linha de hoje muda.

ALTER TABLE atendimento.envio_destinatarios DROP CONSTRAINT envio_dest_situacao;
ALTER TABLE atendimento.envio_destinatarios ADD CONSTRAINT envio_dest_situacao
    CHECK (situacao IN ('aguardando', 'sem_responsavel', 'sem_whatsapp', 'sem_aceite', 'recusou_antes',
                        'ja_recebeu', 'convidado', 'falhou', 'nao_e_whatsapp', 'teto_do_mes'));
