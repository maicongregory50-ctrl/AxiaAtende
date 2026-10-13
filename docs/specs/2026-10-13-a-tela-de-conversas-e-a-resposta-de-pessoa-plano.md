# Plano — A retomada pela OlivIA
**Data:** 2026-10-13
**Chamado:** #989
**Spec de origem:** `C:\AxiaAtende\docs\specs\2026-10-13-a-tela-de-conversas-e-a-resposta-de-pessoa.md` (APROVADA, 13/10/2026)
**Status:** APROVADO (dono, 13/10/2026)
**Executavel pelo agente:** sim

## Contexto

Quem para no meio do atendimento fica sem nada, e ninguém da casa responde à mão. A spec fechou: 30
minutos depois de a conversa parar, a OlivIA relê tudo o que a pessoa escreveu e tocou, acha a opção
do menu que resolve e manda "Pelo que entendi da nossa conversa, você quer: X. É isso?" com **Sim**
(manda o link) e **Ver opções** (a pergunta do ponto onde ela parou). Uma vez por conversa, só nas
24 h da última mensagem, nunca texto livre.

Tudo o que o plano toca já existe no motor: `marcar_paradas` (o gatilho), `propor` (a confirmação
com `ia:sim:<chave>`), `ia.classificar` contra `folhas_e_menus`, `reperguntar` (#988, a pergunta do
nó atual), `campo.ultima_mensagem_de` (a janela), `_registrar` (`enviadas`). Não há tela.

## Passos

**1. Migração 016** — `backend/migracoes/016_retomada.sql` + `_VOLTA.sql`: `conversas.retomada_em
timestamptz` e `retomada_chave text`; semente do ajuste `retomada` em `atendimento.ajustes` com o
texto *"Pelo que entendi da nossa conversa, você quer: {opcao}. É isso?"* (`ON CONFLICT DO
NOTHING`); `tests/test_login.py` ganha a 016 na lista. — verificação: suíte sobe com a 016 —
reversão: `016_retomada_VOLTA.sql`.

**2. A retomada no motor** — `backend/motor.py`: `retomar_paradas(con, saida, ia, agora) -> int`,
chamada em `recepcionista.rotina_do_minuto` logo depois de `marcar_paradas` (a rotina já recebe
`ia`), com `try/except` próprio. Para cada conversa `parou_no_meio` com `retomada_em IS NULL` e
`iniciada_em` nos últimos 2 dias: (a) a janela: `campo.ultima_mensagem_de(con, wa_id)` há menos de
24 h, senão grava `retomada_em` e segue; (b) o que a pessoa disse: os textos e os títulos dos toques
dela em `eventos_meta` desde `iniciada_em`, juntos por " / " (até 1000 caracteres); (c) sem IA ou
sem texto, grava `retomada_em` e segue; (d) `ia.classificar(texto, folhas_e_menus(con))`; nó que
não é raiz nem encerrar: manda os botões com o ajuste `retomada` (`{opcao}` = rótulo e, entre
parênteses, o caminho), `Opcao("ia:sim:<chave>", "Sim")` e `Opcao("ia:volta", "Ver opções")`;
grava `ia_proposta_id`, `retomada_em`, `retomada_chave`, `situacao = 'em_curso'` e `ultimo_toque_em
= agora` (o Sim cai nesta conversa); `_registrar(... "botoes", "ia retomou <chave>")`. Sem nó:
`retomada_em` e silêncio. Erro da Meta: grava `retomada_em` com `retomada_chave = 'erro: ...'` e
segue (uma tentativa). Em `tratar`: `elif e.toque == "ia:volta"`: `ia_confirmou = false` e
`reperguntar(con, saida, p, conversa, "")` (sem a linha da lista antiga; `reperguntar` passa a só
mandar o texto quando há aviso). — verificação: testes do passo 3 — reversão: o commit.

