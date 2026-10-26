# Plano — A fila de envio por número, o papel do contato, e o resumo ao representante
**Data:** 2026-10-26
**Chamado:** #1142
**Spec de origem:** `C:\AxiaAtende\docs\specs\2026-10-26-fila-por-numero-e-resumo-ao-representante.md` (APROVADA)
**Status:** APROVADO
**Executável pelo agente:** não -- a migração 033 e os restarts são de mão (o AxiaAtende não está no catálogo da Porta-Ação), e a prova dos passos depende dela aplicada. Sessão com pessoa.

## Context

O ERP passou a entregar **uma linha por contato** do cliente, com o papel — comprador ou técnico
(#1141, no ar em 26/10) — porque a campanha do marketing fala com cinco públicos (#1103). Duas
coisas do AxiaAtende não acompanham isso.

**A fila é por CADASTRO** (`UNIQUE (envio_id, erp_codigo)`), e o `INSERT` tem
`ON CONFLICT ... DO NOTHING`: dois contatos do mesmo cadastro no mesmo envio e o segundo é
**descartado em silêncio**. O caso real é a **cooperativa**, onde comprador e departamento técnico
recebem na mesma semana e a lista do marketing não separa por papel.

**A cópia ao responsável** manda, a cada convite, uma cópia a quem atende o cliente — e no material
às revendas o responsável é **o dono**, que recebeu as artes da Agro Real e da Agro Símil em 23/10 e
pediu que acabasse. **E o manual já prometia o contrário do que o código fazia:** `envios.md` diz
"Não avisa o responsável de quem quis receber: só de quem recusou". A cópia nunca entrou no manual.

**Decisão do dono (26/10), que substitui a cópia:** **um resumo por lote, só ao representante** — não
ao dono, não ao flutuante. Pelo caminho que já existe (`atendimento.avisos` + `Envio.mandar_avisos`),
como UTILITY, sem imagem e sem botão. O volume de mensagens pagas **cai**: uma por representante por
lote no lugar de uma por cliente.

**O AxiaAtende não sabe quem é o dono** (não há número dele no config daqui), então quem diz o canal
do responsável é o marketing, que já tem o dado — por isso as duas linhas no pedido estão DENTRO
desta etapa, e não num chamado à parte.

## Passos

1. **Migração 033** — `backend/migracoes/033_fila_por_numero_e_resumo.sql` + `_VOLTA.sql`.
   A 031 está reservada ao #1097; a última aplicada é a 032.
   - `envio_destinatarios.papel` (CHECK `comprador|tecnico`, nulo = o pedido de antes) e
     `responsavel_canal` (CHECK `representante|corretor|dono|flutuante`, nulo).
   - **A unicidade:** conta primeiro os pares `(envio_id, whatsapp)` repetidos e **RAISE com o
     número** se houver (em produção isso não foi medido: o banco pede o segredo); depois
     `DROP CONSTRAINT envio_dest_um_por_cliente` e
     `CREATE UNIQUE INDEX envio_dest_um_por_numero ON ... (envio_id, whatsapp) WHERE whatsapp <> ''`.
     **Parcial de propósito:** o destinatário sem celular grava `whatsapp = ''`, e dois deles no
     mesmo envio é caso legítimo (`sem_whatsapp`).
   - `avisos_tipo` ganha `lote_do_representante`; `modelos_uso` ganha
     `aviso_lote_do_representante`; e a linha do modelo (UTILITY, sem imagem, sem botão, 3
     variáveis), com o texto proposto — o final é o que a Meta aprovar.
   - verificação: `python -m pytest tests/test_migracoes.py -q` (o ida-volta-ida do projeto) e, com
     a 033 aplicada, a query de efeito (`\d atendimento.envio_destinatarios`: o índice novo existe e
     a constraint antiga não) — reversão: a `_VOLTA.sql`.

2. **`receber_pedido` grava o papel e o canal, e o conflito é por número** —
   `backend/envio.py`. `ON CONFLICT (envio_id, whatsapp) WHERE whatsapp <> '' DO NOTHING`; os dois
   campos novos no `INSERT`, lidos de `c.get("papel")` e `c.get("responsavel_canal")`. A
   classificação na chegada **não muda**.
   - verificação: `tests/test_1142_fila_por_numero.py` (novo) — dois contatos do mesmo cadastro
     entram os dois; o mesmo número duas vezes entra uma; dois sem número entram os dois —
     reversão: `git revert`.

3. **A cópia sai; o resumo entra** — `backend/envio.py`: `_copias_aos_responsaveis` e a chamada dela
   saem; entra `_resumo_ao_representante(con, e, fila)`, chamada no mesmo lugar, que insere **um**
   aviso `lote_do_representante` por responsável de canal `representante` ou `corretor`, com
   `sobre` = "`<primeiro nome>|<N clientes seus>|<assunto ou peça>`". Nunca ao dono nem ao
   flutuante; nada é mandado aqui — quem manda é `mandar_avisos`, que já existe.
   - O guarda de `envio:<id>:copia` em `tratar_toque` **fica** (há mensagens com esse botão na rua),
     com o comentário dizendo por quê.
   - verificação: no teste, o lote sai e **não** há mensagem ao número do responsável; há UM aviso
     na tabela por representante; com canal `dono` não há aviso nenhum — reversão: `git revert`.

4. **O papel vai ao ERP** — `backend/eventos_erp.py`: `montar` lê `d.papel` e o põe no evento. O ERP
   já aceita (`EventoEnvio.papel`, #1141) e grava em `rel_contatos.envio_papel`.
   - verificação: `tests/test_eventos_erp.py` verde, com o papel no evento — reversão: `git revert`.

5. **Os dois testes que afirmam a cópia** — `tests/test_envio.py`
   (`test_lote_de_20_por_dia_so_com_nota_verde_e_copia_ao_responsavel`) e
   `tests/test_envio_direto.py` (o trecho da cópia e do toque nela) passam a afirmar o resumo. Eles
   são a prova de que a cópia existia; atualizá-los é o passo, não um detalhe.
   - verificação: os dois arquivos verdes, e o nome do teste deixa de prometer a cópia — reversão:
     `git revert`.

6. **O marketing manda o papel e o canal** — `C:\AxiaMarketing\backend\envio_whatsapp.py`:
   `pedido_direta` manda `papel` e `responsavel_canal` (de `c["papel"]` e `c["canal"]`, que a lista
   já traz) e `pedido_material` manda `responsavel_canal = "dono"` (as parceiras são relação do
   dono) — **sem isso o resumo nunca sai e o papel nunca chega ao ERP**.
   - verificação: `tests/test_envio_whatsapp.py` e `tests/test_1103_quem_recebe.py` verdes, com o
     pedido montado carregando os dois campos — reversão: `git revert`.

7. **O manual** — `docs/manuais/envios.md`: o papel na linha do destinatário, a cooperativa com dois
   contatos no mesmo envio, a cópia que acabou (e que o manual já dizia não existir), o resumo ao
   representante, e o sinal "o mesmo número não entra duas vezes". A linha do `INDICE.md` só muda se
   a rota mudar — e ela não muda.
   - verificação: alguém de fora lê e sabe o que o representante recebe hoje — reversão: `git revert`.

8. **Devolver o #1142** — `comentar`/`tratar` pela `/demanda`, com o que mudou, o manual e o
   **pré-requisito**: o modelo `aviso_lote_do_representante` aprovado na Meta, senão o resumo fica
   em `avisos.erro` ("nenhum modelo cadastrado para...") e ninguém recebe.
   - verificação: o autor usa a tela lendo só a devolução — reversão: reabrir.

## O que só você pode fazer

- **Reiniciar — e é só isso que aplica a migração.** Medido no passo 1: aqui o SERVIÇO aplica as
  mudanças do banco ao subir (`backend/migracoes.py`, molde do marketing) e não há script separado,
  então não há nada a rodar à mão antes:
  ```
  Restart-Service axiaatende-backend; Restart-Service axiaatende-recepcionista; Restart-Service axiamarketing-backend
  ```
- **Aprovar o modelo `aviso_lote_do_representante` na Meta** (Business Manager, categoria
  **Utilidade**), com o texto que a linha da migração propõe. Enquanto ele não existir na Meta, o
  resumo falha e fica escrito em `avisos.erro` — nada se perde, e sai quando o modelo entrar.

*(Sem bloco `pos-entrega`: nem o AxiaAtende nem o marketing estão no catálogo da Porta-Ação.)*

## Riscos de execução identificados

- **Passo 1 em produção, com número repetido:** a migração **conta e recusa com o número** antes de
  trocar a unicidade, em vez de falhar no `CREATE UNIQUE INDEX` sem dizer quantos. No dev não há
  nenhum; em produção não foi medido, porque o banco pede o segredo.
- **Passo 1 sem os passos 2 e 3:** as colunas nascem nulas e ninguém as lê; a unicidade nova é mais
  estrita que a antiga, e o `ON CONFLICT (envio_id, erp_codigo)` do código velho passaria a não
  inferir índice nenhum e **levantaria erro no próximo pedido**. Por isso os passos 1 a 3 entram no
  mesmo restart — e, até ele, o código antigo segue com a unicidade antiga.
- **Passo 3 sem o modelo aprovado na Meta:** o aviso fica com `erro` preenchido e **ninguém recebe o
  resumo**; o envio aos clientes não é afetado (a cópia já não existe). Está em "O que só você pode
  fazer", e o manual diz o sinal.
- **Passo 6 sem o restart do marketing:** o pedido continua sem os dois campos, o Atende os grava
  nulos e o resumo não sai. Nada quebra.
- **A janela entre o ERP e aqui:** o ERP já manda o papel na lista desde 26/10. Até o passo 2, o
  Atende descarta o campo — e, como ainda não há técnico cadastrado, nenhuma lista tem dois contatos
  do mesmo cadastro. A ordem é segura.
- **Árvore do AxiaAtende com arquivo de outra sessão:** commit só por caminho, nomeando os arquivos.

## Linha de abertura da sessão de execução

> Leia `C:\AxiaAtende\CLAUDE.md` e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Execute o plano
> `C:\AxiaAtende\docs\specs\2026-10-26-fila-por-numero-e-resumo-ao-representante-plano.md` (spec ao
> lado, mesmo nome sem `-plano`), faixa "aplicação de plano aprovado", os passos na ordem. Chamado
> #1142; todo commit cita `#1142` e leva o prefixo `[axiaatende]` (no marketing, `[axiamarketing]`),
> e o primeiro ato é
> `python C:\SuporteAxia\skills\demanda\demanda.py tratar 1142 --status em_andamento --motivo "..."`
> pela skill `/demanda`. Decisões que NÃO se reabrem: a fila é por número, com a unicidade PARCIAL
> (quem não tem celular grava vazio); a cópia por cliente acaba; entra UM resumo por lote, só a
> representante e corretor, nunca ao dono nem ao flutuante, como UTILITY pelo caminho dos avisos; o
> canal do responsável é dito pelo marketing, porque o Atende não sabe quem é o dono; o guarda de
> `envio:<id>:copia` fica. Pare em "O que só você pode fazer". O que vai para a tela durante a
> execução está no `PADRAO-TRABALHO.md` §1: decisão do dono, incidente que merece chamado próprio, e
> passo que depende da mão dele. Conserto de caminho feito dentro do planejado não se narra.
