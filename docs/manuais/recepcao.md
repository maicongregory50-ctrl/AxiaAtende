# Recepção — manual de uso

> A tela que mostra quem chamou a Renascer no WhatsApp (49 3664 0121), o que a pessoa procurava e para
> quem ela foi mandada. No AxiaAtende: **http://127.0.0.1:8009**, aba **Recepção** (#950, 09/10/2026).
> Spec: `C:\AxiaMarketing\docs\specs\2026-10-09-axiaatende-recepcionista-e-envio.md`.

## 1. Para que serve

A OlivIA atende quem chama no WhatsApp da empresa: mostra o menu (tudo por botão), descobre o
assunto e manda o link do WhatsApp de quem resolve. Esta tela mostra o que aconteceu com cada
pessoa: se chegou ao link, se parou no meio e, quatro horas e meia depois, se disse que foi atendida.
É onde você vê se alguém ficou sem resposta e em que ponto as pessoas desistem.

## 2. Quem usa e quando

Você, no computador, quando quiser acompanhar o atendimento — por exemplo, uma vez por dia.

## 3. O caminho comum

1. Abra **Recepção**.
2. Escolha o período (hoje e ontem, 7 ou 30 dias) e, se quiser, o motivo (Comercial, Fretes…) e a
   situação.
3. Leia os cartões.
4. Na lista, olhe primeiro as linhas **"parou no meio"** e **"Não · você foi avisado"**.

## 4. O que significa cada sinal

| Sinal | Quer dizer |
|---|---|
| **Chegaram** | quantas conversas começaram no período |
| **Receberam o link** | chegaram ao fim do menu e receberam o WhatsApp de quem atende |
| **Pararam no meio** | começaram a escolher e ficaram 30 minutos sem tocar em nada, sem chegar ao link |
| **Disseram que foram atendidos / que não** | a resposta à pergunta "recebeu o atendimento?", que vai 4h30 depois do link |
| **IA acertou / errou** | quem escreveu em vez de tocar recebeu a proposta da IA ("Entendi que você quer… É isso?"): **Sim** é acerto, **Ver todas as opções** é erro |
| **Quem: "5475 · Agro Real…"** | a pessoa é cliente conhecido (está num envio) |
| **Quem: "+55 49 9…·7310"** | não é cliente conhecido; o número aparece com o meio escondido |
| **Caminho** | o que a pessoa tocou, na ordem ("Comercial › Produtor rural › PR › Cascavel") |
| **"— só chegou"** | mandou mensagem e ainda não escolheu nada |
| **Mandado para** | quem recebeu a pessoa pelo link (a tela Destinos diz quem é quem) |
| **"pergunta às 18:34"** | a pergunta "recebeu o atendimento?" ainda vai sair, nesse horário |
| **"perguntado, sem resposta"** | a pergunta saiu e a pessoa não respondeu |
| **"Não · você foi avisado 15:41"** | a pessoa disse que não foi atendida; você recebeu um aviso no WhatsApp nesse horário |
| **"—"** | ainda não aconteceu (não é zero) |

## 5. O que a tela NÃO faz

- **Não mostra a conversa** da pessoa com o atendente: ela acontece no WhatsApp de quem recebeu o link.
- **Não responde ninguém** pela tela.
- **Não muda o menu nem para quem cada motivo vai:** isso é a tela **Destinos**.
- **Enquanto o atendimento não for trocado do Opa para o AxiaAtende** (o dia da troca, Fase H do
  plano), a tela fica vazia: o AxiaAtende só escuta e não responde.
