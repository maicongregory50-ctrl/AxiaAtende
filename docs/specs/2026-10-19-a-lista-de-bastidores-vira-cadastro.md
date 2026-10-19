# A lista de bastidores vira cadastro, e a resposta que não encaixa é dita
**Data:** 2026-10-19
**Chamado:** #1048
**Status:** APROVADO

## Contexto

Hoje às 08:29 o dono mandou **oito fotos** com a legenda *"Estoque."*. Às 08:30 a OlivIA propôs
*"Parece beneficiamento. É isso?"*; às 08:31 ele respondeu **"Estoque."**; às 08:31 ela passou para
*"É de hoje?"* e seguiu. **As oito foram ao catálogo sem classe nenhuma** (ATV-0737 a ATV-0744).

Ele disse a palavra duas vezes. **O sistema não tem onde pô-la** — e não disse isso a ninguém.

**São duas causas somadas, e as duas foram medidas.**

**A primeira: a lista de cinco bastidores não cobre o que a Renascer fotografa.** Os cinco são
`campo-de-sementes`, `colheita`, `beneficiamento`, `controle-de-qualidade` e `entrega`. As legendas
sem classe pedem outras quatro:

| Quando | Peças | A legenda | O palpite da IA |
|---|---|---|---|
| 19/10 08:29 | **8** | "Estoque." | beneficiamento |
| 15/10 | 2 | "Manejo, rolo faca" | colheita |
| 13/10 | 4 | "Parte externa da empresa, estacionamento" | — |
| 12/10 | 6 | "Carregamentos, bastidores, carga" | — |
| 12/10 | 1 | "Primeira versão do AVR Lanço, fórmula" | — |

**A segunda, e é a que mais incomoda: quando a resposta não encaixa, ninguém diz.** O caminho é
este: o texto livre é acrescentado à legenda, a IA relê, não acha, e o fluxo **segue para a próxima
pergunta** marcando `bastidor` como já perguntado. A peça é catalogada, parece resolvida, e está
vazia. É o fracasso silencioso de novo — o modo de falha que este projeto mais combate.

**E a lista vive em SEIS lugares, em dois repositórios** — medido por `grep`:

| Onde | O quê |
|---|---|
| AxiaAtende `campo.py:51` | `BASTIDORES` — chave → rótulo dos botões |
| AxiaAtende `ia.py:120` | o `enum` que o classificador pode devolver |
| AxiaAtende `ia.INSTRUCOES_CAMPO` | a prosa que descreve cada bastidor ao modelo |
| AxiaMarketing `visao.py:67` | a lista no prompt do Gemini que dá o palpite |
| AxiaMarketing `campo.py:257` | `ETIQUETA_DO_BASTIDOR` |
| AxiaMarketing `campo.py:277` | a regra de **institucional** (três dos cinco não levam produto) |

**E faltar em um deles não dá erro: dá silêncio.** `etiquetas = [ETIQUETA_DO_BASTIDOR[b]] if b in
ETIQUETA_DO_BASTIDOR else []`. Acrescentar uma categoria só aqui faria a peça chegar lá **sem
etiqueta**, calada.

**A assimetria que fecha o argumento:** nesta mesma casa os **produtos** são cadastro — um `ajustes`
com `campo.produtos`, lido por `campo.produtos(con)` e escrito por `guardar_produtos`. Os
**bastidores** são código, em seis lugares. Duas listas do mesmo fluxo, tratadas de modos opostos.

## Os fios que encostam

**Quem mais escreve o que esta mudança escreve.** Duas coisas:

| O que a etapa escreve | Quem mais escreve hoje |
|---|---|
| `atendimento.ajustes`, chave nova `campo.bastidores` | as migrações e os endpoints de ajuste da tela Destinos (horário, canal de campo, avisado no não) — **nenhum deles toca esta chave** |
| `material_de_campo.classe_bastidor` | `campo.responder` (a resposta) e `campo._aplicar_classe`. **A etapa não muda quem escreve, só o conjunto de valores aceitos** |

