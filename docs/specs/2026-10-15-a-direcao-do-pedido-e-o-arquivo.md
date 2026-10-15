# A direção do pedido, e o arquivo que ninguém abre
**Data:** 2026-10-15
**Chamado:** #1027
**Status:** APROVADO

## Contexto

Em 15/10/2026, 09:17, a **Yasmin, da World Ráfia Representações** (5542936180594), escreveu ao
WhatsApp da Renascer: *"Trabalhamos com embalagens de Ráfia (Convencional, Laminado, Convertex) e
Big Bags... Eu poderia te fazer uma **cotação** para apresentar nossos preços e condições de
fornecimento?"*, e mandou um PDF de apresentação institucional.

Ela é **fornecedora prospectando** — quem quer **vender para** a Renascer. Duas coisas aconteceram:

1. **a IA propôs `comercial`**, que é o caminho de quem quer **comprar da** Renascer;
2. **ao PDF, a resposta foi `nao entendo: document`** e o menu principal. A retomada das 09:48
   gravou `sem opcao` e a conversa morreu ali.

**A causa do primeiro não é o modelo: é o cadastro.** A IA recebe cada opção como
`chave: caminho (descrição)` (`ia._lista`), e o que ela recebeu foi:

- `comercial` → **"Cotar sementes"**
- `fornecedores` → "Atendimento a fornecedores"
- `fornecedores.ainda` → **nada**

A Yasmin escreveu *"cotação"*. **A única opção cujo texto continha "cotar" era `comercial`.** A IA
fez a coisa razoável com o dado que tinha. E o dado é escasso em geral: **23 das 29 opções não têm
descrição alguma**.

**O segundo caso não é defeito — é decisão sua de 12/10/2026**, escrita no código: *"figurinha,
audio, foto de quem nao e da equipe, localizacao, contato e documento recebem uma linha curta, nunca
as boas-vindas com o menu inteiro"*. A linha curta existe e está certa como princípio; o que ela não
faz é dizer **por que** o arquivo não serve, nem abrir caminho. Mudar isso é capacidade nova, e foi
decidido aqui.

**Uma ressalva de honestidade que muda o tom do argumento:** a IA propôs **4 vezes em 37
conversas** (1 aceita, 1 recusada, 2 sem resposta). **A amostra não permite afirmar que ela erra
muito.** O argumento desta spec é **estrutural, não estatístico**: é sobre o que ela recebe para
decidir, não sobre a frequência medida de erro.

## Os fios que encostam

**Quem mais escreve o que esta mudança escreve.** A etapa **altera linhas que já existem** em
`atendimento.menu` (a coluna `descricao` de sete opções) — diferente do #1031, que só inseriu. Medido
por `grep`, quem escreve em `menu`:

| Quem | O que grava |
|---|---|
| as **migrações** | tudo: a árvore, os textos, e agora as descrições |
| `rotas_telas.py:255` (a tela Destinos) | **somente `destino_id`** — a "ligação" de uma opção a uma pessoa |

**Ninguém mais escreve `descricao`.** A tela Destinos não a edita, e nem a exibe (o `SELECT` dela em
`rotas_telas.py:210` traz `id, chave, caminho, perguntas, destino_id, texto_antes` — `descricao` não
está). Consequência aceita: **depois desta etapa, mudar uma descrição continua sendo migração**,
porque não existe tela para isso. Está em *Escopo — FORA*.

**Quem lê `descricao` para decidir, e aqui está a assimetria que decide o desenho.** Dois leitores:

| Quem lê | O que faz com ela |
|---|---|
| `ia._lista` | entra no texto que a IA classifica — é o dado que faltava |
| `motor.perguntar` → `Opcao(id, rotulo, descricao)` | vai para a mensagem na Meta: **a linha de lista mostra a descrição; o botão NÃO** |

**Então a mesma coluna tem dois públicos, e qual deles lê depende do número de irmãos** (`perguntar`
manda botões com `MAX_BOTOES = 3` ou menos, lista acima disso). Medido:

