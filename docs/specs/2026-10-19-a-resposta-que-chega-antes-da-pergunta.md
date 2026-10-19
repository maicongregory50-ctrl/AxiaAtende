# A resposta que chega antes da pergunta
**Data:** 2026-10-19
**Chamado:** #1047
**Status:** APROVADO

## Contexto

Hoje de manhã o dono mandou duas fotos do controle de qualidade e **respondeu antes de ser
perguntado**. A linha do tempo, pelos relógios do banco:

| Hora | O que aconteceu |
|---|---|
| 08:09:56 / 08:09:59 | as duas fotos chegam — processadas em **1 s** e **3 s** |
| 08:10:28 | ele escreve *"Começar segunda conferindo qualidade."* |
| **08:10:36** | ele escreve **"Hoje"** |
| **08:10:43 / 08:10:49** | o palpite da IA roda — **já com o "Hoje" dentro da legenda** — e acerta a classe (`controle-de-qualidade`) |
| **08:11:33** | sai **"É de hoje?"** — a pergunta que ele já respondera 57 s antes |
| 08:13:17 | ele toca **Sim** |
| 08:13:50 | catalogado, ATV-0733 e ATV-0734 |

**A causa não é o que parecia, e isso importa para não consertar a coisa errada.**

O dono descreveu o defeito como *"o ideal seria parar o raciocínio e ler a próxima mensagem antes de
concluir"*. **Hoje isso não teria mudado nada:** o palpite rodou às 08:10:43 **com o texto na mão** e
a pergunta saiu mesmo assim. Não faltou **reler** — faltou **ler**. `ia.ler_campo` extrai três
campos (`bastidor`, `produto`, `fase`) e **data não é um deles**. A data só entra pelo botão
*"É de hoje?"* ou pela resposta a uma pergunta já feita.

