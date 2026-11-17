# A OlivIA que conversa com quem é de fora — manual de uso

**Chamado:** #1520 · **Spec:** `C:\AxiaAtende\docs\specs\2026-11-14-a-olivia-anonima-fala.md`
· **Código:** `C:\AxiaAtende\backend\olivia.py`

## 1. Para que serve

Quem escreve ao WhatsApp da Renascer (49 3664 0121) e **não é da casa nem cliente da carteira** fala com
a OlivIA. Ela entende o que a pessoa quer, responde **na língua dela** (português ou espanhol), reconhece
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
   mensagem de mais de três palavras a fazem mudar de abordagem.
   Ela escreve **curto**: no máximo duas frases por mensagem, uma pergunta por vez. Quando a pessoa manda
   o currículo sem dizer a vaga, ela pergunta qual antes de encaminhar, e encaminha o arquivo que já veio.
6. **A conversa da vaga** (#1525), com a chave `olivia.conduz_vaga` ligada: quem chega pelo anúncio ou
   toca *Trabalhe conosco* fala com ela desde a primeira mensagem (o fluxo fixo vira reserva). Ela diz a
   vaga, pergunta se a pessoa tem currículo e, na vaga que aceita ficha, faz as cinco perguntas da **ficha
   de contato** depois do aviso de cadastro. Na vaga de currículo obrigatório, diz que o currículo é
   indispensável (pode ser foto) e oferece a vaga de ficha, se houver. Recebida a ficha ou o currículo,
   oferece uma vez a visita à empresa. Quem para no meio, ou nem começa, recebe **um** toque só, dentro das
   24 horas, **e só entre 6h e 21h** (#1543; dono, 17/11/2026): o toque que cairia de noite espera as 6h.
   Às 21h há uma **última chamada**: o toque cuja janela de 24 horas fecharia antes das 6h sai ali, para
   não se perder. Ele vai na língua em que a conversa correu e fala da vaga que a pessoa disse,
   mesmo que tenha sido na conversa anterior. **Na conversa de vaga ela não oferece o botão *Trabalhe
   conosco***: quem atende a vaga é ela; o que não sabe (as tarefas, pagamento), diz que a equipe explica
   no contato. O detalhe está no manual `trabalhe-conosco.md`, seção 6. Ela fala dos **benefícios** que o
   cadastro da vaga traz, nunca de valor, e, quando existir o arquivo da vaga em
   `C:\AxiaAtende\docs\olivia\funcoes\`, do que a função faz (`LEIAME.md` ali).
7. **Corrigir a base:** edite `C:\AxiaAtende\docs\olivia\base-da-empresa.md`. Cada afirmação traz a fonte
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
| **Frase recusada: promessa** | numa conversa de vaga, ela tentou dizer que anotou ou encaminhou antes de a ficha ou o currículo estar gravado; saiu no lugar a frase do que ainda falta, e contou no resumo |
| No resumo, **"N fichas incompletas"** | fichas que foram à Fran pela metade porque a pessoa parou de responder |
| No `/saude`, em `audio`: **"de_fora": true** e **"pendentes_de_fora"** | o áudio de quem é de fora está ligado, e quantos esperam a transcrição |
| Uma mensagem dela começando a conversa depois de um áudio, e na conversa **(áudio) …** | o que a pessoa falou, transcrito; é o texto a que ela respondeu |

## 5. O que NÃO faz

- **Não fala com quem é da casa nem com cliente da carteira** nem com o consultor do piloto: esses têm os
  caminhos deles, que vêm antes dela. Na conversa de vaga, ela vem **antes** do fluxo fixo só com a chave
  `olivia.conduz_vaga` ligada; desligada, a conversa de vaga é a dos textos fixos.
- **Não sabe nada de cliente, pedido, boleto, nota ou carga**, e não finge saber: encaminha pelo botão.
  Não tem nenhuma ferramenta que toque dado de cliente. Sempre tem cinco: ver as vagas, ler o arquivo
  desta mensagem, oferecer uma opção do menu, encaminhar o currículo, encerrar. Com a chave da vaga
  ligada, ganha, conforme o ponto da conversa: escolher a vaga, começar a ficha (o aviso), anotar a ficha
  e marcar a visita (#1525). Quem grava a ficha e a manda à Fran é o código, não a fala dela.
- **Não pergunta idade, estado civil, nacionalidade, filhos nem saúde**, não marca dia de visita e não
  manda mais de um toque por conversa.
- **Não promete prazo, valor, salário nem vaga**, e não escreve telefone, e-mail ou link.
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
