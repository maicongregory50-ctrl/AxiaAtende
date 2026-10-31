# O chamado no WhatsApp: a mensagem sai, a resposta volta
**Data:** 2026-10-31
**Chamado:** #1222
**Status:** APROVADO

## Contexto

Hoje o chamado só conversa com quem o abriu pela caixa do sistema: o comentário e a devolução chegam ao
autor quando ele abre o ERP. A equipe vive no WhatsApp. O dono, em 31/10/2026: escrever no chamado ou
no WhatsApp precisa ter o mesmo efeito, e isso é *"o embrião de uma agenda de trabalho do sistema
tocada por mensagem e aviso no comunicador que todos usam hoje"*.

O caso que abriu o chamado foi a explicação da auditoria de estoque (#350) para a Fran. Ela só escreve
na terça, 03/11, e a mensagem devia esperar por ela.

O que existe e serve (lido no código em 31/10):

- O **porteiro dos avisos internos** (#1188, `backend/envio.py:241-710`): dentro da janela de 24 h o
  aviso sai como texto, de graça; fora dela sai **uma** reabertura por número ("Você tem N aviso(s)…
  Toque em Ver"), e o toque solta o que estava guardado. 7 dias sem toque viram não visto.
- O **WhatsApp diz a qual mensagem nossa a pessoa respondeu**: `Entrada.contexto` (`motor.py:86`) é
  lido em toda mensagem e **ninguém o usa**.
- A **OlivIA** (`backend/ia.py`) só escolhe uma opção de uma lista fechada, com a saída presa por
  esquema, e a pessoa confirma no botão. Ela não tem ferramenta nem escreve resposta, e isso não muda.
- O Atende já fala com o ERP como o agente **ATENDIMENTO** (usuário 130), puxando de tempos em tempos
  (`erp.retomadas`, `erp.auditoria_pendentes`).

O que falta:

- **A corrente do motor é uma fila de filtros em ordem fixa** (`motor.tratar`, `motor.py:670`):
  retorno da Fran na triagem, vaga, cliente aberto do consultor, foto de campo, logo, pergunta de foto,
  e por fim `campo.texto_de_interno`, que toma **qualquer** texto de interno como a frase da próxima
  foto. Uma resposta da Fran a um chamado cairia ali e viraria legenda.
- **Nenhum lugar liga o usuário do ERP ao WhatsApp da pessoa.** A Fran usa o login "Financeiro"
  (usuário 3) e o número dela só está nos Destinos do Atende.
- **Texto técnico vaza para o autor hoje.** Comentário gravado sem a linha `--- para quem despacha ---`
  chega inteiro à caixa: o #1191 levou ao Benedito um texto com hash de commit e nome de script em
  30/10. Com o espelho, isso iria ao celular dele.

## Os fios que encostam

**Quem mais escreve o que a mudança escreve**

- `axia.demandas_eventos` (comentário em nome do autor; Fechar e Não ficou bom pelo autor): escrevem a
  skill `/demanda` (SESSAO-DEV), o widget e a caixa do ERP (o próprio autor), o fio do SuporteAxia, o
  PLANEJADOR, o EXECUTOR e a recepção. O Atende entra como **mais um executor**, sempre `em_nome_de` o
  autor do chamado, pelas mesmas rotas do botão da caixa (`comentar`, `validar_entrega` com
  `pelo_autor`, `esteira_service.py:2270-2295`). Nenhuma escrita direta.
- **Quem lê para decidir:** o **fio** do SuporteAxia acorda quando o último evento é comentário do
  autor (`C:\SuporteAxia\backend\fio.py:719`). A resposta pelo WhatsApp **deve** acordá-lo, como a da
  caixa: é o autor falando. A régua de "quem executou × em nome de quem" (fase 379) continua valendo.
  `satisfacao` e o nó 7 vêm de `validar_entrega`, e o Ficou bom do WhatsApp produz o mesmo
  "Fechado: quem pediu confirmou." que o botão da caixa.
- `axia.usuarios` ganha o WhatsApp. Escrevem nele a tela de usuários e o cadastro; lê a agenda do
  Atende (`agenda.atualizar`, 06:00). O `permissoes_versao` **não** muda com o campo: WhatsApp não é
  permissão.
- `atendimento.*` (as tabelas novas do molde): só o Atende. A tela Envios passa a lê-las.
- `backend/ia.py`: o **#1223** (aberto hoje, outra sessão) mexe no mesmo arquivo para medir o custo
  de cada chamada (`r.usage`). A função nova desta etapa registra o custo do mesmo jeito que as outras
  quatro, e o plano confere o estado do arquivo antes de editar.

**Quem volta depois**

- A **thread do Atende** que puxa do ERP (a cada 60 s, como `avisos_da_auditoria`): busca as mensagens
  novas e devolve as respostas.
- O **porteiro** (a cada volta do recepcionista): solta o guardado quando a janela abre e marca não
  visto aos 7 dias.
- A **agenda** das 06:00 traz o WhatsApp dos usuários.
- O **fechamento da pendência**: quando o chamado anda por outro caminho (respondido na caixa, fechado
  pela sessão), a próxima puxada fecha a pendência no Atende.

## O universo medido

Medido no banco em 31/10/2026, últimos 60 dias, chamados de quem é de fora (autor diferente do dono):

| O que chegou ao autor | Quantos | Vira |
|---|---|---|
| comentário comum (decidimos, começamos, explicação) | 324 | informativo, sem pendência |
| comentário marcado como pergunta (`pergunta = true`) | 33 (só 12 respondidas pelo autor) | pendência |
| devolução de entrega (`entregar-ao-autor`) | 239 (autor reagiu em 13) | pendência com Ficou bom / Não ficou bom |
| recusa | 32 | informativo |
| "Fechado: quem trata a fila testou e fechou pelo autor" | quase todas as entregas | **não vai** |

- Por chamado: média 3,4 mensagens, mediana 3, p90 6, máximo 15.
- Por pessoa, nos dias em que alguém recebeu: mediana 5, p90 12, máximo 33. É o que pede a junção de
  10 minutos.
- Quem abre: Benedito 100 chamados, Financeiro 42, Alisson 26, Rodrigo 7, Vinicius 3.
- **Usuários do ERP com WhatsApp ligado hoje: 0** (o campo não existe). Dos internos que abrem
  chamado, 1 tem o número no cadastro do ERP (Benedito) e 2 só nos Destinos do Atende (Fran, Alisson).
- A **reabertura serve** (`scripts/medir_reabertura.py`, 31/10): 3 saíram desde 28/10, 3 lidas, 2
  tocadas em menos de 20 min (4 dos 7 avisos soltos pelo toque), 1 lida e não tocada (3 guardados há
  1,5 dia), 0 não vistos.

## Conformidade com o Manual legal

não se aplica: canal de comunicação interna sobre chamados; não toca imposto, documento fiscal, texto
legal impresso nem régua.

## Conformidade com a casa

Gatilhos tocados: agente de IA (R7), dado novo (R2), a fila escrita por mais um executor (R5).

- **R7 — conforme, com uma linha a atualizar (muda).** A carta diz que R7 é sobre governança, *"quem
  existe, o que pode, quem desliga, quem é avisado"*, e que *"o que um agente pode fazer sozinho é
  decisão do código que o envolve"*. A OlivIA ganha um segundo uso: escolher entre as pendências
  abertas de uma pessoa, em lista fechada, com confirmação no botão. O inventário
  (`C:\AxiaSecurity\design\agentes.json`, que o #1223 está ajustando) **muda**: uma linha nova para
  esse uso. Passo do plano, coordenado com o #1223.
- **R2 — conforme.** O dado novo mora no banco do Atende, já coberto por
  `rotina:backup-axiaatende-banco` e `rotina:backup-axiaatende-banco-nuvem`. O WhatsApp do usuário
  mora em `axia.usuarios`, coberto pelo backup do PostgreSQL.
- **R5 — conforme.** O Atende escreve na fila pelo token próprio do agente ATENDIMENTO, que já existe e
  já é usado para o ERP. A permissão nova é **atividade** do agente (`require_atividade`), não segredo
  novo.
- **Escrever em nome de alguém a partir do sistema que a internet alcança.** Nenhum item da carta
  cobre isso por nome; o desenho fecha pelo ERP, não pelo Atende: o ERP só aceita a resposta se o
  número que o Atende informa for **o WhatsApp do autor daquele chamado** no cadastro do ERP, e só nos
  chamados dele. O Atende não escolhe em nome de quem escreve.

## Decisão

Caminho **C**, desenhado em 31/10/2026 com o dono, decisão por decisão:

1. **A pendência é um molde do Atende**, e o chamado é o primeiro tipo a usá-lo. Tipo novo, no futuro,
   é código, não tabela. A migração dos fios que já existem (triagem de currículo, cliente aberto,
   pergunta de foto) fica **para o fim deste chamado**: é adição de tipos, não refaz o molde.
2. **O espelho:** vai ao WhatsApp do autor o comentário e a devolução, **só a parte acima de
   `--- para quem despacha ---`**. Vazia, nada sai. O "Fechado" automático não vai. Mensagens à mesma
   pessoa dentro de 10 minutos saem juntas, um bloco por chamado.
3. **Só abre pendência o que espera retorno:** a pergunta ao autor e a devolução de entrega. O
   informativo vai sem pendência; a resposta citada a ele é descartada, com uma linha só, uma vez por
   chamado.
4. **A resposta volta ao chamado:**
   - citada (o WhatsApp diz qual mensagem): direto à pendência, **antes** de qualquer filtro da
     corrente, sem IA;
   - sem citar: os filtros que têm estado próprio continuam antes, como hoje (retorno da triagem,
     cliente aberto, pergunta de foto aberta, logo). **No lugar do pega-tudo** (`texto_de_interno`), se
     a pessoa tem pendência aberta, a OlivIA propõe uma delas ou "nenhuma", e a pessoa confirma
     ([Sim] [Outro chamado] [Outro assunto]). "Outro assunto" segue o caminho de hoje.
5. **A ligação usuário ↔ número fica no ERP**: `axia.usuarios` ganha o WhatsApp, preenchido na tela de
   usuários. O Atende lê com a agenda.
6. **Fora da janela de 24 h:** o informativo espera calado até a pessoa escrever; a pergunta e a
   entrega saem pela reabertura que já existe ("Você tem N aviso(s)… Ver"), uma por pessoa por vez.
7. **O "Bom dia" que solta guardados não leva o menu da casa junto**: quem tinha mensagem esperando
   recebe só as mensagens.
8. **Antes de o espelho ligar**, o comentário ao autor com cara de texto técnico (hash de commit,
   caminho de arquivo, nome de script `.py`/`.ps1`/`.sql`) acima da linha `--- para quem despacha ---`
   é **recusado ao gravar**, com a frase *"isto vai para o autor; ponha o detalhe abaixo de --- para
   quem despacha ---"*. Isso fecha também o vazamento que já existe na caixa.

Maquete aprovada pelo dono em 31/10/2026: quatro cenas (informativo da Fran; pergunta respondida
citando; entrega fora da janela com Ver, Ficou bom e Não ficou bom; texto sem citar com a OlivIA
propondo o chamado).

## Escopo desta etapa

**Dentro**

- ERP: o campo WhatsApp do usuário (fase, tela de usuários, agenda); a régua do texto técnico ao
  autor; as rotas do agente ATENDIMENTO (atividade nova): **puxar** as mensagens ao autor depois de um
  cursor e **devolver** resposta, Ficou bom e Não ficou bom, cada uma conferindo que o número é o do
  autor daquele chamado.
- Atende: o molde (pendência e mensagens da pendência, com o `wamid` como vínculo e o estado de cada
  mensagem); o tipo `chamado`; a thread que puxa e devolve; o envio pelo porteiro com a regra do item
  6; a junção de 10 minutos; os botões da entrega; o degrau da resposta citada no topo da corrente; o
  degrau da OlivIA no lugar do pega-tudo; a linha do informativo; o "Bom dia" sem menu quando solta
  guardado; a tela Envios mostrando as pendências; o manual.
- O primeiro uso real: a mensagem da auditoria para a Fran como comentário informativo no #350.

**Fora**

- Migrar ao molde os fios antigos (triagem, cliente aberto, pergunta de foto): **anotado para o fim
  deste chamado** (comentário #10540).
- Mensagem solta de interno virar chamado novo, ou a agenda de trabalho por pessoa: depois de medir o
  uso deste.
- Áudio, foto e documento como resposta de chamado: nesta etapa só texto e botão.
- Login próprio para a Fran: é cadastro, e é decisão do dono (ver Impacto).

## Impacto em produção

- **ERP:** uma fase (coluna em `axia.usuarios`, a atividade nova do agente 130), restart da 8001 e da
  3001. A régua do texto técnico passa a recusar comentário — é a única mudança de comportamento para
  quem já usa a fila hoje, e ela só recusa o que já era defeito.
- **Atende:** uma migração (o molde e as chaves `pendencias.ligado` e `pendencias.juntar_minutos`),
  restart do recepcionista e das telas. O espelho nasce **desligado** (`pendencias.ligado = false`) e
  liga depois da prova com um número da casa.
- **O login "Financeiro" é compartilhado.** Ligá-lo ao número da Fran quer dizer que o que alguém abrir
  com esse login vai a ela, e que a resposta dela vale como de quem usa esse login.
- **Custo:** a reabertura é modelo pago da Meta, uma por pessoa por vez, e só para pergunta e entrega.
  A OlivIA (Haiku) é chamada só quando a pessoa escreve sem citar e tem pendência aberta.

## ROLLBACK_PLAN

1. Desligar sem tirar nada: `pendencias.ligado = false` no Atende. Nada sai e nenhuma resposta é
   tomada; a corrente volta a ser a de hoje.
2. Atende: rodar a `_VOLTA` da migração (as tabelas do molde e as chaves saem; os avisos de hoje ficam
   intocados) e reiniciar.
3. ERP: rodar a `_VOLTA` da fase (a coluna e a atividade saem) e reiniciar a 8001 e a 3001.
4. Os comentários que já entraram pelo WhatsApp **ficam** no chamado: são do autor, e apagá-los seria
   apagar o que ele disse.

## Manual de uso

**Para que serve.** O chamado conversa com você pelo WhatsApp. O que chega na caixa do sistema chega
também no celular, e o que você responde no celular entra no chamado, como se tivesse escrito no
sistema.

**Quem usa e quando.** Quem abre chamado: Benedito, Fran, Alisson, a equipe. Toda vez que o chamado
anda — decidimos, começamos, está no ar, ou uma pergunta para você.

**O caminho comum.**

1. Uma mensagem chega do número da Sementes Renascer com o título em cima: "Chamado 1217 · Trocar
   unidade do pedido".
2. Se é **só aviso** (vem escrito "Só aviso, não precisa responder"), não precisa fazer nada.
3. Se é **uma pergunta**, responda **deslizando a mensagem para o lado** (o Responder do WhatsApp) e
   escreva. Aparece "Anotado no chamado 1217 ✓".
4. Se é **a entrega** ("está no ar"), teste e toque **Ficou bom** (o chamado fecha) ou **Não ficou
   bom** (escreva numa linha o que falta; o chamado volta para ajuste).
5. Se você escrever **sem deslizar**, a OlivIA pergunta "É sobre o Chamado 1217?". Toque **Sim**,
   **Outro chamado** (para escolher na lista) ou **Outro assunto** (segue o atendimento de sempre).

**O que significa cada sinal.**

- "Você tem 1 aviso… Toque em Ver": você não escreve para a empresa há mais de 24 horas e tem uma
  pergunta ou entrega esperando. Toque em Ver e ela aparece.
- "Anotado no chamado N ✓": a sua resposta entrou no chamado.
- "Esta mensagem é só um aviso": você respondeu a um aviso; nada foi anotado. Para falar do chamado,
  use o sistema ou espere a próxima pergunta.
- Várias mensagens juntas numa só, um bloco por chamado: o chamado andou várias vezes em poucos
  minutos.

**O que esta função NÃO faz.**

- Não abre chamado novo pelo WhatsApp: para isso, continue usando o sistema.
- Não lê áudio, foto ou arquivo como resposta de chamado: só texto e os botões.
- Não manda aviso de madrugada por conta própria: o aviso que não precisa de resposta espera você
  escrever para a empresa.

**Pré-requisito de cadastro.** O seu usuário do sistema precisa ter o seu WhatsApp preenchido na tela
de usuários. Sem ele, nada sai, e tudo continua só na caixa do sistema.

**O que fica diferente no que já existe.**

- `docs/manuais/envios.md` (Atende): a tela Envios ganha as pendências de chamado.
- Manual da tela de usuários do ERP: o campo WhatsApp e o que ele liga.
- Quem trata a fila: comentário ao autor com hash, caminho de arquivo ou nome de script acima da linha
  `--- para quem despacha ---` passa a ser recusado.

## Próximo passo

/writing-plans
