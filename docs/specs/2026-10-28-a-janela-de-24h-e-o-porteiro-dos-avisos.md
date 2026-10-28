# A janela de 24 h: o porteiro dos avisos internos e o modelo de reabertura
**Data:** 2026-10-28  
**Chamado:** #1188  
**Status:** APROVADO

## Contexto

O dono, em 28/10/2026: *"a Meta está trocando tudo para marketing os nossos modelos; temos que ter um
modelo onde, sempre que passou de 24 horas do último contato, a próxima mensagem precisa de um botão,
para receber mensagem do contato e abrir as 24 h de envio novamente."*

Hoje todo aviso INTERNO (ao representante, ao colaborador, ao dono) sai por um modelo pago próprio,
mesmo quando a pessoa falou com o número da empresa uma hora antes — quando a mensagem livre seria de
graça. Os avisos já passam por uma fila só: `atendimento.avisos` (tipos `recusa`, `sem_atendimento`,
`lote_do_representante` e os do vigia, da avaliação e do plano), enviada por
`Envio.mandar_avisos`, um modelo por tipo (`modelo_do_uso(con, "aviso_" + tipo)`).

O convite ao CLIENTE já é uma reabertura (o toque em "Quero receber" abre a janela e as imagens
seguem de graça). O cliente fica FORA desta etapa, por decisão do dono: *"vamos ver como será a reação
do cliente antes de desenhar"* (o cliente que volta é o #1189).

## Os fios que encostam

