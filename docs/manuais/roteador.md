# WhatsApp da equipe: escrever do seu jeito

**Desde:** novembro de 2026 · **Chamado:** #1238 · **Onde:** o WhatsApp da Sementes Renascer
(49 3664 0121)

## 1. Para que serve

Você escreve no WhatsApp da empresa do jeito que escreve para qualquer pessoa, e o sistema entende de
que assunto você está falando: o chamado que espera a sua resposta, a foto que você acabou de mandar, o
cliente que está aberto na sua lista do dia, a logo que você enviou, o currículo que espera o seu
comentário. Ele deixa de exigir que você deslize a mensagem ou escolha num menu.

## 2. Quem usa e quando

A equipe e os representantes, no dia a dia, sempre que escrevem para o número da empresa com algum
assunto em andamento. Quem é de fora da empresa não percebe mudança nenhuma: continua pelo menu.

## 3. O caminho comum

1. Chega alguma coisa do sistema (uma pergunta de chamado, *"O que está acontecendo nessa foto?"*, a
   ficha do cliente do dia) ou você manda uma foto, uma logo, um vídeo.
2. Você responde escrevendo, sem deslizar. Pode citar o assunto pelo nome (*"o 1222"*, *"a Plantagro"*,
   *"a foto do centeio"*) ou só responder.
3. A resposta diz onde a sua mensagem entrou: **"Anotado no chamado 1222 ✓"**, **"Recebi."** (a frase
   virou a legenda da foto), **"Recebi. Vou montar o registro."** (o cliente do dia).
4. Se entrou no lugar errado, escreva na sequência: *"não, era sobre a foto"*, *"isso era do chamado"*.
   O sistema tira de onde pôs e leva para onde você disse, e avisa: **"Certo, tirei de …"**. Uma
   mensagem para um chamado espera alguns minutos antes de ir ao sistema, justamente para você poder
   corrigir. A correção vale para a última mensagem, até 10 minutos depois.
5. Se o sistema ficar em dúvida entre dois assuntos, ele pergunta com botões: **"É sobre …?"**, com
   **Sim**, **Ver os assuntos** e **Outro assunto**.

A foto ou o vídeo que você mandou há menos de dois minutos tem a preferência: o que você escreve logo
em seguida é a legenda dela, sem pergunta nenhuma. Se não era, corrija como no passo 4.

**Áudio.** Você pode mandar áudio em vez de escrever. O sistema transcreve aqui na empresa (nada sai
para fora) e trata o texto como se você tivesse escrito. Leva alguns segundos a mais que o texto. Áudio
muito longo (acima de 3 minutos) não é transcrito, e áudio de quem é de fora continua sem leitura.

## 4. O que significa cada sinal

| Mensagem | O que quer dizer |
|---|---|
| **"Anotado no chamado N ✓"** | entrou no chamado, e vai ao sistema em alguns minutos |
| **"Recebi."** depois de uma foto | a frase virou a legenda da foto |
| **"É sobre …?"** com botões | o sistema não teve certeza: escolha. **Outro assunto** segue o caminho de sempre |
| **"Sobre qual assunto é a sua mensagem?"** | a lista dos seus assuntos abertos: toque no certo, ou em **Outro assunto** |
| **"Certo, tirei de …"** | a sua correção foi feita; em seguida vem onde a mensagem entrou (ou a lista) |
| **"Anotado. Esta mensagem é só um aviso…"** | você respondeu a um aviso que não pedia resposta |
| Nenhuma resposta | você não é da equipe no cadastro, ou não há assunto aberto e a mensagem seguiu o caminho de sempre (o menu da casa, a frase da próxima foto). Se esperava outra coisa, escreva *menu* |

## 5. O que o sistema NÃO faz

- Não entende foto sem texto como resposta de chamado, e não lê áudio de quem é de fora.
- Não abre chamado novo, não pede o próximo cliente e não cria assunto pelo texto: só encaminha para
  assuntos que já estão abertos. Para abrir, use o sistema ou o menu.
- Não lembra de ontem: o contexto é das últimas 24 horas com o número da empresa, e nunca o que você
  falou com outras pessoas.
- Não funciona para cliente ou pessoa de fora: para eles, o atendimento é por botão, como sempre.
- Não apaga comentário que já chegou ao sistema: a correção vira um aviso em seguida, no chamado.

## 6. Para quem cuida

- `roteador.ligado` (em `atendimento.ajustes`) liga e desliga o roteador, na hora, sem reiniciar. É o
  rollback inteiro: desligado, o atendimento volta a ser o de antes. `scripts\roteador.py ver` mostra a
  chave, a contagem por sinal dos últimos 7 dias e a fração que entrou sem botão e sem correção.
- `roteador.carencia_minutos` (3) é a espera do chamado antes de ir ao sistema; 0 manda na hora.
- `audio.transcrever` liga a transcrição; `audio.maximo_s` (180) é o limite. `scripts\audio.py ver`
  diz se o modelo e a biblioteca estão no lugar; `ensaiar <arquivo>` mede o tempo num áudio.
- Cada decisão fica em `atendimento.roteador` (o assunto escolhido, o sinal, a correção). O custo da
  OlivIA aparece na tela Custos como *OlivIA · assunto da mensagem da equipe*; a transcrição, com custo
  zero, como *Transcrição de áudio da equipe*.
- Pré-requisitos: o número da pessoa no cadastro do ERP (equipe ou representante) ou na tela Destinos;
  para o chamado, o WhatsApp no usuário do AxiaGestão (manual `chamado-no-whatsapp.md`); para o áudio,
  o modelo copiado para `C:\Dados\AxiaAtende\modelos` e o `faster-whisper` no venv do Atende.
