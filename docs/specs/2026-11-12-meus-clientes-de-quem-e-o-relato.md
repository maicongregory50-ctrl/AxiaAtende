# Meus clientes: a OlivIA pergunta de quem é o relato, não perde texto ao parar, e não pergunta mais o meio
**Data:** 2026-11-12
**Chamado:** #1439
**Status:** APROVADO

## Contexto

O "Meus clientes" (#1090 etapa 3) foi desenhado **um cliente por vez**: a OlivIA manda a ficha, o
consultor escreve como foi, e **todo texto cai no registro aberto** (`clientes_do_dia.tratar`, `_aberto`
= o registro `aberto`/`conferir` mais novo das últimas 24 h). A leitura (`ia.ler_visita`) recebe só a
ficha do aberto e preenche os campos; ela não tem como saber de **quem** o texto fala.

O atendimento do dono em 12/11/2026, lido por `ler_conversa.py` (número 554991505565), mostrou os
três defeitos no mesmo quarto de hora:

| Hora | O que ele fez | O que o sistema fez |
|---|---|---|
| 08:18 | ⏭ Depois na Plantimar (registro 15) | Plantimar vai para `depois`; vem Agromitos (16) |
| 08:27 | escreveu o relato do Evandro e, em seguida, 🛑 Parar por hoje | o Parar marcou o 16 como `descartado` **com o texto ainda não lido**; o relato se perdeu |
| 08:28 | "meus clientes" e o mesmo texto de novo | registro 17, leu, montou, gravou. Certo |
| 08:30 | | abre Itaipu (18), cliente 3 |
| 08:37 | relato da visita presencial, que era da **Plantimar** | caiu em Itaipu: "Com Itaipu, foi como?" |
| 08:38 | "é da Plantimar, não da Itaipu" | o texto foi **somado ao registro da Itaipu** e a mesma pergunta voltou |

1. **Parar por hoje apaga texto não lido** (`_toque`, ramo `parar`: `estado = 'descartado'` sem olhar
   `textos`/`lido`).
2. **Não há "de quem é"**: a leitura não recebe os outros clientes da fila, e o relato de um cliente
   deixado para depois vai ao aberto.
3. **A correção escrita não alcança isto**: o "isso era do cliente" do roteador (#1238) troca de
   **assunto** (foto, chamado, cliente), não de **cliente** dentro do Meus clientes. A frase de
   correção vira mais texto do registro errado.

E a decisão de produto do dono, na mesma conversa: **o meio do contato (visita, ligação, WhatsApp)
deixa de ser perguntado e de ser gravado**: "não é importante para nós como contatamos". Isto encosta
no ERP (coluna `rel_contatos.meio NOT NULL`, régua `relacionamento_regras.validar`, tela
`RegistrarContato.jsx`): é o chamado irmão, no AxiaGestão, que tem de entrar **antes** (o ERP passa a
aceitar `meio` nulo) para o Atende poder deixar de mandar.

## Os fios que encostam

**O que a mudança escreve:** `atendimento.clientes_registros` (`estado`, `textos`, `proposta`,
`codigo`/`ficha` do registro que recebe um relato movido). Escritores hoje: `clientes_do_dia` (tratar,
_toque, seguir, rodar, proximo) e `clientes_erp.enviar_registros` (gravado/recusado). Nenhum outro.
**Quem lê para decidir:** `_aberto` (o registro em que o texto cai; o roteador lê o mesmo por
`clientes_do_dia.aberto` para o retrato do assunto "cliente"); `proximo` (o conjunto `feitos`: registros
de hoje e os confirmados/gravados/recusados nas últimas 24 h; `depois` volta amanhã). Mover um relato
para outro cliente **reabre** o registro dele (`depois` → `aberto`) ou cria um fora da ordem da fila; o
que estava aberto continua `aberto` e volta a ser o corrente quando o movido fechar (`_aberto` pega o
mais novo vivo). **Quem volta depois:** `rodar` (a cada volta do recepcionista: lê o não lido, avisa
gravado/recusado) e o processo das TELAS (`clientes_erp`, a cada minuto, leva o `confirmado` ao ERP).
**O meio:** `_falta` (1º campo perguntado), `cartao`, `ia.ler_visita` (schema e prompt),
`clientes_erp.corpo_do_registro` (manda `meio`), e o ERP (`ContatoWhatsappIn.meio: str`, `validar`
recusa sem meio: *"Diga como foi o contato"*). Sem o chamado irmão aplicado, mandar `meio` nulo é
recusa do ERP e a frase volta ao consultor: por isso a ordem.

## O universo medido

- **1** consultor no piloto (o dono); fila copiada do ERP com **60** clientes (ficha de 12/11).
- Em 12/11: **5** registros em 20 min (14 a 18), **1** relato perdido (16), **1** relato no cliente
  errado (18, com a correção somada em cima), **2** gravados certos (17 e, antes, o 14 de ontem).
- A pergunta do meio é a **primeira** das quatro possíveis (`_falta`): sair dela tira um toque de todo
  registro em que a leitura não achou o meio, e a leitura raramente acha ("falei com", "liguei" são
  ambíguos). Nos 5 registros de hoje, perguntou o meio em 2.
- Botões de WhatsApp: **3** por mensagem; lista: **10**. A pergunta "de quem é" cabe em botões com o
  aberto + até 2 candidatos; mais que isso vira lista.

## Conformidade com o Manual legal

não se aplica: registro de relacionamento comercial.

## Conformidade com a casa

não se aplica: sem segredo, serviço, agente ou dado novo. A OlivIA já lê o relato (chamada paga pela
API, inventariada); a leitura ganha um campo a mais na mesma chamada, sem chamada nova.

## Decisão

1. **De quem é o relato.** `ia.ler_visita(texto, ficha, motivos, hoje, candidatos)` recebe a lista
   `[{codigo, nome, contato}]` dos clientes da fila do consultor (todos os 60: a fila copiada é
   pequena) e devolve mais um campo, `cliente`: `"aberto"`, o `codigo` de um candidato, ou
   `"desconhecido"`. A instrução diz: o texto é sobre o cliente aberto a menos que **nomeie** outro da
   lista (nome da empresa, nome fantasia ou nome do contato); na dúvida, `desconhecido`.
   Em `rodar`, antes de `seguir`:
   - `aberto` → como hoje;
   - `codigo` de outro → **move** o registro: o `textos` vai para o registro daquele cliente (o
     `depois`/`descartado` de hoje ou de ontem reabre como `aberto`; sem registro, nasce um fora da
     ordem, com a `ficha` da fila), a leitura segue nele, e a OlivIA diz *"Entendi: isso é sobre a
     Plantimar."* antes das perguntas. O que estava aberto fica `aberto`, sem texto, e volta a ser o
     corrente quando o movido fechar (`proximo` o repete).
   - `desconhecido` → pergunta **"De quem é este relato?"** com botões: o aberto, e até dois
     candidatos cujo nome aparece no texto (casamento por texto, sem acento); três ou mais, lista. O
     toque `cli:dequem:<id>:<codigo>` move como acima. Sem nenhum candidato no texto: botões aberto /
     "Outro cliente" (que manda a lista dos 10 primeiros da fila).
   Decisão do dono (12/11): quando o relato nomeia **um** cliente da fila sem ambiguidade, registra
   nele **direto**, sem perguntar. A correção escrita ("é da Plantimar, não da Itaipu") passa pela
   mesma leitura: o texto somado nomeia a Plantimar, a leitura devolve o código dela e o registro
   inteiro é movido.
2. **Parar por hoje não apaga relato.** Com `textos` e `NOT lido`, o Parar deixa o registro `aberto`
   e responde *"Guardei o que você escreveu sobre X; continuo quando você voltar."*; `rodar` lê na
   volta seguinte normalmente (ele não exige que a pessoa esteja "no fluxo"). Sem texto, `descartado`
   como hoje.
3. **Sem meio.** `_falta` deixa de pedir `meio`; `cartao` deixa de mostrá-lo; `ia.ler_visita` deixa de
   pedir `meio` à IA; `corpo_do_registro` manda `meio = None`. A ficha continua mostrando o "último
   contato dd/mm" (sem o meio entre parênteses quando o ERP não o mandar).

Recusado: um comando escrito próprio ("sobre a Plantimar: …"): o nome na frase já basta; sintaxe nova
é mais uma coisa para ensinar.

## Escopo desta etapa

Dentro: os três pontos acima, os testes (dublê de IA com `cliente`), o manual `meus-clientes.md`, a
devolução. **Depende** do chamado irmão do ERP (meio opcional) estar no ar antes do restart daqui.
Fora: mover relato para cliente fora da fila do consultor (vira "desconhecido" e pergunta); áudio.

## Impacto em produção

Restart de `axiaatende-recepcionista` (o fluxo e a IA) e de `axiaatende-backend` (as TELAS, que
mandam ao ERP). Nenhuma migração.

## ROLLBACK_PLAN

`git revert` + restart dos dois serviços. Registros movidos ficam onde estão (são registros válidos).
Se o ERP ainda exigir meio, o `recusado` volta ao consultor com a frase, como hoje.

## Manual de uso

`docs/manuais/meus-clientes.md`: no passo 3, *"Fale do cliente que quiser: se o relato é de outro
cliente da sua lista (um que você deixou para depois, ou falou ontem), diga o nome dele na frase e a
OlivIA registra nele; se ela não entender de quem é, pergunta com botões"*; no passo 4, **sai** "como
foi (visita, ligação, WhatsApp)"; em "O que significa cada sinal": *"Entendi: isso é sobre X"* = o
relato foi para outro cliente que não o da ficha; *"Guardei o que você escreveu"* = parou com relato
pendente, continua ao voltar; em "O que NÃO faz": não pergunta mais como foi o contato.

## Próximo passo

/writing-plans
