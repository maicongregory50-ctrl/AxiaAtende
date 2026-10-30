# Ler a conversa na Recepção, com o texto que nós mandamos
**Data:** 2026-10-30
**Chamado:** #1205
**Status:** APROVADO (dono, 30/10/2026: caminho B)

## Contexto

O dono quer ler, na tela, o que o cliente escreveu e o que o recepcionista respondeu. O pedido nasceu
do caso da COPERMAP (#1204): para saber o que o cliente escreveu foi preciso pedir à sessão, que lê
pelo `scripts/ler_conversa.py` (#981). Em 13/10 o dono recusou uma "tela de Conversas" (#989), mas
aquela tinha **resposta de pessoa** ("precisa muita coisa, não penso em rodar agora; só leitura
agora"). Esta é só leitura, e o pedido de agora a supera.

O que existe (inventário de 30/10):
- `ler_conversa.conversa()` já monta a pessoa inteira em ordem: o que chegou (`eventos_meta`), o que
  saiu (`enviadas`), os atendimentos (`conversas`), o canal de campo e a vaga. Devolve **linhas de
  texto prontas para o terminal**, não itens.
- A tela Recepção (`127.0.0.1:8009`, com login, só no servidor) tem um clique por linha: a coluna
  *Quem* abre o WhatsApp Web da pessoa (#1025).
- **Do nosso lado só existe o resumo.** `enviadas.resumo` guarda `"menu principal"`,
  `"ia retomou fornecedores.ainda"`, `"material criacao-4"`, e não o texto que o cliente viu.
- O recepcionista manda por **um só lugar**, a `Saida` (`backend/saida.py`), com oito formas (texto,
  botões, lista, imagem, contato, modelo, link, documento). Cada uma devolve o `wamid` da Meta. A
  `SaidaMeta` é criada em quatro lugares: `recepcionista.py`, `pergunta_agora.py`,
  `scripts/portao_retroativo.py`, `scripts/prova_agora.py`. O registro em `enviadas` é feito em
  **13 pontos em 5 arquivos**, todos gravando o `wamid`.

## Os fios que encostam

**Quem mais escreve.** A tabela nova (`atendimento.enviadas_texto`) tem **um escritor só**: a
`SaidaMeta`, logo depois de a Meta aceitar o envio. Ninguém mais grava nela. As tabelas lidas pela
janela (`conversas`, `eventos_meta`, `enviadas`, `material_de_campo`, `candidaturas`,
`campo_frases`, `modelos`) **não ganham escritor**: a janela só lê. O registro de leitura das telas
(`C:\Logs\AxiaAtende\telas\leituras.jsonl`, arquivo novo) tem um escritor só, a rota da janela; o
`leituras.jsonl` do #981 continua sendo só do script (um escritor por arquivo, regra do #981).

**Quem lê para decidir.** Ninguém decide pelo texto guardado: nenhum laço, envio ou contagem o lê.
Só a janela o mostra. O papel `axiaatende_ro` passa a enxergá-lo pelo `ALTER DEFAULT PRIVILEGES` já
declarado no #981, e o `ler_conversa.py` passa a mostrá-lo também (a mesma montagem).

**Quem volta depois.** Nenhuma rotina revisita `enviadas_texto`. O backup diário do banco do
atendimento a leva junto (é tabela do mesmo banco).

## O universo medido

- 240 conversas abertas por mensagem (todas); 48 nos últimos 7 dias. A janela abre qualquer uma.
- 1.037 envios em `enviadas`, 237 sem `conversa_id` (avisos, convites, portão): a janela os mostra
  pelo número, como o `ler_conversa` faz. **Todos os 1.037 ficam em resumo**: o texto só passa a ser
  guardado do restart em diante.
- Do lado do cliente, por tipo (todas as mensagens recebidas): toque 373, texto 345, foto 113,
  documento 48, `unsupported` 29, botão de modelo 19, reação 13, vídeo 1, áudio 1, figurinha 1,
  `system` 1. Texto e toque aparecem por inteiro; mídia aparece como "[foto]" com a legenda.
- Formas de envio a capturar: 8 métodos da `Saida`; `SaidaMeta` criada em 4 lugares.

## Conformidade com o Manual legal

Não se aplica: não há regra tributária nem legal. Há dado pessoal (a conversa), e a finalidade
escrita no #981 vale igual: ajustar o atendimento; nada sai do servidor.

## Conformidade com a casa

- **R2 (dado vivo com cópia):** conforme. A tabela nova é do banco `axiaatende`, coberto por
  `rotina:backup-axiaatende-banco` e `rotina:backup-axiaatende-banco-nuvem` e ensaiado toda noite
  (#1144). Nenhum dado novo fora do banco além do log de leituras, que é registro e não dado vivo.
- **R1, R3, R4, R7, R9:** não tocadas. Nenhuma porta, serviço, segredo, chamada a modelo ou sessão
  nova: a janela é uma rota a mais no processo das telas (`127.0.0.1:8009`, com login), e a captura
  roda dentro do recepcionista que já existe, sem rede nova.
- **Dado pessoal:** os leitores não aumentam. A conversa já chega à tela das mesmas pessoas com login,
  e o processo das telas já tinha acesso a essas tabelas. O que muda é que a leitura fica registrada,
  como a da sessão.

## Decisão

Caminho B, escolhido pelo dono em 30/10/2026, com três respostas antes: **a pessoa inteira** (não só
o atendimento clicado); **passar a guardar o texto** (não ficar no resumo); **registrar cada
abertura**, como a leitura da sessão.

- **A — duas etapas:** a janela com resumo agora, o texto num chamado seguinte. Recusado: o resumo é
  o que o dono não quer ler.
- **B — o escolhido:** a janela, mais a captura do texto **na `Saida`**, por `wamid`, numa tabela à
  parte com um escritor só. Os 13 pontos de `enviadas` não mudam, e um ponto de envio novo nasce
  coberto sem ninguém lembrar.
- **C — coluna em `enviadas`, preenchida nos 13 pontos:** recusado. O próximo ponto que esquecer o
  texto devolve a janela ao resumo em silêncio.

## Escopo desta etapa

**Dentro**
1. **Migração 047** (o número é o próximo livre na hora do plano): `atendimento.enviadas_texto`
   (`wamid` PK, `tipo`, `texto`, `opcoes jsonb` com os títulos dos botões e das linhas, `modelo` e
   `variaveis` para modelo, `legenda`, `gravado_em`) e o ajuste `enviadas.guardar_texto = true`
   (a chave da captura). `_VOLTA` derruba os dois.
2. **A captura na `SaidaMeta`:** parâmetro `guardar` (opcional) no construtor. Depois de cada envio
   que a Meta aceitou, ele grava o conteúdo exato por `wamid`, **numa conexão própria e curta**,
   porque o envio já saiu: se a transação de quem mandou desfizer, o texto continua verdadeiro.
   Qualquer erro ao gravar vira uma linha no log e **nunca** derruba o envio. Com o ajuste em
   `false`, não grava nada. Os quatro lugares que criam a `SaidaMeta` passam o `guardar`.
3. **A montagem em itens:** a lógica de `ler_conversa.conversa()` sai para o backend (um módulo de
   leitura) e devolve itens (`quando`, `lado`, `tipo`, `texto`, `estado`, `conversa_id`,
   `resumo`); o script passa a formatar esses itens em linhas, com a mesma saída de hoje mais o
   texto quando houver. Modelo aparece com o texto do modelo e as variáveis preenchidas (lido de
   `modelos`).
4. **A rota da janela** nas telas (com login): a pessoa daquela conversa, inteira. Cada chamada
   grava uma linha em `C:\Logs\AxiaAtende\telas\leituras.jsonl` (quando, usuário da tela, conversa,
   quantos itens).
5. **A janela na Recepção:** abre ao clicar na linha, **fora da coluna Quem**. Balões em ordem de
   tempo, o cliente de um lado e nós do outro; o atendimento clicado em destaque e a tela já rolada
   até ele; nosso envio sem texto guardado aparece como resumo, marcado como resumo; mídia como
   "[foto]" com a legenda; o estado (entregue, lida, falhou) em cada envio nosso.
6. **Manual:** `recepcao.md` ganha "Ler a conversa"; `leitura-da-sessao.md` diz que o texto passa a
   aparecer; `INDICE.md` sem mudança de linha (a tela é a mesma).

**Fora**
- Baixar ou mostrar a mídia (a foto, o PDF, o áudio): etapa própria, se fizer falta.
- Responder pela janela: continua recusado (#989). A janela não manda nada.
- Recuperar o texto dos 1.037 envios antigos: não existe em lugar nenhum.
- Busca por texto entre conversas.

## Impacto em produção

- `axiaatende-recepcionista` (o processo exposto à internet): a captura entra em todo envio. Uma
  conexão curta a mais por envio (dezenas por dia).
- `axiaatende-backend` (as telas): a rota nova, o log novo e o frontend rebuildado.
- Migração 047 aplicada ao subir. Restart dos dois, recepcionista primeiro: **mão do dono** (elevado).
- A conversa da Recepção passa a mostrar o texto do restart em diante; o histórico, em resumo.

## ROLLBACK_PLAN

1. **Só a captura:** `UPDATE atendimento.ajustes SET valor = 'false'::jsonb WHERE chave = 'enviadas.guardar_texto'`.
   Vale no próximo envio, sem restart. A janela continua, mostrando o resumo nos envios novos.
2. **Tudo:** reverter o commit, rebuildar o frontend, restart dos dois serviços, e rodar
   `047_..._VOLTA.sql` (derruba a tabela e o ajuste). Perde-se o texto guardado até ali; os envios e
   as conversas não são tocados.
3. `C:\Logs\AxiaAtende\telas\leituras.jsonl` fica como registro.

## Manual de uso

**Para que serve.** Ler o atendimento de uma pessoa sem sair da Recepção e sem pedir à sessão: o que
ela escreveu e tocou, e o que a OlivIA mandou, na ordem em que aconteceu.

**Quem usa e quando.** Quem confere o atendimento, quando uma linha chama atenção: "parou no meio",
"disse que não foi atendido", nota Ruim, ou um nome conhecido.

**O caminho comum.**
1. Na Recepção, clique na linha (em qualquer lugar **menos** no nome ou no número, que continuam
   abrindo o seu WhatsApp Web).
2. Abre a janela com tudo o que essa pessoa trocou com a Renascer, do mais antigo ao mais novo, já
   rolada até o atendimento que você clicou, que aparece em destaque.
3. Leia. Feche no X ou com Esc. Nada é mandado a ninguém.

**O que significa cada sinal.**
- **Balão à esquerda:** o que a pessoa mandou. Texto inteiro; toque em botão aparece com o nome do
  botão; foto, documento e áudio aparecem como **[foto]**, **[documento]**, **[áudio]** com a
  legenda, sem a imagem.
- **Balão à direita:** o que nós mandamos, com o texto exato, os botões e a lista que a pessoa viu, e
  o estado embaixo: *entregue*, *lida*, *falhou*.
- **Balão à direita em itálico, "resumo":** envio de antes de 30/10/2026, quando o texto não era
  guardado. Mostra só o que era ("menu principal"), não as palavras.
- **Faixa "atendimento"**: onde cada atendimento começou. O que você clicou fica destacado.

**O que NÃO faz.** Não responde nem manda nada: para falar com a pessoa, use o nome ou o número (o
seu WhatsApp Web). Não mostra a foto nem abre o PDF. Não recupera o texto dos envios antigos. E toda
abertura fica registrada: quem abriu e quando.

## Próximo passo

`/writing-plans` — ou o PLANEJADOR, que esta spec aprovada dispara.
