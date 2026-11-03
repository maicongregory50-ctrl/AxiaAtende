# Roteador com contexto por contato: a OlivIA escolhe o assunto pela conversa, não pela ordem dos degraus
**Data:** 2026-11-03
**Chamado:** #1238
**Status:** APROVADO

## Contexto

O WhatsApp da empresa está virando o canal de trabalho da equipe: chamado (#1222), cliente do dia
(#1090), foto do campo (#970), logo de cliente (#1036), currículo (#1098). Cada um desses fios nasceu
com estado próprio e um degrau próprio no motor, e quem decide para onde vai o texto de um interno é a
**ordem fixa** desses degraus: o primeiro que aceita o texto fica com ele. A OlivIA lê **uma** mensagem,
sem memória por contato, e só é chamada dentro de um degrau, para escolher de uma lista.

A prova do #1222, em 03/11/2026, com o dono no celular, mostrou o defeito três vezes no mesmo dia:

- "Ok, recebi" e "blz, legal.", com um chamado esperando resposta, viraram anotação do cliente aberto em
  Meus clientes (o degrau do cliente vinha antes);
- com a oferta do chamado movida para antes do cliente (commit 2a63149), a legenda de um vídeo mandado
  26 segundos antes foi roubada por "É sobre o Chamado 1222?", o canal de campo perguntou a legenda, o
  "." que respondia a essa pergunta foi roubado de novo, e "Outro assunto" jogou o "." no cliente
  seguinte da fila. Quatro mensagens para um vídeo com legenda;
- a DJ AGRO mandou uma logo em PDF e uma foto no mesmo segundo, sem texto: dois fios abriram, duas
  perguntas saíram, nenhuma foi respondida, e a foto entrou no catálogo sem legenda.

Os dois freios de hoje (commits 2a63149, 393b06c e 81eebd0: oferta antes do cliente, pergunta direta com
um chamado só, foto esperando legenda vence a oferta) são remendos na ordem. Nas palavras do dono: *"sem
contexto, lendo uma mensagem por vez, não vai funcionar"*; *"não esperar a base de texto para desenhar,
porque quando a base chega a bagunça já foi feita"*; *"se a gente deixar por menu de ida e volta, a
pessoa não vai usar"*.

**A fronteira, decidida pelo dono:** só a equipe interna. Quem vem de fora continua por botão. O
recepcionista é o único processo da casa que a internet alcança, e a regra "IA sem ferramenta, só chave
de lista fechada" continua valendo para todos.

## Os fios que encostam

**Quem escreve o que o roteador escreve.** O roteador escreve em **uma** tabela nova,
`atendimento.roteador` (o registro de decisão: pessoa, mensagem, candidatos, destino, sinal que
decidiu, confiança, corrigido_em). Ninguém mais escreve nela. **Ele não escreve nas tabelas dos fios**:
escolhe qual fio recebe o texto e o fio grava como hoje (`pendencias._anotar_resposta`,
`campo.responder`/`_lider`, `logos.responder`, `clientes_do_dia.tratar`, `vaga.retorno_da_fran`).

**Quem o roteador lê para decidir** (só leitura, medido em 03/11 no código):

| Assunto aberto | Onde mora | Quem mais escreve lá |
|---|---|---|
| chamado esperando resposta ou validação | `atendimento.pendencias` (`espera IS NOT NULL`) | `pendencias_erp.volta` (as telas), `pendencias.tratar` |
| foto/vídeo esperando legenda ou com conversa aberta | `atendimento.material_de_campo` (`pergunta_pendente`, líder sem `fechado_em`) | `campo.receber`, `campo.responder`, a rotina do minuto (`_fechar`) |
| logo esperando cliente ou marca | `atendimento.logos_de_cliente` (`pergunta_pendente`) | `logos.receber`, `logos.responder`, `logos.puxada` (o marketing) |
| cliente aberto do consultor | `atendimento.clientes_registros` (`aberto`/`conferir`, 24 h) | `clientes_do_dia.tratar`, `_toque`, `rodar` |
| currículo esperando o retorno da Fran | `atendimento.candidaturas` (`fran_wamid` sem `feedback`) | `vaga.retorno_da_fran`, `vaga.mandar_a_fran` |
| o histórico de 24 h | `atendimento.eventos_meta` (o que chegou), `atendimento.enviadas` (o que saiu) | o recepcionista, todos os fios (desde o #1236 também Meus clientes) |

**Quem volta depois** e não muda: a rotina do minuto (fecha grupos de foto por prazo, manda pendências
depois da junção, roda clientes e avisa), o marketing puxando logos (`/logos/pendentes`), as telas levando
respostas de chamado ao ERP (`pendencias_erp.volta`, a cada minuto). **A carência** (abaixo) encosta na
última: a resposta encaminhada a um chamado fica `a_entregar` com `entregar_apos`, e a volta das telas
só leva o que já venceu a carência.

**A régua que lê para decidir e muda de dono:** hoje a ordem dos degraus em `motor.tratar` (linhas
700-760) é a régua. Com a chave ligada, para interno com texto sem citar e com assunto aberto, a régua
passa a ser a resposta do roteador; a ordem continua valendo para todo o resto (toques, mídia, citação,
quem é de fora, chave desligada, sem assunto aberto, OlivIA fora).

## O universo medido

Equipe e representantes (agenda do ERP, papéis `equipe`/`representante`), últimos 30 dias até
03/11/2026, `eventos_meta` e `enviadas` de produção:

| Pressuposto | Contagem |
|---|---|
| textos de internos | **82** (5 pessoas, 19 dias) |
| citando a mensagem ("deslize") | **2** — a citação não é hábito; continua valendo como atalho |
| até 2 min depois de uma mídia da própria pessoa | **16** |
| até 10 min depois de uma mídia | **28** — um terço é legenda ou comentário de foto |
| até 10 min depois de uma mensagem nossa | **42** — metade é resposta a algo que mandamos |
| com foto aberta esperando algo | **31** |
| com logo aberta | **6** |
| com cliente aberto em Meus clientes | **2** |
| toques (botões) de internos | 56 |
| mídias de internos | 75 |
| chamadas da OlivIA no período (todas as funções) | **13**, Haiku, 22 mil tokens de entrada |

O que a contagem diz: proximidade e assunto aberto explicam a maior parte dos textos; a citação não
explica nada. Um roteador em Haiku com uns 3 mil tokens de retrato por texto, chamado só quando há
assunto aberto (hoje uns 40 dos 82), custa centavos por mês. Custo não é objeção.

O que ela **não** diz, e é por isso que o registro de decisão nasce junto: quantos desses textos foram
parar no fio errado. Hoje isso só aparece em leitura manual (a de 03/11 achou três em um dia).

## Conformidade com o Manual legal

não se aplica: atendimento interno pelo WhatsApp, sem regra tributária, fiscal ou documento legal.

## Conformidade com a casa

Gatilhos tocados: **agente ou chamada a modelo de IA** (R7) e **dado novo** (R2). Não toca segredo
(R3: a chave da Anthropic do Atende já existe, com teto de gasto), nem serviço, porta ou exposição (R4/R1:
roda dentro do recepcionista, nada de bind novo), nem sessão de agente (R9), nem projeto novo (R8).

- **R7 — conforme, com uma linha a mais no inventário.** Trecho lido: *"Esta responsabilidade é sobre
  governança: quem existe, o que pode, quem desliga, quem é avisado"* e *"O que um agente pode fazer
  sozinho é decisão do código que o envolve"*. O roteador é a sexta chamada da OlivIA, no mesmo molde
  das cinco de `inventario-agentes.md` (chamada, API, lista fechada, desligamento por chave de ajuste).
  **Muda:** a linha `OlivIA · roteador de assunto da equipe` entra no inventário, passo próprio do plano,
  com `conferir_inventario_agentes.py` verde.
- **Política de uso de IA — conforme.** Trecho lido: *"Ler o atendimento do AxiaAtende em produção
  (#981)... A finalidade é ajustar o atendimento e a OlivIA da casa; nada da conversa sai do servidor e
  nenhuma conversa vai treinar modelo externo"*. O retrato de 24 h vai ao modelo pela mesma API e pela
  mesma chave que já recebem cada mensagem hoje; o que muda é a quantidade de texto por chamada, não o
  destino. **O retrato só leva mensagens trocadas com o número da empresa**, nunca o que a pessoa falou
  com terceiros (o sistema não tem isso). E só de interno: conversa de cliente não entra no roteador.
  A seção *Em aberto* da política ("conversas de cliente como base de treinamento") continua em aberto
  e esta spec não a decide.
- **R2 — conforme para o banco, e cria para os arquivos de áudio.** `atendimento.roteador` e
  `atendimento.audios` nascem no banco `axiaatende`, coberto por `backup_axiaatende_banco.ps1` (02:20,
  disco) e `backup_cloud_axiaatende_banco.ps1` (02:45, nuvem). Trecho lido no `PROJETO.md`/`CLAUDE.md`:
  *"Backup do banco (G6): ... 30 dias ... 90 dias"*. Os arquivos `.ogg` ficam em `<campo_pasta>/audio`,
  ao lado das fotos do campo, que **não têm backup próprio** hoje (a foto vai ao catálogo do marketing;
  o áudio vira texto no banco). Decisão desta spec: o áudio é apagado **7 dias** depois de transcrito
  (o texto fica); o que importa está no banco. É decisão do dono se a pasta entra no backup; a spec
  diz que não precisa.
- **R7 — o transcritor é modelo local, sem API.** Entra no inventário como `transcritor local ·
  faster-whisper`, tipo "chamada", coluna *API* = **local**, desligamento pela chave `audio.transcrever`.
  Não é agente: não decide nada, só converte áudio em texto, e o texto segue a régua de quem o leria.
- **Política de uso de IA — conforme.** O áudio de interno é dado da equipe, não de cliente; fica na
  máquina; nada vai a modelo externo. Áudio de cliente fica fora, de propósito, até a política decidir
  o uso de conversa de cliente.

## Decisão

**Caminho A — roteador na frente da corrente.** Um degrau novo em `motor.tratar`, que só age quando as
quatro condições valem: a chave `roteador.ligado` está ligada; quem escreve é da casa
(`internos.e_interno`); a entrada é texto sem citação e sem toque; e a pessoa tem **ao menos um** assunto
aberto. Fora disso, a corrente é a de hoje, inclusive os três freios de 03/11.

**O retrato que a OlivIA recebe:**
1. os assuntos abertos da pessoa, numerados, com rótulo e o último trecho trocado em cada um (a pergunta
   que fizemos, o que ela já escreveu), e há quanto tempo;
2. as últimas trocas com o número da empresa (24 h, no máximo 20 mensagens, nos dois sentidos, só
   texto e legendas, com a hora e quem falou);
3. o texto que chegou, e há quantos segundos chegou depois da última coisa que mandamos e da última
   mídia dela.

**O que ela devolve** (lista fechada, JSON com schema, como as outras cinco): `destino` (o número de um
assunto aberto, `nenhum` ou `correcao`), `confianca` (`alta`/`baixa`) e, na correção, o `destino_certo`.
Sem ferramenta. Erro, demora acima de 8 s ou resposta fora da lista = `nenhum`.

**O que o motor faz com a resposta:**
- `destino` com `confianca: alta` → chama o fio daquele assunto com o texto (o mesmo caminho de hoje para
  cada fio); a resposta ao interno é a de sempre do fio, que diz onde entrou ("Anotado no chamado 1222",
  "Recebi" com o nome da foto, "Anotado, cliente X"). **Decisão do dono: confirma só na dúvida.**
- `destino` com `confianca: baixa`, ou dois candidatos próximos → botões "É sobre o <assunto>?" com
  Sim / Outro assunto / a lista dos abertos (o molde do #1222, estendido aos outros fios).
- `nenhum` → a corrente de hoje, a partir do degrau seguinte ao roteador.
- `correcao` → vale só sobre o **último** encaminhamento dessa pessoa, em até 10 minutos. O que foi para
  um chamado e ainda está na **carência** sai da fila (`descartada`); o que já foi ao ERP ganha um segundo
  comentário em nome da pessoa dizendo que o anterior não era dali (agente não apaga registro). Legenda de
  foto volta a vazio; anotação de cliente é removida do texto; nome dito da logo é limpo. Depois, o texto
  original vai ao `destino_certo`, ou à lista se não houver.

**A carência (decisão do dono: a correção é escrita).** A resposta encaminhada a um chamado nasce com
`entregar_apos = agora + roteador.carencia_minutos` (padrão 3). `pendencias_erp.volta` só leva ao ERP o
que já venceu. Resposta por citação ou por botão não tem carência (a pessoa escolheu).

**Os sinais, do mais forte ao mais fraco, e nenhum obrigatório:** citação (nem passa pelo roteador);
assunto nomeado no texto (número do chamado, nome do cliente, o que a foto mostra); proximidade (o que
ela recebeu por último e há quanto tempo); botão. Quem decide é a OlivIA com o retrato; a proximidade
entra como **fato no retrato**, não como regra de código, salvo a que já existe (foto esperando legenda
vence tudo em até 2 minutos: fica como está, antes do roteador, porque é o caso mais frequente e o mais
caro de errar).

**O áudio entra como texto (decisão do dono, 03/11/2026, "mais a transcrição de áudio").** Hoje o
áudio de interno é ignorado com uma linha no log, e o de fora recebe "não leio isso". A casa já tem
transcritor local: o `faster-whisper` 1.2.1 com o modelo `large-v3-turbo` (1,6 GB), usado em outubro
nos áudios do caso JC Cereais, no ambiente temporário de uma sessão. Passa a valer, **só para interno**:

- o áudio é baixado como se baixa a foto (`campo.receber` já baixa mídia da Meta) para
  `<campo_pasta>/audio/<dia>/<wamid>.ogg`, e uma linha nasce em `atendimento.audios` (`wamid`, `wa_id`,
  `arquivo`, `duracao_s`, `transcrito_em`, `texto`, `erro`);
- a transcrição roda **fora do trabalhador do motor**, numa thread própria do recepcionista
  (`audio.laco`), um áudio por vez, na CPU, com o modelo carregado uma vez; o motor não espera;
- transcrito, o texto entra na corrente **como se fosse um texto da pessoa**, com `wamid` do áudio,
  `enviado_em` do áudio e a marca `(áudio)` no início, e passa pelo roteador como qualquer texto. A
  resposta ao interno diz onde entrou, como para texto;
- sem modelo no disco, chave desligada, erro ou áudio acima de `audio.maximo_s` (padrão 180 s): o
  comportamento de hoje (ignorado, linha no log), e a linha em `audios` guarda o `erro`;
- **de fora, nada muda**: cliente que manda áudio continua recebendo "não leio isso". Transcrever
  áudio do público é decisão à parte (dado pessoal de cliente, política em aberto).

Nada sai do servidor: o modelo roda na máquina, pela conta `LocalService` do recepcionista. **O que só
o dono pode fazer:** copiar o modelo do cache do perfil dele (`%USERPROFILE%\.cache\huggingface\hub`)
para `C:\Dados\AxiaAtende\modelos\faster-whisper-large-v3-turbo`, legível pelo serviço, e instalar
`faster-whisper` no venv do Atende (traz `ctranslate2` e `av`; só CPU). Chave `audio.transcrever`
em `ajustes`, nasce `false`. Tempo medido na sessão de outubro, a conferir no ensaio: minutos por
hora de áudio na CPU deste servidor; um áudio de WhatsApp de 30 s leva segundos.

**O registro de decisão** (`atendimento.roteador`): uma linha por texto que passou pelo roteador, com
`wamid`, `wa_id`, `candidatos` (os assuntos oferecidos), `destino`, `sinal` (`citacao`, `nomeado`,
`proximidade`, `botao`, `correcao`, `nenhum`, dito pela própria OlivIA no JSON), `confianca`, o custo
(`uso_ia`, função `roteador`), `corrigido_em` e `corrigido_para`. É o número que diz se a equipe trava:
a fração de textos que entram sem botão e sem correção.

**Por que A e não B (migrar os fios ao molde primeiro):** B é refatoração de cinco tabelas sem medir o
que importa, e deixa semanas sem o ganho justamente quando a equipe começa a usar. O roteador lê cada
estado onde ele mora hoje; o fio cujo estado ele mais erra em ler é o primeiro a migrar, pago pela
medição. **Por que não C (só proximidade):** cobre 42 de 82 e não lê "a Plantagro quer preço"; a
proximidade já está dentro do A como fato do retrato.

## Escopo desta etapa

**DENTRO:**
- a tabela `atendimento.roteador` e as chaves `roteador.ligado` (nasce `false`) e
  `roteador.carencia_minutos` (3) em `atendimento.ajustes` (migração 054);
- `backend/roteador.py`: o retrato (leitura dos cinco estados + histórico de 24 h), a chamada à OlivIA
  (`ia.rotear`), a aplicação do destino, a correção;
- o degrau no `motor.tratar`, atrás das quatro condições;
- a carência em `pendencias` (`entregar_apos`) e a volta das telas respeitando-a;
- a função `roteador` em `uso_ia` e na tela Custos;
- a linha no inventário de agentes;
- a **maquete escrita por nós**: 30 mensagens do jeito que a equipe escreve (as 82 reais ajudam),
  passadas pelo roteador no banco de teste com a IA falsa, e uma rodada com a OlivIA real em ensaio
  (`AXIAATENDE_AMBIENTE=dev`) antes de ligar;
- a leitura em sombra da primeira semana, com o registro de decisão como pauta;
- **a transcrição de áudio de interno**, local: a tabela `atendimento.audios` e a chave
  `audio.transcrever` (na mesma migração 054), `backend/audio.py` (download, fila, transcrição na
  thread própria, injeção como texto), o `faster-whisper` no venv do Atende, o modelo copiado pelo
  dono, a linha no inventário de agentes (modelo local, sem API), e a função `audio` na tela Custos com
  custo zero e a duração transcrita (para medir CPU, não dinheiro).

**FORA (anotado):**
- migrar os fios ao molde de pendência (passo seguinte, pago pela medição);
- intenções novas pelo texto (abrir chamado, pedir o próximo cliente): o dono escolheu só destinos
  entre abertos nesta etapa;
- áudio **de fora** (cliente, candidato): continua "não leio isso"; transcrever é decisão à parte;
- a Recepção mostrar quem da casa falou com a empresa hoje sem abrir conversa (requisito de tela,
  registrado no #1238, desenho à parte);
- o público externo: continua por botão, e esta spec não muda uma linha dele;
- a junção dos resumos de lote ao representante (regra do #1142, não de contexto).

## Impacto em produção

- **Serviços:** `axiaatende-recepcionista` (o degrau, a carência) e `axiaatende-backend` (a migração 054
  no arranque, a volta das telas respeitando `entregar_apos`, a função nova na tela Custos). Restart dos
  dois pela Porta-Ação. Sem janela: a chave nasce desligada e nada muda até ligá-la.
- **Dados:** duas tabelas novas (`roteador`, `audios`); quatro chaves em `ajustes` (`roteador.ligado`,
  `roteador.carencia_minutos`, `audio.transcrever`, `audio.maximo_s`); uma coluna nova em
  `pendencias_mensagens` (`entregar_apos`, nula para o que já existe); a pasta `audio/` ao lado das fotos.
  Nenhuma linha existente muda. O venv do Atende ganha `faster-whisper` (CPU); o modelo (1,6 GB) é copiado
  pelo dono para `C:\Dados\AxiaAtende\modelos`.
- **Custo:** mais uma função da OlivIA na API paga do Atende, chamada só para interno com assunto
  aberto. Estimativa pelo universo medido: 40 chamadas/mês × ~3 mil tokens, centavos. Aparece na tela
  Custos como `roteador`.
- **Quem sente:** só a equipe, e só com a chave ligada: menos botões, texto solto chegando ao lugar
  certo, e a frase de onde entrou.

## ROLLBACK_PLAN

0. `audio.transcrever = false`: o áudio volta a ser ignorado na hora; o que já foi transcrito fica como
   texto.
1. `roteador.ligado = false` em `atendimento.ajustes` (um `UPDATE`; o script `scripts/roteador.py
   desligar`, no molde do `chamado_no_whatsapp.py`). Na hora, sem restart: a corrente volta a ser a de
   hoje, com os três freios de 03/11. **É o rollback operacional inteiro.** O registro de decisão fica.
2. Se a carência atrapalhar sozinha: `roteador.carencia_minutos = 0` (o que está `a_entregar` sai na
   volta seguinte).
3. Reverter os commits do plano (código primeiro), restart dos dois serviços pela Porta-Ação.
4. `054_roteador_VOLTA.sql` (tabela, chaves e coluna somem; `casa.mudancas` limpa). Só depois do 3.
5. Tirar a linha do inventário de agentes, se a etapa for desfeita por inteiro.

## Manual de uso

**Para que serve.** Você escreve no WhatsApp da empresa do jeito que escreve para qualquer pessoa, e o
sistema entende de que assunto você está falando: o chamado que espera a sua resposta, a foto que você
acabou de mandar, o cliente que está aberto na sua lista do dia, a logo que você enviou. Ele deixa de
exigir que você deslize a mensagem ou escolha num menu.

**Quem usa e quando.** A equipe e os representantes, no dia a dia, sempre que escrevem para o número da
empresa com algum assunto em andamento. Quem é de fora da empresa não muda nada: continua pelo menu.

**O caminho comum.**
1. Chega alguma coisa do sistema (uma pergunta de chamado, "o que está acontecendo nessa foto?", a
   ficha do cliente do dia) ou você manda uma foto, uma logo, um vídeo.
2. Você responde escrevendo, sem deslizar. Pode citar o assunto pelo nome ("o 1222", "a Plantagro",
   "a foto do centeio") ou só responder.
3. A resposta diz onde a sua mensagem entrou: "Anotado no chamado 1222 ✓", "Recebi" (com o nome da
   foto), "Anotado, cliente Plantagro".
4. Se entrou no lugar errado, escreva na sequência: "não, era sobre a foto", "isso era do chamado". O
   sistema tira de onde pôs e leva para onde você disse. Uma mensagem para um chamado espera alguns
   minutos antes de ir ao sistema, justamente para você poder corrigir.
5. Se o sistema ficar em dúvida entre dois assuntos, ele pergunta com botões: "É sobre o Chamado
   1222?", com Sim, Outro assunto e a lista dos seus assuntos abertos.

**O que significa cada sinal.**
- *"Anotado no chamado N ✓"*: entrou no chamado, e vai ao sistema em alguns minutos.
- *"Recebi"* depois de uma foto: a frase virou a legenda da foto.
- *"É sobre ...?"* com botões: o sistema não teve certeza; escolha.
- *"Anotado. Esta mensagem é só um aviso..."*: você respondeu a um aviso que não pedia resposta.
- Nenhuma resposta: você não é da equipe no cadastro, ou não há assunto aberto e a sua mensagem seguiu o
  caminho de sempre (o menu da casa, a frase da próxima foto). Se esperava outra coisa, escreva *menu*.

**Áudio.** Você pode mandar áudio em vez de escrever. O sistema transcreve aqui na empresa (nada sai
para fora) e trata o texto como se você tivesse escrito: a resposta diz onde entrou, começando por
"(áudio)". Leva alguns segundos a mais que o texto. Áudio muito longo (acima de 3 minutos) não é
transcrito, e áudio de quem é de fora continua sem leitura.

**O que o sistema NÃO faz.**
- Não entende foto sem texto como resposta de chamado, e não lê áudio de quem é de fora.
- Não abre chamado novo, não pede o próximo cliente e não cria assunto pelo texto: só encaminha para
  assuntos que já estão abertos. Para abrir, use o sistema ou o menu.
- Não lembra de ontem: o contexto é das últimas 24 horas com o número da empresa.
- Não funciona para cliente ou pessoa de fora: para eles, o atendimento é por botão, como hoje.
- Não apaga comentário que já chegou ao sistema: a correção vira um aviso em seguida.

**Manuais que passam a dizer errado:** `docs/manuais/chamado-no-whatsapp.md` (item 5, "sem deslizar,
a OlivIA pergunta": passa a entrar direto quando está claro; e o item sobre correção), `campo-equipe.md`
(a frase solta depois da foto continua, mas o texto com chamado esperando pode ir ao chamado),
`meus-clientes.md` (idem para o cliente aberto). O plano corrige os três e cria `roteador.md` com o
texto acima.

## Próximo passo

/writing-plans
