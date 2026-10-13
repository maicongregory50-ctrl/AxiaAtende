# Plano — A leitura da sessão ao AxiaAtende em produção
**Data:** 2026-10-13
**Chamado:** #981
**Spec de origem:** `C:\AxiaAtende\docs\specs\2026-10-13-leitura-da-sessao-ao-atende.md` (APROVADA, 13/10/2026, caminho B)
**Status:** APROVADO (dono, 13/10/2026)
**Executavel pelo agente:** sim

## Contexto

A sessão que cuida do AxiaAtende não lê o que acontece em produção: o banco (5436) fica atrás da
senha do `.env.secrets`, e cada decisão do #970 nasceu de um print seu. A spec fechou o caminho B: um
papel só-SELECT (`axiaatende_ro`) em `atendimento` (sem `casa`), a senha num pgpass de uma linha
fechado como o do executor do ERP (`C:\AxiaSecurity\scripts\criar_pgpass_executor.ps1`, #337), um
leitor na mão da sessão (`scripts/ler_conversa.py`), cada leitura registrada num jsonl próprio e no
log do Postgres só desse papel, e a governança do AxiaSecurity (catálogo de segredos, ficha, painel,
política de uso de IA, runbook de restauração).

O que a releitura da spec e o inventário mediram, e que muda o desenho em dois pontos:

- **O coletor de log do Postgres pede reinício, não `reload`.** `logging_collector` só muda com o
  serviço `axiaatende-postgres` subindo de novo (segundos; as telas e o recepcionista abrem uma
  conexão por pedido, `backend/banco.py`, e não seguram nada). A spec dizia "nenhum serviço reinicia";
  o certo é: **um reinício do Postgres, da sua mão, dentro do script**, e só se você escolher o
  coletor. Sem ele, o log por papel vai ao stderr do serviço (que o WinSW rola por tamanho, mas que
  ninguém acha). Recomendo o coletor, em `C:\Logs\AxiaAtende\postgres\`, um arquivo por dia.
- **Um script só, em vez de dois.** O `instalar.ps1` do projeto já tem os ajudantes (`Nova-Senha`,
  `Ler-Segredo`, `Fechar`, `psql` com `-v senha=`), e o papel e o pgpass nascem do mesmo segredo.
  `servicos\criar_leitura.ps1` faz os dois e prova pelo efeito; `-SoPgpass` reescreve só o arquivo
  depois de uma rotação (o que o `criar_pgpass_executor.ps1` faz no ERP).

Reaproveitado: `scripts/ultimos_eventos.py` (as consultas de `eventos_meta` e `enviadas`, só leitura),
`backend/banco.py` (o padrão de uma conexão por uso), `backend/campo.py` (`BASTIDORES`, `FASES`, para
o leitor imprimir a classe com nome), o tile do `.env.agente_db` em
`C:\AxiaSecurity\agente_seguranca.ps1` (linhas ~1082-1097, "ATIVO ha N dia(s)").

## Passos

### Bloco 1 — AxiaAtende (`C:\AxiaAtende`, commits `[axiaatende] #981 …`)

**1. O script do papel e do pgpass** — `servicos\criar_leitura.ps1` (elevado; molde: `instalar.ps1`
e `criar_pgpass_executor.ps1`). Faz, nesta ordem e idempotente: (a) lê `AXIAATENDE_SU_SENHA` do
`.env.secrets`; se não há `AXIAATENDE_RO_SENHA`, gera com `Nova-Senha` e acrescenta ao
`.env.secrets` (a origem da rotação, como `DB_URL_READONLY` no ERP); (b) no banco, como
superusuário e pela variável do psql (nunca a senha no texto): `CREATE ROLE axiaatende_ro LOGIN
NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD :'senha'` (ou `ALTER ROLE ... PASSWORD` com
`-Rotacionar`); `ALTER ROLE axiaatende_ro SET default_transaction_read_only = on`; `ALTER ROLE
axiaatende_ro SET log_statement = 'all'`; no banco `axiaatende`: `GRANT USAGE ON SCHEMA atendimento`,
`GRANT SELECT ON ALL TABLES IN SCHEMA atendimento`, `ALTER DEFAULT PRIVILEGES FOR ROLE axiaatende_app
IN SCHEMA atendimento GRANT SELECT ON TABLES TO axiaatende_ro` (as migrações criam tabela como
`axiaatende_app`); nada em `casa` nem `public`; (c) escreve `C:\AxiaAtende\.pgpass_leitura` com
UMA linha `127.0.0.1:5436:axiaatende:axiaatende_ro:<senha escapada>`, UTF-8 sem BOM, e a ACL por
SID (`Maicon:(R)`, Administradores `F`, SYSTEM `F`, herança cortada); (d) **prova pelo efeito**,
com `PGPASSFILE` apontando para o arquivo e `$ErrorActionPreference = 'Continue'`: `select
current_user` devolve `axiaatende_ro`; `update atendimento.ajustes set valor = valor where false`
dá `permission denied`; `select 1 from casa.usuarios` dá `permission denied`; (e) com `-ComLog`:
`ALTER SYSTEM SET logging_collector = on, log_directory = 'C:/Logs/AxiaAtende/postgres',
log_filename = 'postgres-%Y-%m-%d.log', log_rotation_age = '1d', log_line_prefix = '%m [%p] %u@%d '`,
cria a pasta, `Restart-Service axiaatende-postgres`, espera o `pg_isready` e prova que o arquivo do
dia nasceu com uma linha do `axiaatende_ro`. Não imprime senha. — verificação: as três provas
escrevem `ok`; `.env.secrets` ganhou uma chave; `icacls .pgpass_leitura` mostra só os três —
reversão: `DROP OWNED BY axiaatende_ro; DROP ROLE axiaatende_ro;`, apagar o pgpass, tirar a chave.

**2. O `.gitignore`** — `.pgpass*` na seção de segredos. — verificação: `git status --short
--ignored -- .pgpass_leitura` dá `!!` depois do passo 1 — reversão: o commit.

**3. O leitor** — `scripts/ler_conversa.py`: conecta a `host=127.0.0.1 port=5436 dbname=axiaatende
user=axiaatende_ro` com `PGPASSFILE` = `C:\AxiaAtende\.pgpass_leitura` (ou `--pgpass`), `psycopg`
com `dict_row`, `con.read_only = True`, nunca lê `.env*`. Argumentos: `--numero <wa_id>` ou `--bsuid`
(a conversa em ordem de tempo: `→` o que chegou, de `eventos_meta` tipo mensagem, com texto, botão
tocado ou "[foto id …]"; `←` o que a OlivIA mandou, de `enviadas`, com tipo, resumo e status; as
linhas `[campo]` de `material_de_campo` e `campo_frases`: pergunta feita, classe, fechado, ATV; o
caminho do menu de `conversas`), `--dias N`/`--desde AAAA-MM-DD`; `--campo [--dias 7]` (o canal
por pessoa e grupo: perguntas feitas, respostas lidas, classe, desistiu, entrou); `--ultimas N` (uma
linha por conversa recente, para achar o número). Sem token, sem hash, sem `casa`, sem baixar
mídia. Cada chamada acrescenta uma linha a `C:\Logs\AxiaAtende\leituras.jsonl` (`quando`, `quem` =
`%USERNAME%` + `AXIA_SESSAO` se existir, `o_que` = argumentos, `linhas`). Erro de conexão diz "rode
`servicos\criar_leitura.ps1` elevado" e sai 2. — verificação: `tests/test_ler_conversa.py` no banco
de teste (`--dsn` só para teste): uma conversa com texto, botão e foto imprime na ordem; o canal de
campo imprime a classe por nome; o jsonl ganha a linha; sem pgpass, sai 2 com a mensagem —
reversão: apagar o script.

**4. Manual e índice** — `docs/manuais/leitura-da-sessao.md` (o `## Manual de uso` da spec, publicado)
e a linha no `docs/manuais/INDICE.md` (formato do projeto, duas colunas). — verificação: alguém de
fora roda `--ultimas 20` e `--numero` lendo só o manual — reversão: apagar arquivo e linha.

**5. Testes e fechamento do bloco** — suíte inteira (`AXIAATENDE_BANCO_TESTE=axiaatende_teste_970
.venv\Scripts\python.exe -m pytest --basetemp=C:/Temp/... -p no:cacheprovider`), commits, push,
`logs/sessions.log`. — verificação: todos passam; `git log` cita `#981` — reversão: n/a.

### Bloco 2 — AxiaSecurity (`C:\AxiaSecurity`, commits `[axiasecurity] #981 …`)

**6. O catálogo de segredos** — `scripts\porta\catalogo_env.json`: entrada
`C:\AxiaAtende\.pgpass_leitura` (`natureza: segredo`, `estado: vivo`, `listas: ["inventario"]`,
`acl_esperada: fechada_dono_le`, `gerida_por: criar_leitura`, `por_que`: "a senha do papel
só-leitura axiaatende_ro, para a sessão ler o atendimento (#981); o dono lê de propósito; ACL vem do
criar_leitura.ps1"). `.env.secrets` do AxiaAtende já está. — verificação: o tile *ACL dos .env* do
painel mostra o arquivo `ok` no ciclo seguinte ao passo 1 — reversão: `estado: apagado`.

**7. O tile do acesso** — `agente_seguranca.ps1`: ao lado do tile do `.env.agente_db`, um
`leituraAtende` com a mesma forma ("ATIVO ha N dia(s)", INFO, nunca alerta) pela `CreationTime` do
`.pgpass_leitura`, mais a contagem de linhas de `leituras.jsonl` nos últimos 7 dias. —
verificação: o painel mostra o tile no ciclo seguinte; sem o arquivo, mostra "sem acesso" —
reversão: tirar o bloco.

**8. A governança escrita** — `docs/governanca/inventario-agentes.md` (ficha `sessao-axiamarketing`:
"O que alcança" ganha o banco do AxiaAtende só leitura pelo `axiaatende_ro`; "O que não pode"
ganha escrever (barreira: o papel e `default_transaction_read_only`) e o token da Meta (barreira: o
`.env.recepcionista` fechado); "Log" ganha `C:\Logs\AxiaAtende\leituras.jsonl` e o log do Postgres);
`docs/governanca/politica-uso-ia.md` (em "Pode sozinho": a leitura do AxiaAtende pelo papel e o
leitor; em "Em aberto": o dado pessoal das conversas, finalidade "ajustar o atendimento e a OlivIA
da casa; nada sai do servidor nem treina modelo externo", decisão do dono em 13/10/2026 registrada);
`docs/RUNBOOK-segredos.md` (seção curta "O pgpass de leitura do AxiaAtende (#981)", a rotação em
dois lugares); `docs/RUNBOOK-RESTAURACAO.md` (na linha do `axiaatende-postgres`: "criar
`axiaatende_ro` antes de restaurar, `criar_leitura.ps1`"). — verificação: `python
scripts\conferir_*` que leem esses docs continuam passando; leitura por alguém de fora —
reversão: os commits.

### Bloco 3 — Com você

**9. O papel e o pgpass** (sua mão, abaixo). — verificação: as provas do script — reversão: idem.

**10. A primeira leitura, que é a medição** — `python scripts\ler_conversa.py --campo --dias 2` e
`--numero <o seu>`: a conversa de 12/10 inteira, do print para o terminal. O que ela contar (quantas
conversas, mensagens, grupos do campo) vai ao #981 como "O universo medido". — verificação: o
terminal mostra o diálogo das 14:25 e das 14:34; `leituras.jsonl` tem duas linhas; o log do
Postgres tem o `select` do papel — reversão: n/a.

**11. Devolver o chamado** — `#981` fechado com o manual (`leitura-da-sessao.md`) e os
pré-requisitos: o script rodado, o papel vivo, o pgpass com a ACL. — verificação: você usa lendo
só a devolução — reversão: reabrir.

## O que só você pode fazer

Em janela elevada, depois do bloco 1 no master:

```powershell
cd C:\AxiaAtende
.\servicos\criar_leitura.ps1 -ComLog     # papel, grants, pgpass, provas; e o coletor de log (reinicia o axiaatende-postgres, segundos)
# sem o coletor: .\servicos\criar_leitura.ps1
# depois de rotacionar a senha (AXIAATENDE_RO_SENHA no .env.secrets): .\servicos\criar_leitura.ps1 -Rotacionar
```

Depois, na sessão (sem elevação): `python scripts\ler_conversa.py --campo --dias 2`.

```pos-entrega
dono=criar_leitura.ps1 elevado (papel axiaatende_ro, pgpass, provas; -ComLog reinicia o axiaatende-postgres), a primeira leitura
```
(O AxiaAtende está fora da Porta-Ação; não há `reiniciar=` nem `fase=`: a mudança de banco é papel e
grant, pelo script do dono, não migração do serviço.)

## Riscos de execução identificados

| Passo | Se interromper no meio | Seguro parar ali? |
|---|---|---|
| 1 (a) | chave no `.env.secrets` sem papel no banco | sim: rodar de novo cria o papel com a mesma senha |
| 1 (b) | papel sem grants | sim: a prova falha e diz; rodar de novo completa (idempotente) |
| 1 (c) | pgpass sem ACL | **não**: o script apaga o arquivo se o `icacls` falhar (como o do ERP) |
| 1 (e) | `ALTER SYSTEM` feito e serviço não subiu | o Postgres sobe sem o diretório? o script cria a pasta antes; se o reinício falhar, `ALTER SYSTEM RESET logging_collector` e subir |
| 3 | leitor sem pgpass | sai 2 com a mensagem; nada muda |
| 7 | tile com erro no `agente_seguranca.ps1` | o ciclo de 30 min acusa; reverter o bloco |
| 10 | — | a leitura não muda estado |

Fios cobertos: papel e grants (1), default privileges para as migrações futuras (1b), pgpass e ACL
(1c, 6), `leituras.jsonl` com um escritor (3), log do Postgres (1e), painel (7), DR (8). Não coberto
de propósito: a `consultar_banco` do SuporteAxia (caminho C, fora); transcrição de áudio (chamado
próprio, se pedido).

## Linha de abertura da sessão de execução

Esta sessão executa (pedido seu, 13/10). Para outra sessão: leia `C:\AxiaAtende\CLAUDE.md`,
`C:\AxiaSecurity\CLAUDE.md` e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`; execute
`C:\AxiaAtende\docs\specs\2026-10-13-leitura-da-sessao-ao-atende-plano.md` (spec ao lado), faixa
"aplicação de plano aprovado". Chamado **#981**; todo commit cita `#981` (nos dois repositórios) e o
primeiro ato é `tratar 981 --status em_andamento` pela skill `/demanda`. Não se reabrem: só leitura,
quem recusa é o Postgres; sem `casa`; um escritor por arquivo de log; o caminho C fica fora. Bloco 1
antes do 2; pare em "O que só você pode fazer". O que vai para a tela durante a execução está no
`PADRAO-TRABALHO.md` §1.
