-- #1267 (dono, 05/11/2026): o material na janela aberta. Quem ja aceitou (ultimo consentimento
-- `aceite`, ou o aceite do cadastro) e mandou qualquer mensagem nas ultimas 24 h recebe o material
-- seguinte SEM o convite pago: uma linha de texto e as imagens, mensagens livres que a Meta nao cobra
-- dentro da janela. `sem_convite` marca esse caminho: a tela Envios mostra, e `resposta` fica nula
-- (ninguem tocou).
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

ALTER TABLE atendimento.envio_destinatarios
    ADD COLUMN sem_convite boolean NOT NULL DEFAULT false;
