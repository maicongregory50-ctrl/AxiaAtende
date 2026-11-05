# Segurar o envio à carteira: suspender por envio e "segurar tudo", pela tela Envios
**Data:** 2026-11-05
**Chamado:** #1169
**Status:** APROVADO

## Contexto

O envio à carteira para hoje por dois caminhos. A nota da Meta põe o envio em `parado_nota` sozinha, e
só a tela o religa. A outra trava é a chave do lado de quem pede (`AXIAMKT_ENVIO_CLIENTES`, no XML dos
serviços do Marketing, #1112). Se aquela chave for ligada por engano, o AxiaAtende despacha o que
receber. Foi o que o #1113 mostrou em 27/10: o pedido de "zero envios até nova ordem" não tinha o que
segurar do lado do Atende.

O estado `suspenso` existe no banco desde a primeira migração (`envios_situacao`), e o despacho de
lotes já o respeita, porque só lê `ativo` e `parado_nota`. Quem o grava hoje é só um script de janela
elevada (`scripts/suspender_envio.py`, #1203). A tela Envios só oferece "Religar" para o envio parado
pela nota, e não existe trava geral.

## Os fios que encostam

**Quem escreve `envios.situacao` hoje** (medido em `backend/envio.py`, `rotas_telas.py` e `scripts/`):

| Escritor | Grava | Quando |
|---|---|---|
| `receber_pedido` | `ativo` (padrão da coluna) | o pedido chega pela API local |
| `mandar_lotes` | `parado_nota` | nota da Meta amarela ou vermelha |
| `mandar_lotes` | `concluido` | a fila de `aguardando` acabou |
| `POST /envios/{id}/religar` (tela) | `ativo` | o dono religa o que parou pela nota |
| `scripts/suspender_envio.py` | `suspenso` / `ativo` | janela elevada, à mão (#1203) |

**Quem lê para decidir:** `mandar_lotes` (só `ativo` e `parado_nota` andam; `suspenso` e `concluido`
ficam de fora). A tela Envios (rótulo de `ESTADO`). Mais ninguém: `mandar_imagens_pendentes` lê os
destinatários pela resposta "quero" e a janela de 24 h, sem olhar o envio; `mandar_avisos` lê a tabela
de avisos.

**A mudança escreve:** `envios.situacao` (mais um escritor: a tela, nos dois sentidos), duas colunas
novas em `envios` (`suspenso_por`, `suspenso_em`) e uma chave nova em `atendimento.ajustes`
(`envio.segurar`, com quem e quando dentro do valor). `receber_pedido` passa a gravar `suspenso` no
nascimento quando a chave está ligada. `mandar_lotes` passa a ler a chave e não mandar nada com ela
ligada.

**Quem volta depois:** a rotina do minuto do recepcionista (`Envio.rotina`: nota, lotes, imagens,
avisos), a cada 60 s. O resumo ao representante (`lote_do_representante`) nasce de dentro do lote, então
para junto quando nenhum lote sai. A nota da Meta continua independente: um envio suspenso não vira
`parado_nota`, porque `mandar_lotes` não o lê. Ao religar com a nota amarela, a nota o põe em
`parado_nota` na volta seguinte, como hoje.

## O universo medido

Banco de produção, 05/11/2026:

| Pressuposto | Contagem |
|---|---|
| envios até hoje | **16** (15 `concluido`, 1 `suspenso`, nenhum `ativo`) |
| o envio suspenso (pelo script, 28/10) | **51** clientes `aguardando` |
| pedidos nos últimos 30 dias | **16** |
| resumos ao representante nos últimos 30 dias | **20** |
| chaves em `atendimento.ajustes` | 29; nenhuma de envio |

Nada muda de estado na migração: as colunas nascem nulas e a chave nasce desligada.

## Conformidade com o Manual legal

não se aplica: trava operacional do envio de WhatsApp, sem regra fiscal, tributária ou documento legal.

## Conformidade com a casa

não se aplica: nenhum segredo, serviço, porta, tarefa, agente ou chamada de IA. O dado novo (duas
colunas e uma chave) mora no banco `axiaatende`, coberto pelo backup diário de disco e de nuvem (R2,
`backup_axiaatende_banco.ps1` e `backup_cloud_axiaatende_banco.ps1`).

## Decisão

**Caminho B — o botão por envio e o "segurar tudo".** Decisões do dono em 05/11/2026:

1. **Pedido novo durante o "segurar tudo" é aceito e nasce suspenso.** A fila de clientes é montada
   normalmente, o envio aparece na tela como suspenso e nada sai até alguém religar aquele envio. O
   Marketing recebe a resposta de sempre e registra a entrega; nada se perde.
2. **Imagens a quem já tocou "Quero receber" continuam saindo**, com envio suspenso ou com o "segurar
   tudo" ligado. A pessoa pediu, a janela está aberta e não há custo. A trava é para convite novo.

O que segue dessas duas, decidido no desenho:

- **"Segurar tudo" para só os convites.** Com a chave ligada, `mandar_lotes` não manda lote de envio
  nenhum, e todo pedido nasce `suspenso`. Imagens, avisos à equipe, Status do dia e chamados seguem.
- **Soltar o "segurar tudo"** volta a andar o que estava `ativo` antes. O que nasceu `suspenso` durante
  a trava continua suspenso até ser religado, um a um: nada sai em massa sem alguém olhar.
- **Suspender e religar por envio, na tela.** "Suspender" vale para `ativo` e `parado_nota`. "Religar"
  vale para `suspenso` e `parado_nota` (o de hoje). Religar com a nota amarela devolve o envio a
  `parado_nota` na volta seguinte, como hoje.
- **Registro.** Cada envio guarda quem suspendeu ou religou e quando (`suspenso_por`, `suspenso_em`). A
  chave guarda quem a ligou e quando. A tela mostra os dois, e a saúde do recepcionista publica
  `envio_segurado` para o painel.
- **A faixa.** Com o "segurar tudo" ligado, a tela Envios mostra uma faixa vermelha no topo: *"Envio à
  carteira SEGURADO desde DD/MM HH:MM por Fulano. Nenhum convite sai."* É a defesa contra a chave
  esquecida ligada.

**Por que não o A (só o botão):** não cobre o caso do #1113, em que o erro vem do lado do Marketing e
chegam vários pedidos de uma vez.

## Escopo desta etapa

**DENTRO:**
- migração 057: `envios.suspenso_por` (text) e `envios.suspenso_em` (timestamptz); a chave
  `envio.segurar` em `ajustes`, desligada;
- `envio.mandar_lotes` e `envio.receber_pedido` respeitando a chave;
- rotas das telas: `POST /envios/{id}/suspender`, `POST /envios/{id}/religar` (passa a aceitar
  `suspenso`), `PUT /ajustes/segurar-envio` (ligar e desligar), todas com o login de quem clicou;
- a tela Envios: o botão Suspender/Religar no envio aberto, o interruptor "Segurar tudo" e a faixa;
- `/saude` do recepcionista com `envio_segurado`;
- `scripts/suspender_envio.py` gravando quem (`script:<usuario do Windows>`) e quando, para o registro
  ser um só;
- o manual `envios.md` e os testes.

**FORA:**
- trava de imagens, avisos e Status do dia (decisão 2);
- recusar pedido (decisão 1);
- tirar a chave do lado do Marketing: as duas travas convivem, e cada uma é de um projeto;
- tile próprio no painel do AxiaSecurity: a saúde publica o estado, e o tile fica para quando alguém
  pedir.

## Impacto em produção

- **Serviços:** `axiaatende-recepcionista` (o despacho e a migração) e `axiaatende-backend` (rotas e
  tela). Restart dos dois pela Porta-Ação, o recepcionista primeiro. Build do frontend.
- **Dados:** duas colunas nulas e uma chave desligada. Nenhum envio muda de estado. O envio suspenso de
  28/10 continua suspenso, agora com o botão Religar na tela.
- **Sem janela:** com a chave desligada, o comportamento é o de hoje.

## ROLLBACK_PLAN

1. Desligar o "segurar tudo" na tela (ou `UPDATE atendimento.ajustes SET valor = '{"ligado": false}'
   WHERE chave = 'envio.segurar'`). É o rollback operacional: tudo volta ao de hoje.
2. Reverter os commits do plano (código primeiro), build do frontend, restart dos dois serviços.
3. `057_segurar_envio_VOLTA.sql`: as duas colunas e a chave saem. Envio que ficou `suspenso` continua
   `suspenso` (o estado já existia), e o script de 28/10 continua religando.

## Manual de uso

**Para que serve.** Parar o envio à carteira pelo lado do atendimento, sem depender de alguém mexer no
marketing. Serve para segurar uma campanha específica ou, de uma vez, tudo o que está saindo e tudo o
que chegar.

**Quem usa e quando.** O dono, ou quem cuida do marketing, quando algo foi aprovado por engano, quando
o número da empresa precisa de descanso, ou quando chega um "zero envios até nova ordem".

**O caminho comum.**
1. Abra a tela **Envios** (http://127.0.0.1:8009, no servidor).
2. Para segurar **um** envio: abra o envio e clique **Suspender**. Os clientes que ainda não receberam o
   convite ficam na fila, sem perder a posição. Para voltar, clique **Religar**.
3. Para segurar **tudo**: ligue **Segurar tudo** no alto da tela. Nenhum convite sai, de envio nenhum, e
   todo pedido novo que o marketing mandar entra como **suspenso**.
4. Para soltar: desligue **Segurar tudo**. O que estava enviando volta a andar. O que chegou durante a
   trava continua suspenso: abra cada um e clique **Religar** quando quiser que saia.

**O que significa cada sinal.**
- **Faixa vermelha no alto** — o "segurar tudo" está ligado, com quem ligou e quando. Enquanto ela
  estiver lá, nenhum convite sai.
- **enviando** — o envio manda um lote por dia útil, na janela das 9h30 às 17h.
- **suspenso** — alguém suspendeu este envio (a linha diz quem e quando), ou ele chegou durante o
  "segurar tudo". Nada sai dele até ser religado.
- **PARADO pela nota do número** — a nota da Meta caiu; o envio parou sozinho. Religar só funciona com a
  nota de volta ao verde.
- **concluído** — a fila acabou.

**O que a tela NÃO faz.**
- Não segura as imagens para quem já tocou "Quero receber": quem pediu recebe.
- Não segura avisos à equipe, chamados no WhatsApp nem o Status do dia.
- Não apaga nem recusa pedido: o que chega fica guardado, suspenso.
- Não desliga o envio do lado do marketing: lá existe outra chave, e as duas valem juntas.

**O que o manual atual passa a dizer errado:** `envios.md` diz que "Religar o envio" só aparece com o
envio parado pela nota (passo 5 e a tabela de sinais). Passa a aparecer também no suspenso, e o envio
ganha o botão Suspender e a faixa do "segurar tudo".

## Próximo passo

/writing-plans