**`classe_bastidor` é `text` sem `CHECK`** (medido em `pg_constraint`): valor novo **não pede
migração de coluna**. O único `CHECK` do assunto é `material_pergunta`, sobre
`pergunta_pendente`, e ele já aceita `'bastidor'` — então o aviso reusa o estado que existe, sem
alterar constraint.

**Quem lê para decidir.** `campo.BASTIDORES` é lido em `_perguntar` (o rótulo do botão do palpite) e
no `_falta`/`_aplicar_classe`; `ia.ler_campo` monta o `enum` a partir da sua lista. **O leitor que
não é nosso é o AxiaMarketing**, e é o fio que atravessa projeto: ele consome `classe_bastidor` pelas
rotas `/campo/*` com a `chave_pedido`, e tem a **sua própria** lista nos três lugares acima. Enquanto
ele não ler o cadastro, peça com categoria nova chega lá **sem etiqueta**. Está em *Escopo — FORA*,
com chamado próprio.

**Quem volta depois:** `_aplicar_classe`, no fechamento do grupo, e os avisos de catálogo. Nenhum
reavalia a classe; só a usam. A leitura das 06:00 da agenda não toca nada disto.

## O universo medido

Medido em 19/10/2026 no banco de produção, como `axiaatende_ro`:

| Pressuposto | Contagem de hoje |
|---|---|
| peças de campo | **35** |
| **sem classe de bastidor** | **27 (77%)** |
| …e **catalogadas assim** | **27 de 27** |
| grupos sem classe | **7** |
| hoje (19/10) | **11 peças, 8 sem classe** |
| com classe | `controle-de-qualidade` 3 · `campo-de-sementes` 3 · `entrega` 2 |
| grupos sem classe em que a IA **tinha** palpite e ele foi recusado | **2** (19/10 "Estoque." → beneficiamento; 15/10 "Manejo" → colheita) |
| `classe_bastidor` tem `CHECK`? | **não** — é `text` livre |
| `classe_fase` preenchida | **0 peças** |

**Três leituras que decidiram o desenho:**

1. **Não é dívida histórica: é hoje.** 8 das 11 peças de hoje estão sem classe. O número de 77% é
   grande em parte porque o atendente de classificação é de 12/10, mas o problema não parou.
2. **Em 2 dos 7 grupos a IA tinha palpite e a pessoa o recusou** — e nos dois a recusa levou a
   **nada**, não a uma segunda tentativa. É o alvo exato do conserto do silêncio.
3. **`classe_fase` está em zero nas 35 peças.** Por isso `FASES` — que tem exatamente o mesmo
   defeito de desenho (código em dois lugares) — **fica fora**: não há caso medido, e consertar o que
   não dói é inventar trabalho.

## Conformidade com o Manual legal

Não se aplica: a etapa não toca imposto, código fiscal, régua, texto legal em documento nem SPED.

## Conformidade com a casa

**Dois gatilhos tocados: "agente ou chamada a modelo de IA" (R7) e "dado novo" (R2).** Nenhum segredo
(R3), nenhum serviço, porta ou exposição (R4/R1 — nada de bind, porta ou tarefa muda), nenhum
processo com sessão de agente (R9), nenhum projeto novo (R8).

- **R7: conforme.** Trecho lido: *"O que NÃO cobre: o **harness** de cada agente. O que um agente
  pode fazer sozinho é decisão do código que o envolve... e a barreira mora lá, com quem a
  constrói."* A etapa muda **o que o classificador pode devolver** — o `enum` passa a ser montado do
  cadastro em vez de uma lista no código. A barreira continua existindo e continua no código: o
  `enum` segue fechado, e o valor fora dele continua recusado pela API. **O que muda é de onde a
  lista vem, não que exista uma.** Nada no inventário de agentes, na política de IA, no desligamento
  ou na lista de notificação.
- **R2: conforme.** O "dado novo" é **uma linha** em `atendimento.ajustes`, tabela que já existe, no
  banco já coberto por `rotina:backup-axiaatende-banco` e `backup_cloud_axiaatende_banco.ps1`.
  Trecho lido: *"Todo dado vivo tem cópia verificada, em disco e fora"* — e a prova mecânica lista
  esta base. Nada a mudar no backup.

