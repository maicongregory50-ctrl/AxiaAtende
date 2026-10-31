# Plano — O chamado no WhatsApp: a mensagem sai, a resposta volta
**Data:** 2026-10-31
**Chamado:** #1222
**Spec de origem:** docs/specs/2026-10-31-o-chamado-no-whatsapp.md
**Status:** APROVADO
**Executável pelo agente:** não -- executado nesta mesma sessão, com o dono no teclado.

## Correções à spec que o plano achou

1. **O Ficou bom e o Não ficou bom não podem ir pela rota do botão da caixa.** `POST
   /demandas/{id}/entrega/validar` compara o autor pelo id CRU (`demandas.py:2857`, regra do #188:
   "agente em nome de alguém não avalia a própria entrega"). O Atende é agente. A saída é uma rota
   própria do agente ATENDIMENTO, que confere o número contra o WhatsApp do autor e chama
   `esteira_service.validar_entrega` com `pelo_autor=True`. A regra do #188 continua intacta para
   todo o resto: só esta rota, só este agente, só com o número batendo.
2. **A entrega e o fechamento gravam o mesmo tipo de evento (`entregue`)** (`esteira_service.py:2289`).
   O espelho distingue pelo texto que o próprio serviço escreve ("Fechado: ..."), que passa a ser
   constante exportada, presa por teste.
3. **Número da migração do Atende: 051.** A 050 é do #1223 (`050_custos.sql`), em paralelo.

## O que a execução ajustou (31/10/2026)

- A atividade do agente chama-se `SUP.WPP` (cadeia SUP, ao lado das outras da fila), e não `DEM.WPP`.
- A agenda do atendimento **não** mudou: o número do autor vem em cada linha de `/saida`, e o ERP
  confere o número na volta; o Atende não precisa saber quem é quem.
- A migração é a **052** (`052_pendencias.sql`): o #1223 gravou a `051_precos_oficiais.sql` no meio.
- A regra das rotas mora em `backend/services/demandas_whatsapp_service.py` (testável sem o `.env`),
  e o router só traduz para HTTP. Há uma quarta rota, `GET /estado`, para o Atende fechar a espera que
  deixou de valer.
- A resposta pelo WhatsApp é gravada com executor = o autor (quem teclou foi ele), com o texto
  começando por "(pelo WhatsApp)": é o que acende "resposta nova" e acorda o fio.

## Passos

**ERP (C:\AxiaGestao)**

1. **Fase 621** (`schema_axia_fase621_chamado_no_whatsapp.sql` + `_VOLTA`): `axia.usuarios.whatsapp`
   (texto, nulo, CHECK `^55[1-9][0-9]9?[0-9]{8}$`, UNIQUE parcial onde não nulo); atividade
   `DEM.WPP` ligada ao agente 130. — verificação: o teste do passo 4 aplica a fase dentro da transação
   quando falta, e o pós-entrega ensaia — reversão: a `_VOLTA`.
