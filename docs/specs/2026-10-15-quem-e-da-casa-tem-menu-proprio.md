# Quem é da casa tem menu próprio
**Data:** 2026-10-15
**Chamado:** #1031
**Status:** APROVADO

## Contexto

Hoje, às 13:52, o **Benedito** escreveu "Boa Tarde" no número da Renascer e recebeu o **menu da
OlivIA** — o menu de cliente. O sistema sabia quem ele era: a conversa 36 foi gravada com
`erp_codigo 7687`, `BENEDITO VASKEVICZ`, `erp_papeis {equipe,cliente}`. Não foi falha de
reconhecimento.

**São três camadas que já existem, e nenhuma delas estava errada:**

1. **O cadastro de internos existe, em duas camadas.** `agenda.reconhecer` acha o número na agenda
   do ERP (lida todo dia às 06:00) e devolve os papéis; e `campo.quem_e` completa com os **destinos
   ativos da tela Destinos** — que é literalmente *"os números que já orientamos os clientes a
   chamar"* — como `equipe` sem código, decisão do dono de 14/10/2026 ("por hora").
2. **A interação diferente também existe, e é a Decisão 13:** *"colaborador e representante só
   recebem o menu se pedirem"*. Está implementada em `campo.texto_de_interno`.
3. **O que furou foi `PEDE_MENU`** (`campo.py:73`), que trata `"oi"`, `"olá"`, `"bom dia"`, `"boa
   tarde"` e `"boa noite"` como *pedido de menu*. O Benedito escreveu "Boa Tarde", o
   `texto_de_interno` leu como pedido, devolveu `False`, e o fluxo de cliente rodou. Para um
   cliente, saudação → menu é o certo: é o acolhimento. Para quem é da casa, é um cumprimento sendo
   lido como "quero o menu de cliente".

**E há um absurdo medido que fecha o argumento: o Benedito percorreu o menu de cliente e recebeu o
cartão de contato DELE MESMO, três vezes** (ele é o destino de Fretes). Seis dos sete caminhos de
interno terminaram num colega — o que a equipe quer do número é falar com alguém da casa, e o
caminho que existe para isso é o do cliente.

**Uma quarta coisa, e é a que o dono mandou separar:** ser interno hoje depende de `campo.ligado`,
a chave do canal de fotos do marketing. `campo.e_interno` é literalmente `ligado(con) and
quem_e(...) is not None`. Desligar o canal de fotos devolve a equipe inteira ao menu de cliente —
duas coisas distintas presas na mesma chave.

## Os fios que encostam

**Quem mais escreve o que esta mudança escreve.** A etapa grava linhas novas em
`atendimento.menu` (a segunda raiz e as duas opções, por migração) e uma linha em
`atendimento.ajustes` (a chave nova). Medido por `grep`, quem mais escreve essas duas:

| Tabela | Quem escreve hoje |
|---|---|
| `atendimento.menu` | as **migrações**, e **um** ponto de código: `rotas_telas.py:255`, o `UPDATE menu SET destino_id` da tela Destinos (a "ligação" de uma opção a uma pessoa) |
| `atendimento.ajustes` | as migrações e os endpoints de ajuste da tela Destinos (horário, avisado no não, canal de campo) |

**Quem lê `menu` para decidir, e o fio que quase passou.** Cinco leitores:

| Quem lê | A partir de onde | O que acontece com uma segunda raiz |
|---|---|---|
| `motor.mostrar_menu` | `_no(con, "raiz")` | não vê a nova (busca pela chave) |
| `motor._no` | exclui `chave <> 'raiz'` | **precisa excluir a nova também**, senão ela é alcançável por chave |
| `rotas_telas.py:81` e `:87` (o `motivo` e o filtro da Recepção) | `chave = 'raiz'` | não vê a nova — e é o certo: opção interna não é motivo de cliente |
| `rotas_telas.py:210` (a árvore da tela Destinos) | `chave = 'raiz'` | **não vê a nova** — a árvore interna fica invisível e não administrável na tela. Está em *Escopo — FORA*, dito |
| **`motor.folhas_e_menus`** | **`WHERE pai_id IS NULL`** | **VÊ A NOVA.** É a lista contra a qual a **IA classifica o texto do cliente** |

