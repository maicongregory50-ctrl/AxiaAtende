# A OlivIA que conversa com quem é de fora — manual de uso

**Chamado:** #1520 · **Spec:** `C:\AxiaAtende\docs\specs\2026-11-14-a-olivia-anonima-fala.md`
· **O cliente da carteira no boletim:** #1754, `C:\AxiaAtende\docs\specs\2026-11-24-olivia-atende-a-carteira-no-boletim.md`
· **Código:** `C:\AxiaAtende\backend\olivia.py`

## 1. Para que serve

Quem escreve ao WhatsApp da Renascer (49 3664 0121) e **não é da casa nem cliente da carteira** fala com
a OlivIA. O cliente da carteira fala com ela **só na conversa do boletim** (#1754, item 8 do caminho
comum): quando toca *Quero saber mais* ou responde em até 7 dias. Ela entende o que a pessoa quer, responde **na língua dela** (português ou espanhol), reconhece
o que ela mandou (um currículo em PDF ou em **foto**, um comprovante) e a leva ao lugar certo: o botão do
setor, a vaga, a Fran. Ela fala da empresa **só o que está na base da empresa**
(`C:\AxiaAtende\docs\olivia\base-da-empresa.md`); o que não estiver lá, ela encaminha.

É o primeiro degrau da atendente que o dono descreveu. O cliente reconhecido pelo número e o cliente
autenticado são os próximos degraus, em chamados próprios.

## 2. Quem usa e quando

