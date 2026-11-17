# A OlivIA na conversa de quem quer comprar: conversar, identificar e encaminhar
**Data:** 2026-11-17
**Chamado:** #1589
**Status:** APROVADO

## Contexto

**O pedido do dono (17/11/2026):** antecipar o atendimento de vendas enquanto o Comercial está em baixa
(a venda se concentra de janeiro a maio). Onde ele quer chegar, nas palavras dele: *"o top, a OlivIA
conseguir atender o cliente e fechar uma negociação"*, em degraus: *"a gente tem que ir pensando
degrauzinho a degrauzinho como que ela chega lá"*. E o primeiro: *"a base do atendimento é ela entender
se está falando com um produtor, com uma revenda, se é um corretor"*; *"no primeiro momento vai ser
passar para frente"*.

**O exemplo que ele deu:** "Eu queria ver se você tem semente de aveia?" — "Temos sim. Eu falo com
quem?" — "Fulano." — "Seu Fulano, a gente tem aveia sim. O senhor já sabe quanta aveia precisa? Em que
cidade o senhor está?" — e o contato de quem atende.

**O que existe hoje.**
- A OlivIA fala com quem é de fora desde 16/11 (#1520) e sabe o que a Renascer tem e não tem (degrau 1
  deste chamado, `docs/olivia/base-da-empresa.md`, seção *Temos e não temos*, 17/11).
- Para quem quer comprar ela só **encaminha**: oferece o nó `comercial` do menu, e a pessoa toca
  produtor, revenda ou corretor, depois o estado (no Paraná, a região), e recebe o cartão de contato.
  Conversa 347 (17/11, 09:41): "Comprar semente" → os botões → três toques → o cartão.
- O representante de cada caminho está no cadastro Destinos: o menu Comercial tem 13 folhas de destino
  (produtor e revenda por SC, PR-Cascavel, PR-Ponta Grossa, SP, RS e Outro; corretor), hoje com dois
  nomes.
- Para oferecer uma folha do menu, a ferramenta `oferecer_opcao_do_menu` manda "Posso te passar para X?"
  com o botão Sim; o cartão só sai no toque.

**A escada decidida na conversa de desenho (17/11/2026):**

| Degrau | O que ela passa a fazer | Quando |
|---|---|---|
| 1 | Dizer o que a Renascer tem e não tem | feito em 17/11 |
| 2 | Conversar e identificar: nome, categoria, o que procura; passar o contato do representante certo | **esta spec** |
| 3 | Registrar o lead (nome, categoria, cidade, produto, volume); o representante recebe a ficha e chama se o cliente não chamar | chamado próprio |
| 4 | Classificar (volume, distância) e dizer o que cabe atender | chamado próprio; depende de regras do dono |
| 5 | Cenário por categoria; indicar produto pelo uso | depende da base corrigida e do #857 |
| 6 | Preço e fechamento de pedido | depende do cliente reconhecido, da lista de preço e do ERP |

**Decisões do dono:**

| # | Decisão |
|---|---|
| D1 | A ficha ao representante **fica fora** desta etapa: *"é mais importante ensinar a OlivIA a atender agora, dar voz, depois avisamos o representante"* |
| D2 | **Caminho B**: ela conduz, pergunta e encaminha. Pergunta com quem fala quando o nome do perfil não é legível; depois de dizer que tem, pergunta a cidade e quanto a pessoa precisa, uma vez; o contato sai em seguida, com ou sem resposta. Nada é gravado como ficha |
| D3 | O contato sai **sem o "Sim"** quando a categoria e o estado estão claros; em dúvida, os botões de hoje |
| D4 | A indicação de produto pelo uso fica para o degrau 5 (a base em uso é o rascunho de 16/11) |

## Os fios que encostam

**Quem escreve o que esta etapa escreve.**
- `atendimento.conversas` (`no_atual_id`, `caminho`, `situacao = 'com_link'`, `destino_id`, `link_em`,
  `pergunta_em`): hoje `motor.escolher`, chamado pelo toque no menu e pelo "Sim" da proposta. A etapa
  acrescenta um chamador, a ferramenta `passar_contato`, **pela mesma função**: nenhuma coluna ganha
  escritor novo. **Quem lê para decidir:** a pergunta das 4h30 (`pergunta_em`), `marcar_paradas`, o
  vigia da OlivIA (`link_em` conta como "terminou bem"), a tela Conversas.
