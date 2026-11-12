# O aviso de classe 1 do painel vai ao WhatsApp do dono
**Data:** 2026-11-12
**Chamado:** #1434
**Status:** APROVADO

## Contexto

A revisão ativa do painel (#1411, AxiaSecurity) abre chamado quando algo **parou** (classe 1) e,
desde 12/11/2026, roda o conserto pela Porta-Ação (`receitas_ativas=true`). Quando sobra algo para o
dono — classe 1 sem receita, receita que não provou, disjuntor aberto — ela marca o item com
`aviso`, mas o aviso ainda não sai: o AxiaSecurity não tem remetente, e o dono decidiu em 11/11 que
quem envia é o AxiaAtende (`aviso_ativo=false` em `C:\AxiaSecurity\design\classes_de_alerta.json`).

O AxiaAtende já tem o caminho inteiro para aviso interno vindo de vizinho: `backend/auditoria_erp.py`
em **canais** (#350 auditoria de estoque, #1337 API externa recusando). A cada minuto o processo das
telas busca as pendências do canal, grava uma linha em `atendimento.avisos` por destino do ajuste do
canal, e devolve ENVIADO ou FALHOU. Quem manda é `envio.mandar_avisos`, com o porteiro ligado em
produção (`AXIAATENDE_PORTEIRO=on`): texto dentro da janela de 24 h, reabertura fora dela.

**A pergunta que o chamado deixou aberta está respondida pelo #1337:** fora da janela de 24 h o
porteiro manda a reabertura ("Você tem N aviso(s)"), e o texto sai no toque em Ver. O modelo do tipo
precisa só existir no cadastro (`envio.py:661-664`); aprovação na Meta só se o porteiro for desligado.

## Os fios que encostam

- **Quem mais escreve em `atendimento.avisos`:** o motor (`_avisar_o_gestor`), o vigia
  (`vigia._avisar`), o envio (`envio.py:523`), os dois canais de `auditoria_erp.py`. Quem lê para
  decidir: `envio.mandar_avisos` / o porteiro (manda e marca `enviado_em`, `erro`, `nao_visto_em`).
- **Quem mais escreve em `atendimento.avisos_auditoria_erp`:** só `auditoria_erp.volta_do_canal`,
  com a chave `(canal, erp_aviso_id)` desde a 060. O canal novo usa a mesma tabela.
- **A pasta dos pedidos** `C:\Logs\Seguranca\revisao\avisos\`: escrita só pela revisão (SYSTEM);
  a pasta-mãe é protegida (SYSTEM e Administradores escrevem, Usuários leem). O processo das telas
  (`axiaatende-backend`) roda como **LocalSystem** (o XML não tem `serviceaccount`): lê.
- **A pasta da devolução** `C:\Dados\AxiaAtende\painel\`: escrita só pelo canal; lida pela revisão
  (SYSTEM) para o resumo.
- **Quem volta depois:** a revisão, na corrida seguinte, lê a devolução para o resumo e apaga o
  pedido que já tem devolução há mais de 7 dias.

## O universo medido

- Avisos que teriam saído: nos 30 dias medidos no #1411, **0** alerta de classe 1. O canal deve
  ficar quieto quase sempre; é a rede de segurança.
- `atendimento.avisos_auditoria_erp.erp_aviso_id` é `integer`: o id do pedido do painel é um
  contador da revisão (`estado.json`), não a data.
- Migrações do AxiaAtende: a última é a 062; a nova é a **063**. Os CHECKs `avisos_tipo` e
  `modelos_uso` foram reescritos pela última vez na 060 (061 e 062 não os tocam).

## Conformidade com o Manual legal

não se aplica: aviso interno ao dono, sem regra fiscal ou legal.

## Conformidade com a casa

- **R1** (alguém sabe): **muda**. A carta diz que o aviso de classe 1 "espera o #1434"; passa a
  dizer que ele sai pelo AxiaAtende quando `aviso_ativo=true`. Passo do plano.
- **R3** (segredo): **conforme**. O caminho escolhido não cria segredo nem leitor novo de segredo:
  é arquivo local, como a casa já faz com os `.req` das portas.
- **R4** (serviço, porta): **conforme**. Nenhuma porta nova; o processo das telas ganha um canal na
  volta que já existe. O restart do AxiaAtende é pela Porta-Ação.
- **R8/PROJETO.md**: **muda** o *Ofereço* do AxiaAtende ("o aviso do painel da casa") e o *Exijo*
  do AxiaSecurity (o AxiaAtende para o aviso). Passo do plano.

## Decisão

Caminho A, aprovado pelo dono em 12/11/2026 ("a"): **canal por arquivo**.

- A revisão grava `C:\Logs\Seguranca\revisao\avisos\<id>.json` (`{"id", "texto"}`), no molde da
  `lista-notificacao.md` §3: `[CRÍTICO] <sistema> — visto às HH:MM no painel. Feito até agora:
  <...>. Chamado #N.` Uma vez por chave por dia.
- O AxiaAtende ganha o canal `painel_classe1` em `auditoria_erp.CANAIS`: `ir` lê a pasta,
  `devolver` grava `C:\Dados\AxiaAtende\painel\<id>.json` (`{"estado", "motivo", "wamid", "em"}`).
  O canal não depende do ERP: a ligação com o ERP desligada para os canais do ERP e não para ele.
- Quem recebe: o ajuste `painel_para`, nascido igual ao `integracoes_para` (o dono).
- Modelo `aviso_painel` (UTILITY, `{{1}}`), só cadastro, como o `aviso_integracao`.

Descartados: B (pelo ERP: credencial nova para a revisão e o aviso dependendo do ERP de pé, justo
quando a classe 1 pode ser o ERP parado); C (entrada HTTP com chave: leitor novo de segredo como
SYSTEM).

## Escopo desta etapa

Dentro: migração 063 (com VOLTA), o canal e os testes no AxiaAtende; a escrita do pedido, a leitura
da devolução e a limpeza na revisão do AxiaSecurity; manuais, carta e `PROJETO.md`; ligar
`aviso_ativo` depois da prova.
Fora: aviso de classe 2 e 3 (lista do dia, sem aviso); servidor inteiro desligado (#185).

## Impacto em produção

Restart do `axiaatende-backend` (aplica a 063 e carrega o canal) pela Porta-Ação, **depois** que a
obra sem commit de outra sessão no AxiaAtende (`backend/vaga.py`, 13:20) for commitada.

## ROLLBACK_PLAN

1. `aviso_ativo=false` na tabela de classes (a revisão para de pedir).
2. `git revert` do canal no AxiaAtende e restart pela Porta-Ação.
3. A 063 fica (só acrescenta); para tirá-la, `063_aviso_painel_VOLTA.sql` à mão.

## Manual de uso

- `C:\AxiaSecurity\docs\manuais\revisao-do-painel.md`: o interruptor `aviso_ativo` passa a ter efeito;
  o que chega no WhatsApp e quando ("Aviso do painel da casa: [CRÍTICO] …"); fora da janela de 24 h
  chega "Você tem N aviso(s)" e o texto no Ver.
- Manual dos avisos do AxiaAtende: o tipo novo na aba de avisos da tela Envios.

## Próximo passo

/writing-plans
