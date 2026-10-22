# O lote novo não entra no grupo fechado
**Data:** 2026-10-22
**Chamado:** #1099
**Status:** APROVADO

## Contexto

Hoje de manhã o dono mandou três lotes de fotos do nabo forrageiro IPR 116, dois de beneficiamento e
um de qualidade, e reclamou: *"as ultimas fotos subiram com o titulo da anterior, o atendimento não
entendeu que era um novo lote"*. A linha do tempo, pela **hora de envio** que a Meta põe em cada
mensagem (`msg.timestamp`) e pela hora em que a mensagem chegou ao recepcionista:

| Mandado | Chegou | O quê |
|---|---|---|
| 08:54:56 | 10:05 (a foto) e 10:24 (o aviso de álbum) | álbum, 1 foto |
| 08:55:15 | 09:39:56 | "Qualidade, amostrando Nabo Forrageiro Safra 2026." |
| 09:44:36 | 09:44:38 a 09:44:50 | álbum de 15 fotos |
| 09:44:46 | 09:44:50 | "Beneficiamento Nabo IPR116 2026" |
| 10:18:53 | 10:18:58 | 1 foto |
| 10:22:59 / 10:24:15 | na hora | "Oi" e "Analise interna de qualidade… hoje" (respostas às perguntas) |
| 10:25:28 | 10:25:31 a 10:25:35 | álbum de 3 fotos |
| 10:25:46 | 10:25:49 | "Beneficiamento Nabo-forrageiro IPR116, safra 2026, hoje" |

**Duas causas, e nenhuma é a IA.**

1. **O grupo fechado recebe foto nova** (`campo.Campo._lider`, `backend/campo.py:276`, segundo
   ramo). Sem conversa aberta, ele devolve o grupo de *qualquer* linha do número recebida nos
   últimos 10 minutos (`RODADA`), **mesmo fechada**, e a foto nova herda classe, data e
   `fechado_em`. O grupo 58 fechou às 10:24:19; o álbum das 10:25 entrou nele e foi ao catálogo como
   "Análise interna de qualidade" (ATV-0799 a ATV-0801). A frase dele, que veio 18 s depois, achou
   tudo fechado e ficou guardada como "frase da próxima foto", que não veio.
2. **A ordem é a de chegada, não a de envio.** A frase de Qualidade, mandada às 08:55 para o álbum
   das 08:54, ficou presa no celular e chegou às 09:39, antes da foto dela. Cinco minutos depois
   chegou o álbum das 09:44, e `receber` pegou a frase guardada "dos últimos 10 minutos" (contados
   pela chegada) como legenda. A frase certa do álbum, Beneficiamento, foi só emendada, e a classe
   ficou Controle de qualidade porque `_ler` grava com `coalesce` e a primeira leitura vence
   (ATV-0780 a ATV-0794; o palpite de imagem de uma delas foi "beneficiamento").

**O gesto do dono é foto primeiro, frase depois.** A decisão 13 (12/10) supôs a frase *antes* da
foto, que é o jeito do Benedito. O canal precisa servir aos dois.

## Os fios que encostam

**Quem mais escreve o que a mudança escreve.** A etapa escreve em `atendimento.material_de_campo` e
`atendimento.campo_frases`, as duas só do `backend/campo.py` (medido por `grep` em `backend/`):

| Escritor | O que grava | Muda? |
|---|---|---|
| `Campo.receber` | a linha da foto, `grupo_id`, a legenda herdada ou da frase | **sim**: o lote passa a ser pela hora de envio, e grupo fechado não recebe lote novo |
| `Campo.texto_de_interno` | `campo_frases` | **sim**: grava também a hora de envio da frase |
| `Campo.responder`, ramo "texto solto" | legenda do grupo aberto | não |
| `Campo._perguntar` / `_gravar` / `_fechar` / `_desistir` | perguntas, classe, data, fechamento | **sim**: a pergunta nova `mesmo` |
| `palpite`, `buscado`, `catalogado`, `foi_ao_ar`, `classe_aplicada` (as rotas do marketing) | colunas próprias | não |