**Esse último é o fio que importa, e ele vira passo do plano.** `folhas_e_menus` não filtra por chave
de raiz: filtra por `pai_id IS NULL`. Sem mexer nele, um **cliente** escrevendo texto livre poderia
receber a proposta de uma opção **interna** ("Entendi que você quer: Mandar foto do campo. É
isso?"). Não é hipótese remota: é o caminho de todo mundo que escreve em vez de tocar, e a IA é
oferecida a toda conversa.

**Quem volta depois: a leitura da agenda, todo dia às 06:00.** `agenda.atualizar` **apaga e reescreve
a agenda inteira** numa transação, a partir do ERP. Consequência aceita: quem o ERP deixar de
reconhecer deixa de ser interno no dia seguinte, sem aviso — e quem for cadastrado passa a ser, como
aconteceu com o próprio Benedito entre 14 e 15/10. O complemento pelos destinos ativos é o que
segura os três que o ERP não conhece. Nada mais revisita o dado.

## O universo medido

Medido em 15/10/2026 no banco de produção, como `axiaatende_ro`:

| Pressuposto | Contagem de hoje |
|---|---|
| nós no menu · raízes · folhas de destino · inativos | **30 · 1 · 21 · 0** |
| verbos (`acao`) que a tabela conhece | **3**: `destino` (21), `menu` (8), `encerrar` (1) |
| destinos ativos | **6** |
| destinos que o ERP reconhece | **3** — Maicon (`equipe`), Benedito (`equipe`), Djeison (`representante`) |
| destinos que entram só pelo complemento de 14/10 | **3** — Willian, Fran, Alisson |
| números de interno que já chamaram | **3** — Maicon (13 conversas), Benedito (6), Alisson (1) |
| conversas de interno | **20** |
| …abertas por saudação que o `PEDE_MENU` lê como pedido de menu | **15** — "oi" 10, "olá" 3, "boa tarde" 2 |
| …abertas sem texto (foto, documento) | 4 · uma por resposta automática |
| caminhos de interno que terminaram num colega | **6 de 7** |
| **…em que a pessoa recebeu o próprio cartão** | **3** — todas do Benedito, em Fretes |
| frases anotadas pelo caminho de interno da Decisão 13 | **1**, do Maicon ("Foto da safra 2025") |
| peças do canal de campo | **24**, todas de `equipe`, **todas catalogadas** |
| `campo.ligado` | **true** |

**Três leituras que decidiram o desenho:**

1. **A saudação é o caso dominante, não a exceção:** 15 de 20. Qualquer desenho que não a trate não
   trata o problema.
2. **O caminho de interno que existe é pouco usado (1 frase) e o canal de campo é muito usado (24
   peças).** Ou seja: a equipe usa o número para mandar foto, e descobre isso mandando a foto — não
   há porta de entrada. É a primeira opção do menu interno.
3. **O menu interno não precisa de "falar com um colega" como opção própria** (escolha do dono): 6
   de 7 caminhos iam para colega, mas por dentro do menu de cliente, que continua alcançável pela
   segunda opção. **Consequência: a guarda do próprio cartão fica MAIS necessária, não menos** — o
   caminho que produziu os três absurdos continua existindo, uma escolha mais fundo.

## Conformidade com o Manual legal

Não se aplica: a etapa não toca imposto, código fiscal, régua, texto legal em documento nem SPED.

## Conformidade com a casa

**Gatilho tocado: um — "agente ou chamada a modelo de IA" (R7).** A etapa muda **o que a IA pode
propor** (`folhas_e_menus`, a lista que ela classifica). Os outros cinco não são tocados: nenhum
segredo (R3), nenhum serviço, porta, tarefa ou exposição de rede (R4/R1 — a mudança roda dentro do
`axiaatende-recepcionista`, que já existe), nenhum dado que o backup já não cubra (R2 — as linhas vão
para `menu` e `ajustes`, no banco já coberto por `rotina:backup-axiaatende-banco`), nenhum processo
que hospede sessão de agente (R9), nenhum projeto novo (R8).

- **R7: conforme.** Trecho lido: *"O que NÃO cobre: o **harness** de cada agente. O que um agente
  pode fazer sozinho é decisão do código que o envolve (`montar_tools()` no SuporteAxia, a camada de
  agentes no AxiaGestão), e a barreira mora lá, com quem a constrói. Esta responsabilidade é sobre
  governança: quem existe, o que pode, quem desliga, quem é avisado."* É exatamente o caso: esta
  etapa **estreita** o harness da IA do atendimento — ela passa a não poder propor opção interna a
  cliente —, e a carta diz que essa barreira mora no código. Nada muda no inventário de agentes, na
  política de uso de IA, no desligamento ou na lista de notificação: nenhum agente novo, nenhuma
  chamada nova a modelo, nenhum dado novo indo a modelo.
- Lido também o `politica-uso-ia.md`: o item "Pode sozinho" sobre o AxiaAtende trata da **leitura**
  das conversas pela sessão (#981) e não da classificação da OlivIA. Não é alterado.

Li o `PROJETO.md` do AxiaAtende (o projeto da etapa) e o do AxiaMarketing, que é o vizinho que
encosta: o canal de campo entrega material à Caixa do marketing, e esta etapa **não muda** o que
entrega nem como — só acrescenta uma porta de entrada explicada no menu.

## Decisão

**Três decisões do dono em 15/10/2026, e uma minha de desenho.**

**1. Quem é da casa recebe um MENU PRÓPRIO, com duas opções** (e não uma linha curta, nem silêncio):

- **Mandar foto ou vídeo do campo** — explica em uma linha o que a equipe já faz 24 vezes sem saber
  que podia. Verbo novo `texto`: o nó diz sua linha e **para**, sem avançar nó nenhum.
- **Ver o menu do cliente** — a saída para quem quer o que o cliente vê, e o caminho pelo qual falar
  com um colega continua existindo. Verbo novo `menu_cliente`: mostra a raiz do cliente.

O menu interno é **cadastro, não código**: uma segunda raiz em `atendimento.menu`, por migração, no
mesmo padrão do menu de cliente — *"modelo novo é linha nova, não código"* é como esta casa trata o
que muda sem deploy.

**2. "Interno" deixa de depender do canal de fotos.** O reconhecimento sai de `campo.quem_e` para
`backend/internos.py`, com chave própria (`interno.ligado` em `ajustes`). `campo.quem_e` passa a
delegar — **uma verdade só, em um lugar só**. Desligar o canal de campo volta a desligar apenas as
fotos.

**A chave nasce LIGADA, e isso é deliberado:** é o comportamento que o dono pediu, e a chave existe
como **alavanca de rollback**, não como porta de entrada. Virá-la é um `UPDATE` numa linha de
`ajustes`, **sem restart e sem deploy** — reversibilidade melhor que um `git revert`.

**3. Os três destinos que o ERP não conhece continuam entrando pelo complemento** (Willian, Fran,
Alisson). O ERP decide primeiro; o destino ativo só completa. O caminho definitivo — cadastrar o
número como contato do colaborador e remover o complemento — fica escrito e **não** é desta etapa.

**4. (desenho) Ninguém recebe o próprio cartão de contato.** Quando quem escolhe uma folha de
`destino` é a própria pessoa daquele destino, o cartão não sai: sai uma linha dizendo que aquele
atendimento é ela mesma. Três ocorrências medidas, todas do Benedito. Não foi pedido; é consertar o
que a medição mostrou enquanto o código é aberto, e está aqui para ser recusado se o dono quiser.

## Escopo desta etapa

**DENTRO**

1. `backend/internos.py` (novo) — `quem_e(con, wa_id)` (agenda do ERP primeiro, destino ativo como
   complemento) e `ligado(con)` lendo `interno.ligado`. É a mudança de `campo.quem_e` para cá, sem
   alterar a regra.
2. `backend/campo.py` — `quem_e` e `e_interno` passam a **delegar** a `internos`; a função não é
   duplicada. `e_interno` continua exigindo `campo.ligado` (o canal de fotos é dele), mas quem é
   interno deixa de depender disso.
3. `backend/migracoes/018_menu_interno.sql` (+ `_VOLTA`) — a raiz `raiz-interna`, as duas opções e a
   linha `interno.ligado` em `ajustes`.
4. `backend/motor.py` — quatro pontos: a saudação de interno leva o **menu interno**; os verbos
   `texto` e `menu_cliente`; `_no` passa a excluir a raiz interna junto com a do cliente; e a guarda
   do próprio cartão.
5. **`backend/motor.py` — `folhas_e_menus` passa a ser do cliente**, por chave de raiz e não por
   `pai_id IS NULL`. É o fio da Fase 2b: sem isto, a IA propõe opção interna a cliente.
6. `tests/test_motor.py` e `tests/test_campo.py` — inclusive o teste que **prova que a IA não
   alcança a árvore interna**, e o que prova que a Decisão 13 (o texto de interno vira frase do
   campo) continua valendo.
7. `docs/manuais/recepcao.md` e `docs/manuais/campo-equipe.md` — a seção nova, e o que mudou para a
   equipe.

**FORA**

- **A árvore interna na tela Destinos.** A tela lê a partir de `chave = 'raiz'` e não enxerga a
  segunda raiz: o menu interno **não será administrável pela tela** nesta etapa. Mudar isso é mexer
  na tela que o dono acabou de aprovar para outra coisa, e o menu interno tem duas opções fixas que
  não mudam por operação. Fica escrito como lacuna conhecida.
- **"Falar com um colega" como opção própria do menu interno** — recusado pelo dono; o caminho
  continua pelo menu do cliente.
- **Abrir chamado no suporte pelo WhatsApp** — recusado pelo dono nesta etapa.
- **Cadastrar Willian, Fran e Alisson no ERP e remover o complemento** — decisão 3; chamado próprio
  quando for a hora.
- **Mudar `PEDE_MENU`** para clientes. A lista continua idêntica para quem é de fora: saudação de
  cliente é acolhimento, e isso está certo.
- **O canal de campo em si** — nenhuma mudança no que ele faz com a foto, na Caixa do marketing nem
  nos avisos de catálogo.
- **A agenda e a leitura das 06:00** — nada muda em como o ERP é lido.

## Impacto em produção

- **Serviço `axiaatende-recepcionista`** (`127.0.0.1:8008`): a migração roda ao subir
  (`migracoes.aplicar` no start) e então `Restart-Service axiaatende-recepcionista`, em janela
  elevada. Durante os segundos de queda a Meta **retém e repete** os avisos por até 7 dias.
- **O `axiaatende-backend` (8009, as telas) também lê o banco** e aplica migração ao subir: reiniciar
  os **dois**, pela mesma razão de sempre (o processo das telas não pode ficar com schema antigo).
- **Banco:** migração **018**, que acrescenta linhas (não altera coluna, não apaga nada). `_VOLTA`
  ao lado apaga exatamente as linhas que ela criou.
- **Janela:** qualquer hora. O efeito para cliente é **nenhum**: quem não é interno segue idêntico.
- **Efeito imediato esperado:** o próximo "oi" do Benedito traz o menu interno.

## ROLLBACK_PLAN

**Rollback de operação, primeiro — é o mais rápido e não precisa de ninguém no teclado do git:**

1. `UPDATE atendimento.ajustes SET valor = 'false' WHERE chave = 'interno.ligado';`
2. Nada mais. Em até uma mensagem, todo mundo volta a ser tratado como hoje: saudação de interno
   leva o menu de cliente. **Sem restart, sem deploy.** As linhas do menu interno ficam no banco,
   inalcançáveis.

**Rollback de código, se for o caso:**

3. `git revert <commit>`.
4. Rodar o `_VOLTA` **à mão**, numa janela elevada — **não existe verbo `voltar` no módulo de
   migrações**, e isso é regra escrita dele: *"o `_VOLTA.sql` nunca é aplicado sozinho; ele existe
   para a mão de quem desfaz"*. O arquivo abre o próprio `BEGIN/COMMIT` e apaga a linha de
   `casa.mudancas`, então ele é autossuficiente:
   `psql -f backend\migracoes\018_menu_interno_VOLTA.sql`, com a credencial de escrita do
   `.env.secrets`.
5. `Restart-Service axiaatende-recepcionista` e `Restart-Service axiaatende-backend`, em janela
   elevada.
6. Conferir: um "oi" de interno volta a trazer o menu de cliente, e
   `SELECT count(*) FROM atendimento.menu WHERE pai_id IS NULL` volta a **1**.

**A ordem dos passos 3 e 4 importa, e é esta:** reverter o código **antes** de desfazer a migração.
Ao contrário, o serviço fica alguns segundos com o código novo buscando uma raiz interna que já não
existe — e `_no(con, "raiz-interna")` devolveria `None` no meio de um atendimento. Como o passo 1
(a chave) já neutraliza o comportamento sem tocar em nada, **o caminho normal é parar no passo 2**;
os passos 3 a 6 são para quando se quer o banco limpo também.

**O que NÃO se desfaz, e é de propósito:** as 24 peças de campo, as frases anotadas e as conversas
já gravadas ficam. A etapa não reescreve histórico.

## Manual de uso

**1. Para que serve.** Quem é da equipe ou representante da Renascer deixa de ser atendido como
cliente ao escrever no número da empresa. Em vez do menu de cliente, recebe um menu curto da casa —
e o menu de cliente continua a uma escolha de distância, para quando for isso que você quer.

**2. Quem usa e quando.** Qualquer pessoa da equipe ou representante, ao escrever no 49 3664 0121 —
em geral para mandar foto do campo, ou para pegar o contato de um colega.

**3. O caminho comum.**
1. Escreva qualquer coisa no número da empresa ("oi", "bom dia").
2. Chega o **menu da casa**, com duas opções.
3. **Mandar foto ou vídeo do campo** explica o que fazer: é só mandar a foto ali mesmo, e a OlivIA
   pergunta o que faltar para catalogar.
4. **Ver o menu do cliente** mostra exatamente o que um cliente vê — inclusive o caminho para falar
   com um colega (Fretes, Qualidade, Comercial).
5. Quer só anotar uma frase para a próxima foto? Escreva a frase, sem pedir menu: ela fica guardada
   e vai com a foto seguinte. Isso já funcionava e continua igual.

**4. O que significa cada sinal.**

| O que você vê | O que quer dizer |
|---|---|
| O **menu da casa** (duas opções) depois de um "oi" | o sistema te reconheceu como da equipe, pelo cadastro do ERP ou por você ser um dos contatos da tela Destinos |
| O **menu do cliente** depois de um "oi" | você **não** foi reconhecido. Ou o seu número não está no cadastro do ERP e não é um destino ativo, ou o reconhecimento está desligado. Não é erro do seu lado |
| *"Anotado. Se for para falar com alguém da empresa, me escreva menu"* | você escreveu uma frase e ela foi guardada para a próxima foto. É o comportamento de sempre |
| *"esse atendimento é você mesmo"* no lugar de um cartão de contato | você escolheu um caminho que leva ao seu próprio WhatsApp. Antes o sistema mandava o seu próprio cartão |
| Na Recepção, o seu nome com a etiqueta azul **Equipe** | é o mesmo reconhecimento. A etiqueta já existia; o que mudou é que agora ela muda o atendimento, e não só o registro |

**5. O que a tela NÃO faz.**
- **Não troca o seu atendimento de cliente:** se você também é cliente da Renascer (como o Benedito,
  que é `equipe` e `cliente`), o menu da casa vem primeiro — e o do cliente está na segunda opção.
- **Não manda a foto por você:** o menu explica; mandar é mandar a foto.
- **Não abre chamado no suporte** pelo WhatsApp.
- **Não deixa editar o menu da casa pela tela Destinos** — ele tem duas opções fixas. A tela
  continua administrando o menu do cliente.
- **Não reconhece quem não está em lugar nenhum:** número que não está no cadastro do ERP nem é um
  destino ativo é tratado como cliente, e está certo.

**O que o manual de hoje passa a dizer errado, e muda no mesmo plano:**
- `docs/manuais/recepcao.md`, seção 1: *"Isso só registra: o que a pessoa recebe no WhatsApp é o
  mesmo para todos."* **Deixa de ser verdade** — é a frase central que esta etapa derruba.
- `docs/manuais/campo-equipe.md`: descreve mandar a foto direto, sem mencionar que agora existe um
  menu da casa que explica isso.

## Próximo passo

`/writing-plans`.
