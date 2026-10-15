# Plano — Pelo nome, e a logo que vira proposta
**Data:** 2026-10-15
**Chamado:** #1036
**Spec de origem:** `docs/specs/2026-10-15-pelo-nome-e-a-logo-que-vira-proposta.md`
**Status:** APROVADO
**Executável pelo agente:** sim

> **Sem bloco `pos-entrega`:** migração do banco do atendimento, fora do catálogo da `Porta-Ação`,
> aplicada pelo serviço ao subir. Os dois restarts são da mão do dono (passo 8).

> **A ORDEM DE INTERCEPTAÇÃO é a trava desta etapa**, e está em dois passos (4 e 5). Fora de ordem,
> a resposta "7687" do Benedito vira **frase da próxima foto** do canal de campo, em vez de ser o
> código do cliente. Ver *Riscos*.

## Passos

**1. O banco: a pergunta com `{nome}` e a tabela da logo** — arquivos:
`backend/migracoes/020_pelo_nome_e_a_logo.sql` e `_VOLTA` — o `UPDATE` da `pergunta` da
`raiz_interna` para trazer `{nome}`, e `CREATE TABLE atendimento.logos_de_cliente`. A tabela guarda
**`wamid` UNIQUE** (idempotência: o mesmo aviso repetido pela Meta não cria duas logos),
`nome_arquivo` (o original — *"Logo rigo sem..pdf"* é informação), `erp_codigo` **nulo**,
`nome_marca` com padrão vazio, `pergunta_pendente` com `CHECK` em (`erp_codigo`, `nome_marca`) e
`puxada_em` para a etapa seguinte. `formato` com `CHECK` nos quatro que o marketing aceita —
verificação: a tabela existe, `SELECT pergunta FROM menu WHERE chave='raiz_interna'` contém
`{nome}`, e um `INSERT` com `formato='docx'` é **recusado** — reversão: o `_VOLTA` à mão (passo 8).

**2. O nome** — arquivo: `backend/motor.py` — `mostrar_menu_interno` formata `{nome}` com
`primeiro_nome(quem["nome"])`, e **tolera a ausência do marcador** (quem editar a frase sem `{nome}`
recebe a frase, não um erro); `ESSE_E_VOCE` passa a usar `primeiro_nome` em vez de `.split()[0]` —
verificação: um teste com o nome do ERP em caixa alta (`BENEDITO  VASKEVICZ`) recebendo `Benedito`, e
outro com a frase sem o marcador não quebrando — reversão: `git checkout`.

**3. Colher a logo** — arquivo: `backend/logos.py` (novo) — `receber` (grava a linha, baixa o
arquivo pelo `saida.baixar` que o canal de campo já usa, e faz a primeira pergunta) e `responder`
(lê a resposta pendente). Regras que vão no código, não no prompt: sem o código do ERP a logo **fica
guardada**, não descartada; `pede_menu` na resposta **abandona a pergunta** e deixa a logo salva; e
depois de **uma** insistência o fluxo para de perguntar — é a lição do teto do #1028, aplicada aqui
antes de o defeito existir — verificação: `pytest tests/test_logos.py` — reversão: apagar o arquivo.

**4. O interceptador, ANTES do silêncio** — arquivo: `backend/motor.py` — a chamada a
`logos.receber` fica **ao lado do `campo.receber`**, não dentro dele, e **antes** do ramo que hoje
cala para quem é da casa. Só documento (`e.tipo == 'document'`) de quem `internos.quem_e` reconhece
— verificação: um teste em que o documento de um interno **não** cai no silêncio **e** um que prova
que `material_de_campo` continua **vazio** depois dele (a mistura que o desenho evita) — reversão:
`git checkout`.

**5. A resposta, ANTES do canal de campo** — arquivo: `backend/motor.py` — `logos.responder` vem
**antes** de `campo.texto_de_interno`. **É a trava:** depois dele, "7687" viraria frase da próxima
foto. E vem **depois** de `campo.responder`, para não roubar a resposta de uma pergunta de foto que
já estava aberta — verificação: um teste com uma pergunta de foto pendente **e** uma logo pendente,
provando que a resposta vai para a foto; e outro com só a logo pendente, provando que vai para ela —
reversão: `git checkout`.

**6. Os testes** — arquivos: `tests/test_logos.py` (novo), `tests/test_motor.py` — o caso real do
Benedito ponta a ponta (documento → pergunta → código → marca → guardada), o nome em caixa alta, o
`material_de_campo` intacto, a ordem do passo 5, e o `pede_menu` escapando — verificação: todos
passam e a suíte inteira passa — reversão: apagar.

