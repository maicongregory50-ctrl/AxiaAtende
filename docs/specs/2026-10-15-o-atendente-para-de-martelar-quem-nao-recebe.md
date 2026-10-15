# O atendente para de martelar quem não recebe
**Data:** 2026-10-15
**Chamado:** #1028
**Status:** APROVADO

## Contexto

Em 15/10/2026, entre 11:34 e 13:14, o atendente da Renascer e um robô do outro lado entraram em
vaivém. O número `5511933157031` manda mensagens de tipo `unsupported` e a frase *"Desculpe, não
consegui entender!"*; nós respondemos "não entendo" a cada `unsupported` e **menu principal** a cada
frase de texto. **13 ciclos em 100 minutos**, e **7 dos nossos envios falharam com `131026 Message
undeliverable`**.

**Por que isso é grave, e não só feio:** a regra permanente 1 do projeto é *"nada que arrisque o
número na Meta"*, e mandar repetidamente para um destino que não recebe é exatamente o que degrada a
nota — que é o que libera o envio em degraus (regra 5). A nota estava **GREEN** na leitura de hoje às
00:01, ou seja **antes** do laço começar; a próxima leitura é meia-noite. Nenhuma mensagem paga foi
gasta: o laço anda dentro da janela de 24 h, então o custo é reputação, não dinheiro.

**A trava que já existe e não pega.** A decisão do dono de 14/10 (commit `23211a7`, sem chamado)
criou o silêncio para resposta automática com este motivo escrito no próprio código: *"a resposta
automatica, a qualquer hora em que mandamos algo nas ultimas 24h: SILENCIO, porque do outro lado e
uma maquina e responder arrisca o vaivem entre os dois robos"* (`backend/motor.py`). Ela não pega por
duas razões distintas:

1. **estrutural:** mensagem de tipo `unsupported` não tem texto nem toque, então cai no ramo de
   "não é texto nem botão" (`motor.py`, perto da linha 395), que responde `NAO_ENTENDO` e **retorna
   antes** de `depois_do_atendimento` ser chamado. A regra de silêncio nunca é consultada;
2. **de lista:** a frase do robô, *"Desculpe, não consegui entender!"*, não está em `AUTOMATICA`.

**E consertar pela frase está descartado pelo critério escrito da própria lista.** O comentário de
`AUTOMATICA` diz: *"so frases que gente pedindo algo nao escreve"*, e registra que `"assim que
possivel"` ficou de fora **de propósito** (*"preciso do boleto assim que possivel" seria
silenciado*). *"Não consegui entender"* é exatamente o que uma pessoa confusa escreve: pôr na lista
calaria gente confusa, que é o oposto do que este projeto combate. **O discriminador confiável não é
o texto — é o `131026`.**

## Os fios que encostam

**Quem mais escreve: ninguém, porque esta etapa não escreve nada.** Ela só **deixa de enviar**.
Nenhuma tabela, nenhuma coluna, nenhum `INSERT`, nenhum `UPDATE`, nenhuma migração.

**Quem lê o mesmo dado para decidir.** O dado lido é `atendimento.enviadas` (`para`, `tipo`, `erro`,
`resumo`, `enviada_em`). Essa tabela tem **três escritores**, medido por `grep`:

| Quem escreve em `enviadas` | O que grava |
|---|---|
| `motor._registrar` | tudo o que a OlivIA manda numa conversa (menu, botões, link, "não entendo") |
| `envio.py` (vários pontos) | o convite, as imagens, a cópia ao responsável, a confirmação de recusa |
| `campo.py` | o que a OlivIA responde no canal de campo (Recebi, as perguntas, Anotado) |

**Isso poderia envenenar a regra, e não envenena — por construção.** A guarda só olha linhas com
`tipo = 'lista'`, e `envio.py` grava `tipo` em `modelo`, `texto` e `imagem`. Um convite que falhe
`131026` para um cliente **não** cala o menu dele. O `campo.py` grava `lista` (`campo.py:171`), e
essa é a única interseção real: está escrita abaixo, em *Escopo — FORA*.