- **lida pelo cliente** (sai como lista): os 7 filhos da raiz — `comercial`, `fretes`, `financeiro`,
  `fornecedores`, `trabalhe`, `qualidade`, `encerrar` — e os 5 estados de `comercial.produtor` e os 5
  de `comercial.revenda`;
- **lida só pela IA** (sai como botão): os 3 filhos de `comercial`, os 3 de `financeiro`, os 2 de
  `fornecedores`, os 2 de cada nó `.pr`, e os 2 do `raiz_interna`.

É o que permite escrever para a máquina onde ninguém de fora lê, e escrever para gente onde o
cliente lê. **Sem essa distinção, uma descrição boa para a IA entraria na tela do cliente.**

**Quem volta depois: ninguém.** Nenhuma rotina revisita `descricao`. A agenda das 06:00 não a toca; a
árvore só muda por migração.

## O universo medido

Medido em 15/10/2026 no banco de produção, como `axiaatende_ro`:

| Pressuposto | Contagem de hoje |
|---|---|
| opções no menu do cliente (sem as duas raízes) | **29** |
| **sem descrição** | **23** — 17 dos 21 destinos, 4 dos 7 menus, e o `encerrar` |
| a descrição de `comercial` | **"Cotar sementes"** — a armadilha lexical do caso |
| a descrição de `fornecedores.ainda` | **vazia** |
| propostas da IA em toda a história | **4** — 1 aceita (`fornecedores.ja`), 1 recusada (`fretes`), 2 sem resposta (`comercial.revenda`, `comercial`) |
| conversas no total | 37 |
| `nao entendo: document` | **2** envios, 2 destinos (a Yasmin e um interno) |
| `nao entendo: unsupported` | 13 envios, **1** destino — o robô do #1028 |
| `nao entendo` de imagem, áudio ou vídeo de quem não é da equipe | **0** — nunca aconteceu |
| limite da coluna `descricao` | **72 caracteres** (`menu_descricao`) |

**Três leituras que decidiram o desenho:**

1. **A amostra de propostas da IA é 4.** Não dá para medir acerto; dá para ver o que ela recebe.
   Toda afirmação desta spec sobre a IA é sobre o **insumo**, não sobre a taxa de erro.
2. **O caso real é `document` (2), não imagem nem áudio (0 cada).** A linha nova vale para arquivo, e
   a genérica fica para o que nunca chegou e para figurinha e localização — não se desenha para o
   que não aconteceu.
3. **O `unsupported` fica de fora da linha nova, e é decisão:** os 13 são de um robô, e o teto de 2
   do #1028 já trata a repetição. Chamar `unsupported` de "arquivo" seria dizer uma coisa falsa a
   quem o mandou.

## Conformidade com o Manual legal

Não se aplica: a etapa não toca imposto, código fiscal, régua, texto legal em documento nem SPED.

## Conformidade com a casa

**Gatilho tocado: um — "agente ou chamada a modelo de IA" (R7).** A etapa muda **o insumo e a
instrução** da IA do atendimento. Os outros cinco não: nenhum segredo (R3), nenhum serviço, porta,
tarefa ou exposição de rede (R4/R1), nenhum dado que o backup já não cubra (R2 — altera linhas de
`menu`, no banco já coberto por `rotina:backup-axiaatende-banco`), nenhum processo que hospede sessão
de agente (R9), nenhum projeto novo (R8).

- **R7: conforme.** Trecho lido: *"O que NÃO cobre: o **harness** de cada agente. O que um agente
  pode fazer sozinho é decisão do código que o envolve... e a barreira mora lá, com quem a constrói.
  Esta responsabilidade é sobre governança: quem existe, o que pode, quem desliga, quem é avisado."*
  Esta etapa não muda **o que a IA pode** — ela continua só devolvendo uma chave de uma lista fechada,
  com `enum` no esquema de saída e conferência no banco. Muda **o que ela sabe** ao decidir. Nada no
  inventário de agentes, na política de uso de IA, no desligamento ou na lista de notificação.
- Lido também o `politica-uso-ia.md`: nada ali trata da classificação da OlivIA. Não é alterado.

