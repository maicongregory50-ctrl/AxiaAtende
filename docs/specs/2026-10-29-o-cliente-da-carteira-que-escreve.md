# O cliente da carteira que escreve: o representante e o menu dele
**Data:** 2026-10-29  
**Chamado:** #1189  
**Status:** APROVADO

## Contexto

Em 28/10/2026 saiu a abertura do canal da CAM-0009: o convite ao comprador da carteira, 20 por dia.
Quem escreve ao número da empresa depois disso caía no fluxo geral (o menu e a OlivIA sobre a árvore
inteira, a mesma de quem nunca comprou). O dono: *"se clientes começarem a voltar, precisamos ajustar
o atendimento personalizado, não podemos ligar no fluxo geral"*; *"um portão básico levando a um
botão com o contato do representante"*; e, refinando: *"OlivIA precisa entender o tipo de
atendimento. Falar com a empresa, comercial, porque não quer falar com o representante, fala comigo;
mas se quiser o boleto, ou saber como está a carga dele, ele é direcionado ao contato correto, como já
temos essa parte. Ou cliente quer reclamar, estiver zangado, aí fala comigo."*

## Os fios que encostam

**Quem escreve o que a mudança escreve:** `atendimento.conversas` (o motor, `_nova_conversa`; a
retomada, `retomar_paradas`), `atendimento.enviadas` (o motor e o envio), `atendimento.menu` (as
migrações e a tela Destinos, que só administra a árvore a partir de `raiz`).

**Quem lê para decidir:** `motor.tratar` (a ordem: toque do envio, vaga, clientes do dia, canal de
campo, **o portão**, o resto); `folhas_e_menus` (a IA geral, que parte de `raiz` e não alcança a
`raiz_carteira`); `depois_do_atendimento` (a resposta automática e o "obrigado", reaproveitados no
portão); `tratar_texto_de_convidado` (o texto na linha da tela Envios).

**Quem volta depois:** `retomar_paradas` (a conversa parada da carteira é retomada só com as opções
dela); a pergunta das 4h30 (igual a qualquer conversa com link); o empurrão de 15 min ao ERP (o texto
continua `texto` → `respondeu`).

## O universo medido

Em 28/10/2026: 32 convites da CAM-0009; 5 "respondeu", dos quais **1** escreveu texto (o 4579, que
parece resposta automática do WhatsApp Business). Os destinos do menu de hoje: financeiro (Fran),
fretes (Benedito), qualidade (Alisson), corretor (o dono) — os quatro do menu da carteira saem deles,
nenhum número novo.

## Conformidade com o Manual legal
não se aplica: atendimento por WhatsApp; nenhuma regra fiscal ou legal.

## Conformidade com a casa
não se aplica: nenhum segredo, serviço, porta ou agente novo; a IA já existente (a mesma chamada de
classificação, com uma frase a mais nas instruções); três linhas a mais em tabelas que já estão no
backup do banco do atendimento.

## Decisão

Aprovado pelo dono em 29/10/2026 ("sim"):

1. **O portão:** o cliente que recebeu um envio da carteira nos últimos 30 dias (e não é da casa, e
   não está numa conversa aberta) recebe "Obrigado pela mensagem!", o contato do representante dele
   e o menu `raiz_carteira`: Boleto e nota, Carga e entrega, Qualidade, Falar com a empresa.
2. **A OlivIA entende o assunto** só entre essas quatro: a palavra exata escolhe na hora; o resto vai
   à IA restrita a elas, com a confirmação de sempre ("É isso?"). Reclamação ou irritação vai a
   **Falar com a empresa**, qualquer que seja o assunto. "Ver todas as opções" volta ao menu da
   carteira, nunca ao geral.
3. **Uma vez por dia** a linha do representante. Texto sem assunto depois dela, no mesmo dia: anotado,
   sem resposta (o vaivém com robô).
4. **Chave:** ajuste `portao.ligado` (nasce `true`); `false` volta ao fluxo geral sem restart.

## Escopo desta etapa

**Dentro:** a migração 040 (a raiz da carteira, as quatro folhas, a chave), `motor.py` (o portão, o
"Ver todas as opções", o texto na conversa da carteira, a retomada), `envio.py` (quem é o convidado e
a linha do representante), a frase da reclamação em `ia.py`, os testes e o manual `envios.md`.
**Fora:** a tela Destinos administrar a `raiz_carteira` (a mesma lacuna da `raiz_interna`); o técnico
e a equipe de campo (o portão é de quem recebeu envio); o #1188 (a janela de 24 h dos avisos internos).

## Impacto em produção

Banco do atendimento: a 040, aplicada pelo serviço ao subir. Serviço: restart do backend e do
recepcionista do AxiaAtende, em janela elevada pelo dono.

## ROLLBACK_PLAN

1. `portao.ligado` = `false` (sem restart): todo mundo volta ao fluxo geral.
2. Se preciso, `git revert` e restart; depois a `040_..._VOLTA.sql` à mão.

## Manual de uso

Em `docs/manuais/envios.md`, seção 4b "Quando o cliente que recebeu um envio escreve".

## Próximo passo
/writing-plans