**3. Testes** — `tests/test_motor.py`: (a) a conversa para (oi › Comercial › Revendedor, texto
"consegue me passar os sc" que a IA falsa não leu), `rotina_do_minuto` aos 31 min marca parou; aos
32 min, com `IAFalsa(resposta="comercial.revenda.sc")`, sai o botão "Pelo que entendi … SC
(Comercial › Revendedor)" com `ia:sim:comercial.revenda.sc` e `ia:volta`; a conversa volta a
`em_curso` com `retomada_em`; a IA viu o texto junto ("oi / … / consegue me passar os sc"); (b) a
rotina de novo não repete; o Sim manda o link de SC e `ia_confirmou = true`; (c) `ia:volta` mostra
"Em qual estado você atua?" com os estados; (d) fora das 24 h (o `recebido_em` dos eventos fixado em
AGORA − 25 h) nada sai e `retomada_em` fica gravado; (e) sem IA, ou IA sem resposta, nada sai e
`retomada_em` fica gravado; (f) a pergunta das 4h30 continua valendo para a conversa retomada com
Sim. Suíte inteira. — verificação: todos passam — reversão: n/a.

**4. Manuais** — `docs/manuais/recepcao.md`: seção "A retomada pela OlivIA" (o que é, quando sai, o
que a Recepção mostra: "escolhendo agora" de novo, "recebeu o link" com o Sim, "parou no meio" de
novo sem resposta, e conta em "IA acertou / errou"); `docs/manuais/leitura-da-sessao.md`: a linha
`←` "ia retomou". — verificação: leitura por alguém de fora — reversão: o commit.

**5. Fechamento do bloco** — commits `[axiaatende] #989 …`, push, `logs/sessions.log`. —
verificação: `git log` cita `#989` — reversão: n/a.

**6. Com você** — os dois reinícios (abaixo) e a prova: a próxima conversa que parar no meio, ou
um teste seu: chame no número da Renascer, entre em Comercial › Revendedor e escreva "quero os de
santa catarina" sem tocar nos botões; 31 minutos depois a OlivIA deve voltar com "Pelo que entendi
… SC". A sessão lê o resultado pelo `ler_conversa.py`. — verificação: a retomada na conversa e
`retomada_em` gravado — reversão: reverter o commit e reiniciar.

**7. Devolver o chamado** — `#989` entregue com o manual e o que fica para depois (texto livre com
o seu ok: caminho C). — verificação: você usa lendo só a devolução — reversão: reabrir.

## O que só você pode fazer

Em janela elevada, depois do passo 5 no master:

```powershell
Restart-Service axiaatende-backend         # aplica a 016
Restart-Service axiaatende-recepcionista   # o laço com a retomada
```

```pos-entrega
dono=Restart-Service axiaatende-backend e axiaatende-recepcionista; a prova com uma conversa parada
```
(O AxiaAtende está fora da Porta-Ação; a 016 é aplicada pelos serviços ao subir.)

## Riscos de execução identificados

| Passo | Se interromper no meio | Seguro parar ali? |
|---|---|---|
| 1 | 016 no repositório sem reinício | sim: nada muda até o serviço subir |
| 2 | motor com a retomada sem reinício | sim: o laço de produção é o antigo |
| 2 em produção | a IA fora: `retomada_em` gravado sem mensagem, uma vez | sim, por desenho (uma tentativa) |
| 2 em produção | a Meta recusa o envio | gravado como erro, sem repetir; a Recepção segue mostrando "parou no meio" |
| 6 | retomada mandada a quem já resolveu por fora | só dentro das 24 h e uma vez; o "Ver opções" não fere |

Fios cobertos: `conversas.situacao` (o quarto escritor volta a `em_curso` para o Sim cair na
conversa), `retomada_em` (um escritor; uma retomada), `ia_proposta_id`/`ia_confirmou` (o cartão
"IA acertou" conta a retomada), `enviadas` (a fala registrada), a pergunta das 4h30 (a conversa
retomada com Sim vira `com_link` como qualquer outra). Não coberto de propósito: tela, texto livre,
segunda retomada.

## Linha de abertura da sessão de execução

Esta sessão executa (pedido seu, 13/10). Para outra sessão: leia `C:\AxiaAtende\CLAUDE.md` e
`C:\SuporteAxia\docs\PADRAO-TRABALHO.md`; execute
`C:\AxiaAtende\docs\specs\2026-10-13-a-tela-de-conversas-e-a-resposta-de-pessoa-plano.md` (spec ao
lado), faixa "aplicação de plano aprovado". Chamado **#989**; todo commit cita `#989` e o primeiro
ato é `tratar 989 --status em_andamento` pela skill `/demanda`. Não se reabrem: sem tela; nunca
texto livre; uma retomada por conversa, nas 24 h; "Ver opções" é a pergunta do nó onde parou. Pare em
"O que só você pode fazer". O que vai para a tela durante a execução está no `PADRAO-TRABALHO.md` §1.
