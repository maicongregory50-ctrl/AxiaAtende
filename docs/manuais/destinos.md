# Destinos — manual de uso

> Para quem a OlivIA manda cada motivo de quem chama no WhatsApp da empresa. No AxiaAtende:
> **http://127.0.0.1:8009**, aba **Destinos** (#950, 09/10/2026).

## 1. Para que serve

O menu da OlivIA termina sempre no WhatsApp de uma pessoa: o representante da região, o
financeiro, o frete. Quem chamou recebe uma mensagem curta e, logo abaixo, o **cartão de contato**
dessa pessoa (nome, número e "Sementes Renascer"): toca em Conversar e já está falando com ela, ou
salva o contato. Esta tela diz quem é essa pessoa em cada caso. Trocar aqui vale para a próxima
pessoa que chamar, sem precisar de ninguém.

## 2. Quem usa e quando

Você, quando muda quem atende um assunto ou uma região, quando alguém troca de número, ou quando o
horário de atendimento muda.

## 3. O caminho comum

**Trocar quem atende um motivo:** na primeira tabela, ache a linha (o motivo, as perguntas do caminho e
a resposta, por exemplo "Comercial · Produtor rural › PR › Cascavel") e escolha outra pessoa em
**Mandado para**. Vale na hora.

**Trocar o número ou o nome de uma pessoa:** em **As pessoas**, clique **editar**, mude e **Salvar**.
Todas as opções que mandam para ela passam a usar o número novo.

**Uma pessoa nova:** **+ Pessoa**, nome e WhatsApp com DDD, **Salvar**; depois ligue as opções a ela na
primeira tabela.

**O horário:** marque os dias, ajuste as faixas e **Salvar horário**.

**Quem é avisado quando alguém diz que não foi atendido:** escolha a pessoa no fim da tela.

**Canal de campo (#970):** a chave *ligado*. Ligada, a foto ou o vídeo que um colaborador ou
representante do cadastro manda ao WhatsApp da Renascer é guardado, a OlivIA pergunta o que é e se é
de hoje, e o marketing busca para a Caixa dele. Desligada, a foto da equipe é só guardada, como
sempre foi, e o marketing não busca; nada se apaga. Nasce desligada; liga-se no primeiro caso, com
o dono, depois de o marketing também ligar a chave dele (`AXIAMKT_CAMPO`).

## 4. O que significa cada sinal

| Sinal | Quer dizer |
|---|---|
| **Motivo** | a opção do menu principal (Comercial, Fretes, Financeiro…) |
| **Perguntas no caminho** | o que a OlivIA pergunta antes de escolher a pessoa (área, estado, cidade) |
| **Resposta** | a combinação de respostas que leva àquela pessoa |
| **"(antes vai um texto)"** | antes do link vai uma mensagem fixa (por exemplo, o link da Fretebras no Frete) |
| **Horário** | fora dele, o link vai do mesmo jeito, com o aviso de que o retorno vem no próximo horário |

## 5. O que a tela NÃO faz

- **Não muda o texto do menu nem cria motivo novo:** isso é chamado.
- **Não confere se o WhatsApp digitado existe:** confira com a pessoa antes de salvar.
- **Não muda o responsável dos clientes da carteira:** esse é o canal comercial do cadastro do cliente,
  no ERP. Destinos vale para quem chama no WhatsApp e não é da carteira.