Li o `PROJETO.md` dos dois projetos. O *Ofereço* do AxiaMarketing confirma que a Caixa e o catálogo
são dele; o *Exijo* do AxiaAtende não muda.

## Decisão

**1. A lista de bastidores vira cadastro, no molde dos produtos.** Um `ajustes` com a chave
`campo.bastidores`, guardando **objetos** e não só slugs — porque os seis lugares precisam de coisas
diferentes da mesma linha:

```
{"chave": "estoque", "rotulo": "Estoque / armazém",
 "descricao": "semente guardada, armazém, pálete, sacaria em estoque",
 "institucional": true}
```

`chave` serve ao `enum` e ao banco; `rotulo` ao botão e à etiqueta; `descricao` à prosa que o modelo
lê; `institucional` à regra de produto. **Uma linha, seis consumidores.**

**2. As quatro categorias que o dono escolheu** entram na semente da migração, ao lado das cinco de
hoje: `estoque` (Estoque / armazém), `estrutura` (Estrutura da empresa), `produto-embalagem`
(Produto / embalagem) e `manejo` (Manejo / implemento). **Nove no total** — e nove cabe numa lista do
WhatsApp, que aceita dez linhas.

**A regra de institucional, proposta por mim e corrigível pelo dono:** `estoque` e `estrutura` são
institucionais (não levam produto); `produto-embalagem` e `manejo` **levam** produto — o primeiro
porque a foto é do produto, o segundo porque o manejo acontece numa lavoura que tem produto.

**3. A ausência do cadastro não cala o fluxo.** Se a linha faltar, `campo.bastidores(con)` devolve a
**semente dos cinco originais**, que fica no código **só para isso** — no molde do `interno.ligado`
do #1031, cujo padrão na ausência é *ligado*. O cadastro é a verdade; a semente é o que impede o
serviço de ficar sem lista se alguém apagar a linha. Degradar para cinco é pior que nove e **muito**
melhor que zero.

**4. A resposta que não encaixa é DITA.** Quando o texto livre na pergunta de bastidor não é
classificado, em vez de seguir calada a OlivIA manda **uma vez** a lista fechada das categorias. Se
nem isso resolver, ela **diz que a peça vai sem classe** e que o marketing classifica na Caixa.
Uma tentativa, nunca duas — a lição do teto do #1028. **O que não se aceita é a peça ir vazia em
silêncio;** ir vazia **dito** é aceitável.

## Escopo desta etapa

**DENTRO**

1. `backend/migracoes/022_bastidores_em_cadastro.sql` (+ `_VOLTA`) — a linha `campo.bastidores` com
   as **nove** categorias.
2. `backend/campo.py` — `bastidores(con)` e `guardar_bastidores(con, lista)` no molde de
   `produtos`/`guardar_produtos`; `BASTIDORES` deixa de ser a verdade e passa a ser a **semente**.
3. `backend/ia.py` — `ler_campo` recebe os bastidores e monta o `enum` **e a prosa** a partir deles;
   `INSTRUCOES_CAMPO` deixa de ser constante.
4. `backend/campo.py` — o aviso: a lista fechada uma vez, e a frase de "vai sem classe".
5. `tests/` — o caso de hoje (*"Estoque."* ⇒ classificado em `estoque`), a resposta que não encaixa
   **sendo dita**, a ausência do cadastro caindo na semente, e o `enum` do modelo vindo do cadastro.
6. `docs/manuais/campo-equipe.md` — as categorias novas e o que acontece quando não encaixa.

**FORA**

- **O lado do AxiaMarketing** — ler a lista do cadastro em vez das três constantes dele
  (`visao.BASTIDORES`, `ETIQUETA_DO_BASTIDOR`, a regra de institucional). **Chamado próprio, outro
  repositório.** Até ele existir, peça com categoria nova chega lá **sem etiqueta** — dito aqui para
  não entregar meia ponte chamando de ponte.