## Decisão

**Duas decisões do dono em 15/10/2026.**

**1. A direção se conserta pelo cadastro E pela instrução** (não por um dos dois):

- **Sete descrições**, e cada uma escrita para quem a lê:
  - **para o cliente e para a IA** (saem em lista): `comercial` deixa de ser *"Cotar sementes"* e
    passa a dizer que é quem quer **comprar**; `fornecedores` passa a dizer que é quem quer
    **vender** para a Renascer;
  - **só para a IA** (saem em botão, invisíveis ao cliente): `comercial.produtor`,
    `comercial.revenda`, `comercial.corretor`, `fornecedores.ja` e `fornecedores.ainda` ganham o
    vocabulário de cada lado — inclusive as palavras que um fornecedor prospectando usa ("oferecer",
    "apresentar nossos preços", "condições de fornecimento", "cotação de venda").
- **Uma linha na instrução da IA** dizendo que a **direção** do pedido importa: quem oferece não é
  quem pede.

**As 16 descrições que continuam vazias não são esquecimento:** são nomes de estado (SC, PR, RS, SP,
Cascavel, Ponta Grossa, Outro) e o `encerrar`. Nome de estado não precisa de explicação, e enchê-los
poria texto na tela do cliente sem ninguém ganhar nada.

**2. Arquivo ganha linha própria.** `document`, `audio` e `video` de quem não é da equipe passam a
receber uma linha que **diz por que** não serve e **abre caminho**: não consigo abrir arquivo por
aqui, me conte em uma linha, ou escreva *menu*. A linha genérica de 12/10 fica para figurinha,
localização, contato e `unsupported`.

**O que a decisão 2 NÃO muda:** o princípio de 12/10 continua — nada disso traz as boas-vindas com o
menu inteiro, e o teto de 2 do #1028 continua valendo por destino. Só o **texto** de três tipos muda.

## Escopo desta etapa

**DENTRO**

1. `backend/migracoes/019_direcao_do_pedido.sql` (+ `_VOLTA`) — as sete descrições. O `_VOLTA`
   devolve exatamente os valores de hoje, inclusive as duas vazias.
2. `backend/ia.py` — a linha da direção em `INSTRUCOES`. Só essa: nada muda no modelo, no esquema de
   saída, no `enum`, no tempo nem no esforço.
3. `backend/motor.py` — a linha nova de arquivo, e a escolha por `e.tipo`.
4. `tests/test_motor.py` e `tests/test_ia.py` — o documento recebendo a linha nova; a figurinha
   continuando com a genérica; e a instrução contendo a palavra da direção.
5. `docs/manuais/recepcao.md` — o que mudou na tela do cliente (duas descrições que ele lê) e a
   linha nova de arquivo.

**FORA**

- **Encher as outras 16 descrições.** Nome de estado não precisa.
- **Uma tela para editar descrição.** Continua sendo migração, e isso fica dito — não é lacuna
  descoberta, é escopo.
- **Imagem, áudio e vídeo na linha de arquivo?** `document`, `audio` e `video` entram; **imagem
  não** — de quem é da equipe ela é o canal de campo, e de cliente **nunca chegou** (0 medido).
  Quando chegar, é chamado próprio, e aí se saberá o que a pessoa queria.
- **`unsupported`** — fica na linha genérica, pelo motivo da seção *O universo medido*.
- **Mandar o arquivo a alguém** (o caminho que o dono recusou): nenhum PDF é encaminhado.
- **Mexer no modelo, no `enum` ou no esquema de saída da IA.**

## Impacto em produção

- **Serviço `axiaatende-recepcionista`** (8008): a migração 019 é aplicada **pelo serviço ao subir**,
  e o `ia.py` e o `motor.py` só valem depois do restart. `Restart-Service
  axiaatende-recepcionista`, em janela elevada.
- **`axiaatende-backend` (8009)** também aplica migração ao subir: reiniciar os **dois**, para
  nenhum ficar com schema antigo.
- **Banco:** migração **019**, que faz `UPDATE` em **sete linhas** de `atendimento.menu`. Nenhuma
  coluna criada, nada apagado.
