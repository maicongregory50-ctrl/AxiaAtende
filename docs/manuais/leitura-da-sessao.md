# A leitura da sessão — o que aconteceu numa conversa

> Para o dono e para a sessão de agente (#981, 13/10/2026). Não é tela: é um comando no terminal
> da sessão. O que a equipe vê do canal de campo está no `campo-equipe.md`; a Recepção, no
> `recepcao.md`.

## 1. Para que serve

Ver, pela sessão, o que de fato aconteceu numa conversa do WhatsApp da Renascer, sem print: o que
a pessoa escreveu, o que a OlivIA respondeu, por onde o atendimento andou, e o que o atendente de
campo perguntou e fechou. Serve para ajustar o atendente hoje e, depois, para o treinamento interno
quando o AxiaAtende atender cliente direto.

## 2. Quem usa e quando

O dono e a sessão de agente, quando um caso precisa ser lido: "o que ela respondeu ao fulano?",
"por que perguntou de novo?", "a foto entrou?". Antes, uma vez, o dono roda em janela elevada
`servicos\criar_leitura.ps1` (de preferência com `-ComLog`): é ele que cria o papel só-leitura no
banco e o arquivo de senha da sessão, e prova que o banco recusa escrever.

## 3. O caminho comum

1. `python scripts\ler_conversa.py --ultimas 20` lista os últimos números que escreveram, com o
   nome do cadastro quando há, para achar quem procurar.
2. `python scripts\ler_conversa.py --numero 5549999990000` imprime a conversa do número, do mais
   antigo ao mais novo, com hora, quem falou e o que. `--dias 2` ou `--desde 2026-10-12` encurta.
   `--bsuid BR.xxx` serve quando só se tem o identificador da Meta.
3. `python scripts\ler_conversa.py --campo --dias 7` imprime o canal de campo da semana: cada
   grupo de fotos, quem mandou, quantas perguntas foram feitas, a classe fechada, a data, se
   fechou ou desistiu e o ATV no catálogo.
4. Toda chamada fica registrada em `C:\Logs\AxiaAtende\leituras.jsonl` (quando, quem, o que,
   quantas linhas); o Postgres também anota, no log do dia em `C:\Logs\AxiaAtende\postgres\`.

## 4. O que significa cada sinal

| Sinal | O que quer dizer |
|---|---|
| `→` | o que chegou da pessoa: texto, `[botão] Sim (id)`, `[lista] ...`, `[foto id=...]`, `[áudio id=...]`, `[reação 👍]` |
| `← [tipo, status]` | o que a OlivIA mandou: `texto`, `botoes`, `lista`, `imagem`, `modelo`; o status é o último que a Meta contou (`aceita`, `enviada`, `entregue`, `lida`, `falhou`) |
| `!!` no fim da linha | erro gravado naquele evento ou envio |
| `[atendimento] abriu ...; caminho:` | a conversa de atendimento e os rótulos tocados no menu |
| `← [botoes, ...] ia retomou <opção>` | a retomada pela OlivIA (#989): 30 min depois de a pessoa parar, a opção do menu que ela propôs com Sim / Ver opções |
| `[campo] foto #id (grupo N)` | a foto no canal de campo: legenda, perguntas feitas, classe (ou "a classificar"), data (e se foi presumida), `aberto` / `fechado` / `desistiu`, o ATV quando entrou |
| `[campo] frase guardada` | o texto que a pessoa escreveu antes da foto; "(usada)" quando virou legenda |
| "nenhuma mensagem no período" | o número existe, mas nada no recorte pedido: é zero |
| "número não reconhecido: nunca escreveu" | não é zero: esse número nunca falou com a Renascer |
| `sem acesso: ...` e saída 2 | falta o arquivo de senha ou o papel: rodar `criar_leitura.ps1` elevado |

## 5. O que NÃO faz

- **Não escreve nada**, em lugar nenhum do banco: o papel não tem o direito e a transação é só
  leitura; quem recusa é o Postgres.
- **Não mostra senha, token nem hash**, e não lê `casa` (usuários e sessões das telas).
- **Não baixa mídia**: diz que houve foto, vídeo ou áudio, com o id; **não transcreve áudio**.
- **Não manda mensagem a ninguém** e não muda o estado de conversa nenhuma.
- **Não serve para tirar conversa do servidor**: a finalidade é ajustar o atendimento e a OlivIA
  da casa (política de uso de IA do AxiaSecurity).
