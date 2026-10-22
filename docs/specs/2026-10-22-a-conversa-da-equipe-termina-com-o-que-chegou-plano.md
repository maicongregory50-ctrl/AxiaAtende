# Plano — A conversa da equipe termina com o que chegou, e a ficha da foto sai certa
**Data:** 2026-10-22
**Chamado:** #1097
**Spec de origem:** docs/specs/2026-10-22-a-conversa-da-equipe-termina-com-o-que-chegou.md
**Status:** APROVADO
**Executável pelo agente:** sim

Faixa: aplicação de plano aprovado, **na mesma sessão** (dono, 22/10/2026). Duas entregas (caminho
B). A **entrega 1** vem agora, com a migração **026** (a 025 do #1098 já está no ar). A **entrega 2**
só começa depois que o **#1099** estiver no ar (os dois reescrevem o `campo.py`); os passos dela são
remedidos naquele dia contra o código novo, e qualquer diferença volta ao dono antes de executar.

## O que o código mostrou (leitura de 22/10)

- O toque em **📸 Foto do campo** grava `no_atual_id` = o nó `interna.campo` (ação `texto`): é por
  aí que se reconhece a conversa do menu interno, sem depender do rótulo.
- Depois da 025, o `CHECK conversas_situacao` tem `curriculo_recebido` e `sem_curriculo`: a 026 leva
  a lista inteira mais os dois valores novos.
- Em `motor.tratar`, `campo.receber` e `logos.receber` devolvem `True` quando tomam a foto ou a logo;
  é nesse ponto que a conversa fecha.

## Passos — entrega 1 (a Recepção)

**1. A migração 026 e a VOLTA** — `backend/migracoes/026_imagem_e_logo_recebida.sql` e `_VOLTA.sql`:
`CHECK conversas_situacao` + `imagem_recebida`, `logo_recebida`; as conversas antigas pela regra da
spec (último toque numa opção `texto` do menu interno e, nas 24 h seguintes, foto em
`material_de_campo` → `imagem_recebida`, logo em `logos_de_cliente` → `logo_recebida`; hoje são 37 e
40 logo, 46, 56 e 107 imagem). VOLTA: as duas voltam a `parou_no_meio` com a retomada marcada, e o
`CHECK` volta ao da 025.
- **Verificação:** `test_migracoes` + teste da VOLTA; a regra, rodada como `SELECT` pelo
  `axiaatende_ro` em produção, acha exatamente as 5.
- **Reversão:** o arquivo, antes do restart.

**2. O fechamento no motor** — `motor.py`: quando `campo.receber` ou `logos.receber` tomam o que
chegou, a conversa da pessoa (a última nas 24 h, `em_curso` ou `parou_no_meio`, com `no_atual_id`
numa opção de ação `texto`) fecha como `imagem_recebida` ou `logo_recebida`. Várias fotos: a
primeira fecha, as outras não acham conversa aberta e não mudam nada.
- **Verificação:** testes: tocar Foto do campo e mandar foto → `imagem_recebida`; mandar logo →
  `logo_recebida`; tocar e não mandar → `parou_no_meio` em 30 min; foto sem ter tocado no menu não
  cria nem fecha conversa; conversa de cliente não é tocada.

**3. A retomada pula o canal interno** — `motor.retomar_paradas`: conversa cujo `no_atual_id` é
opção `texto` ganha `retomada_chave = 'canal interno'`, sem chamar a IA.
- **Verificação:** teste: a IA falsa não é chamada; a conversa de cliente continua retomada.

**4. A Recepção** — `rotas_telas.py` (estados `imagem` e `logo`, fora do cartão "Pararam no meio") e
`frontend/src/Recepcao.jsx` ("Imagem recebida", "Logo recebida" e as duas no filtro).
- **Verificação:** `test_telas`; `vite build --outDir` num rascunho.

**5. O manual** — `docs/manuais/recepcao.md`: os dois estados na tabela de sinais e a frase do
cartão "Pararam no meio".

**6. Produção** — bateria inteira verde, commits com `#1097`, push, build; os dois restarts do dono
(recepcionista primeiro); depois, lido pelo `axiaatende_ro`: as 5 conversas com o estado novo, e a
próxima foto da equipe fechando a conversa sozinha.

## Passos — entrega 2 (a ficha), depois do #1099 no ar

**7. O Marketing primeiro** (`C:\AxiaMarketing`): a migração 038 (o próximo número livre hoje) põe
`palhada` no `CHECK ativos_estagio`, com a VOLTA; `produtos.ESTAGIOS` e `NOME_DA_FASE` ("palhada
(dessecada)"); `visao.FASES` com a descrição; `campo.py` aceita foto sem dia e sem safra (hoje o dia
de hoje entra em `:373` e `:431`). Testes do Marketing; restart do backend do Marketing pelo dono.

**8. O AxiaAtende** — `campo.FASES` e a fase no esquema de `ia.ler_campo` com `palhada`; "sim" e
"não" escritos a "É de hoje?" valem como os botões e nunca vão à legenda; "não sei" (ou o dia que
não se entende) deixa a foto sem dia, em vez de presumir o do envio; a resposta que não cabe em fase
fica sem fase. Testes do `campo`.

**9. As três fichas do Willian** (ATV-0774, 0775, 0776): legenda sem " · Não", sem dia, fase
palhada, nos dois projetos, por migração de dados de cada lado, com a VOLTA que devolve o que estava.

**10. Os manuais** — `campo-equipe.md` (a pergunta aceita "sim"/"não" escritos; "não sei" deixa sem
dia; a fase Palhada) e o manual do catálogo do Marketing que lista as fases.

**11. Produção da entrega 2** — Marketing primeiro, depois o AxiaAtende (senão a foto de palhada é
recusada no catálogo); a prova: uma foto de palhada respondida com "não" e "não sei".

**12. Devolver o chamado** ao dono, com o manual, depois das duas entregas no ar.

## O que só você pode fazer

**Entrega 1** (janela de administrador, depois do meu aviso):

```powershell
Restart-Service axiaatende-recepcionista
Restart-Service axiaatende-backend
```

**Entrega 2:** o restart do backend do Marketing e, depois, os dois do AxiaAtende, na ordem que eu
der no dia; e uma foto de palhada para a prova.

## Riscos de execução identificados

- **026 interrompida:** é uma transação; entra inteira ou não entra.
- **Backend reiniciado antes do recepcionista:** sem efeito ruim nesta entrega (a tela só passa a
  mostrar os estados novos); a ordem é a de sempre por costume.
- **Conversa fechada errada:** só fecha conversa cuja última escolha foi uma opção `texto` do menu
  interno; conversa de cliente nunca passa por esse nó.
- **Entrega 2 antes do #1099:** é o risco de atropelar a outra mudança do `campo.py`; por isso a
  entrega 2 espera e é remedida.
- **Fase nova sem o Marketing aceitar:** a foto é recusada no catálogo; por isso o Marketing vai
  primeiro e a VOLTA da fase só sai se nenhuma peça estiver nela.

## Linha de abertura da sessão de execução

Execução nesta mesma sessão (dono, 22/10/2026). Se outra sessão retomar: ler `C:\AxiaAtende\CLAUDE.md`
e `C:\SuporteAxia\PADRAO-TRABALHO.md`; executar `C:\AxiaAtende\docs\specs\2026-10-22-a-conversa-da-equipe-termina-com-o-que-chegou-plano.md`
(spec ao lado), faixa "aplicação de plano aprovado". Chamado #1097; todo commit cita `#1097`, e o
primeiro ato é `tratar 1097 --status em_andamento` pela skill `/demanda`. Não se reabrem: caminho B;
"Imagem recebida" / "Logo recebida"; a fase "Palhada (dessecada)" nos dois projetos; os erros da
ficha neste chamado. A entrega 2 só depois do #1099 no ar. Parar em "O que só você pode fazer". O
que vai para a tela está no `PADRAO-TRABALHO.md` §1.
