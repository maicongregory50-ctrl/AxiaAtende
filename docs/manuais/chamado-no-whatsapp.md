# O chamado no WhatsApp

**Desde:** novembro de 2026 · **Chamado:** #1222 · **Onde:** o WhatsApp da Sementes Renascer (e a tela
Envios, para quem acompanha)

## 1. Para que serve

O chamado conversa com você pelo WhatsApp. O que chega na caixa do sistema chega também no celular, e o
que você responde no celular entra no chamado, como se você tivesse escrito no sistema.

## 2. Quem usa e quando

Quem abre chamado no sistema: Benedito, Fran, Alisson e o resto da equipe. **Só quando o chamado pede
alguma coisa de você ou termina** (dono, 05/11/2026, #1269): quando precisamos de uma resposta sua (a
pergunta que o dono decidiu fazer), quando alguém da equipe escreve direto a você, e no fim — a entrega,
que diz como usar e pede o teste, ou a recusa. O andamento (virou decisão, o trabalho começou, o plano
foi gravado) fica no chamado, no sistema, e não vem ao celular.

## 3. O caminho comum

1. Chega uma mensagem do número da Sementes Renascer com o título em negrito no alto, por exemplo
   **Chamado 1217 · Trocar unidade do pedido**.
2. Se ela termina com *"Só aviso, não precisa responder"*, não precisa fazer nada.
3. Se é **uma pergunta**, ela termina com *"Para responder, deslize esta mensagem para o lado"*.
   Deslize (é o **Responder** do WhatsApp) e escreva. Volta **"Anotado no chamado 1217. ✓"**.
4. Se é **a entrega** ("já está no ar"), teste e toque:
   - **Ficou bom**: o chamado fecha, em seu nome;
   - **Não ficou bom**: escreva em uma linha o que falta. O chamado volta para ajuste.
5. Se você escrever **sem deslizar** e tiver pergunta ou entrega esperando, **quando estiver claro de
   que assunto você fala, a resposta entra direto no chamado** e volta **"Anotado no chamado 1217. ✓"**
   (#1238; manual `roteador.md`). Ela espera alguns minutos antes de ir ao sistema: se entrou no lugar
   errado, escreva na sequência *"não, era sobre a foto"* e o sistema tira do chamado. Na dúvida, ele
   pergunta *"É sobre o Chamado 1217 · ...?"*:
   - **Sim**: entra no chamado;
   - **Ver os assuntos** (ou **Outro chamado**): aparece a lista dos seus assuntos abertos;
   - **Outro assunto**: segue o atendimento de sempre (o menu da casa, a foto do campo).
   Enquanto o roteador estiver desligado, vale o de antes: o sistema sempre pergunta.

## 4. O que significa cada sinal

- **"Você tem 1 aviso da Sementes Renascer. Toque em Ver."** Você não escreve para a empresa há mais de
  24 horas e tem uma pergunta ou uma entrega esperando. Toque em **Ver** e ela aparece.
- **"Anotado no chamado N. ✓"**: a sua resposta entrou no chamado.
- **"Anotado. Esta mensagem é só um aviso…"**: você respondeu a um aviso. Nada foi anotado; para falar
  do chamado, use o sistema ou espere a próxima pergunta. Essa linha vem uma vez só por chamado.
- **Vários chamados numa mensagem só**, separados por um traço: o sistema junta o que chega para você
  em poucos minutos, para não mandar uma mensagem atrás da outra.
- **"Esta entrega já foi respondida. ✓"**: você (ou alguém pela caixa do sistema) já tinha respondido.
- **Um documento (PDF ou Word) com a legenda "Chamado N"** logo depois da mensagem (#1381): é o arquivo
  que a equipe mandou junto da pergunta ou da entrega, um roteiro ou um manual, por exemplo. Toque para
  abrir. Fora das 24 horas, ele espera junto com a mensagem e chega quando você tocar em **Ver**.
- **Sem o "Bom dia" de volta.** Se você escreve "Bom dia" e havia mensagem esperando, chegam só as
  mensagens, sem o menu da casa.

Na tela **Envios**, a tabela *Chamados no WhatsApp* mostra cada mensagem: → o que saiu, ← o que voltou.
"esperando" é o que ainda não saiu (a pessoa não escreveu, ou a junção dos minutos); "esperando o Ver"
é o que espera o toque na reabertura; "no chamado" é a resposta que já entrou no ERP; "erro" diz por
quê (por exemplo, o número não é o de quem abriu o chamado).

## 5. O que esta função NÃO faz

- Não abre chamado novo pelo WhatsApp: para isso, continue usando o sistema.
- Não lê foto ou arquivo como resposta de chamado: só texto, os botões e, para a equipe, o **áudio**
  transcrito na máquina (#1238, quando a transcrição estiver ligada). O arquivo só vai **da equipe para
  você** (#1381), e só junto de uma pergunta ou de uma entrega.
- O documento que chega pelo WhatsApp não aparece na caixa do sistema: guarde-o no celular.
- Não manda aviso fora de hora por conta própria: o que é só aviso espera você escrever para a empresa.
- Não avisa cada etapa do chamado, nem manda a pergunta do agente de suporte sem o dono (#1269): isso
  fica no chamado, no sistema.
- Não manda o detalhe técnico: só a parte do comentário escrita para quem pediu.

## 6. Pré-requisito de cadastro

O seu usuário no AxiaGestão precisa ter o **WhatsApp** preenchido (Cadastros → Mapa de Atividades →
o usuário → WhatsApp). Sem ele, nada sai, e tudo continua só na caixa do sistema.

## 7. Para quem cuida

- A chave `pendencias.ligado` (em `atendimento.ajustes`) liga e desliga tudo. Desligada, nada sai e
  nenhuma resposta é tomada; o atendimento volta a ser o de antes.
- `pendencias.juntar_minutos` (10) é quanto tempo a junção espera a rajada acabar.
- `roteador.ligado` e `roteador.carencia_minutos` (3): a resposta sem deslizar que entra direto, e a
  espera antes de ir ao ERP (manual `roteador.md`).
- A volta das telas traz do ERP a cada minuto e leva as respostas; o recepcionista manda e lê.
- Resposta que o ERP recusa fica com o erro na tela Envios; não é tentada de novo.
- **O anexo (#1381).** Quem trata manda pela skill `demanda` (`comentar N --pergunta ... --anexo <arquivo>`
  ou `entregar N --devolucao @f --anexo <arquivo>`): PDF ou Word, até 10 MB, um por resposta. A volta das
  telas baixa o arquivo do ERP para `envios_pasta\chamados` (ERP fora: a volta para e tenta de novo, sem
  andar o cursor; anexo recusado de vez pelo ERP: a mensagem sai só com o texto e o motivo vai ao log).
  O recepcionista manda o documento logo depois do texto e antes do "ficou bom?". Se o documento falhar,
  o texto já saiu: o erro fica na mensagem ("anexo: ...") e no log. A chave `pendencias.anexo_ligado`
  desliga só o documento; o texto continua saindo.
