# Plano — Quem é da casa tem menu próprio
**Data:** 2026-10-15
**Chamado:** #1031
**Spec de origem:** `docs/specs/2026-10-15-quem-e-da-casa-tem-menu-proprio.md`
**Status:** APROVADO
**Executável pelo agente:** sim

> **Sem bloco `pos-entrega`, e isso é decisão:** a etapa tem migração, mas de **banco do
> atendimento**, que **não está no catálogo da `Porta-Ação`** (só as fases do ERP estão, e só cinco
> serviços — `axiaatende-recepcionista` e `axiaatende-backend` não são deles). Plano que não nomeia
> fase não autoriza fase; aqui a migração é aplicada **pelo próprio serviço ao subir**, e o restart
> é da mão do dono (passo 9). Não acrescentar o bloco depois: seria recusado na gravação.

> **Correção feita no plano, contra a spec:** a spec dizia `python -m backend.migracoes voltar 018`.
> **Esse verbo não existe** — a regra 3 do módulo é *"o `_VOLTA.sql` nunca é aplicado sozinho; ele
> existe para a mão de quem desfaz"*. A spec foi corrigida antes deste plano ser gravado, e o
> rollback real está no passo 9.

## Passos

**1. O reconhecimento ganha casa própria** — arquivo: `backend/internos.py` (novo) — `quem_e(con,
wa_id)` com a regra de hoje **sem alterá-la** (agenda do ERP primeiro, pelos papéis `equipe` e
`representante`; destino ativo como complemento, `equipe` sem código) e `ligado(con)` lendo o ajuste
`interno.ligado` com padrão `True`. Nada mais muda neste passo — `campo.py` continua como está e o
módulo novo ainda não é chamado por ninguém — verificação: `pytest tests/test_campo.py` passa
inalterado (ninguém usa o módulo novo ainda) — reversão: apagar o arquivo.

**2. `campo.py` passa a delegar, sem duplicar a verdade** — arquivo: `backend/campo.py` — `quem_e`
e `e_interno` chamam `internos`; a regra deixa de existir em dois lugares. `e_interno` **continua**
exigindo `campo.ligado` (o canal de fotos é dele), e o que deixa de depender disso é apenas *ser
interno* — verificação: `pytest tests/test_campo.py` passa **sem alteração nos testes**, que é a
prova de que a regra não mudou ao mudar de lugar — reversão: `git checkout` do arquivo.

**3. A migração: a segunda raiz, as duas opções e a chave** — arquivos:
`backend/migracoes/018_menu_interno.sql` e `018_menu_interno_VOLTA.sql` — a raiz `raiz-interna`, os
dois filhos (`interna.campo` com `acao = 'texto'`, `interna.cliente` com `acao = 'menu_cliente'`) e
a linha `interno.ligado = true` em `ajustes`. **Sem `BEGIN`/`COMMIT` no arquivo da ida** (o módulo
abre e fecha); **com** no `_VOLTA`, que também apaga a linha de `casa.mudancas` — verificação:
`SELECT count(*) FROM atendimento.menu WHERE pai_id IS NULL` devolve **2**, e
`SELECT valor FROM atendimento.ajustes WHERE chave = 'interno.ligado'` devolve `true` — reversão: o
`_VOLTA` à mão, em janela elevada (passo 9).

**4. O FIO: a lista da IA passa a ser só do cliente** — arquivo: `backend/motor.py`,
`folhas_e_menus` — a CTE deixa de partir de `WHERE pai_id IS NULL` e passa a partir da raiz do
cliente por chave. **Este passo vem ANTES do passo 5, e a ordem não é estética:** entre a migração
(passo 3) e esta correção, a árvore interna existe no banco e a IA já a alcançaria. Fazer na ordem
inversa abre uma janela em que um cliente pode receber proposta de opção interna — verificação: um
teste que grava a raiz interna e confere que `folhas_e_menus` **não** devolve nenhuma chave dela —
reversão: `git checkout` do arquivo.