**Quem escreve `atendimento.avisos`:** `envio.py` (recusa, `lote_do_representante`), `motor.py`
(~864, o aviso de avaliação/sem atendimento), `rotas_pedido.py` (~178, o aviso pedido pelo marketing:
o Controle do plano, #926), `vigia.py` (~84, o endereço fora/voltou). **Quem lê para decidir:** só
`Envio.mandar_avisos` (manda o que tem `enviado_em IS NULL AND erro = ''`) e a tela Envios / a rota
do marketing que pergunta pelo aviso (`rotas_pedido.py` ~188, `enviado_em`, `erro`).

**A última mensagem DA PESSOA:** `atendimento.eventos_meta` (tipo `mensagem`, `recebido_em`, o
número no `corpo`) e `atendimento.conversas.ultimo_toque_em` por `wa_id`. O canal de campo já mede a
janela assim (`campo.JANELA`, `_dentro_da_janela`). O plano escolhe UMA fonte e a prova (a conversa
de um interno que só manda foto também conta como mensagem dele).

**Quem volta depois:** `mandar_avisos` roda a cada volta do recepcionista; o toque no botão chega
pelo webhook como qualquer toque (`tratar_toque`, que hoje só conhece `envio:<id>:<acao>`); a tela
Envios lista os avisos.

**Os modelos:** cadastro em `atendimento.modelos`; o nome e o texto têm de ser os aprovados na Meta
(`python -m backend.modelos_meta --propor`, que APLICA as migrações pendentes antes — lição de
28/10, a 037/038). Modelo aprovado não se edita: texto novo é modelo novo.

## O universo medido

**Não medido pela sessão:** o banco de produção do AxiaAtende é fechado a ela (senha em
`.env.secrets`, só administrador). O plano começa medindo, com o dono ou por uma porta de leitura:
quantos avisos por tipo e por número saíram nos últimos 30 dias, quantos teriam saído de graça
(a pessoa tinha escrito nas 24 h anteriores) e quantos números distintos recebem aviso. É essa
contagem que diz quanto o porteiro economiza; sem ela, a economia é estimativa e se diz assim.

Medido no código: 6 escritores de aviso (acima); 1 leitor que decide; 0 controle geral de janela fora
do canal de campo.

## Conformidade com o Manual legal
não se aplica: mensagens internas da empresa; nenhuma regra fiscal ou legal.

## Conformidade com a casa
não se aplica: nenhum segredo, serviço, porta ou agente novo; um modelo novo na Meta, cadastrado pelo
caminho de sempre (`modelos_meta --propor`, pelo dono, em janela elevada), e uma coluna a mais numa
tabela que já está no backup do banco do atendimento.

## Decisão

Caminho A, aprovado pelo dono em 28/10/2026 ("sim, mensagens internas"):

1. **O porteiro está em `mandar_avisos`, e só nos avisos internos.** Para cada aviso pendente:
   - **a pessoa escreveu ao número da empresa nas últimas 24 h:** o aviso sai como TEXTO livre (o
     texto do modelo do tipo, com os mesmos dados), de graça;
   - **não escreveu:** o aviso fica **guardado** e sai UM modelo de reabertura por número, com o total
     guardado. Enquanto houver reabertura sem toque para aquele número, aviso novo só se soma ao
     guardado (não sai outra reabertura);
   - **o toque em [Ver]** abre a janela: todos os guardados daquele número saem como texto, na ordem;
   - **7 dias sem toque:** os guardados viram **"não visto"** na tela Envios, com o número e o
     nome. Não somem.
2. **O modelo de reabertura** (texto aprovado pelo dono em 28/10): nome `reabrir_avisos`, uso
   `reabertura`, categoria pedida UTILIDADE (a Meta pode classificar como marketing), variável
   `n_avisos`, botão de resposta rápida **Ver**:
   > Você tem {{1}} aviso(s) da Sementes Renascer. Toque em Ver para receber.
3. **Uma chave liga o porteiro** (no XML do serviço, nasce desligada). Desligada, tudo sai como hoje.
   Ligar só depois de o modelo estar APROVADO na Meta.

## Escopo desta etapa

**Dentro:** a migração (o estado do aviso: `guardado`, `nao_visto`; o modelo `reabrir_avisos` no
cadastro; a VOLTA), `Envio.mandar_avisos` (o porteiro), `tratar_toque` (o toque `reabrir:<numero>`),
o texto livre de cada tipo a partir do modelo, a chave, a tela Envios (os guardados e os não vistos),
`modelos_meta.EXEMPLOS` (`n_avisos`), os testes e o manual `envios.md`.

**Fora:** o cliente (convite, comunicação direta) — o #1189 e a etapa seguinte deste; o canal de
campo (já controla a própria janela); a vaga (o currículo à Fran).

## Impacto em produção

- Banco do atendimento: uma migração (aplicada pelo serviço ao subir, ou pelo `modelos_meta`).
- Meta: um modelo novo, mandado pelo dono (`modelos_meta --ver` ANTES, para ver o que existe; depois
  `--propor`). Até aprovar, a chave fica desligada e nada muda.
- Serviço: restart do recepcionista e do backend do AxiaAtende, **em janela elevada pelo dono** (os
  serviços do AxiaAtende não estão na Porta-Ação).

## ROLLBACK_PLAN

1. Desligar a chave no XML e reiniciar: os avisos voltam a sair como hoje, um modelo por aviso. Os
   guardados no momento saem na próxima volta pelo modelo do tipo (o porteiro desligado não guarda).
2. Se preciso, `git revert` e a VOLTA da migração (os estados novos voltam a pendente; nenhum aviso é
   apagado).
3. O modelo na Meta pode ficar: sem a chave, ninguém o usa.

## Manual de uso

(Para `docs/manuais/envios.md`, seção dos avisos.)

1. **Para que serve:** os avisos que o sistema manda à equipe (o resumo do lote ao representante, o
   cliente que pediu para parar, o cliente sem atendimento) saem de graça quando a pessoa falou com o
   número da empresa nas últimas 24 horas; quando não falou, chegam juntos depois de um toque.
2. **Quem usa e quando:** o representante e a equipe, ao receber; o dono, na tela Envios, para ver
   quem não está lendo.
3. **O caminho comum:** quem não falou com o número da empresa no último dia recebe "Você tem 3
   aviso(s) da Sementes Renascer. Toque em Ver para receber." Toca **Ver**, e os três chegam na hora.
   Quem falou no último dia recebe o aviso direto, como texto.
4. **O que significa cada sinal (tela Envios, avisos):** **Enviado** (saiu, de graça ou por modelo);
   **Guardado** (esperando o toque em Ver); **Não visto** (7 dias sem toque — a pessoa não está lendo:
   vale um telefonema); **Erro** (a Meta recusou; o motivo está escrito). "—" é ainda não aconteceu,
   não é zero.
5. **O que NÃO faz:** não vale para cliente (o convite dele já tem botão); não reenvia o que ficou
   "não visto"; não muda o texto de nenhum aviso.

## Próximo passo
/writing-plans
