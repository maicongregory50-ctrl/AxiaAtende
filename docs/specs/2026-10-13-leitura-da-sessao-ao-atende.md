# A leitura da sessão ao AxiaAtende em produção
**Data:** 2026-10-13
**Chamado:** #981
**Status:** APROVADO

## Contexto

A sessão de agente que cuida do AxiaAtende (hoje a `sessao-axiamarketing`, por onde o #970 foi feito)
não lê nada do que acontece em produção: o banco está na 5436 atrás da senha do `.env.secrets`, que a
sessão não lê, e o recepcionista não loga o diálogo. No segundo caso do canal de campo (12/10/2026) o
dono teve de mandar prints da conversa para a sessão entender o que o atendente fez; cada decisão do
#970 (12 a 15) nasceu de um print. O dono, em 12 e 13/10/2026: *"a sessão precisa ter um acesso de
leitura... principalmente no AxiaAtende... imprescindível para o aprendizado do próprio agente de IA";
"ler os diálogos será base para nosso treinamento interno em seguida, quando tivermos o AxiaAtende
atendendo nosso cliente direto no canal central de atendimento, não agora, mas a leitura vai
facilitar nossa comunicação aqui".*

O molde é o do ERP, lido no AxiaSecurity (`docs/RUNBOOK-segredos.md`, *O pgpass da Porta-Executor*,
#337): um papel do banco **só SELECT** (`suporteaxia_ro`), a senha dele num pgpass de **uma linha**
com a ACL fechada (SYSTEM + Administradores + Maicon com leitura), criado por script elevado que não
imprime a senha e que, rodado de novo, reescreve o arquivo depois da rotação; `PGPASSFILE` apontando
para ele. A política de uso de IA (`docs/governanca/politica-uso-ia.md`, *Pode sozinho*) já diz: a
sessão lê o banco só para ler, em transação `READ ONLY`, e quem recusa escrita é o Postgres.

O que existe para ler (inventário de 13/10): a conversa inteira é reconstruível do banco. O que chega
está em `atendimento.eventos_meta` (o corpo da Meta, por `bsuid`/`wa_id`), o que a OlivIA manda em
`atendimento.enviadas` (`para`, `tipo`, `resumo`, `status`), e em volta `conversas`, `menu`,
`destinos`, `avisos`, `envios` e `envio_destinatarios`, `consentimentos`, `agenda`,
`material_de_campo` e `campo_frases` (o canal de campo), `nota_qualidade`, `vigia_endereco`,
`modelos`, `ajustes`: 17 tabelas no schema `atendimento`. No schema `casa` ficam `usuarios` (com o
hash da senha) e `sessoes`: fora. Produção: instância em `C:\Dados\AxiaAtende\pgdata`, porta 5436,
só `127.0.0.1`, banco `axiaatende`, papel da aplicação `axiaatende_app` (criado pelo
`servicos\instalar.ps1`). O `logging_collector` da instância está desligado (o log do Postgres vai
ao stderr do serviço). O `.gitignore` do AxiaAtende cobre `.env*` e `*.secrets`, não `.pgpass*`.
A sessão (`Maicon`) tem escrita em `C:\Logs\AxiaAtende` (medido por `icacls`).

## Os fios que encostam

**Quem mais escreve.** O papel novo não escreve em nada: `SELECT` nos 17 objetos de `atendimento`
e `USAGE` no schema, mais `ALTER DEFAULT PRIVILEGES` para as tabelas que as migrações futuras criarem
(as migrações rodam como `axiaatende_app` ao subir o serviço; o default privilege é declarado *para
esse papel*, senão a tabela nova nasce fora do alcance e a leitura falha em silêncio). O pgpass
(`C:\AxiaAtende\.pgpass_leitura`) é escrito só pelo script elevado. O registro das leituras
(`C:\Logs\AxiaAtende\leituras.jsonl`) é escrito só pelo leitor: **um escritor por arquivo**, por
isso ele não vai para o `axiamarketing.sessao.jsonl` do AxiaSecurity, que é do invólucro da sessão
(`subir_sessao_agente.ps1`), e sim para um arquivo próprio que o painel pode ler.

**Quem lê para decidir.** O `conferir_env.ps1` do ciclo de 30 min (AxiaSecurity) passa a vigiar a
ACL do pgpass novo assim que ele entrar no `catalogo_env.json` (tile *ACL dos .env*); o painel de
acessos de desenvolvimento mostra há quantos dias o papel está ativo, como faz com o `axia_dev`.

**Quem volta depois.** O backup do banco (`pg_dump` do `axiaatende`) **não leva papel**: papel é do
cluster. O `RUNBOOK-RESTAURACAO.md` ganha a linha "criar `axiaatende_ro` antes de restaurar, ou
`--no-owner`/sem a grant". A rotação da senha vive em dois lugares (o papel no banco e o pgpass) e o
script reescreve o segundo.

## O universo medido

- 17 tabelas em `atendimento` recebem `SELECT`; 2 em `casa` ficam fora (medido nas migrações 001 a
  015).
- Quantas conversas e mensagens há em produção: **não medido**, porque é exatamente o que a sessão
  não consegue ler hoje. A primeira leitura pelo leitor novo é a medição, e vai ao chamado.
- Permissão de escrita da sessão em `C:\Logs\AxiaAtende`: sim (`Maicon: Modify`, medido).
- `logging_collector`: desligado (medido no `postgresql.conf`); o log por papel precisa de destino.

## Conformidade com o Manual legal

Não se aplica: não há regra tributária nem legal. **Mas há dado pessoal** (conversas de clientes e
colaboradores no WhatsApp), e a finalidade fica escrita: ajustar o atendimento e a OlivIA da casa;
nada da conversa sai do servidor nem vai treinar modelo externo; o "treinamento interno" é ajuste de
instrução e regra, aqui dentro. Isto entra como item da `politica-uso-ia.md` (hoje "Em aberto").

## Decisão

Três caminhos foram postos; o dono escolheu o B em 13/10/2026 ("b"; antes, três respostas: todo o atendimento;
leitor + Postgres; script na mão da sessão).

- **A — conservador:** só o canal de campo (`material_de_campo`, `campo_frases` e as mensagens com
  equipe e representantes), leitor sem log do Postgres. Reversível fácil. Não serve ao treinamento
  futuro: deixa de fora justamente a conversa do cliente.
- **B — o escolhido:** papel `axiaatende_ro` só-SELECT em `atendimento` (sem `casa`), pgpass de uma
  linha fechado, leitor `scripts/ler_conversa.py` na mão da sessão, registro de cada leitura em
  `leituras.jsonl` **e** log do Postgres só desse papel, catálogo de segredos, ficha no inventário de
  agentes, painel com dias ativos e kill switch. Reversível fácil: `DROP ROLE` e apagar o pgpass.
- **C — progressivo:** B mais a `consultar_banco` do SuporteAxia alcançando o AxiaAtende, para o fio
  e o PLANEJADOR lerem também. Amplia leitores de dado pessoal sem pedido de ninguém hoje. Fora.

## Escopo desta etapa

**Dentro**
1. Papel `axiaatende_ro` na 5436: `LOGIN`, `NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT`,
   `USAGE` no schema `atendimento`, `SELECT` em todas as tabelas dele, `ALTER DEFAULT PRIVILEGES FOR
   ROLE axiaatende_app IN SCHEMA atendimento GRANT SELECT`, `default_transaction_read_only = on` no
   papel, `log_statement = 'all'` no papel. Sem nada em `casa` nem em `public`. Criado por
   `servicos\criar_leitura.ps1` (elevado; lê a senha do superusuário como o `instalar.ps1`), que
   também grava a senha do papel em `C:\AxiaAtende\.env.secrets` (`AXIAATENDE_RO_SENHA`), para a
   rotação ter um lugar de origem, como no ERP.
2. `C:\AxiaAtende\.pgpass_leitura`: uma linha, `127.0.0.1:5436:axiaatende:axiaatende_ro:<senha>`,
   ACL SYSTEM + Administradores + Maicon (leitura), escrito por `servicos\criar_pgpass_leitura.ps1`
   (elevado, a partir do `.env.secrets`; não imprime a senha; rodar de novo reescreve). `.pgpass*`
   entra no `.gitignore`. Entra no `catalogo_env.json` do AxiaSecurity (`acl_esperada:
   fechada_dono_le`, listas `inventario`, `gerida_por: criar_pgpass_leitura`) na mesma rodada.
3. O leitor `scripts/ler_conversa.py`, na mão da sessão, conectando com `PGPASSFILE` apontando para o
   pgpass de leitura e `user=axiaatende_ro` (nunca lê `.env.secrets`), em transação `READ ONLY`:
   - `--numero <wa_id>` (ou `--bsuid`): a conversa do número em ordem de tempo, intercalando o que
     chegou (`eventos_meta`: tipo, texto, botão, mídia) e o que a OlivIA mandou (`enviadas`: tipo,
     resumo, status), com a conversa de atendimento (`conversas.caminho`, destino) e o material de
     campo (perguntas, respostas, classe, fechamento) quando houver; `--desde`/`--dias`;
   - `--campo [--dias N]`: o diálogo do atendente de campo da semana, por pessoa e grupo;
   - `--ultimas N`: as últimas conversas da casa, uma linha cada;
   - saída em texto legível no terminal, sem token, sem segredo, sem hash. Cada chamada grava uma
     linha em `C:\Logs\AxiaAtende\leituras.jsonl` (`quando`, `quem` = usuário do Windows e nome da
     sessão se houver, `o_que` = argumentos, `linhas` = quantas mensagens).
4. O log do Postgres para o papel: `log_statement = 'all'` no `ALTER ROLE`; como o
   `logging_collector` está desligado, o plano decide entre ligá-lo (`log_directory` em
   `C:\Logs\AxiaAtende\postgres`, rotação diária) ou deixar no stderr do serviço `axiaatende-postgres`
   (que o WinSW já rola por tamanho). Recomendação: ligar o collector, porque o log por papel só
   serve se alguém consegue achá-lo.
5. Governança: a ficha `sessao-axiamarketing` do `inventario-agentes.md` ganha "O que alcança: o
   banco de produção do AxiaAtende, só leitura, pelo `axiaatende_ro`" e "O que não pode: escrever
   (barreira: o papel e `default_transaction_read_only`), o token da Meta (barreira: o
   `.env.recepcionista` fechado)"; o painel mostra os dias ativos do acesso; a `politica-uso-ia.md`
   ganha o item do dado pessoal (finalidade e "nada sai do servidor"); o `RUNBOOK-RESTAURACAO.md`
   ganha o papel.
6. Manual `docs/manuais/leitura-da-sessao.md` e a linha no `INDICE.md`.

**Fora**
- Escrita de qualquer espécie; `casa.usuarios`, `casa.sessoes`; o token da Meta e o `.env.recepcionista`.
- Transcrever áudio (hoje áudio da equipe é silêncio, decisão 13 do #970): chamado próprio, se o
  dono pedir.
- A `consultar_banco` do SuporteAxia alcançando o AxiaAtende (caminho C).
- Exportar conversas para fora do servidor, para qualquer fim.

## Impacto em produção

Nenhum serviço reinicia. O banco ganha um papel e uma grant; o `ALTER SYSTEM`/`postgresql.conf` do
collector, se o plano o escolher, pede `pg_ctl reload` (sem parada). Dois arquivos novos na raiz
(`.pgpass_leitura` fora do git; `.env.secrets` ganha uma chave). O AxiaSecurity recebe duas linhas
(catálogo e ficha) e um item na política. Mão do dono, em janela elevada: os dois scripts.

## ROLLBACK_PLAN

1. `DROP OWNED BY axiaatende_ro; DROP ROLE axiaatende_ro;` na 5436 (tira as grants e o papel; o
   default privilege sai junto).
2. Apagar `C:\AxiaAtende\.pgpass_leitura`; tirar `AXIAATENDE_RO_SENHA` do `.env.secrets`.
3. No `catalogo_env.json`, o arquivo passa a `estado: apagado` (o conferidor acusa se reaparecer).
4. A ficha e a política voltam ao texto anterior. `leituras.jsonl` fica como registro.
Nada de atendimento é tocado em nenhum passo.

## Manual de uso

**Para que serve.** Ver, pela sessão, o que de fato aconteceu numa conversa do WhatsApp da Renascer,
sem print: o que a pessoa escreveu, o que a OlivIA respondeu, por onde o atendimento andou, e o que
o atendente de campo perguntou e fechou. Serve para ajustar o atendente e, depois, para o
treinamento interno quando o AxiaAtende atender cliente direto.

**Quem usa e quando.** O dono e a sessão de agente, quando um caso precisa ser lido ("o que ela
respondeu ao fulano?", "por que perguntou de novo?"). Não é tela: é um comando no terminal da
sessão.

**O caminho comum.**
1. `python scripts\ler_conversa.py --numero 5549999990000` imprime a conversa do número, do mais
   antigo ao mais novo, com hora, quem falou e o que; `--dias 2` encurta.
2. `python scripts\ler_conversa.py --campo --dias 7` imprime o canal de campo da semana: cada grupo,
   as perguntas feitas, as respostas, a classe fechada e se entrou no catálogo.
3. `python scripts\ler_conversa.py --ultimas 20` lista as últimas conversas, uma por linha, para
   achar o número.
4. Toda chamada fica registrada em `C:\Logs\AxiaAtende\leituras.jsonl`; o Postgres também anota.

**O que significa cada sinal.** `→` é o que chegou; `←` é o que a OlivIA mandou, com o status
(`enviada`, `entregue`, `lida`, `falhou`); `[campo]` marca as linhas do atendente de campo;
`(sem conversa)` quer dizer que a pessoa é da equipe e nada abriu atendimento. "Nenhuma mensagem"
é diferente de "número não reconhecido": o primeiro é zero, o segundo é que o número nunca escreveu.

**O que NÃO faz.** Não escreve nada; não mostra senha, token nem hash; não mostra `casa`; não baixa
mídia (diz que houve uma foto, com o id); não transcreve áudio; não manda mensagem a ninguém.

## Próximo passo

`/writing-plans`.