**5. Os dois verbos novos** — arquivo: `backend/motor.py` — `acao = 'texto'` (o nó diz sua linha e
**para**, sem avançar nó) e `acao = 'menu_cliente'` (mostra a raiz do cliente). Mais `_no`, que
hoje exclui `chave <> 'raiz'` e passa a excluir a raiz interna junto — senão ela é alcançável por
chave — verificação: `pytest tests/test_motor.py` — reversão: `git checkout`.

**6. A saudação de interno leva o menu da casa** — arquivo: `backend/motor.py` — é a mudança que o
chamado pediu: quem `internos.quem_e` reconhece, e que pede menu (o `PEDE_MENU`), recebe a raiz
interna em vez da do cliente. **`PEDE_MENU` não muda** — saudação de cliente continua sendo
acolhimento — verificação: um teste com o número do Benedito recebendo a raiz interna, e um com um
número de fora recebendo a do cliente — reversão: `git checkout`.

**7. Ninguém recebe o próprio cartão** — arquivo: `backend/motor.py`, em `escolher` (a folha de
`destino`) — se o destino escolhido é a própria pessoa, o cartão não sai e uma linha diz que aquele
atendimento é ela mesma. É a decisão 4 da spec, a única não pedida pelo dono — verificação: um teste
com o número do destino de Fretes escolhendo Fretes — reversão: `git checkout`. **Reversão pontual é
independente dos outros passos**, porque é a única mudança no caminho do cliente.

**8. O manual** — arquivos: `docs/manuais/recepcao.md` e `docs/manuais/campo-equipe.md` — publicar o
que a spec já escreveu, **e** apagar o que ficou falso: a frase da seção 1 da Recepção, *"Isso só
registra: o que a pessoa recebe no WhatsApp é o mesmo para todos"*, que é exatamente o que esta
etapa derruba. **Não há linha nova no `INDICE.md`:** os dois manuais já estão indexados, e o índice
deste projeto tem duas colunas (`Manual` / `Do quê`), não o formato de três do AxiaGestão —
verificação: alguém de fora lê e executa o caminho comum sem perguntar; e `grep` no manual não acha
mais a frase derrubada — reversão: `git checkout` dos dois.

**9. [SÓ O DONO] Os dois restarts e a prova** — detalhe abaixo — reversão: o `ROLLBACK_PLAN` da spec.

**10. Devolver a demanda** — fechar o #1031 com o que mudou e o manual. **Pré-requisito de cadastro a
dizer na devolução:** Willian, Fran e Alisson só são reconhecidos enquanto forem **destinos ativos**
na tela Destinos; desativar um deles ali o devolve ao menu de cliente — verificação: quem abriu usa
lendo só a devolução — reversão: reabrir a demanda.

## O que só você pode fazer

**1. Reiniciar os DOIS serviços** (janela elevada). A migração é aplicada **pelo serviço ao subir**,
e os dois leem o mesmo banco — deixar um com schema antigo é o que esta ordem evita:

```powershell
Restart-Service axiaatende-recepcionista
Restart-Service axiaatende-backend
```

Nos segundos de queda a Meta **retém e repete** os avisos por até 7 dias: nenhuma mensagem de
cliente se perde.

**2. A prova, em dois atos de um minuto.** O primeiro é seu, o segundo eu confirmo no banco:

```powershell
Invoke-RestMethod http://127.0.0.1:8008/saude | Select-Object de_pe, ambiente
```

- escreva **"oi"** no WhatsApp da empresa, do seu número (você é `equipe` no ERP, código 42): deve
  chegar o **menu da casa**, com duas opções, e não o menu de cliente;
- toque em **Ver o menu do cliente**: deve chegar o menu de sempre;
- e se quiser a prova do passo 7, siga até **Fretes** — deve chegar a linha dizendo que aquele
  atendimento é você, no lugar do cartão. (Com o seu número o destino de Fretes é o Benedito, então
  essa parte só o Benedito prova.)

**3. O rollback que você provavelmente vai querer, se algo incomodar** — um `UPDATE`, sem restart e
sem deploy, e todo mundo volta a ser tratado como hoje:

```sql
UPDATE atendimento.ajustes SET valor = 'false' WHERE chave = 'interno.ligado';
```