**Quem lê para decidir.** `_lider` e `fazer_perguntas` (o grupo e a vez de perguntar), `pendentes` e
`classificados` (o que o marketing leva: só grupo fechado), `scripts/ler_conversa.py` e a Recepção
(`rotas_telas.py:92`, as medidas da semana). **O marketing não lê `grupo_id`**: agrupa por contato
(`C:\AxiaMarketing\backend\campo.py:399`) e propõe uma peça por pessoa por dia. Ter mais grupos não
muda nada lá.

**Quem volta depois.** O laço do minuto (`fazer_perguntas`, `mandar_avisos`). O "uma mensagem por
pessoa por volta" (`falados`) já existe e segura o caso de dois lotes abertos da mesma pessoa: o
segundo espera o primeiro fechar.

**A hora de envio vem do mesmo aviso que já é gravado** (`eventos_meta.corpo->'msg'->>'timestamp'`).
Os testes mandam hoje um `timestamp` fixo (`"1760040000"`, `tests/test_campo.py:32` e
`tests/avisos_meta.py`): o plano precisa fazer os ajudantes de teste mandarem a hora do `agora` do
passo, senão todas as fotos de teste "foram mandadas no mesmo segundo".

## O universo medido

Medido em 22/10/2026, só leitura (papel `axiaatende_ro`), tudo o que o canal recebeu desde 11/10:

- **62 fotos e vídeos, 18 grupos, 3 pessoas** (dono 53 em 13 grupos, Benedito 6 em 4, Willian 3 em 1).
- **Foto que entrou em grupo já fechado: 4.** As 3 do dono hoje, **erradas**, e 1 do Benedito em
  14/10 (foto 22, 2 min depois de "Carregamento do dia" fechar, sem frase): **certa**, era o mesmo
  carregamento. É o caso que o caminho B pergunta com um botão.
- **Avisos de álbum** (`unsupported`, `type: album`): **6**, todos do dono, desde 15/10. As fotos do
  álbum têm hora de envio de 0 a 3 s depois da do aviso. Antes de 15/10 o mesmo gesto chegava como
  `unsupported` sem tipo (5). **Por isso o lote não depende do aviso de álbum**: fotos mandadas até
  60 s depois da anterior são o mesmo lote, venha ou não o aviso.
- **Mensagem entregue com mais de 60 s de atraso: 11** (dono 9, Benedito 2), de 30 min a 33 h.
  **Fora de ordem** (hora de envio anterior à de uma mensagem que já tinha chegado): **9**.
- **Frase mandada até 60 s DEPOIS de fotos: 6, todas do dono** (12/10, 19/10 duas vezes, 22/10
  três vezes). Em nenhum desses casos chegou foto nos 10 minutos seguintes.
- **Frase guardada e nunca usada: 4 de 6.** Uma é a de Beneficiamento de hoje.
- **Com a regra nova**, os três lotes de hoje saem certos: a frase das 08:55 (19 s depois do álbum
  das 08:54) é dele, mesmo chegando antes da foto; o álbum das 09:44 fica sem frase de antes (a das
  08:55 é 49 min anterior) e leva a das 09:44:46; o das 10:25 é lote novo e leva a das 10:25:46. A
  resposta "Analise interna…" das 10:24 não vira frase de ninguém, porque foi resposta a pergunta
  (nunca passa por `campo_frases`).

## Conformidade com o Manual legal

Não se aplica: classificação de foto do catálogo de marketing, sem imposto, documento fiscal nem
texto legal.

## Conformidade com a casa

Não se aplica: nenhum dos seis gatilhos. Não há segredo, serviço, porta, tarefa nem agente novo.
A IA de texto (`ia.ler_campo`) continua sendo chamada como hoje, nem mais vezes nem com outro dado.
As duas colunas novas ficam no banco que o backup do AxiaAtende já cobre. Nenhuma sessão de agente
é tocada.

## Decisão

**Caminho B**, escolhido pelo dono em 22/10/2026 entre três ("b"). Ele se apoia em quatro regras.

