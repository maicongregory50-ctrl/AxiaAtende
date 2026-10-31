# A OlivIA no nome e o painel de custos das APIs pagas
**Data:** 2026-10-31
**Chamado:** #1223
**Status:** APROVADO

## Contexto

A atendente virtual do AxiaAtende se chama **OlivIA** (dono, 31/10/2026), em todos os projetos. O nome
já está no código (`backend/ia.py:1`) e nos manuais, mas falta em dois lugares:

- no inventário de agentes do painel (`C:\AxiaSecurity\design\agentes.json`), onde ela aparece como
  quatro linhas `chamada` sem o nome (`triagem-motivo`, `leitura-campo`, `triagem-curriculo`,
  `leitura-visita`);
- em `C:\AxiaAtende\CLAUDE.md:13`, que diz "no lugar do Opa Suite (a OlivIA)", como se ela fosse do Opa.

A casa tem **três APIs pagas por uso**, e nenhuma tem o custo medido por função:

| API | Quem usa | O que se mede hoje |
|---|---|---|
| **Claude** (Haiku 5.5) | AxiaAtende, as quatro funções de `backend/ia.py`, no processo do recepcionista | nada: `r.usage` não é lido |
| **Meta WhatsApp** (modelos pagos) | AxiaAtende, `backend/saida.py` → `SaidaMeta.modelo` | estimativa: convites × US$ 0,07 (`rotas_telas.py:17`; `AxiaMarketing/backend/envio_whatsapp.py:527`) |
| **Gemini** | AxiaMarketing: `backend/visao.py` (olhar a foto) e `scripts/motor_edicao.py` (edição) | estimativa mensal por motor em `casa.gasto_ia` (US$ 0,01 por foto, US$ 0,07 por edição), que serve ao teto de US$ 10/mês |

Todo o resto da casa roda na assinatura (o SuporteAxia desde o #899, as sessões, o revisor de arte e o
monitor fiscal). A Graph API do AxiaMarketing (publicar e ler insights) não é cobrada.

**O problema que o dono quer resolver (31/10): saber se cada função compensa.** Para isso o custo
precisa vir por função, e não só o total do mês.

## Os fios que encostam

**Quem mais escreve no que a mudança escreve:**

- `atendimento.eventos_meta`: um escritor só, `recepcionista.gravar` (`ON CONFLICT DO NOTHING`). A
  mudança **só lê** dessa tabela.
- **Tabelas novas do AxiaAtende** (o registro do modelo por mensagem, o uso de IA por chamada, os preços
  e a conferência da Meta): nascem nesta etapa, com escritor único cada uma. O registro do modelo é
  gravado por `SaidaMeta.modelo`, o uso de IA por `ia.py`, a conferência pelo laço do recepcionista, e
  os preços pela tela.
- `atendimento.enviadas`: hoje tem **oito pontos de INSERT espalhados** (motor, envio, campo, vaga,
  logos...). A mudança **não** passa a depender dela para atribuir função: o registro nasce no ponto
  único de saída paga, `SaidaMeta.modelo`.
- `casa.gasto_ia` (AxiaMarketing): **dois escritores**, `visao.py` e `rotas_editor.py`, e uma
  **régua**: o teto de US$ 10 lê dali para barrar o editor e o olhar (`rotas_editor.py:84`,
  `visao.py:83`). Decisão do dono: **o teto continua pela estimativa nesta etapa**. O uso real vai para
  uma tabela nova, e a `casa.gasto_ia` continua como está.
