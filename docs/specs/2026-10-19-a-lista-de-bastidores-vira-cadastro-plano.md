# Plano — A lista de bastidores vira cadastro, e a resposta que não encaixa é dita
**Data:** 2026-10-19
**Chamado:** #1048
**Spec de origem:** `docs/specs/2026-10-19-a-lista-de-bastidores-vira-cadastro.md`
**Status:** APROVADO
**Executável pelo agente:** sim

> **Sem bloco `pos-entrega`:** migração do banco do atendimento, fora do catálogo da `Porta-Ação`,
> aplicada pelo serviço ao subir. Os dois restarts são da mão do dono (passo 7).

> **A ordem 1 → 2 → 3 é dependência real:** o cadastro existe antes de alguém o ler, e o `ia.py` lê a
> lista que o `campo.py` entrega. Fora de ordem, o serviço sobe com `enum` vazio e **nada classifica**.

## Passos

**1. O cadastro, com as nove categorias** — arquivos:
`backend/migracoes/022_bastidores_em_cadastro.sql` e `_VOLTA` — a linha `campo.bastidores` em
`atendimento.ajustes`, com objetos `{chave, rotulo, descricao, institucional}`: as cinco de hoje
(preservando chave, rótulo e a descrição que já está na prosa do `INSTRUCOES_CAMPO`) e as quatro
novas — `estoque`, `estrutura`, `produto-embalagem`, `manejo`. `institucional` **true** em `estoque`
e `estrutura`, **false** nas outras duas (proposta minha, corrigível pelo dono, registrada na spec) —
verificação: `SELECT jsonb_array_length(valor) FROM atendimento.ajustes WHERE chave =
'campo.bastidores'` devolve **9**, e nenhuma `chave` repetida — reversão: o `_VOLTA` à mão (passo 7).

**2. `campo.py` lê o cadastro, e a constante vira SEMENTE** — arquivo: `backend/campo.py` —
`bastidores(con)` e `guardar_bastidores(con, lista)` no molde exato de `produtos`/`guardar_produtos`.
`BASTIDORES` **deixa de ser a verdade**: passa a ser a semente usada **só** quando a linha falta, no
molde do `interno.ligado` do #1031 (padrão na ausência, para o fluxo não morrer calado). Os lugares
que hoje fazem `BASTIDORES[b]` passam a consultar o cadastro — verificação: `pytest
tests/test_campo.py` passa **inalterado** (as cinco de hoje continuam valendo com os mesmos rótulos),
e um teste novo prova que sem a linha o fluxo cai na semente de cinco — reversão: `git checkout`.

**3. `ia.py` monta o `enum` E a prosa do cadastro** — arquivo: `backend/ia.py` — `ler_campo` recebe
os bastidores; `INSTRUCOES_CAMPO` deixa de ser constante e passa a ser montada de `chave` +
`descricao`. **O `enum` continua fechado** — é o que mantém o "conforme" da R7 verdadeiro: muda de
onde a lista vem, não que exista uma — verificação: um teste conferindo que o `enum` mandado ao
modelo tem as **nove** chaves do cadastro e que a prosa cita `estoque` — reversão: `git checkout`.

**4. A resposta que não encaixa é dita** — arquivo: `backend/campo.py`, ramo `bastidor` de
`responder` — quando o texto livre não classifica, em vez de seguir: a **lista fechada** das
categorias, **uma vez** (marcada em `perguntas_feitas`, que é array de texto livre — sem mexer no
`CHECK` de `pergunta_pendente`, que já aceita `'bastidor'`). Não resolvendo, a frase de que a peça
**vai sem classe** e que o marketing classifica na Caixa. Nove categorias cabem numa lista do
WhatsApp (o limite é dez) — verificação: o caso de hoje em teste — *"Estoque."* classificando em
`estoque`; e uma resposta impossível recebendo **a lista** e depois **a frase**, nunca silêncio —
reversão: `git checkout`. **Independente do passo 3.**

**5. Os testes** — arquivos: `tests/test_campo.py`, `tests/test_ia.py` — o caso de hoje ponta a ponta,
a resposta que não encaixa sendo dita, a ausência do cadastro caindo na semente, o `enum` vindo do
cadastro, e **a prova de que as cinco de hoje não mudaram de comportamento** — verificação: todos
passam e a suíte inteira passa — reversão: apagar.

**6. O manual** — arquivo: `docs/manuais/campo-equipe.md` — as categorias novas e o que acontece
quando a resposta não encaixa. **Nada no manual de hoje fica falso** (ele descreve o que a OlivIA
pergunta, não o conjunto de categorias); `INDICE.md` não muda — verificação: alguém de fora sabe o
que fazer ao receber a lista — reversão: `git checkout`.

