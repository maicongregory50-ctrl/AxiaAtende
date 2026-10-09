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

## 4. O que significa cada sinal

| Sinal | Quer dizer |
|---|---|
| **Chegaram** | quantas conversas começaram no período |
| **Receberam o link** | chegaram ao fim do menu e receberam o WhatsApp de quem atende |
| **Pararam no meio** | começaram a escolher e ficaram 30 minutos sem tocar em nada, sem chegar ao link |
| **Disseram que foram atendidos / que não** | a resposta à pergunta "recebeu o atendimento?", que vai 4h30 depois do link |
| **IA acertou / errou** | quem escreveu em vez de tocar recebeu a proposta da IA ("Entendi que você quer… É isso?"): **Sim** é acerto, **Ver todas as opções** é erro |
| **Do nosso cadastro** | quantos dos que chegaram no período estão no cadastro do ERP |
| **Quem: "Agro Real Insumos · 5475"** e as etiquetas | o número está no cadastro: o nome e o código dele. As etiquetas verdes (Cliente, Fornecedor, Produtor) e azuis (Equipe, Representante) dizem o papel; "contato comercial: João" diz de qual contato do cadastro o número veio |
| **"fora do cadastro"** | o número não está em nenhum cadastro. Pode ser um contato novo, ou alguém da casa cujo celular não foi cadastrado; aparece o número com o meio escondido e o nome do perfil do WhatsApp |
| **"número em 2 cadastros"** | o mesmo celular está em mais de um cadastro; o sistema não escolhe. Vale conferir o cadastro no ERP |
| **Quem só com o número, sem etiqueta** | a conversa chegou antes de o cadastro ser lido pela primeira vez |
| **"Cadastro lido em 09/10 06:00 (884 números)"** | o cadastro é lido uma vez por dia, às 06:00: quem foi cadastrado hoje é reconhecido amanhã. Se a leitura falhar, a frase diz o motivo e fica valendo a do dia anterior |
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
- **Não corrige o cadastro:** número faltando ou repetido se corrige no ERP.
- **Não reconhece de novo conversas antigas:** cada conversa guarda quem era no momento em que chegou.
- **Não mostra valor, crédito nem documento** de ninguém.