- **Qualquer pessoa de fora**, a qualquer hora: candidato a vaga, quem quer comprar, fornecedor, curioso.
- **O dono** escreve e corrige a base da empresa, e recebe o resumo do vigia nos dias em que há o que ver.
- **A Fran** recebe os currículos, agora também em foto (manual `trabalhe-conosco.md`).
- **Quem olha a Recepção** vê onde ela falou e quais conversas ficaram sem saída.
- **O cliente da carteira** (o contato comprador ou o técnico), nos 7 dias seguintes a um boletim com o
  botão *Quero saber mais* (#1754).
- **O representante** que cuida do cliente, que recebe no WhatsApp a ficha de interesse.

## 3. O caminho comum

1. A pessoa escreve (*"estão precisando pra trabalhar?"*, *"¡Hola! quiero más información"*) ou manda
   uma foto do currículo.
2. A OlivIA responde em uma a três frases, pergunta o que falta, ou oferece os **botões** do menu quando
   o assunto é de um setor (financeiro, frete, comprar, fornecedor). O contato de quem atende sai **sempre
   pelo botão**, da tela Destinos — nunca escrito por ela.
3. Currículo (PDF ou foto): ela confere o que é, encaminha à Fran (para a vaga que a pessoa disse, ou ao
   banco de currículos) e diz que a equipe vai analisar, sem prometer retorno nem prazo. A foto vai **sem
   pré-triagem**: a Fran olha.
4. **Áudio** (etapa B, D10, 16/11/2026), com a chave `audio.de_fora` ligada: a pessoa fala, e nada chega
   na hora; o áudio é transcrito **aqui no servidor** (o som não sai da máquina, em português ou espanhol)
   e a OlivIA responde ao que a pessoa falou, alguns segundos depois. Se não deu para ouvir (áudio ruim,
   longo demais, mudo), ela diz que não conseguiu ouvir e pede para escrever ou mandar de novo. O áudio
   da equipe passa na frente na fila, e cada número tem um teto de 6 áudios em 24 h; acima disso, ou com
   a chave desligada, vale a linha fixa de quem não lê áudio.
5. Se a conversa **travar**, ela muda de abordagem. Se a pessoa **repetir a mensagem ou disser *"não é
   isso"*** de novo depois disso, ela manda o **menu** e para de falar naquela conversa: dali em diante, é o
   menu de sempre. Cinco respostas dela sem a conversa andar (sem toque, currículo ou opção escolhida) só a
   fazem mudar de abordagem, **nunca** mandam o menu (dono, 16/11/2026: o candidato que ia mandar o
   currículo à noite recebeu o menu no meio de uma conversa boa). **Na conversa de vaga** (#1543,
   17/11/2026) a contagem de respostas não vale, e um segundo "Sim" ou "Ok" não conta como mensagem
   repetida: ali perguntar e ouvir resposta é a conversa andando. Só *"não é isso"* e a repetição de uma
   mensagem de mais de três palavras a fazem mudar de abordagem. **Na conversa de quem quer comprar**
   (#1784, 24/11/2026), com a chave da venda ligada, vale o mesmo: responder por texto é a conversa
   andando, e um segundo "Sim" não manda o menu.
   Ela escreve **curto**: no máximo duas frases por mensagem, uma pergunta por vez. Quando a pessoa manda
   o currículo sem dizer a vaga, ela pergunta qual antes de encaminhar, e encaminha o arquivo que já veio.
6. **A conversa da vaga** (#1525), com a chave `olivia.conduz_vaga` ligada: quem chega pelo anúncio ou
   toca *Trabalhe conosco* fala com ela desde a primeira mensagem (o fluxo fixo vira reserva). Ela diz a
   vaga, pergunta se a pessoa tem currículo e, na vaga que aceita ficha, faz as cinco perguntas da **ficha
   de contato** depois do aviso de cadastro. Na vaga de currículo obrigatório, diz que o currículo é
   indispensável (pode ser foto) e oferece a vaga de ficha, se houver. Recebida a ficha ou o currículo,
   oferece uma vez a visita à empresa. Quem para no meio, ou nem começa, recebe **um** toque só, dentro das
   24 horas, **e só à noite, às 20h** (#1543; dono, 17/11/2026: de dia a pessoa está no trabalho). Às 20h
   sai o toque de quem está há duas horas ou mais sem escrever. Entre 18h e 20h só sai o de quem a janela
   de 24 horas fecharia antes das 20h (quem escreveu entre 18h e 20h da véspera). Depois das 21h e durante
   o dia nada sai: o toque espera a noite seguinte. Ele vai na língua em que a conversa correu e fala da vaga que a pessoa disse,
   mesmo que tenha sido na conversa anterior. **Na conversa de vaga ela não oferece o botão *Trabalhe
   conosco***: quem atende a vaga é ela; o que não sabe (as tarefas, pagamento), diz que a equipe explica
   no contato. O detalhe está no manual `trabalhe-conosco.md`, seção 6. Ela fala dos **benefícios** que o
   cadastro da vaga traz, nunca de valor, e, quando existir o arquivo da vaga em
   `C:\AxiaAtende\docs\olivia\funcoes\`, do que a função faz (`LEIAME.md` ali).
   **A conversa de quem quer comprar** (#1589), com a chave `olivia.conduz_venda` ligada: ela só
   **recebe e direciona** (dono, 18/11/2026). Diz "temos" ou "não temos" (seção *Temos e não temos* da
   base), sem descrever o produto, e oferece indicar o representante da região. Pergunta com quem fala
   quando o nome não aparece no perfil. Aceita a indicação, pergunta **só o que falta** para escolher quem
   atende: se é produtor, revenda ou corretor, e o estado. Não pergunta cidade nem quantidade. Então
   **apresenta quem atende pelo nome** e o cartão sai logo depois, sem o botão "Sim". Pergunta técnica ela
   responde no básico, pela base, só se a pessoa perguntar; se a conversa aprofunda, diz que o
   representante sabe mais e o indica. Em dúvida, manda os botões de sempre. Não fala de preço, estoque
   nem prazo e não diz que vai fazer cotação. Fora do piloto abaixo, não avisa o representante: quem chama
   é a pessoa, pelo cartão. **O cartão nunca sai sem apresentação** (#1660): se ela não disser a frase, o
   sistema manda "Na sua região quem atende é o nosso consultor Fulano. Segue o contato dele." antes do
   cartão. Desligada a chave, quem quer comprar recebe os botões do Comercial, como antes. Liga e desliga
   sem restart: `scripts\olivia.py ligar-venda` e `desligar-venda`.
   **O piloto do produtor rural** (#1660), com a chave `olivia.qualifica_produtor` ligada (só vale com a
   da venda): para o **produtor rural de SC e do RS**, ela faz quatro perguntas rápidas **antes** do
   cartão, e **quem atende a região recebe no próprio WhatsApp a ficha da conversa**. Revenda, corretor e
   produtor de outro estado seguem como acima.
   - **Para que serve.** O consultor atende sabendo do que o produtor precisa, em vez de receber um
     contato vazio.
   - **Quem usa e quando.** O consultor da região (no piloto, o dono), toda vez que a OlivIA fecha uma
     conversa com um produtor desses estados. Não há tela: tudo chega no WhatsApp.
   - **O caminho comum.**
     1. Ela pede licença ("posso te fazer quatro perguntas rápidas?") e pergunta, uma por mensagem, só o
        que ainda não foi dito: qual semente e para quê; a área ou a quantidade; quando planta; o município.
     2. Chega no seu WhatsApp, do número da empresa, a mensagem **"Lead da OlivIA"** com o nome do produtor,
        o que ele procura e para quê, a área ou a quantidade, quando planta, o município, duas linhas de
        resumo e o link para conversar com ele.
     3. Ela diz ao produtor que você está recebendo o resumo, e o seu cartão sai logo depois. Ele pode te
        chamar antes de você chamar.
     4. Toque no link e atenda. Depois, conte na sessão como foi (um print serve): é com isso que as
        próximas etapas são desenhadas.
   - **Quem recebe** a ficha e o cartão é o destino da folha *Comercial › Produtor rural › SC* (ou *RS*) na
     tela **Destinos**. Trocar o destino ali troca quem recebe a ficha.
8. **O cliente da carteira no boletim** (#1754), com a chave `olivia.atende_carteira` ligada.
   - **Para que serve.** Fazer do boletim uma conversa: quem recebe e quer saber mais é atendido na hora,
     pelo nome, recebe o material completo, e quem cuida dele fica sabendo quem se interessou e por quê.
   - **O caminho comum.**
     1. O cliente toca *Quero saber mais* no boletim (ou escreve em resposta, em até 7 dias).
     2. Quem tocou recebe, do sistema e sem fala dela, o cumprimento pelo nome, as imagens do material
        completo e o **texto da parceria**, como o dono o aprovou
        (`C:\AxiaAtende\docs\olivia\parceria-da-carteira.md`). Quem escreveu é recebido por ela, que
        oferece o material.
     3. Ele conversa com a OlivIA. Se disser em que culturas tem interesse, ela anota **qualquer cultura da
        linha da Renascer**, não só as do boletim. O que ele pedir fora da linha (soja, por exemplo) também
        vai, com as palavras dele. **Ela nunca diz que não pode anotar** (emenda de 25/11/2026). A lista da
        linha se vê e se troca, sem reiniciar, com
        `C:\AxiaAtende\.venv\Scripts\python.exe C:\AxiaAtende\scripts\olivia.py linha` (para trocar:
        `linha "Aveia preta;Centeio;..."`).
     4. **Quem cuida do cliente recebe a ficha** no WhatsApp, do número da empresa: *"Interesse no boletim"*,
        com o cliente, quem falou (comprador ou técnico), as culturas, o que ele escreveu e o link para
        conversar. Cada cultura vem marcada **(do boletim)** ou **(fora do boletim)**, e o pedido fora da
        linha vem entre aspas, **(fora da linha)**. Se o cliente indicar mais coisa depois, chega outra
        ficha, **atualizada**. É o responsável **da linha do envio**, o mesmo que já recebe o resumo do lote.
     5. O interesse aparece no **Relacionamento** do cliente, no ERP: *"Quis saber mais. Interesse: …"*.
   - **O que ela sabe dele:** o primeiro nome, o nome do cadastro, se é o comprador ou o técnico, quem cuida
     dele, as culturas que o boletim destaca e a lista da linha. Não sabe faturamento, pedidos nem histórico.
   - **O que ela faz:** manda o material completo, anota o interesse, passa o contato de quem cuida dele
     (quem pede uma pessoa recebe na hora), oferece as opções do cliente (boleto, carga, qualidade, falar
     com a empresa) e encerra.
   - Ela se apresenta pelo nome e não diz por conta própria que é uma inteligência artificial; **se
     perguntarem, responde na mesma mensagem** que é a OlivIA, assistente virtual da Renascer.
9. **Corrigir a base:** edite `C:\AxiaAtende\docs\olivia\base-da-empresa.md`. Cada afirmação traz a fonte
   e a data entre colchetes (a OlivIA não as repete à pessoa). A OlivIA relê o arquivo sozinha quando
   ele muda: **não precisa reiniciar nada**. O inventário das fontes, com o que entrou e por quê, está em
   `C:\AxiaAtende\docs\olivia\FONTES.md`.

## 4. O que significa cada sinal

| Sinal | Quer dizer |
|---|---|
| Na Recepção, a etiqueta **OlivIA falou** | a OlivIA conversou com essa pessoa com texto próprio |
| **OlivIA falou · sem saída** (etiqueta vermelha) e o cartão **OlivIA · sem saída** | o vigia das 23:40 viu que a conversa não terminou em currículo, opção do menu escolhida ou despedida. Vale ler a conversa |
| Filtros **OlivIA falou** e **OlivIA · sem saída** (Situação) | mostram só essas conversas |
| No seu WhatsApp, **"Resumo da OlivIA: Hoje a OlivIA falou em N conversas…"** | chega **só** nos dias em que houve conversa sem saída ou frase recusada, com o número de cada conversa (#…). **Dia sem resumo é dia limpo**, não "ninguém olhou" |
| **Frase recusada** | ela tentou dizer algo com número de 5 dígitos ou mais, valor, link, e-mail, ou as palavras *salário, remuneração, contrato, prazo de resposta*. O sistema mandou no lugar *"Me conte em uma linha o que você precisa…"* e contou no resumo |
| Na tela **Custos**, **OlivIA · conversa com quem é de fora** (Claude Sonnet 5.5) e **OlivIA · leitura do arquivo recebido** (Haiku) | o custo dela, por chamada, desde a primeira conversa |
| No `/saude` do recepcionista (`http://127.0.0.1:8008/saude`), **"olivia": "ligada"** | a voz dela está ligada no servidor |
| No `/saude`, **"olivia_vaga": "ligada"** | ela conduz a conversa de vaga (#1525) |
| No `/saude`, **"olivia_venda": "ligada"** | ela conduz a conversa de quem quer comprar (#1589) |
| No `/saude`, **"olivia_qualifica": "ligada"** | o piloto do produtor rural está valendo (#1660): a chave ligada **e** a venda ligada |
| Na ficha, **"Ficha incompleta: faltou …"** | o produtor teve pressa ou não quis responder; o cartão saiu assim mesmo |
| Na ficha, **"não disse"** ao lado de uma pergunta | ela não perguntou de novo, de propósito |
| Mensagem de uma linha começando com **"Resumo da OlivIA: Lead produtor rural …"** | você estava há mais de 24 horas sem escrever ao número da empresa, e a ficha veio pelo modelo curto, com o telefone escrito em vez do link. Escrever qualquer coisa ao número reabre a forma completa para as próximas |
| **Nenhuma ficha**, e o produtor te chamou pelo cartão | o envio falhou. Ele **não** ouviu que você tinha sido avisado; a falha conta no resumo do vigia ("leads do produtor: … sem envio") |
| **Frase recusada: aviso sem ficha** | ela tentou dizer que o consultor foi avisado ou está recebendo o resumo sem a ficha ter saído; saiu no lugar a apresentação simples, e contou no resumo |
| No resumo, **"leads do produtor: N completos, N incompletos, N sem envio"** | as fichas do dia (#1660); o resumo também chega quando alguma não saiu |
| Na conversa de compra, **o cartão de quem atende sem o botão "Sim" antes** | ela tinha certeza da categoria (produtor, revenda, corretor) e do estado. **Os botões** em vez do cartão: ficou em dúvida, ou a chave está desligada |
| Na tela **Envios**, a resposta **"quis saber mais"** | o cliente tocou *Quero saber mais*, ou escreveu em até 7 dias de um boletim com o botão (#1754). Com interesse anotado, as culturas aparecem ao lado |
| **"quis saber mais · sem indicação"** | entrou na conversa e não indicou cultura. **Não é "sem interesse"**: é sem indicação |
| **Frase recusada: disse que nao anota** | na conversa do boletim, ela tentou dizer que não podia anotar. O sistema anotou o que o cliente escreveu, mandou a ficha e disse a ele *"Anotei o seu pedido e passei a …"* |
| No seu WhatsApp, **"Interesse no boletim (conversa com a OlivIA)"** | a ficha de um cliente seu. Fora das 24 h de você ter escrito ao número da empresa, ela vem numa linha só (*"Resumo da OlivIA: Interesse no boletim: …"*), com o telefone escrito |
| No Relacionamento do ERP, **"Quis saber mais"** sem culturas | o cliente entrou na conversa e não indicou nenhuma. Enquanto a conversa corre, a linha mostra **tocou**; o texto com o interesse chega quando a ficha sai, a conversa fecha ou passam 24 h do toque |
| No resumo do vigia, **"carteira: N conversas, N com interesse, N fichas com erro"** | as conversas do boletim no dia (#1754). **Ficha com erro**: quem cuida do cliente não recebeu, e a OlivIA não disse ao cliente que ele foi avisado |
| No `/saude`, **"olivia_carteira"** | `chave` (ligada ou desligada), `parceria_aprovada` e `atende`: ela só atende a carteira com as duas |
| **Frase recusada: promessa** | numa conversa de vaga, ela tentou dizer que anotou ou encaminhou antes de a ficha ou o currículo estar gravado; saiu no lugar a frase do que ainda falta, e contou no resumo |
| No resumo, **"N fichas incompletas"** | fichas que foram à Fran pela metade porque a pessoa parou de responder |
| No `/saude`, em `audio`: **"de_fora": true** e **"pendentes_de_fora"** | o áudio de quem é de fora está ligado, e quantos esperam a transcrição |
| Uma mensagem dela começando a conversa depois de um áudio, e na conversa **(áudio) …** | o que a pessoa falou, transcrito; é o texto a que ela respondeu |

## 5. O que NÃO faz

- **Não fala com quem é da casa** nem com o consultor do piloto, e **não atende o cliente da carteira
  fora dos 7 dias de um boletim com *Quero saber mais***: aí vale o contato do representante, como antes
  (#1189). Esses têm os caminhos deles, que vêm antes dela. Na conversa de vaga, ela vem **antes** do fluxo fixo só com a chave
  `olivia.conduz_vaga` ligada; desligada, a conversa de vaga é a dos textos fixos.
- **Não sabe nada de cliente, pedido, boleto, nota ou carga**, e não finge saber: encaminha pelo botão.
  Não tem nenhuma ferramenta que toque dado de cliente. Sempre tem cinco: ver as vagas, ler o arquivo
  desta mensagem, oferecer uma opção do menu, encaminhar o currículo, encerrar. Com a chave da vaga
  ligada, ganha, conforme o ponto da conversa: escolher a vaga, começar a ficha (o aviso), anotar a ficha
  e marcar a visita (#1525). Quem grava a ficha e a manda à Fran é o código, não a fala dela.
- **Não pergunta idade, estado civil, nacionalidade, filhos nem saúde**, não marca dia de visita e não
  manda mais de um toque por conversa.
- **Não promete prazo, valor, salário nem vaga**, e não escreve telefone, e-mail ou link.
- **Na conversa de compra não negocia**: não diz preço, dose, época de plantio nem estoque, não recomenda
  produto para a área da pessoa. Fora do piloto do produtor rural de SC e RS (#1660), não guarda ficha de
  quem quer comprar e não avisa o representante. No piloto, não classifica o produtor, não agenda nada, não
  avisa outro representante além do destino da folha, e quem manda a ficha é o código, não a fala dela. A
  ficha é apagada com 12 meses.
- **Com o cliente da carteira** (#1754), não fala de preço, quantidade nem prazo, não reserva estoque, não
  conhece o histórico do cliente e não substitui o representante. Quem grava o interesse e manda a ficha é
  o código, não a fala dela; a ficha sai **uma vez por conversa**.
- **Não faz pré-triagem de currículo em foto**: a Fran olha.
- **Não responde figurinha nem localização**, e o **áudio só com a chave `audio.de_fora` ligada**; fora
  disso, a linha curta de sempre. **Não responde em áudio.**
- **Não lê o catálogo do ERP** nem números de produto (dose, janela, massa): esses ficam fora da base até
  o #857 reconciliar a base técnica.

## 6. Como desligar (e religar)

A voz dela é uma chave no servidor, no arquivo `C:\AxiaAtende\.env.recepcionista`, em janela elevada:

```
OLIVIA_FALA=false
```

e depois, no PowerShell elevado:

```
Restart-Service axiaatende-recepcionista
```

Desligada, tudo volta ao menu de hoje, na hora, e nada se perde. A foto como currículo e a base continuam,
porque não dependem dela. Para religar, `OLIVIA_FALA=true` e o mesmo restart. Conferir em
`http://127.0.0.1:8008/saude`: `"olivia": "ligada"` ou `"desligada"`.

**O áudio de fora** tem chave própria, que liga e desliga **sem restart** (janela elevada, em produção):

```
cd C:\AxiaAtende
$env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
.\.venv\Scripts\python.exe scripts\audio.py ligar-fora
```

`desligar-fora` volta à linha fixa na hora; `ver` mostra as três chaves (a transcrição, o áudio de fora e
o teto por número). Ele só vale com `OLIVIA_FALA=true` e a transcrição ligada.

**A conversa da vaga** (#1525) tem chave própria, `olivia.conduz_vaga`, que nasce desligada e liga e
desliga **sem restart** (janela elevada, em produção):

```
cd C:\AxiaAtende
$env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
.\.venv\Scripts\python.exe scripts\olivia.py ligar-vaga
```

`desligar-vaga` volta ao fluxo fixo na hora (a ficha que já tinha nome ainda vai à Fran); `mostrar` diz a
chave, os dois tempos (o toque às 2 h, a parcial 4 h depois do toque) e os textos ainda provisórios.
**`ligar-vaga` recusa** enquanto algum texto de cadastro da ficha tiver a marca `[TEXTO DO DONO]`. Conferir
em `http://127.0.0.1:8008/saude`: `"olivia_vaga": "ligada"`. Ela só vale com `OLIVIA_FALA=true`.

**O piloto do produtor rural** (#1660) tem chave própria, `olivia.qualifica_produtor`, que nasce desligada
e liga e desliga **sem restart**. **Antes de ligar**, confira na tela **Destinos** quem recebe *Comercial ›
Produtor rural › SC* e *› RS*: a ficha vai a essa pessoa. Em janela elevada, em produção:

```
cd C:\AxiaAtende
$env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
.\.venv\Scripts\python.exe scripts\olivia.py ligar-qualifica
```

`desligar-qualifica` volta, na hora, ao "recebe e direciona" (as fichas já guardadas ficam). **`ligar-qualifica`
recusa** com a venda desligada. `mostrar` diz a chave, os estados do piloto e quem recebe cada folha.
Conferir em `http://127.0.0.1:8008/saude`: `"olivia_qualifica": "ligada"`. **Quem recebe a ficha precisa
escrever ao número da empresa** de vez em quando: dentro das 24 h a ficha chega completa, com o link; fora
delas, numa linha só.

**O cliente da carteira no boletim** (#1754) tem chave própria, `olivia.atende_carteira`, que nasce
desligada e **só o dono liga**, quando o boletim com *Quero saber mais* for sair. **Antes de ligar:** o
modelo `boletim_quero_saber_mais` aprovado na Meta e o texto da parceria com **Situação: APROVADO** em
`C:\AxiaAtende\docs\olivia\parceria-da-carteira.md`. Em janela elevada, em produção:

```
cd C:\AxiaAtende
$env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
.\.venv\Scripts\python.exe scripts\olivia.py ligar-carteira
```

`desligar-carteira` volta na hora, sem restart: o toque em *Quero saber mais* passa a responder com a linha
do representante (como o *Falar com meu atendimento*), e o texto volta ao portão do cliente. Conversas já
abertas com ela terminam pelo caminho de sempre. **`ligar-carteira` recusa** enquanto o texto da parceria não
estiver APROVADO; e mesmo com a chave ligada, sem o texto aprovado ela não atende. `mostrar` diz a chave e a
situação do texto. Conferir em `http://127.0.0.1:8008/saude`: `"olivia_carteira"`. Só vale com
`OLIVIA_FALA=true`.