**Quem volta depois: a Meta, e isso muda o comportamento da regra.** O `erro` e o `status` de
`enviadas` **não** são escritos no envio: chegam depois, pelo aviso de status da Meta (é assim que o
`131026` foi gravado). Consequência aceita e dita por extenso: **a guarda só pega a partir da segunda
lista.** A primeira é enviada, falha, o aviso chega segundos depois, e só então aquele destino passa
a ser poupado. Não há como fazer melhor sem adivinhar — e adivinhar aqui erraria contra gente de
verdade.

Nada mais revisita o dado: nenhuma rotina recalcula, nenhum agendador volta, nenhum gatilho de
esteira é acordado.

## O universo medido

Medido em 15/10/2026 no banco de produção (`127.0.0.1:5436`), como `axiaatende_ro`, sobre
`atendimento.enviadas` inteira (169 envios desde 09/10):

| Pressuposto | Contagem de hoje |
|---|---|
| destinos que já deram `131026` em TODA a história | **1** — o robô, e mais ninguém |
| em que tipo de mensagem o `131026` acontece | **`lista`: 7 de 7 falharam** · **`texto`: 13 de 13 entregaram** |
| outros erros da Meta em 169 envios | 2× `131047 Re-engagement message`, 1 destino (um interno) |
| "não entendo" por conversa | **13** (o robô) · **1, 1, 1** (os três casos de gente real) |
| quem já mandou `unsupported` | **1 destino** — o robô. **Nenhuma pessoa, nunca** |
| quem já mandou `document` | 2 destinos (a Yasmin do #1027 e um interno), 1 cada |

**Duas leituras que decidiram o desenho:**

1. **O `131026` é propriedade do TIPO de mensagem, não do destino.** O robô recebe texto (13 de 13)
   e não recebe lista interativa (0 de 7). Por isso a regra cala **a lista** para aquele destino, e
   não o destino inteiro: calar tudo seria mais do que o medido autoriza.
2. **Um teto de 2 nunca teria tocado ninguém de verdade.** Os três casos reais levaram exatamente
   **um** "não entendo" cada. O teto é desenhado com folga de 100% sobre o pior caso real.

**A assinatura do robô é também a de um cliente com WhatsApp muito antigo** (lista falha, texto
chega). Isso está tratado em *Escopo — FORA*, com o motivo.

## Conformidade com o Manual legal

Não se aplica: a etapa não toca imposto, código fiscal, régua, texto legal em documento nem SPED.

## Conformidade com a casa

Não se aplica: nenhum dos seis gatilhos da Fase 1c é tocado. Conferido um por um, porque a ausência
da seção não quer dizer conforme:

- **Segredo (R3): não toca.** Nenhum segredo criado, movido ou com leitor novo.
- **Serviço, porta, tarefa, exposição de rede (R4 e R1): não toca.** A mudança é regra dentro do
  processo `axiaatende-recepcionista`, que já existe e já escuta em `127.0.0.1:8008` atrás do Funnel.
  Nenhum bind, porta, tarefa agendada ou regra de firewall muda. **Ela só REDUZ o que sai.**
- **Dado novo (R2): não cria.** A etapa não grava nada; a decisão sai de `enviadas`, que já existe e
  já está no backup do banco (`rotina:backup-axiaatende-banco`).
- **Agente ou modelo de IA (R7): não toca.** A IA não é consultada em nenhum dos dois caminhos — é
  justamente o ponto: a decisão vem do erro da Meta e de uma contagem, não de julgamento.
- **Processo que hospeda sessão de agente (R9): não toca.**
- **Projeto novo (R8): não.**

A regra que esta etapa serve é do próprio projeto, não da carta: a **regra permanente 1** do
`CLAUDE.md` do AxiaAtende (*"nada que arrisque o número na Meta"*).

## Decisão

**Caminho C, escolhido pelo dono em 15/10/2026**: duas regras, nenhuma delas baseada em texto.

**R1 — lista que a Meta recusou não é tentada de novo para aquele destino.** Antes de mandar o menu
como lista, se já existe em `enviadas` um envio de `tipo = 'lista'` para aquele destino com erro
`131026`, a lista **não sai**. O destino continua recebendo texto, que é o que ele comprovadamente
recebe.

**R2 — teto de 2 "não entendo" por destino em 24 h.** Depois de dois, o terceiro não sai.

**Por que o teto é por DESTINO e não por conversa**, embora eu tenha dito "por conversa" ao
apresentar: o "não entendo" só é **registrado** quando há conversa aberta (`motor.py`, o
`_registrar` dentro do `if aberta`). Contar por conversa deixaria o caso sem conversa aberta sempre
em zero, e o teto nunca engataria justamente onde ele mais precisa engatar. Por destino em 24 h
cobre os dois casos com uma consulta só, e a medição mostra que é seguro (pior caso real: 1).

**O silêncio é VISÍVEL, e isso não é enfeite.** Este projeto combate o fracasso silencioso; uma
regra que para de responder sem deixar rastro é exatamente o que ele combate. Então cada supressão
escreve uma linha no log do recepcionista (padrão `print(..., flush=True)` da casa) e incrementa um
contador `calados` no `/saude`, ao lado de `chegadas` — que é por onde o painel do AxiaSecurity já
olha este serviço.

**O que eu disse e não vou fazer:** prometi "visível no log e **na Recepção**". A Recepção fica de
fora, e o motivo é concreto — um envio suprimido **não deixa linha em `enviadas`**, então mostrá-lo
na tela exigiria gravar um registro novo, o que puxa a responsabilidade R2 da carta para dentro de
um caso que aconteceu uma vez. O log e o `/saude` entregam a visibilidade sem criar dado.

## Escopo desta etapa

**DENTRO**

1. `backend/motor.py` — R1 em `perguntar()` (linha 128), que é o **único** ponto por onde o menu sai
   como lista (o menu principal passa por ele). A guarda consulta `enviadas` e, achando `131026` em
   `lista` para aquele destino, não envia e registra a linha de log.
2. `backend/motor.py` — R2 no ramo de "não é texto nem botão" (perto da linha 395), antes de mandar
   `NAO_ENTENDO`: conta os "não entendo" daquele destino nas últimas 24 h e, de 2 em diante, não
   envia e registra a linha de log.
3. `backend/recepcionista.py` — o contador `calados` no `/saude`, no molde de `chegadas` (linha 187),
   separando `lista_recusada` de `nao_entendo`.
4. `tests/test_motor.py` — a lista não sai depois do `131026` e o texto continua saindo; o terceiro
   "não entendo" não sai e o segundo sai; e **o caso de gente de verdade continua intacto** (um
   `unsupported` isolado recebe a linha curta como hoje).
5. `docs/manuais/recepcao.md` — a seção nova, no molde da *"A retomada pela OlivIA"* que já está
   lá: por que uma conversa pode ficar sem resposta, e que isso é decisão e não falha.

**FORA**

- **A lista do canal de campo** (`campo.py:171`). É a única outra chamada de `saida.lista` da casa,
  serve a equipe interna pelo cadastro, e nunca deu `131026`. Mexer nela sem caso é mexer no escuro.
- **O menu em texto para quem não recebe lista** (o Caminho B que o dono recusou). Quem tiver
  WhatsApp muito antigo tem a mesma assinatura do robô e passa a não receber a lista — mas **hoje
  ela já não chega a essa pessoa**; a diferença é só que paramos de martelar. Se um cliente real
  aparecer preso nisso, é chamado próprio, e o sinal a procurar é um destino com `131026` em `lista`
  **e** mensagens de texto entregues que não sejam "não entendo".
- **A lista `AUTOMATICA` e qualquer regra por texto** — descartado pelo critério escrito dela.
- **O `#1027`** (fornecedor lido como comercial; `document` vira "não entendo"): é o mesmo beco visto
  do lado de gente, e segue separado.
- **Mostrar a supressão na tela da Recepção**, pelo motivo da seção *Decisão*.

## Impacto em produção

- **Serviço `axiaatende-recepcionista`** (`127.0.0.1:8008`): `Restart-Service
  axiaatende-recepcionista`, em janela elevada. Segundos. Durante o restart a Meta **retém e repete**
  os avisos por até 7 dias, então nenhuma mensagem se perde (`PROJETO.md`, *Se eu cair*).
- **O `axiaatende-backend` (8009, as telas) não é tocado.**
- **Banco:** nenhuma migração, nenhum dado escrito.
- **Janela:** qualquer hora, e **quanto antes melhor** — a nota do número é lida à meia-noite.
- **Efeito imediato esperado:** o laço com `5511933157031` para de produzir `131026`. Ele já tem 7
  listas falhadas gravadas, então a R1 engata na primeira tentativa depois do restart.

## ROLLBACK_PLAN

1. `git revert <commit>` (ou `git checkout -- backend/motor.py backend/recepcionista.py tests/test_motor.py docs/manuais/recepcao.md`).
2. `Restart-Service axiaatende-recepcionista`, em janela elevada.
3. Conferir em `http://127.0.0.1:8008/saude` que o bloco `calados` desapareceu.

**Nada a desfazer no banco:** a etapa não escreve. **E o rollback parcial é por regra:** as duas são
independentes — dá para reverter só a R2 (o teto) mantendo a R1 (a lista), ou o contrário, porque
nenhuma depende da outra.

**O risco de reverter é conhecido:** volta-se ao estado em que um robô do outro lado produz envios
`131026` sem limite. Se a reversão for necessária e o laço estiver ativo, a contenção grosseira é
`ATENDE_RESPONDE=false` no `.env.recepcionista` — que cala o atendimento **todo**.

## Manual de uso

**1. Para que serve.** Explica por que uma conversa na Recepção pode aparecer **sem resposta nossa**.
Em dois casos o atendente passa a ficar calado de propósito, e saber disso evita procurar defeito
onde há decisão.

**2. Quem usa e quando.** Quem olha a Recepção e estranha uma conversa em que a OlivIA parou de
responder.

**3. O caminho comum.** Nada a fazer: as duas regras são automáticas. Se você quiser conferir se
alguma entrou em ação, o número aparece no `/saude` do recepcionista, no bloco `calados`.

**4. O que significa cada sinal.**

| O que você vê | O que quer dizer |
|---|---|
| Uma conversa que **recebeu o menu uma vez e nunca mais** | o WhatsApp daquele número **recusou** o menu (a Meta respondeu "não entregável"). Em vez de insistir, paramos de mandar o menu para ele. Quase sempre é um robô do outro lado; pode ser alguém com WhatsApp muito antigo |
| Uma conversa com **duas respostas "Recebi, mas por aqui eu entendo texto e os botões" e nada depois** | a pessoa (ou o robô) mandou um terceiro conteúdo que não dá para ler — figurinha, enquete, documento. Depois de avisar duas vezes, o atendente para: avisar uma terceira vez não ajudaria ninguém |
| `calados` no `/saude` com número **maior que zero** | alguma das duas regras agiu desde que o serviço subiu. Não é erro |
| `calados` **em zero** | nenhuma agiu — ou ninguém esbarrou nelas, ou o serviço acabou de subir. **Zero não quer dizer que a regra está desligada** |

**5. O que a tela NÃO faz.**
- **Não avisa ninguém** quando cala. Não há alerta: é comportamento normal, e o rastro é o log.
- **Não mostra na Recepção qual conversa foi calada** — uma mensagem que não foi enviada não deixa
  linha. Quem precisa saber lê o log do recepcionista.
- **Não desfaz:** o destino que recusou a lista não volta a recebê-la sozinho. Se um dia precisar,
  é mudança de código, não botão.
- **Não cala texto:** quem recusa a lista continua recebendo nossas mensagens de texto.

**O que o manual de hoje passa a dizer errado:** nada. É seção nova, no molde da *"A retomada pela
OlivIA"*; nenhuma frase existente fica falsa.

## Próximo passo

`/writing-plans`.
