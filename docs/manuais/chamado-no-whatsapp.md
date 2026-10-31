# O chamado no WhatsApp

**Desde:** novembro de 2026 · **Chamado:** #1222 · **Onde:** o WhatsApp da Sementes Renascer (e a tela
Envios, para quem acompanha)

## 1. Para que serve

O chamado conversa com você pelo WhatsApp. O que chega na caixa do sistema chega também no celular, e o
que você responde no celular entra no chamado, como se você tivesse escrito no sistema.

## 2. Quem usa e quando

Quem abre chamado no sistema: Benedito, Fran, Alisson e o resto da equipe. Toda vez que o chamado anda:
quando ele vira decisão, quando o trabalho começa, quando fica pronto, ou quando precisamos perguntar
alguma coisa a você.

## 3. O caminho comum

1. Chega uma mensagem do número da Sementes Renascer com o título em negrito no alto, por exemplo
   **Chamado 1217 · Trocar unidade do pedido**.
2. Se ela termina com *"Só aviso, não precisa responder"*, não precisa fazer nada.
3. Se é **uma pergunta**, ela termina com *"Para responder, deslize esta mensagem para o lado"*.
   Deslize (é o **Responder** do WhatsApp) e escreva. Volta **"Anotado no chamado 1217. ✓"**.
4. Se é **a entrega** ("já está no ar"), teste e toque:
   - **Ficou bom**: o chamado fecha, em seu nome;
   - **Não ficou bom**: escreva em uma linha o que falta. O chamado volta para ajuste.
5. Se você escrever **sem deslizar** e tiver pergunta ou entrega esperando, a OlivIA pergunta
   *"É sobre o Chamado 1217 · ...?"*:
   - **Sim**: entra no chamado;
   - **Outro chamado**: aparece a lista dos seus chamados que esperam resposta;
   - **Outro assunto**: segue o atendimento de sempre (o menu da casa, a foto do campo).

## 4. O que significa cada sinal

- **"Você tem 1 aviso da Sementes Renascer. Toque em Ver."** Você não escreve para a empresa há mais de
  24 horas e tem uma pergunta ou uma entrega esperando. Toque em **Ver** e ela aparece.
- **"Anotado no chamado N. ✓"**: a sua resposta entrou no chamado.
- **"Anotado. Esta mensagem é só um aviso…"**: você respondeu a um aviso. Nada foi anotado; para falar
  do chamado, use o sistema ou espere a próxima pergunta. Essa linha vem uma vez só por chamado.
- **Vários chamados numa mensagem só**, separados por um traço: o sistema junta o que chega para você
  em poucos minutos, para não mandar uma mensagem atrás da outra.
- **"Esta entrega já foi respondida. ✓"**: você (ou alguém pela caixa do sistema) já tinha respondido.
- **Sem o "Bom dia" de volta.** Se você escreve "Bom dia" e havia mensagem esperando, chegam só as
  mensagens, sem o menu da casa.

Na tela **Envios**, a tabela *Chamados no WhatsApp* mostra cada mensagem: → o que saiu, ← o que voltou.
"esperando" é o que ainda não saiu (a pessoa não escreveu, ou a junção dos minutos); "esperando o Ver"
é o que espera o toque na reabertura; "no chamado" é a resposta que já entrou no ERP; "erro" diz por
quê (por exemplo, o número não é o de quem abriu o chamado).

## 5. O que esta função NÃO faz

- Não abre chamado novo pelo WhatsApp: para isso, continue usando o sistema.
- Não lê áudio, foto ou arquivo como resposta de chamado: só texto e os botões.
- Não manda aviso fora de hora por conta própria: o que é só aviso espera você escrever para a empresa.
- Não manda o detalhe técnico: só a parte do comentário escrita para quem pediu.

## 6. Pré-requisito de cadastro

O seu usuário no AxiaGestão precisa ter o **WhatsApp** preenchido (Cadastros → Mapa de Atividades →
o usuário → WhatsApp). Sem ele, nada sai, e tudo continua só na caixa do sistema.

## 7. Para quem cuida

- A chave `pendencias.ligado` (em `atendimento.ajustes`) liga e desliga tudo. Desligada, nada sai e
  nenhuma resposta é tomada; o atendimento volta a ser o de antes.
- `pendencias.juntar_minutos` (10) é quanto tempo a junção espera a rajada acabar.
- A volta das telas traz do ERP a cada minuto e leva as respostas; o recepcionista manda e lê.
- Resposta que o ERP recusa fica com o erro na tela Envios; não é tentada de novo.
