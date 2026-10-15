# Plano — O atendente para de martelar quem não recebe
**Data:** 2026-10-15
**Chamado:** #1028
**Spec de origem:** `docs/specs/2026-10-15-o-atendente-para-de-martelar-quem-nao-recebe.md`
**Status:** APROVADO
**Executável pelo agente:** sim

> **Sem bloco `pos-entrega`, e isso é decisão:** a etapa não aplica fase nenhuma, e
> `axiaatende-recepcionista` **não está** nos cinco serviços do catálogo da `Porta-Ação`. Plano que
> não nomeia fase não autoriza fase, e o restart desta etapa é da mão do dono (passo 6). Não
> acrescentar o bloco depois: ele seria recusado na gravação.

> **As duas regras são independentes de propósito** (spec, `ROLLBACK_PLAN`). Os passos 1 e 2 podem
> ser revertidos separadamente, e é por isso que são passos separados e não um só.

## Passos

**1. R1 — lista recusada não é tentada de novo** — arquivo: `backend/motor.py`, em `perguntar()`
(linha 128), que é o **único** ponto por onde o menu sai como lista (o menu principal passa por ele).
Uma função ao lado consulta `atendimento.enviadas` por `tipo = 'lista'` com `erro` de `131026` para
aquele destino; achando, a lista **não sai** e uma linha vai ao log. O caminho de `botoes` (3 opções
ou menos) **não** é tocado: a medição só viu `131026` em `lista`, e calar o que não foi medido é
passar do que o dono autorizou — verificação: `pytest tests/test_motor.py` passa como antes (ninguém
tem `131026` nas fixtures) — reversão: tirar a guarda; o menu volta a sair sempre.

**2. R2 — teto de 2 "não entendo" por destino em 24 h** — arquivo: `backend/motor.py`, no ramo de
"não é texto nem botão" (perto da linha 395), **antes** de `saida.texto(p.para, NAO_ENTENDO)`. Conta
em `enviadas` os `resumo LIKE 'nao entendo:%'` daquele destino nas últimas 24 h; de 2 em diante, não
envia e registra no log. Por destino e não por conversa, pelo motivo escrito na spec (o registro só
existe quando há conversa aberta) — verificação: `pytest tests/test_motor.py` — reversão: tirar a
contagem; volta a responder sempre.

**3. O silêncio fica visível** — arquivo: `backend/recepcionista.py` — o contador `calados` no
`/saude`, no molde de `chegadas` (linha 187), com `lista_recusada` e `nao_entendo` separados. É o que
impede esta etapa de ser ela mesma um fracasso silencioso — verificação: `GET
http://127.0.0.1:8008/saude` traz o bloco `calados` com os dois campos em zero — reversão: tirar o
bloco.

**4. Os testes, inclusive o que protege gente de verdade** — arquivo: `tests/test_motor.py` — quatro
casos: (a) depois de um envio de `lista` com `131026` gravado, o menu não sai e o texto continua
saindo; (b) o segundo "não entendo" sai e o terceiro não; (c) **um `unsupported` isolado continua
recebendo a linha curta como hoje** — é o caso dos três reais medidos, e é o que a etapa não pode
quebrar; (d) um `131026` gravado em `tipo = 'modelo'` (um convite do `envio.py`) **não** cala o menu
daquele destino — a prova de que os três escritores de `enviadas` não envenenam a regra —
verificação: os quatro passam, e a suíte inteira passa — reversão: apagar os casos.

**5. O manual** — arquivo: `docs/manuais/recepcao.md` — a seção nova, publicando o que a spec já
escreveu (`## Manual de uso`), no molde da *"A retomada pela OlivIA"* que já está lá. **Não há linha
nova no `docs/manuais/INDICE.md`:** `recepcao.md` já está indexado, e o índice deste projeto tem duas
colunas (`Manual` / `Do quê`), não o formato de três do AxiaGestão — verificação: alguém de fora lê e
entende por que uma conversa ficou sem resposta, sem perguntar — reversão: `git checkout` do arquivo.

**6. [SÓ O DONO] O restart e a prova** — verificação abaixo — reversão: o `ROLLBACK_PLAN` da spec.