**4. Se precisar desfazer o banco também** (só aí): o `_VOLTA` à mão, em janela elevada, **depois**
de reverter o código — `psql -f backend\migracoes\018_menu_interno_VOLTA.sql`. Não há verbo
`voltar` no módulo de migrações, e isso é regra escrita dele.

Nada mais pede a sua mão: nenhum segredo, nenhuma tarefa agendada, nenhuma fase do ERP.

## Riscos de execução identificados

| Passo | O que quebra se interromper no meio | É seguro ficar parado ali? |
|---|---|---|
| 1 e 2 | nada: o módulo novo não é chamado no passo 1, e o passo 2 só troca o endereço da mesma regra | **sim** |
| **3 sozinho** (migração no disco, código antigo) | nada em produção: o serviço só aplica a migração ao **subir**, e o código antigo não conhece a raiz interna. Ela fica no banco, inalcançável | **sim** |
| **3 + restart sem o passo 4** | **AQUI É O RISCO REAL:** a árvore interna existiria e a IA a alcançaria — um cliente poderia ouvir *"Entendi que você quer: Mandar foto do campo. É isso?"*. É por isso que o passo 4 vem antes do 5 e **nenhum restart acontece antes do passo 8** | **não** — e o plano não deixa esse estado existir |
| 5, 6, 7 | nada: código no disco, serviço ainda rodando o antigo | **sim** |
| 8 (manual) | nada | **sim** |
| 9 (os dois restarts) | se só um subir, um processo fica com schema novo e outro com o antigo. A migração é **transacional e com trava** (`pg_advisory_xact_lock`), então não há aplicação parcial; o pior caso é o outro serviço aplicar ao subir depois | **sim**, terminando o segundo restart |

**O único passo que escreve em dado de produção é o 3**, e ele é **atômico por construção**: o
módulo abre e fecha a transação, grava o sha256 em `casa.mudancas`, e a trava impede dois processos
de aplicarem a mesma mudança. Mudança aplicada **não se edita** — se o arquivo mudar depois, o
serviço **não sobe** e diz qual. Então, depois do passo 3 e de um restart, corrigir a 018 é escrever
a 019.

**O fio de `enviadas` e dos três escritores não é tocado:** esta etapa não escreve lá. O fio da
agenda das 06:00 continua valendo como a spec diz — quem o ERP deixar de reconhecer deixa de ser
interno no dia seguinte, e o complemento pelos destinos ativos é o que segura os três.

## Linha de abertura da sessão de execução

> Leia o `C:\AxiaAtende\CLAUDE.md` inteiro e o `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Faixa:
> **aplicação de plano aprovado** — execute
> `C:\AxiaAtende\docs\specs\2026-10-15-quem-e-da-casa-tem-menu-proprio-plano.md`, com a spec ao lado
> (mesmo nome, sem `-plano`). Chamado **#1031**: todo commit cita `#1031`, com o prefixo
> `[axiaatende]`, e o primeiro ato é `tratar 1031 --status em_andamento` pela skill `/demanda`. **As
> decisões que NÃO se reabrem:** o menu interno tem **duas** opções (mandar foto do campo; ver o menu
> do cliente) — *"falar com um colega"* como opção própria e *"abrir chamado"* foram **recusados**
> pelo dono, e o caminho para o colega segue por dentro do menu do cliente; `interno.ligado` nasce
> **ligada**, e é ela o rollback; o complemento pelos destinos ativos **fica** (cadastrar Willian,
> Fran e Alisson no ERP é chamado próprio); `PEDE_MENU` **não muda** para cliente. **A ordem do passo
> 4 antes do 5 é trava, não gosto:** sem ela a IA alcança a árvore interna e propõe opção interna a
> cliente. Pare no passo 9 — os dois restarts e a prova são da mão do dono. O que vai para a tela
> durante a execução está no `PADRAO-TRABALHO.md` §1: decisão do dono, incidente que merece chamado
> próprio, e passo que depende da mão dele. Conserto de caminho feito dentro do planejado não se
> narra.