- `scripts/motor_edicao.py` **não toca no banco** (por desenho do #916): o uso do Gemini volta na saída
  dele para `rotas_editor.py`, que grava.
- `agentes.json`: três leitores, `scripts/painel_bloco.ps1`, `scripts/gerar_tabela_agentes.py` e
  `scripts/conferir_agentes.py`. O campo novo tem de ser lido sem quebrar nenhum dos três.

**Quem volta depois:**

- `recepcionista.aplicar_status` atualiza `enviadas` a cada status, e não muda.
- `clientes_erp` empurra os estados ao ERP (`CRM.EVT.W`), e não muda.
- O backup noturno do banco do AxiaAtende (02:20 e 02:45) e o do AxiaMarketing levam as tabelas novas
  sem configuração nova, e o ensaio de restauração das 03:30 também (R2).
- A conferência diária da Meta é rotina nova no laço do recepcionista, uma chamada por dia.

## O universo medido

Medido em 31/10/2026, só leitura, `axiaatende_ro` na 5436:

- **3.785** avisos de status gravados em `eventos_meta`, de 09/10 a 31/10. **3.770** trazem
  `pricing_model = PMP`; os 15 sem `pricing` são `failed`.
- **Mensagens cobradas** (`billable = true`, uma por mensagem): **190** marketing, **26** utility e
  **2** marketing_lite, total **218**. Outras 1.183 saíram de graça (627 `free_customer_service` e 556
  `free_entry_point`).
- **Por semana:** 05/10: 1 utility. 12/10: 18 marketing, 13 utility, 1 lite. 19/10: 37 marketing, 9
  utility, 1 lite. 26/10: 135 marketing, 3 utility.
- **Atribuição de hoje:** das 218, **130** estão em `enviadas` e **36** em `avisos`, e **52 (24%) não
  estão em tabela nenhuma** com `wamid` (dez tabelas conferidas). Essas 52 ficam como "anteriores ao
  registro", sem função.
- `enviadas_texto.modelo`: 1 de 11 linhas, todas desde 30/10. O nome do modelo **não** é registrado
  hoje.
- `atendimento.modelos`: **16** modelos, cada um com `categoria` (MARKETING/UTILITY) e `uso` (convite,
  direta, curriculo, reabertura, aviso_*). O `uso` vira a função.
- **Entradas que podem ir à IA desde 09/10:** 348 textos e 48 documentos. O custo do Claude não foi
  medido. A estimativa pelo preço de tabela (US$ 0,10 por milhão de tokens de entrada e US$ 0,50 de
  saída) fica abaixo de US$ 1 por mês, e é exatamente isso que esta etapa troca por número.
- **Gemini:** não medido. A sessão não tem leitura do banco de produção do AxiaMarketing.
- `casa.usuarios` do AxiaAtende **não tem papel**: login, nome, senha e ativo.

## Conformidade com o Manual legal

Não se aplica: custo de fornecedor de tecnologia, sem regra tributária nem documento fiscal.

## Conformidade com a casa

- **R7 (agentes de IA têm inventário...): muda.** Lido: *"quem existe, o que pode, quem desliga, quem é
  avisado"*. O inventário ganha o nome OlivIA nas quatro linhas e o campo `cobranca` (`api` |
  `assinatura`) em **toda** linha com modelo. `conferir_agentes.py` passa a recusar linha `agente`,
  `chamada` ou `sessao` sem o campo, e `gerar_tabela_agentes.py` e `painel_bloco.ps1` passam a mostrá-lo.
  É passo próprio do plano. Nenhuma chamada a modelo nova nasce: as quatro da OlivIA e as duas do
  Gemini só passam a registrar o uso. A política de uso de IA não muda.
- **R3 (segredo legível só por quem executa): conforme.** Lido: *"Segredo é legível só por quem
  executa; nenhum em log, argv ou commit"*. **Nenhum segredo novo.** A conferência da Meta usa o token
  que o recepcionista já tem, em `.env.recepcionista`. A API de custo da Anthropic (chave de
  administrador) ficou **fora** por isso. O login autorizado a ver a tela vai no `.env`, e não é segredo.
- **R2 (dado vivo tem cópia verificada): conforme.** Lido: `rotina:backup-axiaatende-banco` ·
  `rotina:backup-axiaatende-banco-nuvem` · `rotina:backup-axiamarketing-banco`. As tabelas novas moram
  nos dois bancos que já têm backup e ensaio.
- **R4 (superfície de rede): conforme.** A rota nova do AxiaMarketing é local (`127.0.0.1:8006`), como
  as que ele já oferece. A conferência é uma chamada de saída a `graph.facebook.com`, que o
  recepcionista já faz. Nenhuma porta nova.
- **PROJETO.md:** o do AxiaMarketing ganha no *Ofereço* "o uso real do Gemini, por função e por dia,
  em rota local". O do AxiaAtende ganha no *Exijo* essa rota, com *se faltar: o Gemini aparece como "sem
  leitura" na tela Custos; o resto continua*.

## Decisão

**Caminho B**, aprovado pelo dono em 31/10/2026: as três APIs, por função, numa etapa.

