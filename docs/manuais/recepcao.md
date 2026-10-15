# Recepção — manual de uso

> A tela que mostra quem chamou a Renascer no WhatsApp (49 3664 0121), o que a pessoa procurava e para
> quem ela foi mandada. No AxiaAtende: **http://127.0.0.1:8009**, aba **Recepção** (#950, 09/10/2026).
> Spec: `C:\AxiaMarketing\docs\specs\2026-10-09-axiaatende-recepcionista-e-envio.md`; quem é, pelo
> cadastro: `C:\AxiaAtende\docs\specs\2026-10-09-reconhecer-o-cadastro-no-atendimento.md` (#969).

## 1. Para que serve

A OlivIA atende quem chama no WhatsApp da empresa: mostra o menu (tudo por botão), descobre o
assunto e manda o cartão de contato de quem resolve. Esta tela mostra o que aconteceu com cada
pessoa: se chegou ao link, se parou no meio e, quatro horas e meia depois, se disse que foi atendida.
É onde você vê se alguém ficou sem resposta e em que ponto as pessoas desistem.

Quando quem chamou já está no **cadastro do ERP**, a tela mostra quem é: o nome, o código, o papel
(cliente, fornecedor, produtor, representante, equipe) e por qual contato do cadastro o número foi
achado. Isso só registra: o que a pessoa recebe no WhatsApp é o mesmo para todos.

E quando você precisa falar com a pessoa, a coluna **Quem** é o caminho: um clique abre a conversa
com ela no **seu** WhatsApp Web, já no lugar certo (#1025). Antes era preciso sair da tela e procurar
o número em outro sistema.

## 2. Quem usa e quando

Você, no computador, quando quiser acompanhar o atendimento — por exemplo, uma vez por dia.

## 3. O caminho comum

1. Abra **Recepção**.
2. Escolha o período (hoje e ontem, 7 ou 30 dias) e, se quiser, o motivo (Comercial, Fretes…) e a
   situação.
3. Para ver só quem já é da casa, escolha **"Só quem está no cadastro"** no último filtro; para ver
   os contatos novos (os leads), **"Só quem não está"**.
4. Leia os cartões.
5. Na lista, olhe primeiro as linhas **"parou no meio"** e **"Não · você foi avisado"**.
6. Para chamar alguém de volta, clique na coluna **Quem**: no botão **Conversar no WhatsApp** (quando
   a pessoa está no nosso cadastro) ou no **próprio número** (quando não está). Abre uma aba nova com
   a conversa dela no seu WhatsApp Web — **a primeira mensagem é você que escreve**, o sistema não
   manda nada. Depois volte para a aba da Recepção, que continua como estava.

## 4. O que significa cada sinal

| Sinal | Quer dizer |
|---|---|
| **Chegaram** | quantas conversas começaram no período |
| **Receberam o link** | chegaram ao fim do menu e receberam o WhatsApp de quem atende |
| **Pararam no meio** | começaram a escolher e ficaram 30 minutos sem tocar em nada, sem chegar ao link |
| **Disseram que foram atendidos / que não** | a resposta à pergunta "recebeu o atendimento?". Ela vai **uma vez por dia** para cada pessoa, 4h30 depois da **última** mensagem dela, e só em horário comercial (segunda a sábado, das 8h às 11h e das 14h às 17h: fora disso, espera a próxima faixa). Logo depois do "Sim" vem a nota, em três botões na própria mensagem (Bom, Normal, Ruim); se no mesmo dia ela foi mandada a mais de um atendente, a resposta vale para todas as conversas do dia (e cada uma conta no cartão) |
| **IA acertou / errou** | quem escreveu em vez de tocar recebeu a proposta da IA ("Entendi que você quer… É isso?"): **Sim** é acerto, **Ver todas as opções** é erro |
| **Do nosso cadastro** | quantos dos que chegaram no período estão no cadastro do ERP |
| **Quem: "Agro Real Insumos · 5475"** e as etiquetas | o número está no cadastro: o nome e o código dele. As etiquetas verdes (Cliente, Fornecedor, Produtor) e azuis (Equipe, Representante) dizem o papel; "contato comercial: João" diz de qual contato do cadastro o número veio |
| O botão verde **Conversar no WhatsApp**, ao lado do nome | abre a conversa com essa pessoa no seu WhatsApp Web, pelo número por onde ela chamou. É um atalho: nada é mandado, e nada é registrado |
| **"fora do cadastro"** | o número não está em nenhum cadastro. Pode ser um contato novo, ou alguém da casa cujo celular não foi cadastrado; aparece o número com o meio escondido e o nome do perfil do WhatsApp |
| O **número sublinhado** de verde (`+55 46 9…·4421`) | o número é o link: clique e a conversa abre no seu WhatsApp Web. O meio continua escondido de propósito — você **clica**, não lê o número inteiro |
| O nome **sem** o botão, ou o número **sem** sublinhado | não temos telefone dessa conversa (ela chegou só pelo identificador do WhatsApp). Não é erro, e por aqui não há como chamar essa pessoa |
| **"sem número"** no lugar do número | o mesmo caso acima, dito por extenso |
| O clique abre o WhatsApp pedindo o código QR | o seu WhatsApp Web não está conectado neste navegador. Conecte e clique de novo |
| **"número em 2 cadastros"** | o mesmo celular está em mais de um cadastro; o sistema não escolhe. Vale conferir o cadastro no ERP |
| **Quem só com o número, sem etiqueta** | a conversa chegou antes de o cadastro ser lido pela primeira vez |
| **"Cadastro lido em 09/10 06:00 (884 números)"** | o cadastro é lido uma vez por dia, às 06:00: quem foi cadastrado hoje é reconhecido amanhã. Se a leitura falhar, a frase diz o motivo e fica valendo a do dia anterior |
| **Caminho** | o que a pessoa tocou, na ordem ("Comercial › Produtor rural › PR › Cascavel") |
| **"— só chegou"** | mandou mensagem e ainda não escolheu nada |
| **Mandado para** | quem recebeu a pessoa pelo link (a tela Destinos diz quem é quem) |
| **"pergunta às 14:30"** | a pergunta "recebeu o atendimento?" ainda vai sair, nesse horário (se for de manhã cedo, é do dia seguinte) |
| **"perguntado, sem resposta"** | a pergunta saiu e a pessoa não respondeu |
| **"já perguntado hoje, em outra conversa"** | a pessoa já tinha recebido a pergunta do dia por outra conversa; nesta não se perguntou de novo |
| **"não perguntado (mais de 24h sem mensagem)"** | a próxima faixa de horário chegou quase um dia depois da última mensagem da pessoa, e o WhatsApp não deixa mais mandar a pergunta (acontece com quem chama sábado à tarde ou domingo cedo) |
| **"Não · você foi avisado 15:41"** | a pessoa disse que não foi atendida; você recebeu um aviso no WhatsApp nesse horário |
| **"Sim" seguido de "Bom" ou "Normal"** | a pessoa foi atendida e deu essa nota. Só "Sim", sem nota: ela confirmou o atendimento e não tocou na nota |
| **"Sim" seguido de "Ruim · você foi avisado"** | a pessoa foi atendida e saiu insatisfeita; você recebeu um aviso no WhatsApp, como no "Não" |
| **"—"** | ainda não aconteceu (não é zero) |
| **Fotos do campo (equipe)** | quantas fotos e vídeos colaboradores e representantes do cadastro mandaram pelo **canal de campo** no período, e quantas já estão no catálogo do marketing (#970). Não são conversas: a OlivIA responde "Recebi", lê a frase e pergunta só o que faltou para classificar (o que mostra, o produto, a fase, a data; no máximo três perguntas), e o marketing busca para a Caixa. O cartão só aparece quando houve alguma; o canal se liga na tela **Destinos** |

## 5. O que a tela NÃO faz

- **Não mostra a conversa** da pessoa com o atendente: ela acontece no WhatsApp de quem recebeu o link.
- **Não responde ninguém** pela tela.
- **Não manda mensagem no clique da coluna Quem:** ele só abre a conversa. Quem escreve é você.
- **Não fala pelo número da empresa:** a conversa sai do **seu** WhatsApp, não do 49 3664 0121 — a
  pessoa vai ver que é você.
- **Não mostra o número inteiro**, nem depois do clique: o que você lê continua mascarado.
- **Não registra** que você clicou, nem avisa a pessoa.
- **Não muda o menu nem para quem cada motivo vai:** isso é a tela **Destinos**.
- **Não corrige o cadastro:** número faltando ou repetido se corrige no ERP.
- **Não reconhece de novo conversas antigas:** cada conversa guarda quem era no momento em que chegou.
- **Não mostra valor, crédito nem documento** de ninguém.
- **Não mostra a foto do campo:** ela vai para a Caixa do marketing (manual `caixa.md` do AxiaMarketing); aqui só a contagem. O que a equipe deve mandar está no `campo-equipe.md`.

## A retomada pela OlivIA (#989, 13/10/2026)

Quem **parou no meio** (não achou a opção, escreveu o que o menu não entendeu) não fica sem nada:
trinta minutos depois de parar, a OlivIA relê tudo o que a pessoa escreveu e tocou naquela conversa,
acha a opção do menu que resolve e manda *"Pelo que entendi da nossa conversa, você quer: SC
(Comercial › Revendedor). É isso?"*, com **Sim** e **Ver opções**. O **Sim** manda o contato, como
se ela tivesse tocado certo; **Ver opções** repete a pergunta do ponto onde ela parou, com as opções
daquele ponto (o menu principal só se parou no começo). É automático, uma vez por conversa, só nas
24 horas da última mensagem da pessoa, e nunca escreve texto livre: só o que o menu já daria.

Na Recepção, a conversa retomada volta a "escolhendo agora"; com o Sim vira "recebeu o link" e conta
em "IA acertou"; sem resposta volta a "parou no meio" em 30 minutos, e não há segunda retomada. Nada
é mandado quando a pessoa escreveu há mais de 24 horas, quando a IA não achou opção que servisse, ou
quando a IA estava fora; nos três casos a conversa fica "parou no meio" como antes. A frase da
retomada é o ajuste `retomada` (a sessão troca pela porta, se um dia for preciso).
