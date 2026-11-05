# O material na janela aberta: sem convite pago para quem já aceitou e conversou nas últimas 24 h
**Data:** 2026-11-05
**Chamado:** #1267
**Status:** APROVADO

## Contexto

O dono vai mandar à Campos Gerais (7724) oito pacotes do AxiaMarketing (#1266), e quis aproveitar a
janela de 24 h: *"agendo isso tudo com menos de 24 horas, pego a primeira janela dele e vou mandando
todas as outras de graça"*. Hoje isso não acontece. `Envio.mandar_lotes` manda o **modelo de convite**
(categoria MARKETING, US$ 0,0625 na tela Custos) a cada destinatário de todo envio de material, mesmo
que a pessoa tenha tocado "Quero receber" na véspera e a janela esteja aberta. A janela já é medida
aqui (`janela_aberta`, #1237, pela hora da mensagem em `eventos_meta`), e o status do dia, a logística e
as pendências já a usam para mandar texto livre. O envio de material não.

A conta, dita ao dono nesta sessão: cada pacote fora da janela é um convite pago; dentro da janela, a
mensagem livre e as imagens não custam nada. **Não há cópia ao dono nas revendas**: desde o #1142 o
resumo do lote vai só ao representante (`CANAIS_DO_RESUMO`).

## Os fios que encostam

**Quem mais escreve o que a mudança escreve.** `atendimento.envio_destinatarios` (situação, lote,
`convite_wamid`, `convite_em`, `imagens_total`, `resposta_em`, `imagens_enviadas`): escritores de hoje
`receber_pedido` (a fila), `mandar_lotes`/`_mandar_um` (o convite), `tratar_toque` (aceite e recusa),
`_mandar_imagens`, a resposta em texto (`resposta = 'texto'`) e os avisos de status da Meta (entregue,
lido). Coluna nova `sem_convite` (migração 057), escrita só pelo caminho novo.

**Quem lê para decidir.** `mandar_imagens_pendentes` (resposta `quero` e janela pela `resposta_em`);
`_mandar_imagens` (para quando `agora - resposta_em > 24 h`); `recebidas_no_mes` (o teto do comprador,
por `convite_em`); `ja_hoje` do lote (por `convite_em`); a tela Envios (`rotas_telas`); o resumo do KR2
e o "O que rendeu" (`rotas_pedido`, `eventos_erp`, pela `resposta` e pelos estados). A régua do aceite é
`_ultimo_consentimento(con, numero)` e `aceite_cadastro` (a mesma da direta).

**Quem volta depois.** O recepcionista, a cada minuto (`rotina`: lotes, imagens pendentes, avisos); os
avisos de status da Meta (entregue e lido pelo `convite_wamid`, que no caminho novo é o da mensagem de
texto); o `eventos_erp` a cada 15 min, que leva `resposta` ao Relacionamento do ERP: no caminho novo a
`resposta` fica **nula** (ninguém tocou), e o ERP não conta aceite que não houve.

**O #1169 (segurar o envio), aprovado hoje:** suspende o envio inteiro; o caminho novo só corre dentro
de um envio que anda, então um envio suspenso não manda nada, nem sem convite. Não há conflito.

## O universo medido

- Pela leitura do código: todo destinatário de material sai por `_mandar_um` (o modelo), sem exceção;
  `janela_aberta` é chamada em 5 lugares e em nenhum do material.
- O caso: a 7724 não tem aceite gravado (nunca recebeu material por aqui); o **primeiro** pacote dela
  sai com convite, e só os seguintes podem sair sem.
- A contar no passo 0 do plano, no banco de produção (só leitura, pela tela ou pela sessão do dono):
  quantos números têm aceite como último consentimento, e quantos destinatários de material dos últimos
  30 dias estavam com a janela aberta na hora do convite (o que teria saído de graça).

## Conformidade com o Manual legal

Não se aplica: nenhum assunto tributário ou legal.

## Conformidade com a casa

- **R7 (agente e modelo de IA): não se aplica**, nenhuma chamada a modelo.
- **Regra 4 do projeto (consentimento não se apaga): conforme.** Só recebe sem convite quem já tem o
  aceite como último consentimento (ou o aceite do cadastro); recusa mais nova vence; nada é gravado
  como aceite novo.
- **Regra 5 (degraus) e 6 (categoria declarada): conforme.** O caminho novo respeita o lote de 20 e a
  nota verde (corre dentro do mesmo laço) e não manda modelo nenhum: a mensagem livre não tem
  categoria; dentro da janela a Meta não cobra.
- **R2 (dado novo):** uma coluna no banco do AxiaAtende, já coberto pelo backup diário.

## Decisão

**Caminho A, pedido do dono em 05/11/2026 ("vamos fazer o 1267 aqui"): no envio de MATERIAL, o
destinatário que já aceitou e está com a janela aberta recebe uma linha de texto e as imagens, sem o
convite.**

- **Quando:** `e.tipo == 'material'`, o último consentimento do número é `aceite` (ou
  `aceite_cadastro`), e a janela está aberta na hora do lote. Fora disso, o convite de sempre.
- **O que sai:** o texto "Mais material da Renascer com a marca da sua loja:" (mensagem livre) e, em
  seguida, as imagens do envio, como depois do "Quero receber". Se o texto falhar (a Meta diz que a
  janela fechou), vai o convite de sempre, no mesmo minuto.
- **O que se grava:** `situacao = 'convidado'`, `convite_em = agora`, `convite_wamid` = o do texto,
  `sem_convite = true`, `imagens_total`, e `resposta_em` = **a hora da última mensagem da pessoa** (o
  começo da janela que a Meta conta), para as imagens pararem quando a janela fechar. `resposta` fica
  nula.
- **O que não muda:** a direta (o comprador tem o teto e o modelo próprios); o lote de 20; a nota; a
  janela do envio (seg a sex, 9h30 às 17h); o "não enviar"; quem recusou.
- **A tela Envios** mostra "sem convite (janela aberta)" na linha do destinatário.

## Escopo desta etapa

**Dentro:** migração 057 (`sem_convite`), `inicio_da_janela` (de onde `janela_aberta` passa a ler), o
caminho novo em `mandar_lotes`, o envio das imagens pendentes aceitando `sem_convite`, a coluna na tela
Envios, testes, o manual `envios.md`.

**Fora:** a direta; o ERP saber de `sem_convite`; a legenda do post junto com as imagens (pedido à
parte); o AxiaMarketing (nada muda lá).

## Impacto em produção

- **Serviços:** `axiaatende-recepcionista` (o laço) e `axiaatende-backend` (as telas e a migração),
  um restart cada, fora da janela de envio ou sem lote em curso.
- **Dados:** a 057 só acrescenta uma coluna com padrão `false`.
- **Janela:** nenhuma.

## ROLLBACK_PLAN

1. Reverter o commit; restart dos dois serviços. Os destinatários já gravados com `sem_convite` ficam
   como estão (as imagens já saíram).
2. A `057_…_VOLTA.sql` tira a coluna.

## Manual de uso

**Para que serve.** Não pagar convite a quem já aceitou e está conversando: quem tocou "Quero receber"
ou escreveu nas últimas 24 h recebe o material seguinte direto, sem custo.

**Quem usa e quando.** Ninguém aciona: acontece sozinho no lote. Você aproveita agendando os envios
seguintes para dentro das 24 h da última mensagem da revenda.

**O caminho comum.** A revenda toca "Quero receber" no primeiro envio (pago). Os envios que saem nas 24
h seguintes chegam a ela como "Mais material da Renascer com a marca da sua loja:" e as imagens, sem
convite e sem custo.

**O que significa cada sinal.** Na tela Envios, "sem convite (janela aberta)" na linha da pessoa. A
resposta fica em branco: ninguém tocou.

**O que NÃO faz.** Não abre janela: quem não falou nas últimas 24 h recebe o convite pago de sempre.
Não vale na comunicação direta ao comprador. Não manda a quem nunca aceitou.

## Próximo passo

/writing-plans
