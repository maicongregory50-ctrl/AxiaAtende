# Plano — O aviso de API externa recusando chega ao WhatsApp do dono
**Data:** 2026-11-09
**Chamado:** #1337
**Spec de origem:** docs/specs/2026-11-09-aviso-de-api-recusando-no-whatsapp.md
**Status:** APROVADO
**Executável pelo agente:** não -- a migração e o restart são de janela elevada, e a prova de efeito roda no ERP (outro repositório)

## Contexto

O ERP (#1280) deixa o aviso PENDENTE e publica as duas rotas; aqui só há um canal de avisos do ERP,
o da auditoria de estoque. Decisão da spec: generalizar `auditoria_erp.py` em canais e acrescentar o
canal `integracao_recusada`, sem copiar a volta. Com o porteiro ligado, o modelo da Meta é cadastro,
não pré-requisito.

## Passos

1. **Migração 060** — `backend/migracoes/060_aviso_integracao.sql` + `_VOLTA.sql`: CHECK
   `avisos_tipo` ganha `integracao_recusada` (lista inteira repetida, como a 049 faz); CHECK de `uso`
   em `modelos` ganha `aviso_integracao`; linha do modelo (`aviso_integracao`, UTILITY, variável
   `aviso1`, botão `nenhum`, texto `{{1}}` com a frase de abertura "Aviso do AxiaGestão: {{1}}");
   `avisos_auditoria_erp` ganha `canal text NOT NULL DEFAULT 'auditoria_estoque'` e a PK passa a
   `(canal, erp_aviso_id)`; ajuste `integracoes_para` com o mesmo valor de `auditoria_estoque_para`
   filtrado ao destino do dono (`ON CONFLICT DO NOTHING`). Guardas `DO $$` como a 049. — verificação:
   `pytest tests/test_migracoes.py` ida e volta — reversão: a `_VOLTA`.

2. **Os dois clientes em `erp.py`** — `integracoes_pendentes(cfg)` (molde `auditoria_pendentes`;
   devolve `{"pendentes": [{"id", "partes": [texto]}], "token"}` para o canal não precisar saber o
   formato do ERP) e `estado_do_aviso_integracao(cfg, token, id, estado, motivo, wamid)` (molde
   `estado_do_aviso_auditoria`; 409 e 404 = já respondido, não é erro). Mensagens de 403 citam
   `AUD.AVISO`. — arquivos: `backend/erp.py` — verificação: teste com `urlopen` falso (200, 403, 409)
   — reversão: `git revert`.

3. **Canais em `auditoria_erp.py`** — `@dataclass Canal(nome, ir, devolver, ajuste)`;
   `CANAIS = (Canal("auditoria_estoque", erp.auditoria_pendentes, erp.estado_do_aviso_auditoria,
   "auditoria_estoque_para"), Canal("integracao_recusada", erp.integracoes_pendentes,
   erp.estado_do_aviso_integracao, "integracoes_para"))`; `destinos(con, ajuste)`;
   `volta(cfg, canais=CANAIS)` itera e soma por canal, `{"canais": {nome: contagem|{"erro"}}}`; a
   correlação grava e lê `canal`; o `tipo` do aviso é `canal.nome`. A assinatura antiga
   `volta(cfg, ir=..., devolver=...)` **continua aceita** (monta um canal da auditoria com elas), para
   os testes do #350 não mudarem. — arquivos: `backend/auditoria_erp.py`, `backend/main.py` (só a
   linha do log, que passa a citar o canal) — verificação: `pytest tests/test_auditoria_erp.py` verde
   **sem alteração**; teste novo `tests/test_1337_aviso_integracao.py`: pendente vira um aviso por
   destino com `tipo='integracao_recusada'` e `sobre` = texto; enviado devolve ENVIADO com o wamid;
   erro em todos devolve FALHOU; sem destino, FALHOU com a frase do ajuste; o mesmo id de ERP nos dois
   canais não colide; canal fora do ar não para o outro; dentro da janela sai texto e fora sai a
   reabertura (com `porteiro=True`, molde do teste da auditoria) — reversão: `git revert`.

4. **Manual** — `docs/manuais/envios.md`: entrada "API externa recusando" na tabela dos avisos à
   equipe e em "O que NÃO faz", com o texto da spec; `INDICE.md` já aponta `envios.md`. —
   verificação: alguém de fora lê e sabe o que fazer ao receber; `grep -n "integra" docs/manuais/envios.md`
   acha a entrada — reversão: `git revert`.

