# A OlivIA atende o cliente da carteira na conversa do boletim
**Data:** 2026-11-24
**Chamado:** #1754
**Status:** APROVADO

## Contexto

O Boletim de safra nº 1 (CAM-0009, 28/10/2026) foi lido e quase não virou conversa: no público
comprador, 84 viram, 4 responderam por texto, 1 tocou em "Falar com meu atendimento". O dono quer que
o nº 2 seja uma chamada com convite, e que quem aceitar seja atendido pela OlivIA: ela chama pelo
nome, entrega a versão maior do boletim, explica a parceria (oferta curta, prioridade da carteira) e
avisa o representante de quem mostrou interesse (23/11/2026).

Hoje isso não acontece, por duas decisões anteriores:

- **O cliente da carteira não fala com a OlivIA** (#1189, 28/10). Quem recebeu um envio nos últimos 30
  dias e escreve recebe a linha do representante e o menu `raiz_carteira` (`motor.portao_do_cliente`).
  `olivia.e_de_fora` devolve `False` para ele (`olivia.py:435-436`) e `olivia.atender` recusa a
  conversa em `raiz_carteira` (`olivia.py:975-979`).
- **O toque no botão do envio nunca chega a ela** (#1203). O id `envio:<id>:falar` sai de
  `motor.tratar` no degrau do prefixo `envio:` (`motor.py:702-705`), e `Envio._falar_pelo_toque`
  responde com a linha do representante, sem abrir conversa.

E o cerco dela (D2 do #1520) é não saber nada de cliente: a regra 4 da instrução diz isso, e a base
da empresa proíbe afirmar nome de cliente.

A política de uso de IA da casa registra o momento: *"o resto é decisão do dono quando o AxiaAtende
atender cliente direto"*. Este chamado é essa decisão.

## Os fios que encostam

**O que a etapa escreve, e quem mais escreve aí** (lido no código em 24/11/2026):

- `atendimento.envio_destinatarios.resposta`, `resposta_texto`, `resposta_em` — escritores hoje:
  `Envio.tratar_toque` (quero, nao_quero), `_falar_pelo_toque` (falar), `tratar_texto_de_convidado`
  (texto, só na janela de 24 h e só com resposta nula), `_na_janela`. A etapa acrescenta um escritor:
  o toque novo. **Quem lê para decidir:** `tratar_toque` (ignora segundo toque depois de quero ou
  nao_quero), `eventos_erp.montar` (o que vai ao Relacionamento do ERP, a cada 15 min, 60 dias), a
  tela Envios, `GET /pedido/mensagens` e o `O_Que_Rendeu.csv` do AxiaMarketing.
- `atendimento.modelos` — a migração registra o modelo novo e alarga o CHECK `modelos_botao` (já
  alargado nas migrações 005, 025, 039, 043 e 044: cada uma repete a lista inteira).
- `atendimento.envios` — coluna nova com a lista de culturas do boletim; escritor: `receber_pedido`.
- `atendimento.conversas` — a OlivIA já abre e marca `conduzida_por = 'olivia'`; a etapa abre a
  conversa do cliente da carteira por um caminho novo. Quem lê: `portao_do_cliente` (não age com
  conversa aberta), `olivia.atender`, a tela Recepção, o vigia `fechar_dia`.
- Tabela **nova** de interesses, com um escritor (a ferramenta nova) e a ficha saindo pelo código.
- `atendimento.enviadas` — todo envio grava aqui; `_portao_hoje` conta os resumos que começam por
  `portao do cliente`. Os resumos novos não podem começar assim.

**Quem volta depois:**

- `eventos_erp.empurrar` (telas, 15 min): manda o estado de cada destinatário ao ERP, que "decide o
  estado e só o deixa avançar". **Não se sabe se o ERP aceita um valor novo em `resposta`** — é
  medição do plano. Por isso o valor novo é traduzido na saída para um que o ERP já conhece.
- O vigia `olivia.fechar_dia` (23:40) marca cada conversa dela como `bem` ou `sem_saida`.
- A retomada da conversa (`motor.py:1224`) conhece a `raiz_carteira`; a conversa nova tem de ser
  retomável do mesmo jeito.
- `PROJETO.md` do AxiaAtende (*Ofereço*: o estado da Meta por wamid; *Exijo*: o pedido do Marketing
  com o responsável de cada cliente). O campo novo do pedido é opcional: o Marketing de hoje continua
  valendo, e passa a mandá-lo pelo #1755.

## O universo medido

Produção, 24/11/2026, papel `axiaatende_ro`:

| Pressuposto | Medição |
|---|---|
| Números que o portão alcança hoje (envio em 30 dias) | 101 |
| Clientes que já receberam envio direto | 91 números; 90 de papel `comprador`, 1 sem papel (canal `dono`) |
| Contatos técnicos que já receberam envio direto | **0** |
| Um número em mais de um cadastro | 0 de 91 |
| Destinatários sem WhatsApp do responsável | 0 |
| Responsáveis distintos | **2** |
| Reação ao Boletim nº 1 (comprador) | 4 por texto, 1 por toque, 2 pediram para parar |
| Modelos de direta ativos | 4; nenhum com botão de convite |
| Chaves | `portao.ligado`, `olivia.conduz_venda` e `olivia.qualifica_produtor` ligadas |

Leituras: o contato técnico é público novo (estreia pelo #1755); a ficha de interesse chega a duas
pessoas, no ritmo dos lotes (até 20 clientes por dia); e a entrada só pelo botão perderia quatro de
cada cinco que reagiram.

**Não medido, e é passo do plano:** o que o ERP faz com um valor de `resposta` que não conhece; e se
o modelo `olivia_resumo` está aprovado na Meta.

## Conformidade com o Manual legal

não se aplica: atendimento e registro de interesse comercial, sem regra tributária. A pergunta de lei
sobre avisar clientes de que há um operador de IA no exterior continua **em aberto** na política da
casa (#1584); a decisão do dono abaixo (D8) é sobre o que a OlivIA diz na conversa, e não a responde.

## Conformidade com a casa

- **R7 — muda.** Trecho lido: *"a política nomeia o provedor como parte... e classifica o dado em
  cinco classes; cada uso de IA de `design\agentes.json` diz o provedor e a classe mais alta"*; e na
  política: *"Dado pessoal... Sim, pelo mínimo necessário e com a finalidade escrita. Cada fluxo novo
  entra nesta página antes de ligar."* A política hoje diz que a OlivIA fala com quem "não é da casa
  nem cliente da carteira" e que não tem ferramenta "que toque dado de cliente". As duas frases
  deixam de ser verdade. **Passo do plano:** `C:\AxiaSecurity\docs\governanca\politica-uso-ia.md`
  ganha a linha deste fluxo em "Pode sozinho" (o que vai ao modelo, a finalidade, a chave), a ficha
  da OlivIA no inventário é atualizada, e `design\agentes.json` é conferido (a classe continua 3; o
  provedor continua a API comercial da Anthropic). **Antes de a chave ligar.**
- **R2 — conforme.** Trecho lido: `rotina:backup-axiaatende-banco` e `-nuvem`. A tabela nova nasce no
  banco do AxiaAtende, já coberto.
- **R4 — conforme.** Nenhuma porta, serviço ou saída nova: o recepcionista já fala com a Meta e com a
  Anthropic.
- **R3 — não se aplica:** nenhum segredo novo; a chave da Anthropic é a mesma.

## Decisão

Caminho A (dono, 24/11/2026): o degrau inteiro numa etapa, atrás de chave própria.

- **D1. A entrada.** A OlivIA atende o cliente da carteira **(a)** pelo toque no botão "Quero saber
  mais" de um boletim, e **(b)** pelo texto de quem recebeu um boletim com esse botão nos **7 dias**
  seguintes. Fora disso, o portão de hoje. Vale para contato comprador e técnico, do mesmo jeito.
- **D2. O botão.** Modelo novo de direta com dois botões de resposta rápida: "Quero saber mais"
  (`envio:<id>:saber`) e "Não quero receber" (a recusa de sempre). Sem "Falar com meu atendimento":
  quem quer a pessoa pede na conversa. O texto do botão é do dono; propor o modelo à Meta é ato dele.
- **D3. O toque é do código.** Ao toque: a saudação pelo primeiro nome, as imagens da versão maior
  (as `imagens` do pedido, pelo molde de `_mandar_imagens`) e o **texto da parceria, literal**, do
  arquivo aprovado pelo dono. Nenhuma fala de IA nesse primeiro bloco. A conversa abre conduzida pela
  OlivIA, e ela fala a partir da resposta do cliente. Quem entrou por texto (D1b) é recebido por ela,
  que oferece a versão maior; as imagens saem por ferramenta, pelo código.
- **D4. O que ela sabe.** O primeiro nome, o nome do cadastro, o papel (comprador ou técnico), o nome
  de quem atende o cliente, a lista de culturas do boletim e o texto da parceria. **Não** sabe
  faturamento, faixa, histórico de compra, cidade, telefone nem nada do ERP. O dado vem da linha do
  envio; ela não tem ferramenta de busca.
- **D5. O que ela faz**, com lista de ferramentas própria deste modo (as de vaga, venda e lead não
  são oferecidas): mandar a versão maior; anotar o interesse, numa **lista fechada** com as culturas
  do boletim; passar o contato do representante do cliente; oferecer as opções da `raiz_carteira`
  (boleto, carga, qualidade, falar com a empresa); encerrar.
- **D6. O que ela não faz.** Não fala de quantidade, preço nem prazo: diz que isso é com o
  representante. Não promete estoque: o texto da parceria fala de esforço, com limite. O filtro de
  saída continua valendo para toda fala dela.
- **D7. A ficha é do código.** Uma ficha por cliente, na hora, ao WhatsApp do responsável da linha do
  envio: o cliente, o papel de quem falou, as culturas, e o que ele escreveu, literal. Texto dentro
  da janela de 24 h do responsável; fora dela, o modelo `olivia_resumo`. A fala que diz que o
  representante foi avisado, sem a ficha ter saído, é trocada (o molde de `aviso_sem_ficha`).
- **D8. IA.** Ela não avisa por conta própria que é uma IA; apresenta-se pelo nome. **Perguntada, não
  nega.**
- **D9. O registro no ERP.** O interesse viaja por `eventos_erp` e aparece no Relacionamento do
  cliente como a resposta dele ao boletim ("Quis saber mais. Interesse: aveia preta, nabo
  forrageiro"). Sem mudança no ERP: na saída, o valor novo é traduzido para um que ele já aceita.
- **D10. A lista de culturas vem no pedido.** `POST /pedido/envio` ganha um campo opcional com os
  rótulos das culturas do boletim. Sem ele, a ferramenta de anotar interesse não é oferecida, e ela
  só passa o representante.
- **D11. A chave.** `olivia.atende_carteira`, ajuste no banco, nasce `false`, liga e desliga por
  `scripts\olivia.py` sem restart e aparece no `/saude`. Desligada: o toque "saber" responde com a
  linha do representante (como o "falar" de hoje) e o texto cai no portão.
- **D12. O vigia.** `fechar_dia` passa a contar as conversas da carteira, os interesses e as fichas
  com erro, no resumo que o dono já recebe.

## Escopo desta etapa

**DENTRO:** D1 a D12; a migração com `_VOLTA`; o arquivo do texto da parceria (rascunho da sessão,
aprovação do dono); os testes; o manual; a política de IA e o inventário de agentes (AxiaSecurity).

**FORA:**
- o estado "interessado" no ERP, filtrável e somável por cultura (chamado próprio, ligado ao #1753);
- a OlivIA atender todo cliente da carteira, fora do boletim (caminho C da primeira pergunta);
- o AxiaMarketing mandar o campo das culturas e o contato técnico receber envio direto (#1755);
- a peça em si: a chamada, a versão maior e a leitura de cenário (#1755);
- ela conhecer faixa, histórico ou pedido do cliente (degrau seguinte, com spec própria).

## Impacto em produção

- **Serviços:** `axiaatende-recepcionista` e `axiaatende-backend` reiniciam uma vez (a migração roda
  no arranque). Com a chave desligada, nada muda para ninguém.
- **Dados:** uma migração (tabela de interesses, coluna em `envios`, o modelo novo, o CHECK do botão,
  a chave). Nenhum dado existente muda.
- **Meta:** um modelo novo de categoria Marketing, proposto pelo dono; a etapa não registra número,
  não troca nome nem PIN (regra 1 do projeto).
- **IA:** as conversas da carteira usam a mesma chamada `conversar` (Sonnet), com o mesmo teto de
  gasto da chave. O volume é o dos lotes: até 20 clientes por dia.
- **Representantes:** os dois responsáveis passam a receber fichas de interesse no WhatsApp.

## ROLLBACK_PLAN

1. **Desligar a chave** `olivia.atende_carteira` (`scripts\olivia.py`): na hora, sem restart. O toque
   "saber" passa a responder com a linha do representante e o texto volta ao portão. Conversas já
   abertas com ela terminam pelo caminho de sempre.
2. Se o defeito for de código: reverter os commits e reiniciar os dois serviços.
3. A `_VOLTA` da migração: sai a tabela de interesses, a coluna de `envios`, o modelo e a chave, e o
   CHECK volta à lista anterior. **Antes**, conferir que nenhum envio em voo usa o modelo novo.
4. O que não se desfaz: as fichas já enviadas aos representantes e as linhas já levadas ao
   Relacionamento do ERP. São registro do que aconteceu.
5. O modelo na Meta pode ficar aprovado sem uso; apagá-lo lá é ato do dono.

## Manual de uso

O manual `docs/manuais/olivia.md` passa a dizer errado, hoje, em "Quem usa e quando" e em "O que NÃO
faz", que ela não atende cliente da carteira.

1. **Para que serve.** Fazer do boletim uma conversa: quem recebe e quer saber mais é atendido na
   hora, pelo nome, recebe o material completo, e o representante fica sabendo quem se interessou e
   por quê. Sem isso o boletim é lido e o interesse se perde.
2. **Quem usa e quando.** O cliente da carteira (contato comprador ou técnico), nos dias seguintes a
   um boletim com o botão "Quero saber mais". O representante, que recebe a ficha. O dono, que lê o
   resumo do dia.
3. **O caminho comum.**
   1. O cliente toca "Quero saber mais" (ou escreve em resposta, em até 7 dias).
   2. Recebe o cumprimento pelo nome, as imagens do material completo e o texto da parceria.
   3. Conversa com a OlivIA; se disser em que tem interesse, ela anota.
   4. O representante recebe a ficha no WhatsApp e procura o cliente.
   5. O interesse aparece no Relacionamento do cliente, no ERP.
4. **O que significa cada sinal.**
   - Na tela Envios, a resposta **"quis saber mais"** é o toque no botão; com interesse anotado, as
     culturas aparecem ao lado.
   - **Ficha com erro** no resumo do dia: o representante não recebeu; a OlivIA não disse ao cliente
     que ele foi avisado.
   - No Relacionamento do ERP, **"Quis saber mais"** sem culturas quer dizer que o cliente entrou na
     conversa e não indicou nenhuma. Não é "sem interesse": é sem indicação.
   - Cliente sem nenhuma resposta: não tocou nem escreveu. Não quer dizer que não leu.
5. **O que NÃO faz.** Não fala de preço, quantidade nem prazo. Não reserva estoque. Não conhece o
   histórico do cliente. Não atende o cliente da carteira fora dos 7 dias de um boletim: aí vale o
   contato do representante, como antes. Não substitui o representante: quem pede uma pessoa recebe o
   contato na hora.

Para quem cuida: a chave `olivia.atende_carteira`, como ligar e desligar, e o que acontece com o
toque quando ela está desligada.

Pré-requisito que a etapa cria: **o modelo novo aprovado na Meta e o texto da parceria aprovado pelo
dono**. Sem os dois, a chave não liga.

## Próximo passo

/writing-plans