**E a função que lê exatamente a palavra que ele escreveu já existe.** `campo.ler_data` (linha 626)
tem como primeiro caso `if t in ("hoje", "hj", "sim")`, e `campo.ler_safra` (#982) lê *"safra 2025"*,
*"24/25"* e companhia. As duas são autônomas e já usadas em dois lugares. **Elas nunca foram
apontadas para a mensagem que chega** — só para respostas a perguntas já feitas.

**O ponto exato do código é conhecido**, e o comentário dele já descreve meio conserto
(`campo.responder`, linha 414): *"Texto solto logo depois da foto, sem pergunta aberta: é a legenda
do grupo, **e é lido**"* — onde "é lido" é o `_ler`, que chama a IA para bastidor/produto/fase. É ali
que a data e a safra precisam ser lidas também.

**A demora não é lentidão de código.** Processar cada mensagem levou 0 a 3 s. Os ~95 s entre a foto e
a pergunta são duas esperas deliberadas: `ESPERA_PALPITE` (até 2 min aguardando o palpite) e o tique
de um minuto do laço. **Com a data lida da frase não há pergunta, e a espera desaparece deste
caminho** sem mexer em nenhum dos dois relógios.

## Os fios que encostam

**Quem mais escreve o que esta mudança escreve.** A etapa grava `data_dita` e `safra_dita` em
`atendimento.material_de_campo` — **colunas que já existem e já têm escritor**. Medido por `grep`,
quem escreve nelas hoje:

| Quem | Quando |
|---|---|
| `campo.responder`, ramo `data` | o botão *Sim* (hoje) ou a resposta em texto |
| `campo.responder`, ramo `qual_dia` | o dia dito, ou o presumido quando não entendeu |
| `campo._fechar` (linha ~382) | **presume o dia do recebimento** quando não há dia dito NEM safra dita (#982) |

**Esse terceiro é o fio que importa, e ele é a favor da mudança.** O `_fechar` já trata `data_dita`
preenchida como "não presumir" — então preencher a data mais cedo **não cria caminho novo**: ela
entra pela porta que o `_fechar` já conhece, e `data_presumida` continua `false`, como fica hoje
quando a pessoa responde.

**Quem lê para decidir.** `campo._falta` (linha 325): `if r["data_dita"] is None and
r["safra_dita"] is None and "data" not in feitas: return "data"`. **É a régua inteira**, e é por isso
que preencher a data antes faz a pergunta desaparecer sozinha — sem tocar em `_falta`.

**Quem volta depois:** o `_fechar` (ao fim do grupo) e os avisos de catálogo. Nenhum deles reavalia a
data; só a usam. E a leitura das 06:00 da agenda não toca nada disto.

## O universo medido

Medido em 19/10/2026 no banco de produção, como `axiaatende_ro`:

| Pressuposto | Contagem de hoje |
|---|---|
| peças no catálogo | **26** |
| **que não receberam pergunta nenhuma** | **21 (81%)** |
| perguntas de data já feitas | **5** |
| …em que a legenda já dizia (`hoje`, `ontem`, `safra`, `dd/mm`) | **2** |
| perguntas por tipo | `data` 5 · `legenda` 4 · `bastidor` 2 · `qual_dia` 1 |
| latência de processamento por mensagem | **0 a 3 s** |
| foto → primeira pergunta (as duas de hoje) | **94 s** e **97 s** |
| foto → catalogado (as duas de hoje) | **3,9 min** |

**Três leituras, e a terceira é um limite do próprio argumento:**

1. **O fluxo já é fluido para 81% das peças.** O atrito está concentrado na pergunta de data, e em
   **2 de 5** vezes ela foi feita com a resposta já na tela. É exatamente o incômodo relatado.
2. **A espera de 95 s é deliberada, não defeito.** Nenhum dos dois relógios é tocado aqui.
3. **A amostra é pequena: 26 peças e 5 perguntas.** O argumento desta spec é sobre a **forma** do
   fluxo (existe uma função que lê a palavra e ninguém a chama), não sobre volume. Dito para que o
   número não seja lido como maior do que é.

## Conformidade com o Manual legal

Não se aplica: a etapa não toca imposto, código fiscal, régua, texto legal em documento nem SPED.

## Conformidade com a casa

**Gatilho tocado: um — "agente ou chamada a modelo de IA" (R7).** Nenhum segredo (R3), nenhum
serviço, porta ou exposição (R4/R1 — nada muda de bind, porta ou tarefa), nenhum dado novo (R2 — as
duas colunas já existem e o banco já tem cópia verificada), nenhum processo com sessão de agente
(R9), nenhum projeto novo (R8).

- **R7: conforme.** Trecho lido: *"O que NÃO cobre: o **harness** de cada agente. O que um agente
  pode fazer sozinho é decisão do código que o envolve... e a barreira mora lá, com quem a
  constrói."* E aqui a etapa **reduz** o que depende da IA, em vez de ampliar: a data passa a sair de
  um **parser determinístico** (`ler_data`, `ler_safra`), não do modelo. `ia.ler_campo` **não é
  alterada** — mesmo esquema, mesmos três campos, mesmo enum. Nada muda no inventário de agentes, na
  política de uso de IA, no desligamento ou na lista de notificação.

## Decisão

**1. A data e a safra passam a ser lidas de cada mensagem que chega**, no mesmo ponto em que o texto
já é absorvido como legenda e já é lido pela IA (`campo.responder`, o ramo "texto solto", e o ramo
`bastidor`, que faz o mesmo). Se `ler_data` ou `ler_safra` devolverem valor, ele é gravado e **a
pergunta de data nunca é feita** — porque `_falta` já para de pedi-la sozinha.

**Por um parser, não pela IA.** Seria possível acrescentar a data ao que o modelo extrai; é pior. O
parser é determinístico, já existe, já é testado e já é o que interpreta a resposta hoje — então a
frase e a resposta passam a ser lidas **pela mesma régua**, o que é a propriedade que queremos. A IA
erraria uma data de vez em quando, em silêncio, e data errada vai ao catálogo sem ninguém ver.

**2. Reler a linha imediatamente antes de enviar a pergunta** (`_perguntar_proxima`), para que uma
mensagem processada entre a leitura da linha e o envio não se perca.

**Dito com honestidade, porque o dono pediu isto acreditando que era o conserto:** a releitura
**não** teria mudado o caso de hoje, e em boa medida **já existe** — `_falta` lê o estado atual da
linha, e os caminhos de resposta já re-leem do banco. O que não existe é a releitura no último
instante antes do envio. A janela é pequena (processamento de 0–3 s contra tique de 1 min) e **não há
ocorrência medida**. Entra porque o dono decidiu, informado disso, e porque custa duas linhas.

**3. Nada de caminho especial para o dono.** Ele levantou a possibilidade ("principalmente quando for
comigo"); recusado no desenho, com o motivo: o conserto é o mesmo código para todos, 81% das peças já
passam sem pergunta, e uma regra só para uma pessoa é a primeira que se esquece ao mexer no fluxo
três semanas depois.

## Escopo desta etapa

**DENTRO**

1. `backend/campo.py` — um ajudante que passa o texto por `ler_data` e `ler_safra` e grava o que
   achar, chamado nos **dois** pontos em que o texto livre é absorvido (o "texto solto" da linha 414
   e o ramo `bastidor` da 445).
2. `backend/campo.py` — a releitura da linha no último instante, em `_perguntar_proxima`.
3. `tests/test_campo.py` — o caso de hoje ponta a ponta (**duas fotos + frase + "Hoje" ⇒ zero
   perguntas**), a safra pela frase, e a prova de que `data_presumida` continua `false`.
4. `docs/manuais/campo-equipe.md` — que dizer a data na frase dispensa a pergunta.

**FORA**

- **Acrescentar data ao que a IA extrai** (`ia.ler_campo` não muda) — decisão 1, com o motivo.
- **Caminho especial para o dono** — decisão 3.
- **Mexer em `ESPERA_PALPITE` ou no tique do laço.** O dono pesou e recusou: foi o palpite que
  acertou a classe hoje, em 47 s, e encurtar a espera é apostar contra ele.
- **Ler produto e fase da frase por parser** — isso já é da IA, e ela acertou a classe hoje. Não há
  caso medido de produto ou fase antecipados e perdidos.
- **O `unsupported`** que ele mandou às 08:09 (o sétimo dele): continua em silêncio, porque é da
  casa. Ver a correção de medição registrada no #1027.

## Impacto em produção

- **`axiaatende-recepcionista`** (8008): só código, **nenhuma migração**. `Restart-Service
  axiaatende-recepcionista`.
- **`axiaatende-backend` (8009) não é tocado** — não há schema novo, então um serviço só.
- **Banco:** nada. Nenhuma coluna, nenhuma linha, nenhuma migração.
- **Janela:** qualquer hora. Para cliente, **nenhum efeito**: o caminho é o do canal de campo, que é
  de equipe e representante.
- **Efeito esperado:** a próxima foto com a data na frase entra no catálogo **sem nenhuma pergunta**.

## ROLLBACK_PLAN

1. `git revert <commit>`.
2. `Restart-Service axiaatende-recepcionista`.
3. Conferir: uma foto com *"hoje"* na frase volta a receber *"É de hoje?"*.

**Nada a desfazer no banco** — a etapa não tem migração e não reescreve o que já foi catalogado. As
peças já gravadas ficam como estão. **É o rollback mais barato de todos os desta semana**, e é
consequência de a etapa não criar dado nem estado.

## Manual de uso

**1. Para que serve.** Quando você já sabe o que a OlivIA vai perguntar, **diga antes** e ela não
pergunta. Dizer *"hoje"*, *"ontem"*, *"09/10"* ou *"safra 2025"* junto com a foto já resolve a data.

**2. Quem usa e quando.** Quem manda foto do campo e quer despachar rápido: a frase completa faz a
foto entrar no catálogo sem nenhuma pergunta.

**3. O caminho comum.**
1. Mande a foto (ou várias, em seguida — são uma conversa só).
2. Escreva **uma frase** dizendo o que é, de que produto, e **quando**: *"colheita do centeio IPR 89
   hoje"*. A frase pode vir antes ou depois da foto.
3. A OlivIA responde *"Recebi."* e, se a frase cobriu tudo, **não pergunta nada** — a foto vai ao
   catálogo.
4. Faltou algo? Ela pergunta **só o que faltou**, uma coisa por vez, como antes.

**4. O que significa cada sinal.**

| O que você vê | O que quer dizer |
|---|---|
| *"Recebi."* e **mais nada** | a frase cobriu tudo, inclusive a data. Em alguns minutos chega *"entrou no catálogo"* |
| *"É de hoje?"* | a data não estava na frase. Toque **Sim**, ou **Outra data** e diga o dia |
| *"É de hoje?"* **mesmo tendo escrito a data** | não deve mais acontecer. Se acontecer, me avise: era o defeito deste chamado |
| A data no catálogo **sem** você ter respondido nada | foi lida da sua frase. Vale igual a resposta dada no botão — não é palpite |

**5. O que isto NÃO faz.**
- **Não adivinha data.** Só *"hoje"*, *"ontem"*, *"anteontem"*, uma data escrita (`09/10`,
  `2026-10-09`) e a safra. Qualquer outra coisa continua levando à pergunta.
- **Não lê produto e fase por palavra exata** — isso continua sendo a IA, que já acerta e já
  pergunta só o que faltou.
- **Não muda nada para cliente:** este caminho é do canal de campo.
- **Não deixa a foto entrar sem data**: sem data dita nem safra, o dia do recebimento continua sendo
  presumido no fechamento, como hoje.

**O que o manual de hoje passa a dizer errado:** o passo 2 do `campo-equipe.md` descreve a data
**sempre** como pergunta (*"e 'É de hoje?' (toque Sim, ou Outra data…)"*). Passa a ser *"se você não
disse a data na frase"*. É a única frase que muda.

## Próximo passo

`/writing-plans`.