1. **O lote é pela hora de envio.** Duas fotos do mesmo número mandadas com até **60 s** de diferença
   (a hora da Meta, não a de chegada) são o mesmo lote. Vale para álbum e para fotos soltas em
   sequência.
2. **Grupo fechado não recebe lote novo.** Foto de outro lote abre grupo novo. A que pertence ao
   mesmo lote (mesmo envio, chegou atrasada) continua entrando nele, fechado ou não. **Continua
   valendo a regra de 12/10 (decisão 15c):** foto que chega com pergunta em aberto entra na conversa
   aberta.
3. **O título do lote é a frase mais próxima dele pela hora de envio.** A frase mandada até
   **10 min antes** da primeira foto, ou até **60 s depois** da última. Quando há as duas, vale a de
   antes, que é o jeito de quem escreve primeiro. A frase de antes já usada por outro lote não
   serve de novo. A frase que chega antes da foto dela (celular sem rede) fica guardada e é achada
   quando a foto chegar.
4. **Lote sem frase, mandado até 10 min depois de um lote do mesmo número que já fechou, ganha uma
   pergunta de botão.** É a primeira pergunta dele, no mesmo tempo das outras (depois da espera do
   palpite): *"É do mesmo assunto da anterior (<título da anterior, curto>)?"*, com **Sim** e
   **Outra coisa**.
   - **Sim:** herda a legenda, a classe, a data e a safra do anterior, diz "Anotado. Obrigado!" e
     fecha.
   - **Outra coisa:** segue o roteiro de sempre ("O que está acontecendo nessa foto?"…).
   - **Sem resposta:** a lembrança de 2 h e a desistência, como as outras perguntas. Desistiu: fecha
     sem herdar.
   - **Contagem:** essa pergunta não entra no limite de três perguntas de classificação, como a
     data.

**Por que B e não A nem C.** A (perguntar sempre) faria quem manda mais uma foto do mesmo assunto
dizer de novo o que acabou de dizer. C (herdar calado, como hoje) é o defeito deste chamado sempre
que a frase não chegar. B resolve os dois com um toque e não deixa nada passar calado, a régua que
este projeto segue desde o #1028.

**A hora de envio só vale quando é plausível.** Se faltar, ou se for mais de 5 min no futuro em
relação à chegada (relógio do aparelho errado), vale a hora de chegada. O atraso para trás é
legítimo e não tem teto: 33 h foram medidas.

## Escopo desta etapa

**Dentro:**
- a hora de envio lida do aviso e gravada na foto e na frase (migração 025, com a VOLTA);
- `_lider` pela hora de envio, sem grupo fechado para lote novo;
- a frase de antes e a de depois pela hora de envio, inclusive a que chegou antes da foto;
- a pergunta `mesmo` (botões, herança, lembrança, desistência);
- a chave `campo.lote_pelo_envio` em `atendimento.ajustes` (ligada): desligada, `_lider` e a frase
  voltam à regra de chegada de hoje;
- o `ler_conversa.py` mostrando a hora de envio quando ela difere da de chegada em mais de 60 s;
- os testes (os ajudantes mandam a hora do passo; os casos de hoje, do Benedito e do atraso);
- os manuais `docs\manuais\campo-equipe.md` e `docs\manuais\recepcao.md`.

**Fora:**
- separar um lote novo que chega enquanto há pergunta em aberto (a decisão 15c continua);
- corrigir as ATV de hoje: o dono, na Caixa do marketing;
- reclassificar no catálogo o que já foi levado: o marketing já aplica a classe de grupo que fecha
  depois (`classificados`), mas o grupo de hoje não reabre;
- o texto solto emendado na legenda do grupo aberto (`responder`) continua como está;
- o #1097 (a conversa de foto do campo que termina como "parou no meio"), que é outro chamado.

## Impacto em produção

- **Serviços:** `axiaatende-recepcionista` e `axiaatende-backend`. A migração 025 é aplicada no
  restart do backend; o recepcionista reinicia depois. É **aditiva** (duas colunas que aceitam
  vazio, um valor a mais no `CHECK` de `pergunta_pendente`, uma linha em `ajustes`), então pode ir
  antes do restart sem derrubar o código no ar.