**7. [SÓ O DONO] Os dois restarts e a prova** — abaixo — reversão: o `ROLLBACK_PLAN` da spec.

**8. Devolver a demanda, e abrir a do marketing** — fechar o #1048 dizendo que a categoria nova
**ainda não aparece etiquetada no catálogo**, e abrir o chamado do AxiaMarketing (ler a lista do
cadastro em vez das três constantes dele) — verificação: quem abriu entende o limite sem perguntar —
reversão: reabrir.

## O que só você pode fazer

**1. Os dois restarts** (janela elevada; a migração entra ao subir):

```powershell
Restart-Service axiaatende-recepcionista
Restart-Service axiaatende-backend
```

**2. A prova é repetir a manhã de hoje.** Mande uma foto com a legenda **"Estoque."** — deve vir
*"Parece estoque. É isso?"*, e não beneficiamento. Toque **Sim** e a peça fica com classe.

Para provar o outro lado, responda à pergunta de bastidor com algo que não existe (*"xisto betuminoso"*):
deve chegar **a lista** das nove categorias; ignore-a, e deve chegar a frase de que a foto **vai sem
classe**. O que não pode acontecer é silêncio.

Eu confiro no banco: `classe_bastidor = 'estoque'` e as nove chaves no cadastro.

**3. O que esta etapa NÃO faz, e você vai notar:** a peça classificada em `estoque` chega ao
catálogo do marketing **sem etiqueta**, porque o lado de lá tem a lista dele. É o chamado que o
passo 8 abre.

## Riscos de execução identificados

| Passo | O que quebra se interromper no meio | É seguro ficar parado ali? |
|---|---|---|
| 1 (migração no disco) | nada: só é aplicada ao subir | **sim** |
| 1 aplicado + código antigo | nada: `BASTIDORES` ainda é a verdade e a linha é **ignorada**. É também o rollback barato | **sim** |
| **2 sem o 3** | **AQUI É O RISCO:** `campo` entrega nove e `ia` ainda tem cinco no `enum` — a IA nunca devolveria as novas, e o palpite voltaria a chutar errado em silêncio. Os dois são do mesmo commit | **não** — e o plano não deixa esse estado existir |
| 3 sem o 1 | o `enum` sairia **vazio** e nada classificaria. É por isso que a migração é o passo 1 | **não** |
| 4, 5, 6 | nada: é o aviso, teste e documento | **sim** |
| 7 (restarts) | se só um subir, um fica com schema novo; a migração é transacional e com trava | **sim**, terminando o segundo |

**O único passo que escreve em produção é o 1**, e ele **acrescenta uma linha** — não altera nem
apaga nada. Nenhuma peça já catalogada é tocada: as 27 sem classe continuam sem classe, por decisão
da spec.

**O fio que atravessa projeto e NÃO é coberto aqui:** o AxiaMarketing tem a lista dele em três
lugares, e valor desconhecido lá produz **etiqueta vazia, em silêncio**. Está em *FORA* na spec, e o
passo 8 abre o chamado. Enquanto isso, a categoria nova é correta aqui e invisível lá.

## Linha de abertura da sessão de execução

> Leia o `C:\AxiaAtende\CLAUDE.md` inteiro e o `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Faixa:
> **aplicação de plano aprovado** — execute
> `C:\AxiaAtende\docs\specs\2026-10-19-a-lista-de-bastidores-vira-cadastro-plano.md`, com a spec ao
> lado. Chamado **#1048**: todo commit cita `#1048`, prefixo `[axiaatende]`, e o primeiro ato é
> `tratar 1048 --status em_andamento`. **As decisões que NÃO se reabrem:** a lista vira **cadastro**
> (molde de `campo.produtos`), com as **nove** categorias que o dono escolheu; `BASTIDORES` fica no
> código **só como semente** para a ausência da linha; o `enum` do modelo continua **fechado**, só
> passa a vir do cadastro; a resposta que não encaixa recebe **a lista uma vez** e depois a frase de
> "vai sem classe" — **nunca silêncio**; `FASES` fica **fora** (0 de 35 peças medidas); as 27 peças
> sem classe **não** são reclassificadas. **A ordem 1 → 2 → 3 é dependência**, não gosto: o cadastro
> antes de quem o lê, e `campo` e `ia` no mesmo commit. Pare no passo 7. O que vai para a tela
> durante a execução está no `PADRAO-TRABALHO.md` §1.
