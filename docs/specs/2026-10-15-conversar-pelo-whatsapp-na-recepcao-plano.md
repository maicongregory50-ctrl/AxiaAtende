# Plano — Conversar pelo WhatsApp a partir da coluna QUEM da Recepção
**Data:** 2026-10-15
**Chamado:** #1025
**Spec de origem:** `docs/specs/2026-10-15-conversar-pelo-whatsapp-na-recepcao.md`
**Status:** APROVADO

> **Sem bloco `pos-entrega`, e isso é decisão:** a etapa não aplica fase nenhuma, e
> `axiaatende-backend` **não está** nos cinco serviços do catálogo da `Porta-Ação`. Plano que não
> nomeia fase não autoriza fase, e o restart desta etapa é da mão do dono (passo 7). Não acrescentar
> o bloco depois: ele seria recusado na gravação.

## Passos

**1. O endereço do WhatsApp nasce no backend** — arquivo: `backend/rotas_telas.py` — uma função ao
lado de `mascarar()` que recebe o `wa_id` e devolve `https://web.whatsapp.com/send?phone=<dígitos>`
ou `None`, usando **o mesmo limiar da máscara** (menos de 10 dígitos ⇒ `None`, para texto e link
nunca discordarem), e o campo `conversar` em cada linha de `/recepcao`. O número vai como a Meta o
entregou (`wa_id`), **sem** `com_nove` — verificação: `pytest tests/test_telas.py tests/test_agenda.py`
passa como antes (o campo é aditivo) — reversão: tirar a função e o campo; a tela perde todo link
sozinha.

**2. O teste cobre o caso que a contagem de hoje não tem** — arquivo: `tests/test_telas.py` — três
asserções: número normal vira o endereço esperado; `wa_id` nulo devolve `None` (hoje são 0 linhas, e
a coluna é `NULL`-ável por desenho); e `mascarar()` continua devolvendo exatamente o que devolvia —
verificação: os três testes passam, e os dois antigos de `mascarar` continuam passando sem
alteração — reversão: apagar as asserções.

**3. A coluna QUEM passa a linkar nos dois ramos** — arquivo: `frontend/src/Recepcao.jsx` — no ramo
do cadastro, a pílula **Conversar no WhatsApp** ao lado do nome (onde hoje não há número nenhum); no
ramo de fora, o número mascarado vira o link. Sem o campo `conversar`, **nada aparece** — nunca um
link morto. Aba nova, com `rel="noopener noreferrer"` — verificação: `npm run build` sem erro, e a
leitura do diff confirma que os dois ramos tratam a ausência do campo — reversão: `git checkout` do
arquivo.

**4. O estilo da pílula e do número como link** — arquivo: `frontend/src/atende.css` — pílula na
família do `.chip` que já existe, e o número sublinhado discreto; nada de azul de navegador no meio
de uma tabela verde — verificação: a tela desenha a pílula alinhada com as etiquetas de papel que já
ficam ali — reversão: `git checkout` do arquivo.

**5. O manual conta o que mudou, e corrige o que ficou incompleto** — arquivo:
`docs/manuais/recepcao.md` — publicar o que a spec já escreveu (`## Manual de uso`), **e** caçar o
que a mudança tornou incompleto: a linha *"fora do cadastro"* (hoje linha 44) não diz que o número
agora é link, e a linha do cadastro (43) não menciona a pílula. **Não há linha nova no
`docs/manuais/INDICE.md`:** `recepcao.md` já está lá, e o índice deste projeto tem duas colunas
(`Manual` / `Do quê`) — não é o formato de três colunas do AxiaGestão, e `conferir_indice.py` não
existe aqui — verificação: alguém de fora abre o manual e executa o caminho comum sem perguntar
nada — reversão: `git checkout` do arquivo.

**6. O pacote da tela** — pasta: `frontend/` — `npm run build` (gera `frontend/dist`, que é o que o
serviço serve) — verificação: o build termina sem erro e `dist` fica mais novo que os fontes —
reversão: nenhuma necessária; o `dist` anterior volta com o build do código revertido.