- **`FASES`** — mesmo defeito de desenho, **zero** casos medidos (`classe_fase` em 0 de 35).
- **Reclassificar as 27 peças já catalogadas.** Nenhuma está errada; estão vazias. Mexer em dado
  gravado e no catálogo do marketing por isso é risco sem dor.
- **Tela para editar a lista.** O cadastro muda por migração ou por `guardar_bastidores`, como os
  produtos.

## Impacto em produção

- **`axiaatende-recepcionista`** (8008) e **`axiaatende-backend`** (8009): migração 022 aplicada pelo
  serviço ao subir; reiniciar os **dois**.
- **Banco:** migração 022 — **uma linha** em `ajustes`. Nenhuma coluna, nada apagado, nenhuma peça
  tocada.
- **Janela:** qualquer hora. Para cliente, **nenhum efeito**.
- **Efeito imediato:** a próxima foto de estoque classifica em `estoque`; e a resposta que não
  encaixa passa a receber a lista em vez de silêncio.

## ROLLBACK_PLAN

1. `git revert <commit>`.
2. O `_VOLTA` à mão, em janela elevada (**não há verbo `voltar`**):
   `psql -f backend\migracoes\022_bastidores_em_cadastro_VOLTA.sql` — apaga a linha do ajuste.
3. `Restart-Service axiaatende-recepcionista` e `axiaatende-backend`.
4. Conferir: *"Estoque."* volta a receber o palpite de beneficiamento e a peça volta a ir sem classe.

**Reverter só o código já basta na prática:** com a linha do ajuste no banco e o código antigo,
`BASTIDORES` volta a ser a verdade e a linha é simplesmente ignorada. **As peças classificadas em
`estoque` ficam** — e ficam legíveis, porque `classe_bastidor` é texto livre; o que elas perdem é a
etiqueta do lado do marketing, que já não tinham.

## Manual de uso

**1. Para que serve.** A OlivIA passa a reconhecer mais do que a Renascer fotografa — estoque,
estrutura da empresa, produto e manejo —, e quando ela **não** entende a sua resposta ela **diz**, em
vez de catalogar a foto sem classe e ficar quieta.

**2. Quem usa e quando.** Quem manda foto do campo. Antes, *"Estoque."* virava oito fotos sem classe
e ninguém era avisado.

**3. O caminho comum.** Igual ao de hoje. A diferença aparece em dois momentos:
1. a sua frase passa a poder ser classificada em **nove** categorias, não cinco;
2. se a sua resposta não encaixar em nenhuma, ela manda **a lista** para você escolher — uma vez. Se
   você não escolher, ela diz que a foto **vai sem classe** e que o marketing classifica na Caixa.

**4. O que significa cada sinal.**

| O que você vê | O que quer dizer |
|---|---|
| *"Parece estoque. É isso?"* | a IA achou a categoria nova pela sua frase |
| A **lista** de categorias depois de você escrever algo | a sua resposta não encaixou. Escolha uma — ela pergunta isto **uma vez só** |
| *"Vou guardar sem classe; o marketing classifica na Caixa."* | ninguém escolheu. A foto entra no catálogo **sem classe**, e agora **você sabe disso** |
| A foto no catálogo sem classe e **sem ninguém dizer nada** | não deve mais acontecer. Se acontecer, me avise: era o defeito deste chamado |

**5. O que isto NÃO faz.**
- **Não reclassifica as fotos antigas.** As 27 sem classe continuam sem classe.
- **Não faz a categoria nova aparecer etiquetada no catálogo do marketing** — ainda. Aquele lado tem
  a lista dele, e lê-la do cadastro é chamado próprio.
- **Não deixa editar a lista por tela.** Ela muda por migração, como os produtos.
- **Não mexe nas fases** da lavoura.

**O que o manual de hoje passa a dizer errado:** o `campo-equipe.md` não lista as categorias (ele
descreve o que a OlivIA pergunta, não o conjunto), então **nada fica falso**. Ganha a seção das
categorias novas e a do que acontece quando a resposta não encaixa.

## Próximo passo

`/writing-plans`.
