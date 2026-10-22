# A conversa da equipe termina com o que chegou, e a ficha da foto sai certa
**Data:** 2026-10-22
**Chamado:** #1097
**Status:** APROVADO

## Contexto

O dono abriu a Recepção em 22/10 e viu o Willian e o Benedito como "parou no meio". Pediu:
*"precisa finalizar na tela pra mim, não pode ser parou no meio, Imagem Recebida, talvez"*.

O atendimento do Willian funcionou: as três fotos de palhada viraram ATV-0774, ATV-0775 e ATV-0776
no catálogo do marketing. O "parou no meio" vem do jeito como o menu interno funciona:

1. Quem é da equipe toca **📸 Foto do campo** (`interna.campo`, ação `texto`). O menu diz a linha
   dele e para (`motor.escolher`, ramo `texto`, #1031). A conversa fica `em_curso`.
2. A foto (ou a logo de cliente, que chega como documento) é tomada por `campo.receber` ou
   `logos.receber`, em `motor.tratar`, **sem tocar na conversa**.
3. Trinta minutos depois, `marcar_paradas` muda a conversa para `parou_no_meio`, e `retomar_paradas`
   gasta a única tentativa da IA nela, que não acha opção ("sem opcao").

Na leitura da conversa do Willian apareceram também três erros na ficha das fotos, e o dono decidiu
que eles entram neste chamado ("b"):

- **O "Não" foi para a legenda.** À pergunta "É de hoje?" ele escreveu "Não". A conversa só
  entende o botão; o texto não é data nem safra e foi emendado na legenda das três peças
  (`campo.py:637-640`).
- **"Não sei" virou a data do dia.** Na pergunta "Qual dia?", o que não se entende como data
  presume o dia do envio (`campo.py:657-659`).
- **"Dessecada, apenas palhada" virou pré-colheita.** A IA encaixa a resposta numa das cinco
  fases (`campo.py:611-618`, `FASES`) e pegou a mais próxima. Palhada depois da dessecação é o que
  o +Palha Multi entrega, e o dono decidiu que ganha fase própria ("a"):
  **"Palhada (dessecada)"**, no AxiaAtende e no catálogo do AxiaMarketing.

## Os fios que encostam

**Quem mais escreve `atendimento.conversas.situacao`** (medido por `grep` em `backend/`): só o
`motor.py`. `_abrir`/`retomar` (em_curso), `escolher` (com_link, encerrada), `marcar_paradas`
(parou_no_meio), `retomar_paradas` (em_curso de volta). O `CHECK conversas_situacao` (migração 001)
aceita `em_curso`, `com_link`, `parou_no_meio`, `encerrada`, `envio`.

**Quem lê para decidir:** o índice `conversas_uma_aberta` (só `em_curso`), `_PENDENTES` e a
pergunta do dia (só `com_link`), `retomar_paradas` (só `parou_no_meio`) e a Recepção
(`rotas_telas.py:80-135`: o cartão "pararam no meio" e o estado de cada linha). Uma situação nova
fica fora de todas essas réguas, que é o que se quer: não é aberta, não tem link, não é parada.

**O #1098 mexe no mesmo `CHECK`** (acrescenta `curriculo_recebido` e `sem_curriculo`). A migração
que entrar depois tem de levar a lista inteira, com os valores da outra.

**Quem mais escreve a ficha da foto** (`material_de_campo`: `legenda`, `data_dita`,
`data_presumida`, `classe_fase`): só o `campo.py`. O **#1099** (spec aprovada em 22/10, caminho B)
reescreve `_lider`, a frase e as perguntas do mesmo arquivo. Por isso os consertos da ficha vão
**depois** dele, na segunda entrega.

**No AxiaMarketing**, a fase e o dia encostam em:
- `backend/produtos.py:14` (`ESTAGIOS`) e o `CHECK ativos_estagio` (migração 002): a lista de fases
  aceitas no catálogo;
- `backend/visao.py` (`FASES`): a leitura da imagem;
- `backend/campo.py:373`, `:395` e `:431`: o catálogo só aceita foto sem dia quando vem a safra; sem
  ela, `:373` e `:431` põem o dia de hoje.

**Quem volta depois:** o laço do minuto (`marcar_paradas`, `retomar_paradas`) e a puxada do
marketing (`pendentes`/`classificados`), que leva só o grupo fechado e aplica a classe depois.

## O universo medido

Medido em 22/10/2026, só leitura (papel `axiaatende_ro`):

- **Conversas por situação:** 75 com link, 42 paradas no meio, 4 encerradas.
- **Conversas começadas em 📸 Foto do campo: 5**, todas `parou_no_meio`, todas com a retomada da IA
  gasta em "sem opcao". Nas 24 h seguintes, cada uma recebeu o que veio mandar:

  | Conversa | Quem | Chegou depois |
  |---|---|---|
  | 37, 40 (15/10) | dono | 1 logo de cliente cada |
  | 46 (20/10), 56 (21/10) | dono | 3 e 2 fotos |
  | 107 (21/10) | Willian | 3 fotos (ATV-0774 a 0776) |

  As cinco saem da conta das paradas e passam a "Imagem recebida" (3) e "Logo recebida" (2).
- **Fichas com os três erros:** as 3 do Willian (ATV-0774, 0775, 0776), únicas no canal desde
  11/10 com resposta escrita a "É de hoje?".

## Conformidade com o Manual legal

Não se aplica: rótulo de atendimento e classificação de foto do catálogo de marketing, sem imposto,
documento fiscal nem texto legal.

## Conformidade com a casa

Não se aplica: nenhum dos seis gatilhos. Não há segredo, serviço, porta, tarefa, agente nem
projeto novo. A IA de texto (`ia.ler_campo`) é chamada como hoje, só com a fase nova na lista e
"nenhuma" como resposta válida; a retomada passa a gastar **menos** chamadas (não roda no canal
interno). Os dados novos são valores em colunas que já existem, no banco que o backup cobre.

## Decisão

**Caminho B**, escolhido pelo dono em 22/10/2026 ("b, mas vamos fazer tudo aqui nesta sessão").
Duas entregas, um chamado, um plano.

**Entrega 1: a Recepção (agora, sem tocar no `campo.py` nem no Marketing).**
1. Duas situações novas: `imagem_recebida` e `logo_recebida`.
2. Quando `campo.receber` ou `logos.receber` tomam o que a pessoa mandou, a conversa dela começada
   no menu interno (a última nas 24 h, em curso ou parada, cuja última escolha foi uma opção de ação
   `texto`) fecha com a situação do que chegou. Várias fotos: a primeira fecha, as outras não mudam
   nada.
3. `retomar_paradas` não gasta a IA em conversa do menu interno: marca `retomada_chave =
   'canal interno'` e segue.
4. Quem tocou 📸 Foto do campo e não mandou nada continua "parou no meio": é verdade.
5. Na Recepção, o estado novo aparece como **"Imagem recebida"** e **"Logo recebida"**, fora do
   cartão "pararam no meio".
6. As 5 conversas antigas são corrigidas pela própria migração, pela mesma regra (o que chegou nas
   24 h seguintes).

**Entrega 2: a ficha (depois que o #1099 estiver no ar).**
1. À pergunta "É de hoje?", "não" escrito vale como o botão **Outra data**, e "sim" como **Hoje**.
   Resposta curta de sim ou não nunca vai para a legenda.
2. "Não sei", ou o dia que não se entende, deixa a foto **sem dia** (`data_dita` vazia), em vez de
   presumir o dia do envio.
3. Fase nova **`palhada`, "Palhada (dessecada)"**, no `FASES` do AxiaAtende e, antes, no
   `ESTAGIOS`, no `CHECK ativos_estagio` e no `visao.FASES` do AxiaMarketing. A IA pode responder
   "nenhuma": a resposta que não cabe em fase fica **sem fase**, para o marketing classificar.
4. O catálogo do marketing aceita foto **sem dia e sem safra** (`campo.py:373`, `:431`), sem pôr o
   dia de hoje.
5. As fichas ATV-0774, 0775 e 0776 são corrigidas nos dois projetos: legenda sem " · Não", sem dia,
   fase Palhada.

**Ordem da sessão** (os dois desenhos de hoje usam a migração 025, e a entrega 2 depende do #1099):
plano e execução do **#1098** (025), entrega 1 do **#1097** (026), **#1099** (027), entrega 2 do
**#1097** (028 e a migração do Marketing). O número final é o do plano; cada migração leva a lista
inteira do `CHECK`.

## Escopo desta etapa

**Dentro:**
- entrega 1: migração com as duas situações (e a VOLTA), o fechamento em `motor.tratar`, a retomada
  que pula o canal interno, a Recepção (backend e `frontend/src/Recepcao.jsx`), a correção das 5
  conversas, os testes;
- entrega 2: os três consertos do `campo.py`, a fase Palhada nos dois projetos (com a migração do
  Marketing e a VOLTA), a foto sem dia no catálogo, as três fichas, os testes dos dois projetos;
- os manuais `docs\manuais\recepcao.md` e `docs\manuais\campo-equipe.md` do AxiaAtende e o manual do
  catálogo do AxiaMarketing que lista as fases.

**Fora:**
- o lote e a frase pela hora de envio: é o #1099;
- conversa de cliente (não interna) que parou no meio: segue como hoje;
- reclassificar outras fotos antigas do catálogo como palhada: o dono faz na Caixa, se quiser.

## Impacto em produção

- **Entrega 1:** `axiaatende-backend` (migração e rotas) e `axiaatende-recepcionista` (motor). A
  migração é aditiva (o `CHECK` cresce) e vai antes do restart; a correção das 5 conversas é um
  `UPDATE` delas, só delas. Frontend com build antes do restart.
- **Entrega 2:** os dois serviços do AxiaAtende e o backend do AxiaMarketing. **A ordem é o
  Marketing primeiro**: se o AxiaAtende mandar `palhada` antes de o catálogo aceitar, a foto é
  recusada lá.
- **Janela:** fora de conversa aberta do canal; a Meta reenvia o aviso que não teve resposta.

## ROLLBACK_PLAN

**Entrega 1**
1. `git revert` dos commits da entrega 1 em `C:\AxiaAtende`, build e restart dos dois serviços.
2. Migração VOLTA: as conversas `imagem_recebida`/`logo_recebida` voltam a `parou_no_meio` (com a
   retomada já marcada, para a IA não rodar nelas) e só então o `CHECK` volta à lista anterior.

**Entrega 2**
1. `git revert` dos commits da entrega 2 nos dois projetos e restart.
2. VOLTA do Marketing: só se nenhuma peça estiver na fase `palhada`; se houver, elas passam a sem
   fase antes de o `CHECK` voltar. Mesma coisa no AxiaAtende.
3. Foto que ficou sem dia continua sem dia: a resposta "não sei" foi da pessoa.
4. As três fichas do Willian não voltam ao erro.

## Manual de uso

**`recepcao.md` passa a dizer errado:** a lista de estados de uma conversa não tem "Imagem
recebida" nem "Logo recebida", e o cartão "pararam no meio" hoje conta a equipe que mandou foto.

**`campo-equipe.md` passa a dizer errado:** a pergunta "É de hoje?" só aceita o botão; "não sei"
põe o dia do envio; a lista de fases não tem Palhada.

**O texto, para quem usa:**

1. **Para que serve.** A Recepção mostra a conversa da equipe terminada com o que chegou, e a ficha
   da foto sai com o que a pessoa disse, sem inventar dia nem fase.
2. **Quem usa e quando.** O dono na Recepção, todo dia; a equipe, ao mandar foto ou logo.
3. **O caminho comum.**
   1. Toque 📸 Foto do campo e mande a foto ou a logo.
   2. Na Recepção, a conversa aparece como **Imagem recebida** ou **Logo recebida**.
   3. À pergunta "É de hoje?", pode tocar o botão ou escrever "sim" ou "não".
   4. Não sabe o dia? Escreva "não sei": a foto entra sem dia.
   5. Foto de cobertura morta depois da dessecação: diga "palhada"; ela entra como **Palhada
      (dessecada)**.
4. **O que significa cada sinal.**

   | Na Recepção | Quer dizer |
   |---|---|
   | **Imagem recebida** | alguém da equipe tocou Foto do campo e a foto chegou |
   | **Logo recebida** | alguém da equipe tocou Foto do campo e mandou a logo de um cliente |
   | **Parou no meio** (de alguém da equipe) | tocou Foto do campo e não mandou nada em 30 min |

   No catálogo, **sem dia** quer dizer que a pessoa não sabia a data, e não que a foto é de hoje.
   **Sem fase** quer dizer que a resposta não cabia em nenhuma fase e fica para o marketing.
5. **O que NÃO faz.**
   - Não fecha conversa de cliente: só a do menu interno.
   - Não adivinha a fase quando a resposta não encaixa.
   - Não corrige sozinha foto antiga do catálogo, fora as três do Willian.

## Próximo passo
/writing-plans
