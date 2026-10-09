# Plano — Reconhecer o cadastro no atendimento
**Data:** 2026-10-09
**Chamado:** #969
**Spec de origem:** `C:\AxiaAtende\docs\specs\2026-10-09-reconhecer-o-cadastro-no-atendimento.md` (documento #1174)
**Status:** APROVADO
**Executável pelo agente:** sim

## Contexto

O atendimento do WhatsApp está no ar desde 09/10 (#950) e não sabe quem é quem. O dono quer começar a **reconhecer** quem chama e já está no cadastro do ERP (qualquer cadastro: cliente, fornecedor, produtor, representante, equipe), gravar a ligação e mostrar na Recepção, **sem mudar** o que a pessoa recebe. Maquete aprovada: `docs/specs/2026-10-09-reconhecer-cliente-maquete/1-recepcao.png`. Planejador desligado: o plano é desta sessão, a pedido do dono.

Medido: 884 de 3.278 cadastros têm celular válido; 23 números estão em mais de um cadastro; a Meta manda o celular sem o 9.

## Passos

### A — ERP (AxiaGestão)

**A1. Fase 551: o agente ATENDIMENTO**
- **Arquivos:** `schema_axia_fase551_agente_atendimento.sql` e `_VOLTA.sql`, cópia da `schema_axia_fase546_agente_marketing.sql`: perfil `AGENTE-ATENDIMENTO` só com `STK.R`, usuário `ATENDIMENTO` com `eh_agente` e a sentinela, sem concessão. Conferir na hora que 551 está livre (outra sessão pode ter tomado).
- **Verificação:** ensaio pela Porta-Ação (`ensaiar-fase`), que roda e desfaz.
- **Reversão:** a `_VOLTA.sql`.

**A2. `GET /atendimento/agenda` (STK.R)**
- **Arquivos:** `backend/services/atendimento_agenda_service.py` (novo), `backend/routers/atendimento.py` (novo, molde `routers/marketing.py`), registro em `backend/main.py`; teste `backend/tests/test_969_agenda_atendimento.py` (molde `test_950_lista_envio_marketing.py`).
- **O quê:** uma linha por (celular válido, cadastro): `numero` (55+DDD+9+8), `codigo` (id), `nome` (fantasia, senão razão social), `papeis` (equipe, representante, cliente, produtor, fornecedor), `contato_setor` (COMERCIAL/FINANCEIRO; `whatsapp_comercial` = comercial, `whatsapp_fiscal` = fiscal), `contato_nome`. Fontes: `stakeholders_contatos` sem `saida_em`, `stakeholders.whatsapp_comercial/fiscal`. De `colaboradores`, só "ativo existe". **Nunca:** valor, crédito, salário, cargo, documento, endereço.
- **Verificação:** teste (formato, nada sensível na resposta, 401 sem login, número com e sem 55); contagem bate com a medição (884 cadastros, 862 números).
- **Reversão:** tirar o roteador.

### B — AxiaAtende

**B1. Migração 006**
- `atendimento.agenda` (numero, codigo, nome, papeis text[], contato_setor, contato_nome) e `atendimento.agenda_leitura` (lida_em, linhas, erro); em `conversas`: `erp_nome`, `erp_papeis text[]`, `erp_contato_setor`, `erp_contato_nome`, `erp_cadastros int` (quantos casaram; >1 = ambíguo). `erp_codigo` já existe. Tudo anulável. `_VOLTA.sql` ao lado.
- **Verificação:** pytest; `test_login.py` lista a 006.

**B2. A leitura diária**
- **Arquivos:** `backend/erp.py` (novo, molde `C:\AxiaMarketing\backend\erp.py`: `POST /auth/agente` + `GET /atendimento/agenda`, 30 s, segredo nunca em log); `backend/agenda.py` (troca a tabela inteira numa transação; ERP fora = mantém a de ontem e grava o erro); `config.py` (`erp_url`, `erp_agente`='ATENDIMENTO', `erp_segredo` de `AXIAATENDE_ERP_SEGREDO`, **só no processo das telas**); `main.py` `vida`: uma linha de leitura ao subir e um laço que lê às 06:00.
- **Verificação:** testes com ERP falso (troca inteira, falha mantém a anterior, sem segredo não tenta).

**B3. O reconhecimento na chegada**
- **Arquivo:** `backend/motor.py` `_nova_conversa`: procura `envio.com_nove(wa_id)` na agenda e grava as colunas novas; 2+ cadastros grava só `erp_cadastros`.
- **Verificação:** testes (casa sem o 9, ambíguo, fora do cadastro, agenda vazia não quebra o atendimento).

**B4. A Recepção (maquete 1)**
- **Arquivos:** `backend/rotas_telas.py` `recepcao` (troca o casamento antigo por `envio_destinatarios`, que também falhava sem o 9, pelas colunas da conversa; filtro `quem=cadastro|fora`; cartão `do_cadastro`; data da última leitura); `frontend/src/Recepcao.jsx` e `atende.css` (etiquetas verde/azul, "fora do cadastro", "número em N cadastros", filtro, cartão, "cadastro lido em…" ou "leitura do cadastro não ligada").
- **Verificação:** testes da rota; `vite build --outDir` no rascunho; foto headless comparada à maquete e mandada ao dono.

**B5. O manual da Recepção**
- **Arquivo:** `docs/manuais/recepcao.md`, com o texto da seção *Manual de uso* da spec; trocar "(não é cliente)" por "fora do cadastro".
- **Verificação:** alguém de fora lê e usa o filtro sem perguntar.

### C — No ar e devolver

**C1. Instalar** (ver *O que só você pode fazer*): fase, segredo nos dois `.env`, permissão na tela, restarts, build. **Verificação:** a Recepção mostra "cadastro lido em…" com ~880 números, e um "oi" do Maicon aparece como "Equipe · Representante".

**C2. Registrar a etapa no #969**: o chamado é de escopo amplo, então a etapa 1 é entregue por **comentário** (para quem abriu: o que mudou na Recepção, o manual e o pré-requisito "celular da equipe no cadastro"), e o chamado segue em Execução para as próximas etapas. Só vai ao 5.2 (`entregar 969 --devolucao`) quando o dono disser que o escopo fechou. **Verificação:** o dono usa o filtro novo lendo só o comentário.

## O que só você pode fazer

1. **A fase 551** (janela elevada, no padrão de sempre — o comando exato vai pronto na hora).
2. **O segredo do agente:** gerar um e pôr nos dois lugares — no `AGENTE_SEGREDOS` do `.env` do ERP (JSON, acrescentar `"ATENDIMENTO": "<segredo>"`) e em `C:\AxiaAtende\.env.secrets` (`AXIAATENDE_ERP_SEGREDO=`). O comando que gera e grava nos dois sem mostrar vai pronto.
3. **A permissão:** tela de usuários do ERP › Mapa de Atividades › aplicar o perfil `AGENTE-ATENDIMENTO` ao usuário `ATENDIMENTO`.
4. **Restarts:** o do ERP vai pela Porta-Ação (a sessão faz); os do AxiaAtende (`axiaatende-backend`, `axiaatende-recepcionista`) são da sua mão.
5. **O cadastro da equipe:** o celular do Willian, da Fran, do Alisson e do Benedito no cadastro deles.

Sem bloco `pos-entrega`: o chamado é do AxiaAtende e a fase mora no repositório do ERP; a fase e o restart do ERP vão pela Porta-Ação durante a execução, e os restarts do AxiaAtende são de mão.

## Riscos de execução identificados

| Passo | Se parar no meio | Pode ficar? |
|---|---|---|
| A1 | Usuário sem segredo nem permissão: não autentica | Sim (estado seguro) |
| A2 | Endpoint no ar sem quem chame | Sim |
| B1–B4 | Colunas vazias; Recepção como hoje | Sim |
| C1 sem segredo | "leitura do cadastro não ligada"; atendimento igual | Sim |
| Leitura diária falha | Fica a agenda de ontem; a tela mostra a data | Sim |

## Linha de abertura da sessão de execução

> Execução nesta mesma sessão (dono, 09/10/2026). Plano `C:\AxiaAtende\docs\specs\2026-10-09-reconhecer-o-cadastro-no-atendimento-plano.md`, spec ao lado. Chamado #969; todo commit cita `#969`; primeiro ato `tratar 969 --status em_andamento`. Não se reabre: todos os cadastros, só registrar (nada muda no WhatsApp), leitura diária por agente próprio só STK.R, nada sensível na agenda. Pare em *O que só você pode fazer*. O que vai à tela: `PADRAO-TRABALHO.md` §1.
