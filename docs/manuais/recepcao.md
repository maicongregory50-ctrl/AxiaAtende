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
achado.

**Desde 15/10/2026 (#1031) esse reconhecimento muda o atendimento, e não só o registro.** Quem é
**equipe** ou **representante** recebe o **menu da casa** em vez do menu de cliente — ver a seção *O
menu da casa* no fim deste manual. Para todos os outros, o que a pessoa recebe no WhatsApp continua
sendo o mesmo.

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
| **Pararam no meio** | começaram a escolher e ficaram 30 minutos sem tocar em nada, sem chegar ao link. A conversa do **Trabalhe conosco** não entra aqui: ela termina como *currículo recebido* ou *sem currículo* (#1098) |
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
| No menu principal, **"Comercial"** diz *comprar* e **"Fornecedores"** diz *vender para a Renascer* | mudou em 15/10/2026 (#1027). Antes "Comercial" dizia só "Cotar sementes", e quem escrevia *"posso te fazer uma cotação"* querendo **vender** caía no Comercial — foi o caso de uma empresa de embalagens naquela manhã |
| *"Recebi o arquivo, mas não consigo abrir arquivo por aqui…"* | alguém mandou **PDF, áudio ou vídeo** fora da conversa da vaga. A frase diz por que não serve e abre caminho (escrever em uma linha, ou *menu*). Dentro da conversa do Trabalhe conosco, o PDF é o currículo e vai à Fran |
| **"currículo recebido"** | conversa do Trabalhe conosco: o candidato mandou o PDF, e ele vai à Fran com a pré-triagem (manual `trabalhe-conosco.md`) |
| **"sem currículo"** | conversa do Trabalhe conosco em que a pessoa conversou, ou tocou **Encerrar**, e não mandou o PDF |
| *"Recebi, mas por aqui eu entendo texto e os botões"* | continua valendo para **figurinha, localização e contato** — o que não é arquivo |
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

## Quando a OlivIA fica calada de propósito (#1028, 15/10/2026)

Em dois casos ela **para de responder**, e isso é decisão, não falha. Se você vir uma conversa sem
resposta nossa, veja se é um destes antes de procurar defeito:

| O que você vê | O que quer dizer |
|---|---|
| A conversa **recebeu o menu uma vez e nunca mais** | o WhatsApp daquele número **recusou** o menu — a Meta respondeu "não entregável". Em vez de insistir, paramos de mandar o menu para ele. Quase sempre é um robô do outro lado; pode ser alguém com WhatsApp muito antigo |
| **Duas** respostas *"Recebi, mas por aqui eu entendo texto e os botões"* e nada depois | mandaram um terceiro conteúdo que não dá para ler — figurinha, enquete, áudio, documento. Depois de avisar duas vezes, ela para: avisar uma terceira não ajudaria ninguém |

**Por que existe.** Em 15/10/2026 um robô do outro lado ficou 100 minutos trocando mensagens com a
OlivIA: ele mandava algo ilegível, ela respondia, ele respondia, e o menu dela voltava como "não
entregável" — sete vezes. Insistir com quem não recebe é o que estraga a reputação do nosso número
na Meta, e é essa reputação que nos deixa mandar material à carteira.

**Quem recusa o menu continua recebendo texto.** Não é bloqueio do contato: só o menu com lista de
opções deixa de ser tentado.

**Onde conferir se alguma das duas agiu:** no `/saude` do recepcionista, o bloco `calados`. Número
maior que zero quer dizer que agiu desde que o serviço subiu. **Zero não quer dizer desligada** —
quer dizer que ninguém esbarrou nelas, ou que o serviço acabou de subir.

**O que isto NÃO faz:** não avisa ninguém, não aparece na lista da Recepção (mensagem que não foi
enviada não deixa registro) e não se desfaz sozinho — o número que recusou a lista não volta a
recebê-la sem mudança de código.

## O menu da casa (#1031, 15/10/2026)

**Quem é da equipe ou representante da Renascer não é mais atendido como cliente.** Ao escrever no
número da empresa, recebe um menu curto da casa, com duas opções:

- **📸 Foto do campo** — explica em uma linha o que fazer: é só mandar a foto ou o vídeo ali mesmo, e
  a OlivIA pergunta o que faltar para catalogar;
- **👤 Menu do cliente** — mostra exatamente o que um cliente vê, inclusive o caminho para falar com
  um colega (Fretes, Qualidade, Comercial).

**Por que existe.** Em 15/10 o Benedito escreveu "Boa Tarde" e recebeu o menu de cliente, embora o
sistema soubesse que ele é equipe. E havia um caso pior, medido: ele percorreu o menu de cliente até
Fretes e **recebeu o cartão de contato dele mesmo, três vezes** — porque ele é o destino de Fretes.

| O que você vê | O que quer dizer |
|---|---|
| O **menu da casa** depois de um "oi" | a pessoa foi reconhecida como equipe ou representante — pelo cadastro do ERP, ou por ser um dos contatos da tela **Destinos** |
| O **menu do cliente** depois de um "oi", de alguém da casa | ela **não** foi reconhecida: o número não está no cadastro do ERP nem é um destino ativo. Não é erro dela |
| *"Esse atendimento é você mesmo"* no lugar de um cartão | a pessoa chegou a um caminho que leva ao próprio WhatsApp dela. Antes o sistema mandava o próprio cartão |
| Na Recepção, a etiqueta azul **Equipe** ou **Representante** | é o mesmo reconhecimento que troca o menu |

**Quem é reconhecido, e por onde.** Primeiro o **cadastro do ERP** (papel equipe ou representante);
depois, como complemento, os **destinos ativos** da tela Destinos — porque o celular de trabalho de
quem atende não sempre está no cadastro. Hoje três dos seis destinos estão no ERP e três entram só
pelo complemento: **desativar alguém na tela Destinos devolve essa pessoa ao menu de cliente**, se o
número dela não estiver no ERP.

**O que isto NÃO faz:** não troca o atendimento de quem também é cliente (o menu do cliente está na
segunda opção); não manda a foto por você; não abre chamado no suporte; e **não é editável pela tela
Destinos** — o menu da casa tem duas opções fixas, e a tela continua administrando o do cliente.

**Pelo nome (#1036, 15/10/2026).** O menu da casa chama você pelo primeiro nome, lido do cadastro —
se ele estiver em caixa alta no ERP, sai como gente escreve ("Benedito", não "BENEDITO").

## A logo de um cliente, mandada pelo WhatsApp (#1036, 15/10/2026)

Quando um cliente te manda a logo dele para a arte personalizada, **mande o arquivo para o WhatsApp
da Renascer e ela não se perde mais**. A OlivIA confirma que recebeu, pergunta **de qual cliente é**
(o **código no ERP** — é por ele que o marketing liga a parceira; o nome não serve) e **o nome da
marca**, como deve aparecer na arte. Depois diz que guardou.

**O limite, e ele é o ponto:** a OlivIA **não autoriza nada**. Arte com a marca de um cliente só sai
com a **autorização de uso** registrada na tela **Parceiras** do marketing, com documento — e isso
não se faz por WhatsApp.

| O que você vê | O que quer dizer |
|---|---|
| Ela confirma a logo e **pergunta o código** | o arquivo chegou e está guardado. A pergunta é só para ligar ao cliente certo |
| *"a autorização de uso é na tela Parceiras"* | o limite acima. Guardar não é autorizar |
| *"Não achei um código aí"* | o que você respondeu não tinha números. Ela pergunta **uma vez** mais e depois guarda sem o cliente |
| *"Deixei a logo guardada sem o cliente"* | ninguém disse de quem era. **Está guardada, não perdida** — alguém completa depois |
| Nada acontece ao mandar um `.docx`, `.zip` ou similar | só **PDF, SVG, PNG e JPG** viram logo, porque são os quatro que a tela Parceiras aceita |

**O que este caminho NÃO faz:** não autoriza e não gera arte; não manda a logo a ninguém; **não lê o
PDF** nem gera a versão em branco da logo (isso é do gerador do marketing); e **ainda não faz a logo
aparecer na tela Parceiras** — puxá-la para lá é a etapa seguinte, em chamado próprio. Até ela
existir, a logo fica guardada aqui, esperando.