1. **Meta.** `SaidaMeta.modelo` grava, a cada envio aceito, o `wamid` e o nome do modelo. A função é o
   `uso` do modelo no cadastro. A **quantidade cobrada** vem do aviso de status da Meta (`pricing`), e o
   **valor** é a quantidade × o preço vigente da categoria na tabela de preços. A mensagem cobrada sem
   registro aparece como **"sem função"**, nunca some.
2. **Conferência da Meta** (decisão do dono): uma vez por dia, o recepcionista lê o custo oficial do
   dia anterior na API de análise de preços da conta (`META_CONTA_WA`), por categoria, e grava. A tela
   mostra "calculado × cobrado". Sem permissão ou sem resposta, grava **"sem acesso"**, nunca zero. Tem
   chave própria no `.env.recepcionista` para desligar.
3. **Claude.** As quatro funções de `ia.py` gravam, por chamada, a função, o modelo e os tokens de
   entrada e saída que a API devolve, inclusive quando a resposta é descartada (recusa, fora do
   esquema). Erro de rede sem resposta não tem uso e não grava.
4. **Gemini** (decisão do dono: real, pelos tokens). O AxiaMarketing grava, por chamada, a função
   (`edicao` ou `olhar_foto`), o modelo e os tokens que o Google devolve (`usageMetadata`). O
   `motor_edicao.py` devolve o uso na saída, e `rotas_editor.py` grava. O AxiaMarketing oferece o
   resumo por dia e por função numa **rota local** de leitura, e a tela do AxiaAtende lê dali. **O teto
   de US$ 10 continua pela estimativa** (decisão do dono).
5. **Tabela de preços com vigência**, na própria tela: por categoria da Meta e por modelo (entrada e
   saída por milhão) para Claude e Gemini. O dono preenche. Preço ausente aparece como **"sem preço"**
   ao lado da quantidade, nunca como US$ 0.
6. **Tela Custos** no AxiaAtende, **só para o dono**: um login permitido, por chave no `.env`.
7. **OlivIA no nome:** as quatro linhas do inventário, a correção do `CLAUDE.md:13` e o campo
   `cobranca` (ver Conformidade com a casa).

## Escopo desta etapa

**Dentro:** os sete itens da Decisão. O passado da Meta desde 09/10 é calculado pelos avisos já
gravados: com a quantidade real, e sem função quando não houver registro.

**Fora:**

- alerta ou teto por API (é o Caminho C, depois de um mês de números);
- trocar o teto do Gemini para o valor real;
- a API de custo da Anthropic e qualquer chave de administrador;
- recalcular o passado do Claude e do Gemini (eles não têm registro antes desta etapa);
- tirar a estimativa "× 0,07" da tela Envios. Ela continua lá: é a previsão **antes** do envio, e a
  tela Custos é o fato depois dele.

## Impacto em produção

- **AxiaAtende:** uma migração (050 em diante) com `_VOLTA`. Afeta os serviços `axiaatende-recepcionista`
  (`saida.py`, `ia.py`, o laço da conferência) e `axiaatende-backend` (a tela). Restart dos dois. O
  registro é uma gravação a mais por envio pago e por chamada de IA. **A falha da gravação nunca trava o
  envio nem a resposta**: o envio é o evento real (mesma doutrina do registro da conversa no
  SuporteAxia).
- **AxiaMarketing:** uma migração (049 em diante) com `_VOLTA`, mais `visao.py`, `motor_edicao.py`,
  `rotas_editor.py` e a rota nova. Restart do `axiamarketing-backend`. O teto não muda.
- **AxiaSecurity:** `agentes.json`, o conferidor, o gerador da tabela e o bloco do painel.
- Sem janela de manutenção. Nada que barra hoje muda de comportamento.

## ROLLBACK_PLAN

1. **A conferência da Meta**, sozinha: a chave dela no `.env.recepcionista` em `false` e restart do
   recepcionista. A tela passa a mostrar "conferência desligada".
2. **A tela:** tirar o login da chave do `.env` das telas e reiniciar. A tela some e o registro continua
   gravando, então nada se perde.
3. **O registro no AxiaAtende:** reverter o commit de `saida.py`, `ia.py` e do laço, e reiniciar. As
   tabelas ficam, paradas.
4. **As tabelas do AxiaAtende:** aplicar a `_VOLTA` da migração. Isso perde o registro gravado desde a
   subida, e por isso é o último passo.