- **Janela:** qualquer hora. **A mudança é visível ao cliente** em duas linhas do menu principal —
  `comercial` e `fornecedores` —, e é por isso que o manual muda junto.
- **Custo:** nenhum aumento de chamada à IA. O texto do sistema cresce algumas dezenas de tokens por
  chamada, a US$ 0,10 por milhão de tokens de entrada.

## ROLLBACK_PLAN

1. `git revert <commit>`.
2. Rodar o `_VOLTA` **à mão**, em janela elevada — **não existe verbo `voltar`** no módulo de
   migrações (regra 3 dele: *"o `_VOLTA.sql` nunca é aplicado sozinho; ele existe para a mão de quem
   desfaz"*). O arquivo abre o próprio `BEGIN/COMMIT` e apaga a linha de `casa.mudancas`:
   `psql -f backend\migracoes\019_direcao_do_pedido_VOLTA.sql`.
3. `Restart-Service axiaatende-recepcionista` e `Restart-Service axiaatende-backend`.
4. Conferir: `SELECT descricao FROM atendimento.menu WHERE chave = 'comercial'` volta a
   **"Cotar sementes"**.

**A ordem 1 antes de 2 importa:** com o código novo e as descrições antigas nada quebra (a IA só
recebe menos contexto); com o código antigo e as descrições novas também não. **Não há estado
intermediário perigoso** — é a diferença desta etapa para o #1031, onde a ordem era trava.

**Rollback parcial, por decisão:** as duas são independentes. Dá para reverter só a linha de arquivo
(código) mantendo as descrições (banco), ou o contrário.

## Manual de uso

**1. Para que serve.** Duas correções no atendimento de quem escreve em vez de tocar. Quem oferece
produto ou serviço **para** a Renascer deixa de ser mandado ao Comercial, que é o caminho de quem
quer **comprar**. E quem manda um arquivo passa a receber uma resposta que explica o que fazer, em
vez de uma frase que não diz por que o arquivo não serve.

**2. Quem usa e quando.** Ninguém "usa": é o atendimento no WhatsApp. Você percebe na Recepção, ao
olhar o caminho que as pessoas seguiram.

**3. O caminho comum.** Nada a fazer. Se quiser conferir, escreva ao número da empresa uma frase de
fornecedor (*"represento uma empresa de embalagens, posso apresentar nossos preços?"*) e veja se a
proposta que volta é **Fornecedores**, e não Comercial.

**4. O que significa cada sinal.**

| O que você vê | O que quer dizer |
|---|---|
| No menu principal, **"Comercial"** agora diz que é para **comprar** sementes | a descrição mudou para não capturar quem usa a palavra "cotação" querendo *vender* |
| No menu principal, **"Fornecedores"** agora diz **vender para a Renascer** | mesma razão, do outro lado |
| *"Não consigo abrir arquivo por aqui…"* na Recepção | alguém mandou PDF, áudio ou vídeo. Antes recebia a frase genérica, que não explicava por quê |
| *"Recebi, mas por aqui eu entendo texto e os botões"* | continua valendo para figurinha, localização e contato |
| **"IA errou"** no cartão da Recepção | a pessoa recusou a proposta da IA tocando "Ver todas as opções". Continua sendo o sinal para olhar |

**5. O que a tela NÃO faz.**
- **Não encaminha o arquivo a ninguém.** Nenhum PDF chega a uma pessoa pelo sistema.
- **Não deixa editar as descrições por tela** — elas mudam por migração, como hoje.
- **Não garante que a IA acerte:** ela propõe e a pessoa confirma com um botão. O que mudou é o que
  ela sabe ao propor.
- **Não muda o menu de ninguém que toca nos botões** — quem não escreve texto não vê diferença
  alguma, além das duas descrições do menu principal.

**O que o manual de hoje passa a dizer errado:** nada fica falso. A tabela de sinais ganha as três
linhas acima; a seção *A retomada pela OlivIA* e a do *menu da casa* continuam exatas.

## Próximo passo

`/writing-plans`.