2. **A régua do texto técnico ao autor**: em `registrar_evento` (`demandas.py:3895`) e em
   `entregar_ao_autor`, a síntese (acima de `--- para quem despacha ---`) com hash de commit (7 a 40
   hex isolados), caminho com `\` ou `/` de arquivo, ou nome `*.py|*.ps1|*.sql|*.jsx` é recusada com
   400 e a frase da spec. Só para texto que chega ao autor (comentário e devolução), nunca para
   `analise`/`aviso`. — verificação: teste com o texto do #1191 (recusa) e com as três devoluções do
   Benedito de 29–30/10 (passam) — reversão: tirar a chamada.
3. **O WhatsApp do usuário**: `UsuarioResponse`, `PATCH /usuarios/{id}` aceita `whatsapp` (normaliza
   para só dígitos com 55; recusa formato inválido); `MapaAtivPage.jsx` ganha o campo no usuário; a
   agenda do atendimento (`atendimento_agenda_service`) passa a levar `usuario_id` e o papel `equipe`
   para quem tem WhatsApp no usuário. — verificação: teste do PATCH; build do frontend — reversão:
   reverter os arquivos.
4. **As rotas do agente** (`backend/routers/demandas_whatsapp.py`, prefixo `/demandas/whatsapp`,
   `require_atividade("DEM.WPP")`, declaradas antes das genéricas):
   - `GET /saida?depois=<evento_id>`: os eventos de `EVENTOS_VISIVEIS_AO_AUTOR` com texto
     (comentário, entregue, recusada), autor do evento ≠ autor do chamado, autor do chamado com
     WhatsApp, síntese não vazia, sem o "Fechado: ..."; cada linha leva demanda, título, número do
     autor, texto da síntese e a classe (`informativo`, `pergunta`, `entrega`). Também devolve, para
     as demandas que o Atende pedir (`abertas=1,2,3`), se a pendência ainda vale (nó e último evento).
   - `POST /{id}/resposta` {numero, texto}: confere número = WhatsApp do autor; grava comentário
     em nome do autor, executor 130.
   - `POST /{id}/validar` {numero, resultado, motivo}: confere o número; `validar_entrega` com
     `pelo_autor=True`.
   — verificação: `test_1222_whatsapp.py` (número errado → 403; chamado de outro → 403; fechado →
   "quem pediu confirmou"; não ficou bom → reaberta; o fio vê o comentário como do autor) — reversão:
   tirar o router do `main.py`.

**Atende (C:\AxiaAtende)**

5. **Migração 051** (`051_pendencias.sql` + `_VOLTA`): `atendimento.pendencias` (tipo, referencia,
   para_whatsapp, usuario_erp_id, rotulo, resumo, classe, aberta_em, ultima_em, fechada_em,
   motivo_fechamento) e `atendimento.pendencias_mensagens` (pendencia_id, sentido, wamid UNIQUE,
   texto, estado `esperando|enviada|entregue|erro`, origem_evento_id UNIQUE, criado_em, enviada_em,
   erro); o cursor em `ajustes` (`pendencias.cursor`), `pendencias.ligado = false`,
   `pendencias.juntar_minutos = 10`; modelo e tipo de aviso não mudam (a reabertura já existe). —
   verificação: ida e volta no teste, no molde do `test_auditoria_erp` — reversão: `_VOLTA`.
6. **O molde e o tipo chamado** (`backend/pendencias.py`): registro de tipos (`TIPOS = {"chamado":
   TipoChamado}`), cada tipo com `entregar_resposta`, `validar` e `ainda_vale`. — verificação: testes
   unitários com ERP falso.
7. **A puxada** (`erp.py` + thread `pendencias_do_erp` de 60 s no `main.py`): busca `/saida` depois do
   cursor, grava a mensagem `esperando` (informativo sem pendência aberta; pergunta e entrega abrem
   pendência), avança o cursor; devolve as respostas `entregue` pendentes; fecha pendência que não
   vale mais. Com `pendencias.ligado = false` não faz nada. — verificação: teste com ERP falso,
   inclusive ERP fora do ar (o cursor não anda).
8. **O envio** (no porteiro, `envio.py`): mensagens `esperando` do mesmo número dentro de
   `juntar_minutos` saem juntas, um bloco por chamado, com o título em cima; janela aberta → texto (a
   entrega com os botões `pend:ok:<id>` e `pend:nao:<id>`); janela fechada → informativo espera, e
   pergunta/entrega entram na reabertura que já existe. O `wamid` de cada envio fica na mensagem. —
   verificação: testes com Saida falsa: dentro, fora, junção, entrega com botões.
9. **A volta pelo motor** (`motor.tratar`):
   - degrau 1, no topo: `contexto` = `wamid` de mensagem de pendência → resposta à pendência
     ("Anotado no chamado N ✓"); de informativo → a linha do aviso, uma vez por chamado; toques
     `pend:` → validar (Não ficou bom pede o motivo numa linha e espera o próximo texto);
   - degrau 2, no lugar do pega-tudo, antes de `campo.texto_de_interno`: texto sem citar de quem tem
     pendência aberta → OlivIA propõe (passo 10) e a pessoa confirma ([Sim] [Outro chamado] [Outro
     assunto]);
   - o "Bom dia" que soltou guardado não leva o menu da casa.
   — verificação: testes de cada caso da maquete, e os testes de hoje do motor, campo, vaga e
   clientes do dia sem mudança.
10. **O segundo uso da OlivIA** (`ia.py`, `escolher_pendencia(texto, pendencias)`): enum das ids
    abertas + "nenhuma", mesmas regras (8 s, falha = nenhuma, sem ferramenta); registra o custo como
    as outras quatro depois do #1223 — conferir o arquivo antes de editar. — verificação: teste com
    IA falsa; sem pendência a IA não é chamada.
11. **A tela Envios** mostra as pendências de chamado (aberta, esperando, respondida, fechada). —
    verificação: build.
12. **Inventário de agentes** (`C:\AxiaSecurity\design\agentes.json`): a linha do uso
    `escolha-pendencia` da OlivIA, coordenada com o #1223. — verificação:
    `conferir_inventario_agentes.py`.
13. **Manuais**: Atende `docs/manuais/envios.md` + manual novo `chamado-no-whatsapp.md` com a linha
    no `INDICE.md`; ERP: o campo WhatsApp no manual do Mapa de Atividades/usuário
    (`usuario-novo-e-empresa.md`) e a régua do texto técnico no manual da fila. — verificação:
    `conferir_indice.py` no ERP; alguém de fora lê o caminho comum.
14. **Bateria** dos dois projetos (ERP com `--continue-on-collection-errors`, as 2 coleções sem
    `.env` já conhecidas; Atende inteira). — verificação: só falhas já existentes.
15. **Subida**: fase621 pela Porta-Ação (ensaiar, aplicar); restart 8001 e 3001 (build antes);
    restart do axiaatende-backend (a 051 aplica no arranque). — verificação: `/saude` lista a 051;
    rotas respondem 401 sem token.
16. **A prova em duas voltas.** O espelho só manda o que outro escreveu ao autor, e os chamados do
    dono são escritos por ele mesmo; por isso a prova usa o #350, aberto pelo usuário Financeiro.
    - Volta 1, com o número do DONO posto no usuário Financeiro: ligar `pendencias.ligado`; uma
      pergunta no #350 ("teste do #1222: responda citando"); o dono responde citando e sem citar;
      confere o comentário no #350 em nome do Financeiro e o "Anotado".
    - Volta 2: trocar para o número da Fran; o informativo da auditoria (o texto aprovado) como
      comentário no #350. Ele espera calado e sai quando ela escrever na terça.
    — verificação: as duas voltas como na maquete — reversão: `pendencias.ligado = false`.
17. **Devolver**: comentário no #1222 para o dono; o #1222 **não** fecha: fica a migração dos fios
    antigos ao molde (comentário #10540).

## O que só você pode fazer

- Preencher o WhatsApp no seu usuário e no usuário Financeiro (Mapa de Atividades → usuário), ou me
  dizer os números para eu pôr pela tela.
- Decidir o login da Fran: se mais alguém usa "Financeiro", ela precisa de login próprio antes.
- Mandar uma mensagem qualquer ao número da empresa na hora da prova (abre a janela).

```pos-entrega
reiniciar=axiagestao-backend
reiniciar=axiagestao-frontend
dono=fase621 do ERP pela Porta-Acao (a fase mora no AxiaGestao, nao no projeto dono); migracao 051 e restart do AxiaAtende; WhatsApp dos usuarios; ligar pendencias.ligado depois da prova
```

## Riscos de execução identificados

- Passo 2 (régua) no ar antes do resto: recusa comentário técnico mal posto; é o comportamento
  desejado, seguro ficar parado.
- Fase 621 aplicada sem o código: coluna e atividade sem uso; seguro.
- Migração 051 aplicada com `pendencias.ligado = false`: nada sai, nada é tomado; seguro.
- Passo 9 é o de maior risco (a corrente do motor): os degraus só agem com pendência ou `pend:`;
  sem pendência o caminho é o de hoje. Os testes de hoje do motor são a régua.
- Interrompido entre puxada e envio: as mensagens ficam `esperando` e saem na volta seguinte; o
  cursor só anda depois de gravar.

## Linha de abertura da sessão de execução

Executado nesta mesma sessão. Se cair: ler `C:\AxiaAtende\CLAUDE.md` e
`C:\SuporteAxia\docs\PADRAO-TRABALHO.md`; executar este plano (spec ao lado); faixa: aplicação de
plano aprovado. Chamado #1222; todo commit cita `#1222`, e o primeiro ato é
`tratar 1222 --status em_andamento` pela skill `/demanda`. Não se reabrem: caminho C, molde no Atende,
WhatsApp em `axia.usuarios`, pendência só pergunta e entrega, informativo espera calado, junção de
10 min, régua do texto técnico antes de ligar. O que vai para a tela está no `PADRAO-TRABALHO.md` §1.
Parar em "O que só você pode fazer".