5. **Commit e bateria** — `[axiaatende] #1337 ...` nomeando os arquivos (`git add -N` nos novos;
   `git status` antes: há `frontend/dist.antes-1200/` e `tmp/` de outras sessões); bateria inteira com
   as falhas pré-existentes anotadas (#1289: 5). — verificação: `git log -1 --stat`.

6. **Prova de efeito em produção** (depois da migração e do restart, mão do dono) — no ERP, janela
   elevada: `python scripts/conferir_1280_vigia.py --valendo` cria um episódio real na fonte `ensaio`
   e, com ele, um aviso PENDENTE; em até 2 min o aviso aparece em `atendimento.avisos` com
   `tipo='integracao_recusada'` e chega ao WhatsApp do dono (texto ou reabertura); o ERP recebe
   ENVIADO (`SELECT estado FROM axia.integracoes_avisos ORDER BY id DESC LIMIT 1`). Saída em
   `docs/medicoes/2026-11-09-1337-prova.txt`. — reversão: nenhuma (o script do ERP limpa a fonte e
   recusa o chamado de ensaio).

7. **Devolver** — texto para quem abriu (o dono): o que acontecia, o que mudou, como chega, o manual;
   `entregar 1337 --devolucao @f` + `fechar 1337` com `ESTEIRA_587_LIGADA`, senão `tratar 1337
   --status resolvido --prova`. Linha em `logs/sessions.log`. Comentar no #1280 que a frase sobre o
   modelo da Meta foi corrigida aqui. Vem **depois** do passo 6.

## O que só você pode fazer

- **Aplicar a migração 060** no banco do atendimento (janela elevada, o caminho de sempre das
  migrações do AxiaAtende) e **reiniciar `axiaatende-backend`** (as TELAS).
- **Rodar a prova do passo 6** no ERP: `C:\AxiaGestao\backend\.venv\Scripts\python.exe C:\AxiaGestao\scripts\conferir_1280_vigia.py --valendo`.
- **Só se um dia o porteiro for desligado:** `python -m backend.modelos_meta --propor --so aviso_integracao`
  e aprovar na Meta.

```pos-entrega
dono=aplicar a migração 060 do AxiaAtende e reiniciar axiaatende-backend; rodar conferir_1280_vigia.py --valendo no ERP e conferir o aviso no celular
```

## Riscos de execução identificados

- **Migração aplicada e TELAS sem restart:** nada acontece; o aviso segue PENDENTE no ERP, visível.
  Seguro.
- **Restart sem a migração:** a volta do canal novo falha no INSERT (CHECK) a cada minuto, só no log,
  e o canal da auditoria continua (um canal não para o outro, testado). Seguro, barulhento.
- **PK trocada com linhas existentes:** a 060 preenche `canal` pelo DEFAULT antes de trocar a PK;
  ida e volta no teste de migrações.
- **Destino vazio em produção:** FALHOU com frase, e o ERP fica com o estado; conferir o ajuste na
  prova do passo 6.

## Linha de abertura da sessão de execução

Leia `C:\AxiaAtende\CLAUDE.md` inteiro e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md` §1. Faixa:
aplicação de plano aprovado. Execute
`C:\AxiaAtende\docs\specs\2026-11-09-aviso-de-api-recusando-no-whatsapp-plano.md` (spec ao lado,
mesmo nome sem `-plano`). Chamado #1337; todo commit cita `#1337`, e o primeiro ato é
`python C:\SuporteAxia\skills\demanda\demanda.py tratar 1337 --status em_andamento --motivo "..."`
pela skill `/demanda`, rodado em `C:\AxiaAtende`. Decisões que não se reabrem: generalizar
`auditoria_erp.py` em canais, sem copiar o módulo; os testes do #350 passam sem alteração; o tipo
é `integracao_recusada`, o modelo `aviso_integracao` é cadastrado na migração e não se propõe à Meta
enquanto o porteiro estiver ligado; destino só o ajuste `integracoes_para`. A migração, o restart e a
prova no ERP são de janela elevada: entregue os comandos prontos e pare em "O que só você pode
fazer". O que vai para a tela durante a execução está no `PADRAO-TRABALHO.md` §1.