**7. [SÓ O DONO] O restart e a prova do clique** — verificação: a tela mostra o link e a conversa
abre — reversão: passo a passo do `ROLLBACK_PLAN` da spec.

**8. Devolver a demanda** — fechar citando o que mudou e apontando o manual. Nenhum pré-requisito de
cadastro foi criado: a etapa não pede nada de ninguém antes de servir — verificação: quem abriu usa
a tela lendo só a devolução — reversão: reabrir a demanda.

## O que só você pode fazer

**1. Reiniciar o serviço das telas** (janela elevada — o serviço roda como LocalSystem, e esta sessão
não eleva):

```powershell
Restart-Service axiaatende-backend
```

**2. A prova do clique — é o único passo que o código não prova.** Abra
`http://127.0.0.1:8009`, aba **Recepção**, e clique no link de **um número que você conhece**.

- **Abriu a conversa certa:** está provado, e a etapa fecha.
- **O WhatsApp disse que o número é inválido:** é o achado do `## O universo medido` se
  confirmando — 31 dos 33 `wa_id` vêm **sem** o nono dígito, e a casa tem o `com_nove()` que o
  acrescenta. Me diga, e a correção é de uma linha no passo 1 (passar o número por `com_nove`), com
  o teste do passo 2 ajustado junto. **Não é replanejamento:** a alternativa já está escrita na spec.

Nada mais pede a sua mão: não há fase `.sql`, não há segredo, não há tarefa agendada, e o
recepcionista (8008) não é tocado — o atendimento no WhatsApp não para em nenhum momento.

## Riscos de execução identificados

| Passo | O que quebra se interromper no meio | É seguro ficar parado ali? |
|---|---|---|
| 1 e 2 (backend) | nada: campo aditivo numa rota de leitura. Com o backend novo e a tela antiga, a tela ignora o campo e fica como hoje | **sim** |
| 3 e 4 (tela) | nada em produção: o serviço serve o `dist`, e o `dist` só muda no passo 6 | **sim** |
| 6 (build) | `dist` meio escrito faria a tela não carregar. É de segundos, e refazer o build conserta | **sim**, refazendo o build |
| 7 (restart) | o serviço das telas fica alguns segundos fora. **Ninguém de fora usa a 8009**; o recepcionista não é tocado | **sim** |

**Nenhum passo escreve dado.** Não há estado intermediário em banco, e por isso nenhum passo precisa
ser atômico. O fio da spec (`wa_id` lido por `agenda`, `campo` e `envio`) não é tocado por passo
nenhum: a etapa não escreve `wa_id` nem muda a forma guardada.

**O risco que sobra não é de execução, é de leitura da tela:** a partir daqui o número inteiro está
no endereço do link, visível ao passar o mouse e ao copiar. Foi decisão do dono, com a alternativa
pesada e recusada (spec, `## Decisão`, ponto 1).

## Linha de abertura da sessão de execução

> Leia o `C:\AxiaAtende\CLAUDE.md` inteiro e o `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Faixa:
> **aplicação de plano aprovado** — execute
> `C:\AxiaAtende\docs\specs\2026-10-15-conversar-pelo-whatsapp-na-recepcao-plano.md`, com a spec ao
> lado (mesmo nome, sem `-plano`). Chamado **#N**: todo commit cita `#N`, com o prefixo
> `[axiaatende]`, e o primeiro ato é `tratar N --status em_andamento` pela skill `/demanda`. **As
> decisões que NÃO se reabrem:** a máscara continua no texto e o número inteiro vai no `href` (a rota
> com `302` foi apresentada e recusada); o link aparece em **toda** linha, inclusive na de quem está
> no cadastro; o endereço é `web.whatsapp.com/send`, não `wa.me`; o clique **não** é registrado. Pare
> no passo 7 — restart e a prova do clique são da mão do dono. O que vai para a tela durante a
> execução está no `PADRAO-TRABALHO.md` §1: decisão do dono, incidente que merece chamado próprio, e
> passo que depende da mão dele. Conserto de caminho feito dentro do planejado não se narra.