- **Dados:** nenhuma linha existente muda. As linhas antigas ficam sem hora de envio e caem na hora
  de chegada (a regra de antes).
- **Janela:** fora de uma conversa aberta do canal. O recepcionista fica parado alguns segundos, e a
  Meta reenvia o aviso que não recebeu resposta.

## ROLLBACK_PLAN

1. **Sem deploy:** `UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave =
   'campo.lote_pelo_envio'`. O próximo evento já segue a regra de chegada; não precisa reiniciar.
2. **O código:** `git revert` dos commits do #1099 em `C:\AxiaAtende` e restart dos dois serviços.
3. **A migração:** `025_lote_pelo_envio_VOLTA.sql`. Antes, ela limpa `pergunta_pendente = 'mesmo'`
   (vira `NULL`, e o grupo segue para a próxima pergunta ou fecha) e só então volta o `CHECK`. Depois
   tira as duas colunas e a linha de `ajustes`.
4. **O que não volta sozinho:** um grupo que herdou pelo "Sim" fica com a classe herdada. Ela foi
   escolhida pela pessoa, então está certa.

## Manual de uso

**O que o `campo-equipe.md` passa a dizer errado:**
- §3 passo 1, *"A frase pode ir antes ou junto da foto"*. Agora pode ir **antes, junto ou logo
  depois** (até um minuto depois da última foto).
- §3 passo 3, *"Várias fotos do mesmo lugar, mandadas em seguida, são uma conversa só"*. Fica certo,
  com a precisão de que "em seguida" é **até um minuto** entre uma foto e a outra.
- §4, a nota *"a frase fica guardada e vira a legenda da foto que chegar nos dez minutos
  seguintes"*. Os dez minutos contam **da hora em que você mandou**, e não da hora em que chegou.
- §4, a tabela ganha a linha nova da pergunta "É do mesmo assunto da anterior?".

**O texto, para quem é da equipe:**

1. **Para que serve.** Cada lote de fotos entra no catálogo com o título dele. Antes, um lote
   mandado logo depois de outro podia herdar o título do anterior.
2. **Quem usa e quando.** Quem manda foto do campo, da produção ou da qualidade, toda vez que manda
   mais de um lote seguido.
3. **O caminho comum.**
   1. Mande as fotos (soltas ou em álbum) e escreva o que são. Pode escrever antes, junto ou logo
      depois delas.
   2. Fotos mandadas com até um minuto entre uma e outra são **um lote**. Esperou mais que isso?
      As próximas são outro lote.
   3. Mandou outro lote sem escrever nada, logo depois de um que já fechou? A OlivIA pergunta
      **"É do mesmo assunto da anterior?"**. Toque **Sim** e ele leva o mesmo título; toque **Outra
      coisa** e ela pergunta o que é.
   4. Celular sem sinal? Vale a hora em que você mandou, e não a hora em que chegou: a frase encontra
      as fotos dela mesmo chegando atrasada.
4. **O que significa cada sinal.**

   | Mensagem | O que quer dizer |
   |---|---|
   | **"É do mesmo assunto da anterior (…)?"** | você mandou fotos sem frase logo depois de outro lote; **Sim** repete o título e a data do anterior, **Outra coisa** abre as perguntas |
   | **"Recebi."** | uma vez por lote: dois "Recebi." seguidos são dois lotes |

5. **O que NÃO faz.**
   - **Não separa** um lote que você manda enquanto ela ainda espera uma resposta sua: ele entra na
     mesma conversa. Responda primeiro e depois mande o próximo.
   - **Não corrige** foto que já entrou no catálogo com o título errado: isso é na Caixa do marketing.
   - **Não lê** o conteúdo da foto para decidir o lote: quem decide é a hora em que você mandou.

**O `recepcao.md`** ganha uma linha: no canal de campo, o lote é contado pela hora de envio, e
"Recebi." duas vezes seguidas quer dizer dois lotes.

## Próximo passo
/writing-plans