5. **AxiaMarketing:** reverter o commit e reiniciar o `axiamarketing-backend`. A `_VOLTA` da migração
   só depois disso. A `casa.gasto_ia` e o teto não foram tocados, então não há o que restaurar.
6. **Inventário:** reverter o commit do `agentes.json` e do conferidor. O painel volta ao de antes.

## Manual de uso

Manual novo: `docs/manuais/custos.md`, com linha no `INDICE.md`.

1. **Para que serve.** Mostra quanto a Renascer paga por mês a cada serviço cobrado por uso (a Meta pelo
   WhatsApp, a Anthropic pela OlivIA e o Google pelo Gemini) e **qual função gerou cada gasto**. É para
   decidir se cada função compensa o que custa.
2. **Quem usa e quando.** Só o dono, no começo do mês para fechar o anterior, ou quando uma função nova
   entra no ar e ele quer ver quanto ela pesa.
3. **O caminho comum.**
   1. Abrir **Custos** nas telas do AxiaAtende.
   2. Escolher o mês (abre no mês corrente).
   3. Ler a linha de cada função: serviço, quantidade (mensagens ou chamadas) e valor em US$.
   4. Na Meta, comparar o total **calculado** com o **cobrado** pela Meta.
   5. Quando a Meta ou o Google mudarem o preço, abrir **Preços**, lançar o novo com a data em que
      passou a valer e salvar. O preço antigo continua valendo para os dias anteriores.
4. **O que significa cada sinal.**
   - **"sem preço"**: a quantidade é real, mas falta o preço daquela categoria ou modelo naquela data.
     **Não é US$ 0**: lance o preço e o valor aparece.
   - **"sem função"**: mensagem cobrada pela Meta que o sistema não sabe de qual função saiu. Até
     31/10/2026 isso é esperado (52 mensagens de outubro). Depois, se aparecer, é defeito: abra chamado.
   - **"sem acesso"** na coluna Cobrado: a Meta não deixou ler o valor oficial naquele dia. O calculado
     continua valendo. **Não é zero.**
   - **"sem leitura"** no Gemini: o sistema do marketing não respondeu. O gasto existe, só não foi lido.
   - **Calculado diferente de Cobrado**: diferença pequena é arredondamento ou câmbio. Diferença grande
     quer dizer preço desatualizado na tabela.
5. **O que a tela NÃO faz.** Não é a fatura: o valor oficial é o da Meta, da Anthropic e do Google. Não
   barra nem avisa quando o gasto sobe (o teto de US$ 10 do Gemini continua no AxiaMarketing, pela
   estimativa). Não mostra o que roda na assinatura do Claude, que não é cobrado por uso. Não mostra o
   custo do Claude e do Gemini antes de 31/10/2026, porque ninguém o registrava.

**Manuais que passam a dizer algo errado:** `docs/manuais/envios.md`, se tratar o "Custo US$" como o
gasto. O plano confere e diz que aquele é a previsão, e que o fato está em Custos.

## Emenda de 31/10/2026, no plano: o Gemini é EMPURRADO, não lido

Ao escrever o plano, a leitura do código mostrou que a seta da casa é a outra: **o AxiaMarketing chama o
AxiaAtende** (`127.0.0.1:8009`, com a chave do pedido que já existe), e o Atende nunca chama o Marketing.
As rotas da 8006 exigem login, e ler dali pediria uma credencial nova do Atende para o Marketing (R3:
"cria"). **Decisão do dono:** o AxiaMarketing grava o uso real de cada chamada na tabela dele e o
**empurra** ao Atende (`POST /pedido/uso-ia`); se o Atende estiver fora, a linha vai na próxima chamada.
Onde esta spec diz "rota local de leitura no AxiaMarketing" e "a tela do AxiaAtende lê dali", vale isto.
Nenhum segredo novo; o R3 continua **conforme**.

E um achado que muda a Decisão 1: **o registro do modelo por mensagem já existia** desde 30/10 (#1205,
`enviadas_texto.modelo`, gravado pela `SaidaMeta`). Para a Meta não nasce registro novo: o custo é uma
leitura que junta o `pricing` do aviso, o modelo e o `uso` do cadastro.

## Próximo passo

`/writing-plans`. O AxiaAtende não tem raiz de leitura para o PLANEJADOR (#976), então o plano é
escrito em sessão com o dono.
