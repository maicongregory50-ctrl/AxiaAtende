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
4. Se a conversa **travar** (a pessoa repete a mensagem, diz *"não é isso"*, ou ela falou três vezes sem
   a conversa andar), ela muda de abordagem; se travar de novo, manda o **menu** e para de falar naquela
   conversa: dali em diante, é o menu de sempre.
5. **Corrigir a base:** edite `C:\AxiaAtende\docs\olivia\base-da-empresa.md`. Cada afirmação traz a fonte
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

## 5. O que NÃO faz

- **Não fala com quem é da casa nem com cliente da carteira** nem com o consultor do piloto: esses têm os
  caminhos deles, que vêm antes dela.
- **Não sabe nada de cliente, pedido, boleto, nota ou carga**, e não finge saber: encaminha pelo botão.
  Não tem nenhuma ferramenta que toque dado de cliente — são cinco, e só elas: ver as vagas, ler o arquivo
  desta mensagem, oferecer uma opção do menu, encaminhar o currículo, encerrar.
- **Não promete prazo, valor, salário nem vaga**, e não escreve telefone, e-mail ou link.
- **Não faz pré-triagem de currículo em foto**: a Fran olha.
- **Não responde áudio, figurinha ou localização de quem é de fora**: esses continuam com a linha curta
  de sempre.
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