**7. Devolver a demanda** — fechar o #1028 citando o que mudou e o que ficou de fora, com o manual.
Nenhum pré-requisito de cadastro foi criado — verificação: quem abriu entende lendo só a devolução —
reversão: reabrir a demanda.

## O que só você pode fazer

**1. Reiniciar o recepcionista** (janela elevada — o serviço roda como LocalService, e esta sessão
não eleva):

```powershell
Restart-Service axiaatende-recepcionista
```

Durante os segundos de restart a Meta **retém e repete** os avisos por até 7 dias: nenhuma mensagem
de cliente se perde.

**2. A prova, e ela é barata porque o laço já deixou rastro.** O `5511933157031` já tem **7 listas
falhadas gravadas**, então a R1 engata na primeira tentativa depois do restart — não é preciso
provocar nada. Confira em:

```powershell
Invoke-RestMethod http://127.0.0.1:8008/saude | Select-Object -ExpandProperty calados
```

- **`lista_recusada` subiu de zero** na próxima vez que aquele robô escrever: provado, e o chamado
  fecha. Eu leio o banco e confirmo que não há `131026` novo depois do restart.
- **O robô parou de escrever sozinho** antes disso: a prova fica para a próxima vez. A regra está no
  ar e testada; o que falta é testemunho, e isso é honesto dizer no fechamento.

**3. A conta que importa é à meia-noite.** A nota do número é lida então. Se ela sair de GREEN, me
diga: não é consequência desta etapa (ela só reduz envios), mas é o sinal de que os 7 `131026` de
hoje já custaram algo, e aí o assunto é a Meta, não o código.

Nada mais pede a sua mão: não há fase `.sql`, não há segredo, não há tarefa agendada, e as telas
(8009) não são tocadas.

## Riscos de execução identificados

| Passo | O que quebra se interromper no meio | É seguro ficar parado ali? |
|---|---|---|
| 1 e 2 | nada em produção: o serviço só carrega o código novo no restart (passo 6) | **sim** |
| 3 | idem — o `/saude` em produção continua o de hoje até o restart | **sim** |
| 4 e 5 | nada: teste e documento | **sim** |
| 6 (restart) | o recepcionista fica segundos fora e **a Meta repete os avisos retidos**; nenhuma mensagem se perde | **sim** |

**Nenhum passo escreve dado.** Não há estado intermediário em banco e nenhum passo precisa ser
atômico. Os três escritores de `enviadas` (`motor`, `envio`, `campo`) continuam escrevendo como
hoje: esta etapa só **lê** aquela tabela.

**O risco que sobra é de desenho, não de execução, e está na spec:** um cliente com WhatsApp muito
antigo tem a mesma assinatura do robô e deixa de receber a lista — que hoje já não chega a ele. O
sinal para descobrir se isso aconteceu é um destino com `131026` em `lista` **e** mensagens de texto
entregues que não sejam "não entendo".

## Linha de abertura da sessão de execução

> Leia o `C:\AxiaAtende\CLAUDE.md` inteiro e o `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Faixa:
> **aplicação de plano aprovado** — execute
> `C:\AxiaAtende\docs\specs\2026-10-15-o-atendente-para-de-martelar-quem-nao-recebe-plano.md`, com a
> spec ao lado (mesmo nome, sem `-plano`). Chamado **#1028**: todo commit cita `#1028`, com o prefixo
> `[axiaatende]`, e o primeiro ato é `tratar 1028 --status em_andamento` pela skill `/demanda`. **As
> decisões que NÃO se reabrem:** o discriminador é o `131026`, nunca o texto da mensagem (consertar
> pela lista `AUTOMATICA` está descartado pelo critério escrito dela, porque calaria pessoa
> confusa); a regra cala a **lista** para aquele destino, não o destino inteiro, porque a medição
> mostrou texto entregando 13 de 13 e lista falhando 7 de 7; o teto é **2 por destino em 24 h**, não
> por conversa; o menu em texto para quem não recebe lista foi **recusado** pelo dono. Pare no passo
> 6 — restart e prova são da mão dele. O que vai para a tela durante a execução está no
> `PADRAO-TRABALHO.md` §1: decisão do dono, incidente que merece chamado próprio, e passo que depende
> da mão dele. Conserto de caminho feito dentro do planejado não se narra.
