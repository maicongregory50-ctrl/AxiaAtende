# Plano — A resposta que chega antes da pergunta
**Data:** 2026-10-19
**Chamado:** #1047
**Spec de origem:** `docs/specs/2026-10-19-a-resposta-que-chega-antes-da-pergunta.md`
**Status:** APROVADO
**Executável pelo agente:** sim

> **Sem bloco `pos-entrega`:** não há fase `.sql` — esta etapa **não tem migração**. Só código, num
> serviço que não está no catálogo da `Porta-Ação`. O restart é da mão do dono (passo 5).

> **Esta é a etapa mais barata da semana, e é de propósito:** nenhuma coluna nova, nenhuma tabela,
> nenhuma migração, nenhum texto de cadastro. Só duas funções que já existem passando a ser chamadas
> onde ninguém as chamava. O rollback é `git revert` e um restart.

## Passos

**1. O ajudante que lê a data da frase** — arquivo: `backend/campo.py` — uma função que recebe o
texto e a linha, passa por `ler_data(texto, agora)` e `ler_safra(texto)` **nessa ordem** (data dita
ganha de safra, como no ramo de resposta), e grava `data_dita` ou `safra_dita` **no grupo todo**,
com `data_presumida = false`. **Não grava se já houver data ou safra** — a primeira resposta vale, e
isso evita que uma segunda frase troque a data que a pessoa já deu. **Por parser, não pela IA**, pelo
motivo da decisão 1 da spec — verificação: `pytest tests/test_campo.py` passa inalterado (nenhum
teste existente manda data na frase) — reversão: apagar a função.

**2. Chamá-lo nos DOIS pontos em que o texto livre é absorvido** — arquivo: `backend/campo.py` — o
ramo *"texto solto logo depois da foto"* (linha ~414, onde o `_ler` da IA já roda) e o ramo
`bastidor` (linha ~445, que faz o mesmo). São os dois lugares em que o texto vira legenda e é lido;
deixar um de fora faria a data se perder exatamente num dos caminhos — verificação: um teste por
ponto, e a conferência de que `_falta` deixa de devolver `"data"` nos dois — reversão: `git checkout`.

**3. A releitura no instante do envio** — arquivo: `backend/campo.py`, `_perguntar_proxima` — ler a
linha do banco antes de decidir, em vez de confiar na que o chamador passou. **Ganho estreito e dito
como tal:** não teria mudado o caso de hoje, a janela é de segundos, e **não há ocorrência medida**;
entra porque o dono decidiu sabendo disso e porque custa duas linhas — verificação: a suíte inteira
passa (é mudança de leitura, não de regra, e nenhum teste deve mudar de resultado) — reversão:
`git checkout`. **Reversão independente do passo 2.**

**4. Os testes** — arquivo: `tests/test_campo.py` — o **caso real de hoje ponta a ponta**: duas fotos,
a frase, `"Hoje"`, e **zero perguntas** (é a asserção que descreve o chamado); a safra pela frase
(`"safra 2025"` ⇒ sem dia, `data_presumida` false); a frase que **não** tem data continuando a levar
à pergunta; e a data já dada **não** sendo trocada por uma frase posterior — verificação: os quatro
passam e a suíte inteira passa — reversão: apagar.

**5. [SÓ O DONO] Um restart e a prova** — abaixo — reversão: `ROLLBACK_PLAN` da spec.

**6. O manual** — arquivo: `docs/manuais/campo-equipe.md` — a frase do passo 2 que passa a dizer
errado (ela descreve a data **sempre** como pergunta) e a seção nova do `## Manual de uso` da spec.
`INDICE.md` não muda — verificação: alguém de fora lê e sabe que dizer a data na frase dispensa a
pergunta — reversão: `git checkout`.

**7. Devolver a demanda** — fechar o #1047 com o manual — verificação: quem abriu entende lendo só a
devolução — reversão: reabrir.

## O que só você pode fazer

**1. Um restart só** (janela elevada). Não há migração, então o das telas não é necessário:

```powershell
Restart-Service axiaatende-recepcionista
```

**2. A prova é repetir a manhã de hoje**, e ela tem um sinal claro: mande uma foto com a frase
**incluindo a data** — *"conferindo qualidade hoje"* — e a OlivIA deve responder **"Recebi." e mais
nada**. Em alguns minutos chega *"entrou no catálogo"*, **sem nenhuma pergunta**.

Para provar o outro lado, mande uma foto com frase **sem** data (*"colheita do centeio"*): a pergunta
*"É de hoje?"* deve continuar vindo, porque a etapa não adivinha.

Eu confiro no banco: `data_dita` preenchida, `data_presumida = false`, `perguntas_feitas` **vazio**.

## Riscos de execução identificados

| Passo | O que quebra se interromper no meio | É seguro ficar parado ali? |
|---|---|---|
| 1 (a função, sem chamador) | nada: código morto até o passo 2 | **sim** |
| 2 (um ponto só dos dois) | a data seria lida num caminho e perdida no outro — inconsistência difícil de explicar depois. Os dois pontos são do mesmo arquivo e entram no mesmo commit | **não** — e o plano não deixa esse estado existir |
| 3 | nada: é leitura, não regra | **sim** |
| 4, 6 | nada: teste e documento | **sim** |
| 5 (restart) | o recepcionista fica segundos fora; a Meta retém e repete os avisos por até 7 dias | **sim** |

**Nenhum passo escreve em produção**, e esta é a primeira etapa da semana em que isso é verdade:
sem migração, sem tabela, sem `UPDATE` de cadastro. O que muda é **quando** uma coluna que já existe
é preenchida.

**O fio da spec que vira cuidado de código, não passo:** `_fechar` presume o dia quando não há data
dita nem safra. Preencher a data mais cedo **não cria caminho novo** — entra pela porta que o
`_fechar` já conhece, e `data_presumida` continua `false`. O teste do passo 4 cobre exatamente isso.

**O risco que sobra é de desenho e está medido:** `ler_data` aceita `"sim"` como hoje (é o texto do
botão). Uma frase que seja exatamente *"sim"* viraria data — mas para chegar ali ela teria de ser uma
mensagem isolada com essa única palavra, logo depois de uma foto e **sem pergunta aberta**, o que é o
caso em que "sim" não responde nada mesmo. Fica dito; se incomodar, é uma linha.

## Linha de abertura da sessão de execução

> Leia o `C:\AxiaAtende\CLAUDE.md` inteiro e o `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Faixa:
> **aplicação de plano aprovado** — execute
> `C:\AxiaAtende\docs\specs\2026-10-19-a-resposta-que-chega-antes-da-pergunta-plano.md`, com a spec
> ao lado. Chamado **#1047**: todo commit cita `#1047`, prefixo `[axiaatende]`, e o primeiro ato é
> `tratar 1047 --status em_andamento`. **As decisões que NÃO se reabrem:** a data sai de um **parser**
> (`ler_data`, `ler_safra`), **não** da IA — `ia.ler_campo` não é alterada; **nenhum caminho especial
> para o dono**; **`ESPERA_PALPITE` e o tique do laço não são tocados** (foi o palpite que acertou a
> classe hoje, em 47 s); a releitura do passo 3 é **ganho estreito**, pedida pelo dono já informado de
> que não teria mudado o caso de hoje. **Os dois pontos do passo 2 entram juntos.** Pare no passo 5 —
> o restart e a prova são da mão do dono. O que vai para a tela durante a execução está no
> `PADRAO-TRABALHO.md` §1.