- `atendimento.enviadas`: o cartão sai registrado como `link: <chave>`, como hoje; a ferramenta registra
  `olivia: ferramenta passar_contato: <chave>`.
- `atendimento.ajustes`: a chave nova `olivia.conduz_venda`.
- Nenhuma tabela nova, nenhum dado novo de quem compra: o que a pessoa responde fica só na conversa
  (`eventos_meta`), como qualquer texto dela.

**Quem volta depois.**
- **A pergunta das 4h30** ("você recebeu o atendimento que precisava?") continua saindo para quem recebeu
  o cartão, pela mesma `pergunta_em`.
- **`depois_do_atendimento`** (o "obrigado" depois do cartão) continua antes da OlivIA em `motor.tratar`.
- **O vigia das 23:40**: conversa de venda com cartão entregue é `bem`; sem cartão nem opção, `sem_saida`.

## O universo medido

Medido em 17/11/2026 (papel de leitura), 30 dias:

| Pressuposto | Contagem |
|---|---|
| conversas pelo Comercial | 13 (contra 59 de vaga); 11 receberam o contato |
| caminhos | Produtor rural > SC 3 · Produtor rural > PR > Cascavel 2 · Produtor > SP 1 · Produtor > Outro 1 · Revendedor > SC 1 · Revendedor > Outro 1 · só "Comercial" 2 |
| o que escreveram | "tem milheto e sudão?", "soja ou milho vocês fazem?", "gostaria de fazer um orçamento", "2000 unidades de ipê amarelo", e 3 vezes a frase pronta do site |
| perguntas de dose, época ou preço ao número | nenhuma no período |
| folhas de destino do Comercial | 13, com 2 representantes |

**A medida de sucesso:** das conversas de quem quer comprar, quantas terminam com o cartão do
representante certo, e em quantas mensagens; e quantas pessoas responderam a cidade e a quantidade.
**O fracasso silencioso:** ela dizer que avisou o representante (ninguém é avisado nesta etapa), ou
entregar o cartão do representante errado.

## Conformidade com o Manual legal
não se aplica: atendimento ao público, sem regra fiscal ou legal. Ela continua sem falar de preço.

## Conformidade com a casa

Gatilho tocado: **agente de IA** (R7).

