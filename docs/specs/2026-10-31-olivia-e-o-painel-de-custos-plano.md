# Plano — A OlivIA no nome e o painel de custos das APIs pagas
**Data:** 2026-10-31
**Chamado:** #1223
**Spec de origem:** `C:\AxiaAtende\docs\specs\2026-10-31-olivia-e-o-painel-de-custos.md`
**Status:** APROVADO (dono, 31/10/2026, no Plan Mode)
**Executável pelo agente:** não -- executado nesta sessão, com o dono no teclado.

## Context

O dono quer saber **se cada função paga por uso compensa**, nas três APIs pagas da casa: Meta (WhatsApp),
Claude (as quatro funções da OlivIA) e Gemini (AxiaMarketing). Quer também que a OlivIA apareça com
esse nome no painel. A spec foi aprovada no caminho B. Na leitura do código para este plano apareceram
dois achados e uma decisão nova:

- **O registro do modelo por mensagem JÁ EXISTE** desde 30/10 (#1205): `SaidaMeta.modelo` grava
  `enviadas_texto.modelo` por `wamid` (`backend/texto_enviado.py`). Para a Meta não se escreve
  registro novo: o custo é uma LEITURA que junta `eventos_meta.pricing` → `enviadas_texto.modelo` →
  `modelos.uso`. O passado anterior a 30/10 é atribuído por `avisos.wamid` e pelo prefixo de
  `enviadas.resumo` (`material …` = convite, `direta …` = direta), marcado "pelo resumo". O que sobra
  fica "sem função".
- **A Meta cobrou `reabrir_avisos` como marketing**, embora o cadastro o declare UTILITY. O custo usa a
  categoria que a Meta cobrou, nunca a do cadastro.
- **Emenda à spec, decidida pelo dono em 31/10:** o Gemini **é empurrado** do Marketing ao Atende
  (`POST 127.0.0.1:8009/pedido/uso-ia`, com a chave de pedido que já existe), e não lido pelo Atende.
  A seta da casa não inverte, e nenhum segredo é criado (R3).

## Passos

**AxiaAtende** (testes contra o banco de teste da 5437, `pytest`)

1. **Migração `050_custos.sql` + `_VOLTA`.** Arquivos: `backend/migracoes/`. Cria:
   - `atendimento.uso_ia`: `id`, `em`, `origem` (`axiaatende`|`axiamarketing`), `id_origem`, `servico`
     (`claude`|`gemini`), `funcao`, `modelo`, `entrada`, `saida`, com `UNIQUE (origem, id_origem)`;
   - `atendimento.precos`: `servico`, `item` (categoria da Meta ou modelo), `vale_desde`,
     `por_mensagem`, `por_milhao_entrada`, `por_milhao_saida`, `moeda`, `criado_por`, `criado_em`.
     Semente: `claude-haiku-5-5` 0,10/0,50 desde 06/10/2026 (fonte: `ia.py`);
   - `atendimento.meta_cobrado` (`dia`, `categoria`, `volume`, `custo`, `moeda`, `lido_em`) e
     `atendimento.meta_conferencia` (`dia`, `situacao` `ok`|`sem_acesso`|`erro`, `detalhe`, `lido_em`);
   - o ajuste `custos.conferir_meta = true` em `atendimento.ajustes`;
   - GRANT SELECT ao `axiaatende_ro`, no padrão das migrações anteriores.

   Verificação: `pytest tests/test_migracoes.py`, e a `_VOLTA` aplicada e reaplicada no banco de teste.
2. **Claude: registrar o uso.** Arquivos: `backend/ia.py`, `backend/uso_ia.py` (novo, escritor único,
   conexão própria e curta, no molde de `texto_enviado.guardar_no_banco`) e `recepcionista.py:209`
   (`IA(cfg, registrar=uso_ia.guardar_no_banco(cfg))`). Cada um dos quatro métodos chama `registrar`
   depois de ter a resposta, inclusive a descartada, com a função `triagem`, `campo`, `curriculo` ou
   `visita`. Erro ao registrar vira uma linha no log e nunca muda o retorno.
   Verificação: um teste em `tests/test_ia.py` com cliente falso que devolve `usage`, e um teste de que
   `registrar` com exceção não muda a resposta.
3. **Rota que recebe o uso do Gemini.** Arquivo: `backend/rotas_pedido.py`, `POST /pedido/uso-ia`, com a
   mesma conferência de `chave_pedido` das rotas vizinhas. Grava idempotente por `(origem, id_origem)` e
   devolve os ids aceitos. Verificação: teste com chave errada (401), e o mesmo lote enviado duas vezes
   resultando em uma linha só.
4. **Conferência diária da Meta.** Arquivo: `backend/custos_meta.py` (novo), chamado de
   `rotina_do_minuto` (`recepcionista.py:141`) dentro de `try`. Roda uma vez por dia, depois das 06:00,
   se `custos.conferir_meta` estiver ligado. Faz GET `/{meta_conta_wa}?fields=currency,pricing_analytics…`
   com granularidade diária por `PRICING_CATEGORY`, dos últimos 3 dias (upsert), reaproveitando o
   cliente de `modelos_meta._cliente(cfg)`. 403 ou erro de permissão grava `sem_acesso`; qualquer outra
   falha grava `erro` com o detalhe. Nunca grava zero.
   Verificação: testes com `httpx.MockTransport` (resposta ok, 403 e forma inesperada).
5. **Rotas da tela Custos.** Arquivos: `backend/rotas_custos.py` (novo), `backend/main.py` e
   `backend/config.py` (`custos_logins` lido de `AXIAATENDE_CUSTOS_LOGINS`). Login fora da lista recebe
   403. Rotas:
   - `GET /custos?mes=AAAA-MM`: por serviço e por função, com quantidade, valor e os estados
     `sem preço`, `sem função`, `pelo resumo` e `sem acesso`, mais o calculado × cobrado da Meta por dia;
   - `GET` e `POST /custos/precos`: o preço novo é uma linha nova, e as antigas não são editadas;
   - `GET /custos/permitido`.

   O preço vigente é o de maior `vale_desde` que seja menor ou igual ao dia. Verificação: testes de
   atribuição contra os casos medidos (modelo → uso; aviso; resumo; sem função), de "sem preço" nunca
   ser 0 e do 403.
6. **Tela Custos.** Arquivos: `frontend/src/Custos.jsx` (novo) e `frontend/src/App.jsx` (a entrada do
   menu só aparece se `/custos/permitido` responder sim), no estilo da tela Envios (cartões e tabela).
   Mostra o mês com setas, uma tabela por função e serviço, o bloco "Calculado × Cobrado (Meta)" e uma
   aba Preços com um formulário de linha nova. Verificação: `npm run build` sem erro, e
   `servicos/axiaatende-backend.xml` com `AXIAATENDE_CUSTOS_LOGINS=maicon`.

**AxiaMarketing**

7. **Migração `049_uso_ia.sql` + `_VOLTA`.** Cria `casa.uso_ia` (`id`, `em`, `funcao`
   `edicao`|`olhar_foto`, `modelo`, `entrada`, `saida`, `enviado_em`). A `casa.gasto_ia` e o teto não
   são tocados. Verificação: a suíte de migrações do projeto.
8. **Gravar e empurrar.** Arquivos:
   - `scripts/motor_edicao.py`: devolve `uso` com o `usageMetadata` no JSON de `rodar`;
   - `backend/rotas_editor.py:298`, junto do INSERT do gasto, e `backend/visao.py:olhar`, junto do
     `anotar_gasto`: gravam em `casa.uso_ia`, com `entrada = promptTokenCount` e
     `saida = candidatesTokenCount + thoughtsTokenCount`;
   - `backend/uso_ia.py` (novo): `enviar_pendentes(cfg, con)` faz POST de até 200 linhas sem
     `enviado_em` ao Atende, pelo helper de `envio_whatsapp.py:53`, e marca as linhas aceitas.

   Chamado depois de cada gravação. Falha vira log, e a linha espera a próxima chamada. Verificação:
   testes com o Atende falso (aceita, recusa e fora do ar), e o teto continuando a ler só `gasto_ia`.

**AxiaSecurity (R7: "muda")**

9. **Inventário.** Arquivos: `design/agentes.json`, `scripts/conferir_agentes.py`,
   `scripts/gerar_tabela_agentes.py` e `scripts/painel_bloco.ps1`. As mudanças:
   - as quatro linhas viram "OlivIA · triagem", "OlivIA · campo", "OlivIA · currículo" e
     "OlivIA · registro de visita";
   - toda linha `agente`, `chamada` ou `sessao` ganha `cobranca` (`api` nas quatro da OlivIA e nas duas
     do Gemini; `assinatura` no resto);
   - o conferidor reprova linha sem o campo;
   - a tabela e o painel mostram o campo;
   - a tabela da governança é regerada.

   Verificação: `python -s scripts/conferir_agentes.py --sem-banco` sai 0, e `gerar_tabela_agentes.py`
   atualiza `docs/governanca/inventario-agentes.md`.
10. **Documentos.** Arquivos:
    - `C:\AxiaAtende\CLAUDE.md:13`: a OlivIA é a nossa atendente, e o Opa foi o que ela substituiu;
    - os dois `PROJETO.md`: o Marketing ganha em *Exijo* o `/pedido/uso-ia` do Atende, e o Atende ganha
      em *Ofereço* "recebe o uso de IA dos vizinhos";
    - uma emenda datada na spec sobre a direção do Gemini.

    Verificação: leitura.

**Fechamento**

11. **Manual.** `C:\AxiaAtende\docs\manuais\custos.md`, publicado da spec, com a linha no `INDICE.md` do
    AxiaAtende no formato de três colunas. `envios.md` ganha uma linha dizendo que o "Custo US$" é
    previsão e que o fato está em Custos. Vem antes do restart. Verificação: o caminho comum executável
    sem perguntar.
12. **Suítes completas, commits e push.** `pytest` no AxiaAtende e no AxiaMarketing. Um commit por
    projeto, citando `#1223`, nomeando os arquivos com `git commit -- <arquivos>`, e push.
13. **Restart e prova em produção**, pela sua mão (ver abaixo). Depois:
    - `/saude` do recepcionista, e as tabelas novas no `axiaatende_ro`;
    - a primeira linha de `uso_ia` na próxima mensagem escrita;
    - a conferência gravada (`ok` ou `sem_acesso`) no dia seguinte, às 06:00;
    - a tela Custos aberta com o seu login.
14. **Devolver o #1223** (`tratar --status resolvido --prova`, ou pelo rito da 5.2 se a 8001 o exigir),
    com o manual e o pré-requisito de cadastro: **lançar os preços da Meta (Marketing, Utilidade,
    marketing_lite) e do Gemini** na aba Preços. Sem eles a tela mostra "sem preço".

## O que só você pode fazer

- **Restart** em PowerShell elevado, depois do passo 12:
  `Restart-Service axiaatende-recepcionista, axiaatende-backend, axiamarketing-backend`
  As migrações 050 e 049 se aplicam sozinhas na subida (`migracoes.aplicar`).
- **Preços:** lançar na aba Preços da tela Custos o valor por mensagem de Marketing, Utilidade e
  marketing_lite (pela tabela da Meta para o Brasil ou pela fatura) e o do Gemini por milhão de tokens
  (`gemini-3.8-flash` e o modelo do editor).

## Riscos de execução identificados

- **Passos 1 a 11** só mexem em código e no banco de teste. Interromper deixa a árvore suja, sem efeito
  em produção.
- **Restart:** se o recepcionista não subir, quem escreve no WhatsApp fica sem resposta, e é o efeito
  mais visível da casa. A volta é reverter o commit e reiniciar. A migração 050 só cria tabelas, então
  não há estado intermediário perigoso.
- **A forma exata de `pricing_analytics`** não é conferida antes de subir: a sessão não lê o token. Se
  a forma divergir, a conferência grava `erro` com o detalhe, e o custo calculado continua certo.
- **`enviadas.guardar_texto=false`** desliga também a atribuição por modelo. A partir dali, as
  mensagens aparecem como "sem função", que é visível, não silencioso. O manual diz isso.

## Linha de abertura da sessão de execução

Esta mesma sessão executa, por decisão do dono. Primeiro ato: `tratar 1223 --status em_andamento`.
Todo commit cita `#1223`. As decisões que não se reabrem são o caminho B, o Gemini empurrado, o teto
pela estimativa e a tela só para o login `maicon`. O que vai para a tela durante a execução segue o
`PADRAO-TRABALHO.md` §1.