**7. Os manuais** — arquivos: `docs/manuais/recepcao.md` e `docs/manuais/campo-equipe.md` — publicar
o `## Manual de uso` da spec, **e a diferença que o `campo-equipe.md` não tinha**: mandar **foto** é
canal de campo; mandar **arquivo de logo** é este caminho novo. `INDICE.md` não muda — verificação:
alguém de fora manda uma logo lendo só o manual — reversão: `git checkout`.

**8. [SÓ O DONO] Os dois restarts e a prova** — abaixo — reversão: o `ROLLBACK_PLAN` da spec.

**9. Devolver a demanda** — fechar o #1036 com o manual, **dizendo que a logo ainda não aparece na
tela Parceiras** (a outra metade é chamado próprio) e **abrindo esse chamado** — verificação: quem
abriu entende o limite sem perguntar — reversão: reabrir.

## O que só você pode fazer

**1. Reiniciar os dois** (janela elevada; a migração entra ao subir):

```powershell
Restart-Service axiaatende-recepcionista
Restart-Service axiaatende-backend
```

**2. A prova, e ela é a do caso real.** Peça ao Benedito (ou faça do seu número) exatamente o que ele
fez às 15:27:

- escreva **"oi"** → deve vir *"Olá, Benedito!"* (ou o seu nome) no menu da casa;
- mande **a mesma logo em PDF** → a OlivIA deve **confirmar que recebeu** e perguntar o código do
  cliente no ERP;
- responda o código, depois o nome da marca → ela confirma que guardou e diz que **a autorização é
  na tela Parceiras**.

Eu confiro no banco que a linha ficou completa e que `material_de_campo` não recebeu nada.

**3. Se quiser abortar sem reverter código:** não há chave para esta etapa, e isso é dito de
propósito — colher uma logo não tem risco a desligar. O que existe é o rollback inteiro da spec. **E
antes de revertê-lo, salve as logos já colhidas:** é o único ponto desta etapa em que reverter
destrói dado que não existia antes.

## Riscos de execução identificados

| Passo | O que quebra se interromper no meio | É seguro ficar parado ali? |
|---|---|---|
| 1 (migração no disco) | nada: só é aplicada ao subir | **sim** |
| 1 aplicado + código antigo | nada: a tabela fica vazia e a frase com `{nome}` literal **nunca é mostrada**, porque só `mostrar_menu_interno` novo a formata — o antigo manda o texto cru. **Atenção:** neste estado o menu da casa mostraria `{nome}` na tela. Dura o intervalo até o restart, e o restart é o passo 8 | **sim**, mas é o único estado feio |
| 2, 3, 6, 7 | nada: código e documento no disco | **sim** |
| **4 sem o 5** | **AQUI É O RISCO:** a logo seria colhida e a resposta "7687" cairia no `campo.texto_de_interno`, virando frase da próxima foto — a logo ficaria para sempre sem código. Os dois passos são do mesmo arquivo e entram no mesmo commit | **não** — e o plano não deixa esse estado existir |
| 8 (restarts) | se só um subir, um fica com schema novo. A migração é transacional e com trava: sem aplicação parcial | **sim**, terminando o segundo |

**O passo 1 é o único que escreve em produção.** Cria tabela (nada a perder) e faz **um** `UPDATE`
numa linha de `menu`, cujo valor literal de hoje está no `_VOLTA`.

**O fio da spec que não virou passo, e por quê:** `menu.destino_id`, que a tela Destinos escreve, não
é tocado por esta etapa — nenhum dos sete passos escreve naquela coluna.

## Linha de abertura da sessão de execução

> Leia o `C:\AxiaAtende\CLAUDE.md` inteiro e o `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Faixa:
> **aplicação de plano aprovado** — execute
> `C:\AxiaAtende\docs\specs\2026-10-15-pelo-nome-e-a-logo-que-vira-proposta-plano.md`, com a spec ao
> lado. Chamado **#1036**: todo commit cita `#1036`, prefixo `[axiaatende]`, e o primeiro ato é
> `tratar 1036 --status em_andamento`. **As decisões que NÃO se reabrem:** a logo vira **proposta,
> nunca aprovada** (o `CHECK` `parceiras_autorizada_com_documento` do banco do marketing impede o
> contrário, então não há o que discutir); a logo **espera ser puxada** pelo Marketing, pela
> `chave_pedido` que já existe — **esta etapa não cria rota de saída nem segredo**; sem o código do
> ERP a logo **fica guardada**, nunca descartada; logo que chega como **foto** continua indo ao canal
> de campo; o nome vem de `primeiro_nome()` e o texto continua **cadastro**. **A ordem dos passos 4 e
> 5 é trava**, não gosto. **Escopo:** só o lado do AxiaAtende — puxar e mostrar na tela Parceiras é
> chamado próprio, em outro repositório, e o passo 9 o abre. Pare no passo 8. O que vai para a tela
> durante a execução está no `PADRAO-TRABALHO.md` §1.
