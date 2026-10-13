# A retomada pela OlivIA: a conversa que parou no meio recebe a opção que resolve
**Data:** 2026-10-13
**Chamado:** #989
**Status:** PROPOSTO

> O arquivo nasceu como "a tela de Conversas e a resposta de pessoa" e foi refeito no mesmo dia: o
> dono recusou a tela ("precisa muita coisa, não penso em rodar agora; só leitura agora e a resposta
> por IA") e escolheu a retomada pelo menu. O nome do arquivo ficou, para o chamado achar.

## Contexto

O número da Renascer só fala pela API da Meta, pelo recepcionista; ninguém da casa responde à mão.
Quando a OlivIA não resolve e a pessoa para (o Vinicius às 14:00 de 13/10, pedindo os contatos de
SC; a Giovana às 11:31, numa lista antiga), a conversa fica "parou no meio" na Recepção e a pessoa
fica sem nada. A leitura pela sessão já existe (#981) e o menu já entende texto e lista antiga desde
o #988; o que falta é alguém voltar à conversa parada.

O dono em 13/10: a resposta é **por IA, pelo menu**: 30 minutos depois de a conversa parar, a OlivIA
relê a conversa inteira, acha a opção do menu que resolve e pergunta "Pelo que entendi, você quer
X. É isso?", com Sim e Ver opções; o Sim manda o link. **Nunca texto livre**: só o que o menu já daria
a quem tocasse certo. Sem pessoa no meio, dentro das 24 h da última mensagem.

O que existe e que a etapa reaproveita (inventário de 13/10):
- `motor.marcar_paradas` (laço de 1 min) marca `situacao = 'parou_no_meio'` 30 min depois do último
  toque (D5 do #950). `conversas` guarda `ia_proposta_id` e `ia_confirmou` (a proposta da IA e o
  acerto), e o toque `ia:sim:<chave>` / `ia:menu` já é tratado no motor (`escolher` manda o link).
- `motor.propor` manda a confirmação "Entendi que você quer: X. É isso?" com os dois botões e
  registra em `enviadas`; `ia.classificar(texto, folhas_e_menus)` lê um texto contra a árvore
  inteira, com a chave fechada por `json_schema`.
- O que a pessoa escreveu está em `eventos_meta` (texto e toques), lido em ordem pelo leitor do #981.
- A janela de 24 h é medida pela última mensagem recebida (`campo.ultima_mensagem_de`).

## Os fios que encostam

**Quem mais escreve.** `conversas.situacao` tem três escritores (o motor ao abrir, escolher e
encerrar; `marcar_paradas`; e o que fecha ao chegar o toque) e ganha um quarto: a retomada volta a
conversa a `em_curso` ao mandar a pergunta, para o Sim da pessoa cair nela (e não numa conversa
nova) e `escolher` mandar o link. A coluna nova `retomada_em` tem um escritor só (a retomada) e é o
que garante **uma retomada por conversa**: sem resposta, `marcar_paradas` a marca de novo em 30 min
e a retomada não repete. `ia_proposta_id` é escrito por `propor` e pela retomada (a mesma coisa: o
que a IA propôs); `ia_confirmou` continua sendo escrito pelo toque. `enviadas` ganha a linha da
retomada como qualquer fala.

**Quem lê para decidir.** A Recepção lê `situacao` (a conversa retomada volta a "escolhendo agora" e,
com o Sim, "recebeu o link"; sem Sim, "parou no meio" de novo em 30 min, sem nova retomada). A
pergunta das 4h30 lê `com_link`: a conversa retomada com Sim entra nela como qualquer outra. O
cartão "IA acertou / errou" lê `ia_proposta_id` + `ia_confirmou`: a retomada conta ali (acerto quando a
pessoa diz Sim).

**Quem volta depois.** `marcar_paradas` (de novo em 30 min). O leitor da sessão mostra a retomada
como `←` (de `enviadas`, resumo "ia retomou <chave>").

## O universo medido

- Conversas que param no meio: contadas pela Recepção; em 13/10, duas de fora. Com o #988 no ar
  desde 14:35 o número tende a cair; a retomada mede o resto: quantas retomadas por semana e quantas
  viram link (acerto), pelos mesmos cartões.
- O que a IA lê: os textos e os títulos dos toques da pessoa na conversa (de `eventos_meta` desde
  `iniciada_em`), juntos, até 1000 caracteres (o limite que `classificar` já corta).
- Escritores de `conversas.situacao`: 3 hoje, 4 depois (medido por `grep situacao = ` no motor).

## Conformidade com o Manual legal

Não se aplica. A mensagem sai dentro das 24 h da última mensagem da pessoa (mensagem de sessão da
Meta, sem modelo); fora dela não sai.

## Decisão

Caminho B, escolhido pelo dono em 13/10/2026 ("retomada pelo menu"):

- **A, conservador:** nada automático; só a leitura (#981) e a Recepção dizendo quem parou. Não dá
  nada à pessoa.
- **B, o escolhido:** a retomada pela OlivIA, só pelo menu, uma vez por conversa, dentro das 24 h.
- **C, progressivo:** texto livre escrito pela IA com o ok do dono por botões no WhatsApp dele.
  Fica para depois, se a retomada mostrar pedidos que o menu não cobre.

## Escopo desta etapa

**Dentro**
1. Migração 016: `conversas.retomada_em timestamptz` (e `retomada_chave text`, o que foi proposto,
   para a medição).
2. `motor.retomar_paradas(con, saida, ia, agora)` no laço de 1 min, depois de `marcar_paradas`:
   para cada conversa `parou_no_meio` sem `retomada_em`, com a última mensagem da pessoa há menos
   de 24 h e com IA: junta o que ela escreveu e tocou nessa conversa (de `eventos_meta`), chama
   `ia.classificar` contra a árvore; com um nó que não é a raiz nem encerrar, manda os botões
   "Pelo que entendi da nossa conversa, você quer: X. É isso?" (`ia:sim:<chave>` / `ia:menu`),
   grava `ia_proposta_id`, `retomada_em`, `retomada_chave`, volta a conversa a `em_curso` com o
   toque de agora, e registra em `enviadas` ("ia retomou <chave>"). Sem nó (ou IA fora), grava só
   `retomada_em` e fica em silêncio: uma tentativa, nunca duas. Erro da Meta não derruba o laço.
   O texto da retomada é um ajuste (`atendimento.ajustes`, chave `retomada`), como as outras frases.
3. O toque depois da retomada é o de hoje: `ia:sim` manda o link; `ia:menu` mostra o menu.
4. Manual: `recepcao.md` ganha "A retomada pela OlivIA" (o que é, quando sai, o que a Recepção
   mostra); `leitura-da-sessao.md` ganha a linha `←` da retomada.

**Fora**
- Tela de conversas e resposta de pessoa (recusada pelo dono em 13/10).
- Texto livre pela IA (caminho C).
- Retomar conversa que parou há mais de 24 h, ou mais de uma vez.
- Mudar o menu.

## Impacto em produção

Migração 016 aplicada ao subir. Reinício do `axiaatende-recepcionista` (o laço) e do
`axiaatende-backend` (a migração chega pelos dois): mão do dono. Custo: uma chamada da IA de texto
por conversa parada (Haiku, centavos).

## ROLLBACK_PLAN

1. `016_retomada_VOLTA.sql` (tira as duas colunas).
2. Reverter o commit (o laço deixa de retomar). Reiniciar o recepcionista.
3. As conversas retomadas ficam como estão; nada se apaga.

## Manual de uso

**Para que serve.** Quem parou no meio do atendimento (não achou a opção, escreveu o que o menu não
entendeu) recebe, meia hora depois, a opção que a OlivIA entendeu que a pessoa queria, para
confirmar com um toque e receber o contato certo, sem ninguém da casa no meio.

**Quem usa e quando.** Ninguém aciona: é automático, uma vez por conversa parada, só dentro das 24
horas da última mensagem da pessoa, com a IA ligada.

**O caminho comum.**
1. A pessoa chama, não chega a um contato e para. Trinta minutos depois a Recepção a mostra como
   "parou no meio".
2. No minuto seguinte a OlivIA relê tudo o que a pessoa escreveu e tocou, e manda: *"Pelo que
   entendi da nossa conversa, você quer: SC (Comercial › Revendedor). É isso?"* com **Sim** e **Ver
   opções**.
3. **Sim** manda o contato certo, como se a pessoa tivesse tocado no menu; **Ver opções** mostra o
   menu. Sem resposta, nada mais é mandado.

**O que significa cada sinal.** Na Recepção, a conversa retomada volta a "escolhendo agora"; com o
Sim vira "recebeu o link" e conta em "IA acertou"; sem resposta volta a "parou no meio" em 30 min, e
não há segunda retomada. Na leitura da sessão a retomada aparece como `←` com "ia retomou". "Nada
foi mandado" tem três motivos: a pessoa escreveu há mais de 24 h, a IA não achou opção que
servisse, ou a IA estava fora.

**O que NÃO faz.** Não escreve texto livre; não manda nada fora das 24 h; não retoma duas vezes;
não responde o que o menu não tem (isso fica para a pessoa pedir de novo, ou para a etapa C).

## Próximo passo

`/writing-plans`.
