# A tela de Conversas e a resposta de pessoa
**Data:** 2026-10-13
**Chamado:** #989
**Status:** PROPOSTO

## Contexto

O número da Renascer no WhatsApp (49 3664 0121) só fala pela API da Meta, pelo recepcionista. Quando
a OlivIA não resolve (o Vinicius às 14:00 de 13/10, pedindo os contatos de SC, refez o menu três
vezes; a Giovana às 11:31 tocou uma lista antiga e parou), **ninguém da casa consegue responder**: o
dono em 13/10, *"não existe mandar à mão; não temos comunicador, não tem tela para digitar e ver
conversa"*. O pedido original do chamado (a sessão lê a conversa que parou e manda a informação) vem
depois disso: antes de propor resposta, falta o básico, ver a conversa e responder.

O que existe e que esta etapa reaproveita (inventário de 13/10):
- A conversa inteira está no banco: o que chega em `atendimento.eventos_meta`, o que a OlivIA manda
  em `atendimento.enviadas` (desde o #981 também as falas do canal de campo), a conversa de menu em
  `conversas` (situação `parou_no_meio` marcada 30 min depois do último toque, D5 do #950), o canal
  de campo em `material_de_campo`. O leitor `scripts/ler_conversa.py` (#981) já monta a conversa em
  ordem de tempo.
- O recepcionista (127.0.0.1:8008, LocalService) é o único processo com o token; roda um laço de 1 s
  (`processar_pendentes`) e um de 1 min. As telas (8009, LocalSystem) nunca falam com a Meta
  (`rotas_telas.py`): o que muda é o banco, e o recepcionista lê. É o mesmo corte do marketing: a
  tela enfileira, o processo com o segredo envia.
- A janela de 24 h da Meta já é medida (`campo.ultima_mensagem_de`: a última mensagem recebida da
  pessoa); fora dela a mensagem livre não sai (seria modelo pago).
- As telas: `App.jsx` com três abas (Recepção, Envios, Destinos), `api.js` (`pegar`, `mandar` com o
  cabeçalho da tela), login único (`casa.usuarios`, sem direitos por pessoa: decisão do dono em 13/10,
  "qualquer login responde"), `Recepcao.jsx` como molde de tela e `test_telas.py` como molde de teste.

## Os fios que encostam

**Quem mais escreve.** `atendimento.enviadas` tem quatro escritores (o motor, o envio, o canal de
campo e, agora, a resposta de pessoa): todos gravam a mesma forma (`wamid`, `para`, `tipo`, `resumo`)
e o status chega pelo webhook pela `wamid`; nada muda neles. A tabela nova `atendimento.respostas` tem
dois escritores com colunas distintas: as telas inserem (`texto`, `autor_id`, `criada_em`) e o
recepcionista fecha (`enviada_em`, `wamid`, `erro`). `conversas` não é tocada (a resposta não muda o
nó nem a situação; a Recepção continua dizendo "parou no meio", e a tela nova diz "respondida por
pessoa" pela própria `respostas`).

**Quem lê para decidir.** O recepcionista lê `respostas` a cada segundo e decide pela janela: a
última mensagem da pessoa há menos de 24 h envia; senão marca `erro = 'fora da janela'` e não envia
(a tela já tinha recusado; o segundo portão é para a fila que atravessou a meia-noite). A Recepção lê
`conversas` como antes.

**Quem volta depois.** O webhook de status da Meta atualiza `enviadas` pela `wamid` (como qualquer
fala). O backup do banco leva a tabela nova por ser do schema. O leitor da sessão (#981) passa a
mostrar a resposta de pessoa como `←` com o nome de quem respondeu (já lê `enviadas`).

## O universo medido

- Conversas que pararam no meio: a Recepção conta por período (cartão "Pararam no meio"); em 13/10,
  as duas de fora do dia (Vinicius chegou ao link por insistência; Giovana parou). A tela nova mede
  o que importa daqui em diante: quantas conversas recebem resposta de pessoa por semana.
- Janela de 24 h: medida pela última mensagem recebida (`eventos_meta`), como no canal de campo.
- Escritores de `enviadas`: 3 hoje (medido por `grep INSERT INTO atendimento.enviadas`), 4 depois.
- Logins das telas: 1 hoje (`casa.usuarios`), por isso "qualquer login responde".

## Conformidade com o Manual legal

Não se aplica: não há regra tributária. Dado pessoal: a conversa já está no banco e na Recepção; a
tela mostra o número mascarado na lista e inteiro só dentro da conversa aberta, como a Recepção.

## Decisão

- **A, conservador:** só a tela de leitura (ver a conversa), sem responder. Não resolve o pedido.
- **B, o escolhido:** a tela **Conversas** (lista de quem escreveu, a conversa em ordem, a caixa de
  resposta), a fila `atendimento.respostas` que as telas enchem e o recepcionista envia dentro das
  24 h, gravada em `enviadas` com o nome de quem respondeu. Qualquer login responde. A proposta por
  IA (o pedido original) é a etapa seguinte, na mesma tela, depois de medir quantas conversas ainda
  param com o #988 no ar.
- **C, progressivo:** B mais a proposta por IA já nesta etapa. Amplia o desenho antes de medir se
  ainda há o que propor (o #988 entende "Sc" e lista antiga desde 13/10). Fora.

## Escopo desta etapa

**Dentro**
1. Migração 016: `atendimento.respostas` (`id`, `wa_id`, `bsuid`, `conversa_id` opcional, `texto`
   até 1000 caracteres, `autor_id` → `casa.usuarios`, `criada_em`, `enviada_em`, `wamid`, `erro`).
2. A leitura da conversa sai do script para `backend/leitura.py` (`ultimas`, `conversa`), usada
   pelo leitor da sessão (#981, que continua lendo pelo papel só-leitura) e pelas rotas.
3. Rotas das telas: `GET /conversas?dias=7&so=paradas|sem_resposta` (quem escreveu: número
   mascarado, cadastro, última mensagem, mensagens, situação da última conversa, dentro da janela,
   resposta pendente ou enviada), `GET /conversas/{wa_id}` (a conversa em ordem, com número inteiro,
   e a janela), `POST /conversas/{wa_id}/responder` (`texto`; 409 fora da janela ou com resposta
   ainda não enviada; grava com o autor do login).
4. Recepcionista: `respostas.enviar(con, saida, agora)` no laço de 1 s: para cada resposta sem
   `enviada_em` e sem `erro`, confere a janela, `saida.texto`, grava `enviada_em` + `wamid` e a linha
   em `enviadas` (`tipo texto`, `resumo "resposta de <nome>: <texto>"`, `conversa_id` da conversa
   aberta se houver); falha da Meta vai a `erro` e não se repete sozinha (a tela mostra e deixa
   mandar de novo).
5. Tela `Conversas.jsx` (aba nova, entre Recepção e Envios): lista à esquerda (filtros: período, "só
   paradas no meio", "só sem resposta de pessoa"), conversa à direita com `→` o que chegou e `←` o que
   saiu (status), as linhas do campo, a caixa de resposta com contador e o botão Responder;
   fora da janela a caixa fica fechada e diz desde quando; resposta enviada aparece na hora com
   "você" e o status; atualização a cada 15 s.
6. Manual `docs/manuais/conversas.md`, a linha no `INDICE.md`, uma frase na `recepcao.md`.

**Fora**
- A proposta de resposta por IA ou pela sessão (etapa seguinte, mesmo chamado ou outro).
- Direito por login (um login só hoje).
- Mensagem fora das 24 h (modelo pago: exige modelo aprovado na Meta; chamado próprio se um dia).
- Anexos na resposta (foto, documento); só texto.
- Marcar a conversa como resolvida ou mudar o nó do menu.

## Impacto em produção

Migração 016 aplicada pelos dois serviços ao subir. Reinício do `axiaatende-backend` (rotas e tela) e
do `axiaatende-recepcionista` (o envio da fila): mão do dono. `npm run build` antes. Nenhum segredo
novo. A primeira resposta é a prova: uma pessoa da casa escreve a um número que falou hoje.

## ROLLBACK_PLAN

1. `016_respostas_VOLTA.sql` (apaga a tabela; o que foi enviado fica em `enviadas`).
2. Reverter os commits (a aba some; o recepcionista deixa de olhar a fila).
3. Reiniciar os dois serviços. Nenhuma conversa é tocada.

## Manual de uso

**Para que serve.** Ver uma conversa do WhatsApp da Renascer inteira e responder a quem a OlivIA não
resolveu, sem aplicativo nem celular: a resposta sai pelo mesmo número.

**Quem usa e quando.** Quem entra nas telas do AxiaAtende, quando a Recepção mostra "parou no meio"
ou "disse que não foi atendido", ou quando alguém pediu algo que o menu não tem. Só vale nas 24 horas
depois da última mensagem da pessoa: depois disso a caixa fecha (mensagem fora da janela é paga e
exige modelo aprovado).

**O caminho comum.**
1. Abra **Conversas**. À esquerda, quem escreveu, do mais recente; marque "só paradas no meio" para
   ver quem ficou sem solução.
2. Toque num nome: à direita, a conversa inteira, o que a pessoa mandou (`→`) e o que a OlivIA
   respondeu (`←`), com hora e status.
3. Escreva na caixa e toque **Responder**. A mensagem aparece na conversa com "você" e o status
   muda para entregue e lida conforme a Meta avisa.
4. Se a Meta recusar, a linha fica em vermelho com o motivo, e dá para mandar de novo.

**O que significa cada sinal.** `→` chegou da pessoa; `←` saiu do número da Renascer (OlivIA ou
você, com o nome de quem respondeu); "parou no meio" é da Recepção; "sem resposta de pessoa" é que
ninguém da casa respondeu ainda; "janela fechada desde …" é que a pessoa não escreve há mais de 24 h
e a resposta não pode sair; "respondida por …" é a sua ou de outro login.

**O que NÃO faz.** Não manda foto nem documento; não manda fora das 24 h; não muda o menu nem o
destino; não encerra a conversa; não responde sozinha (a proposta por IA é a etapa seguinte).

## Próximo passo

`/writing-plans`.