- **R7 — muda.** Lido: *"O que um agente pode fazer sozinho é decisão do código que o envolve (...) Esta
  responsabilidade é sobre governança: quem existe, o que pode, quem desliga, quem é avisado."* A OlivIA
  ganha uma ferramenta que entrega o contato de uma pessoa da equipe sem a confirmação do botão. **Passos
  do plano:** a linha dela no `inventario-agentes.md` (a ferramenta e a chave `olivia.conduz_venda`) e,
  na `politica-uso-ia.md`, em *Pode sozinho*: *"Conduzir a conversa de quem quer comprar e entregar o
  contato do representante certo, sem preço, dose nem prazo, e sem gravar ficha; decidido em 17/11/2026
  (#1589)"*.
- **R2 — não tocado:** nenhum dado novo.
- **R3 e R4 — não tocados.**

## Decisão

**Caminho B.** Com a chave `olivia.conduz_venda` ligada:

**1. As regras da venda entram na instrução dela** (como as da vaga), e só com a chave:
- responde primeiro se a Renascer tem o que a pessoa procura, pela seção *Temos e não temos*;
- se o nome do perfil não parece nome de gente, pergunta com quem fala, uma vez (o nome do perfil
  chega a ela como nota, fora do texto da pessoa);
- depois de dizer que tem, pergunta **em uma mensagem só** a cidade e quanto a pessoa precisa (área ou
  quantidade); uma vez, sem insistir;
- descobre pela conversa se é produtor rural, revenda ou corretor; se não der, pergunta em uma frase;
- com a categoria e o estado claros (no Paraná, a região: Cascavel ou Ponta Grossa), entrega o contato
  com `passar_contato` e diz em uma frase quem vai atender; em dúvida, usa os botões de hoje;
- não fala de preço, dose, época, estoque nem prazo: isso é com o representante;
- **não diz que avisou o representante**: nesta etapa ninguém é avisado; diz que a pessoa chama pelo
  cartão.

**2. A ferramenta `passar_contato`.** Oferecida só com a chave ligada, fora da conversa de vaga. A chave
vem de lista fechada: as folhas de destino do menu Comercial. Ela chama `motor.escolher`, a mesma função
do toque: sai o texto e o cartão, a conversa fica `com_link`, e a pergunta das 4h30 fica marcada.

**3. A chave.** `olivia.conduz_venda`, ajuste no banco, nasce `false`, liga e desliga por script sem
restart, e só vale com `OLIVIA_FALA` ligada. Desligada, a conversa de quem quer comprar é a de hoje.

**Por que B e não A:** sem as duas perguntas o hábito não nasce, e o degrau 3 teria de ensinar a
perguntar e a gravar ao mesmo tempo. **Por que não C:** o dono pediu a ficha fora desta etapa.

## Escopo desta etapa

**Dentro:** as regras da venda na instrução; a nota com o nome do perfil; a ferramenta `passar_contato`;
a chave e o script; o `/saude`; testes; inventário e política; o manual.

**Fora (degraus seguintes, chamado próprio quando chegar a vez):** gravar o lead e avisar o
representante; classificar por volume e distância; cenários por categoria; indicar produto pelo uso;
preço, estoque, prazo e pedido; corrigir a base da empresa (é do dono, e continua pendente).

## Impacto em produção

`axiaatende-recepcionista` (a conversa) e `axiaatende-backend` (aplica a migração do ajuste). Uma
migração: uma linha em `ajustes`. Restart dos dois pela Porta-Ação. Custo de API: a conversa de venda já
passava pela OlivIA; nada novo.

## ROLLBACK_PLAN

1. `python scripts\olivia.py desligar-venda`: na hora, sem restart, a conversa de quem quer comprar
   volta a ser a de hoje (os botões).
2. Desfazer o código: `git revert` dos commits do chamado e a `_VOLTA` da migração (tira o ajuste).
3. Inventário e política: revert no AxiaSecurity.

## Manual de uso

**Manual que muda:** `docs/manuais/olivia.md`, item novo na seção 3 e linhas nas seções 4 e 5.

1. **Para que serve.** Quem escreve querendo comprar conversa com a OlivIA em vez de só receber
   botões: ela diz se a Renascer tem o que a pessoa procura e entrega o contato de quem atende.
2. **Quem usa e quando.** Qualquer pessoa de fora que queira comprar, a qualquer hora. O representante
   continua sendo quem negocia.
3. **O caminho comum.**
   1. A pessoa pergunta por um produto. A OlivIA diz se tem.
   2. Se o nome não aparece no perfil, ela pergunta com quem fala.
   3. Ela pergunta a cidade e quanto a pessoa precisa, uma vez.
   4. Sabendo se é produtor, revenda ou corretor e de que estado, entrega o cartão de quem atende.
   5. A pessoa toca em Conversar no cartão.
4. **Sinais.**
   - Na conversa, **o cartão do representante sem o botão "Sim" antes**: ela tinha certeza da categoria
     e do estado.
   - **Os botões de produtor, revenda e corretor**: ela ficou em dúvida, ou a chave está desligada.
   - No `/saude` do recepcionista, **"olivia_venda": "ligada"**.
5. **O que NÃO faz.** Não fala de preço, dose, época de plantio, estoque nem prazo. Não avisa o
   representante nem guarda ficha de quem quer comprar: a pessoa é quem chama, pelo cartão. Não
   recomenda produto para a área da pessoa. Não fecha pedido.

**O que o manual passa a dizer errado:** na seção 5, *"Não sabe nada de cliente, pedido, boleto... encaminha
pelo botão"* continua verdade, mas "pelo botão" ganha "ou entregando o cartão direto, na conversa de
compra".

## Próximo passo
/writing-plans
