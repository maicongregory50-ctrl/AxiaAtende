# A resposta ao cooperante que responde a um aviso do contrato

> #1664 (19/11/2026). Spec: `C:\AxiaAtende\docs\specs\2026-11-19-resposta-padrao-ao-aviso-de-contrato.md`.

## Para que serve

O produtor cooperante que responde a um aviso automático do contrato (hoje, o termo de reprovação de
lote) recebe uma explicação curta de que aquilo foi um envio automático, e o contato de quem o atende.
Quem o atende é avisado na hora, com o que ele escreveu.

## Quem usa e quando

O contato legal dos contratos de multiplicação (hoje o dono, o destino "Maicon Gregory" da tela
Destinos), sempre que um produtor escreve ao número da empresa nos dias seguintes a um aviso.

## O caminho comum

1. O produtor responde ao aviso.
2. Ele recebe a mensagem padrão e o seu cartão. A mensagem é sempre a mesma, sem IA:
   *"Bom dia, Alfonso! Essa mensagem foi um envio automático do nosso sistema, que passou a informar os
   andamentos do seu contrato de multiplicação de sementes. Aos poucos todas as etapas vão chegar por
   aqui. Eu não tenho os detalhes do seu contrato; quem atende na empresa é o Maicon. Segue o contato
   dele."* A saudação segue a hora de Brasília (bom dia, boa tarde, boa noite) e o nome é o primeiro
   nome do produtor no termo.
3. Você recebe no WhatsApp: **"Cooperante respondeu ao aviso"**, com o nome, o aviso, o que ele
   escreveu (ou "mandou um áudio", "mandou uma foto", "mandou um documento") e o link para falar com ele.
4. Você responde a ele, pelo cartão ou pelo link.

## O que significa cada sinal

- **Mensagem de uma linha, "Resumo da OlivIA: cooperante respondeu ao aviso do contrato ..."**: você
  estava há mais de 24 horas sem escrever ao número da empresa; veio a forma curta, com o telefone
  escrito.
- **Mais de um aviso seguido do mesmo produtor**: ele continuou escrevendo; cada mensagem é repassada, e
  ele ouve "o Maicon já foi avisado da sua mensagem; o contato dele está logo acima". A mensagem padrão
  sai uma vez só por aviso; um aviso novo ao mesmo produtor a faz sair de novo.
- **Nenhum aviso, e o produtor te chamou**: a chave está desligada, ou o prazo de dias já passou e ele
  caiu no atendimento comum.
- **O produtor tocou em "Recebi e estou ciente"**: isso continua sendo a ciência do termo, como antes;
  não sai a mensagem padrão. Toque num botão do menu também segue o menu.

## O que isto NÃO faz

Não responde nada sobre o contrato, o lote ou a cobrança. Não reconhece o produtor que escreve sem ter
recebido um aviso recente. Não muda o termo.

**Cuidado com o ensaio no seu próprio número:** se um termo de teste for mandado ao seu WhatsApp, durante
o prazo (7 dias) toda mensagem sua ao número da empresa recebe a resposta padrão ou a linha curta, em vez
do caminho da equipe. Para encerrar antes, desligue a chave.

## Como ligar e desligar

Em PowerShell administrador, sem reinício:

```
cd C:\AxiaAtende; $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'; .\.venv\Scripts\python.exe scripts\cooperante.py ligar
```

Troque `ligar` por `desligar` ou `mostrar` (a chave, o prazo, o contato e o texto). O `/saude` do
recepcionista mostra `cooperante_resposta: ligada` ou `desligada`.

O prazo, o texto e o contato são ajustes no banco (`cooperante.dias`, `cooperante.texto`,
`cooperante.destino`, este o número do destino na tela Destinos). O texto usa `{saudacao}`, `{nome}` e
`{contato}`.
