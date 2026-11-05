# Plano — Segurar o envio à carteira: suspender por envio e "segurar tudo", pela tela Envios
**Data:** 2026-11-05
**Chamado:** #1169
**Spec de origem:** docs/specs/2026-11-05-segurar-o-envio-a-carteira.md
**Status:** APROVADO
**Executável pelo agente:** sim

## Contexto

O envio à carteira só para pela nota da Meta ou pela chave do lado do Marketing. A spec aprovou o
caminho B: botão Suspender/Religar por envio na tela Envios e um "Segurar tudo" que barra todos os
convites e faz todo pedido novo nascer suspenso. Imagens a quem já pediu, avisos, chamados e Status do
dia continuam. O estado `suspenso` já existe no banco e o despacho de lotes já o ignora; falta a tela,
a chave geral e o registro de quem e quando. Plano e execução nesta mesma sessão, a pedido do dono.

## Passos

1. **Migração 057** — `backend/migracoes/057_segurar_envio.sql` + `_VOLTA.sql`: `envios.suspenso_por`
   (text) e `envios.suspenso_em` (timestamptz); chave `envio.segurar` em `ajustes` com valor
   `{"ligado": false}` (`ON CONFLICT DO NOTHING`, como a 052). — verificação: `test_migracoes` ida e
   volta — reversão: `_VOLTA`.

2. **O despacho e o pedido respeitam a chave** — `backend/envio.py`: função `segurado(con) -> dict|None`
   (lê `envio.segurar`; devolve `{por, em}` quando ligada); `mandar_lotes` sai sem mandar nada com ela
   ligada (antes do laço, sem mexer na nota); `receber_pedido` grava `situacao='suspenso'`,
   `suspenso_por='segurar tudo'`, `suspenso_em=now()` no INSERT quando ligada. `mandar_imagens_pendentes`
   e `mandar_avisos` não mudam (decisão 2). — verificação: testes em `tests/test_envio.py`: (a) chave
   ligada, envio ativo com fila: nenhum convite sai na janela; (b) pedido com a chave ligada nasce
   suspenso com o registro; (c) imagens a quem disse "quero" saem com a chave ligada; (d) chave
   desligada: o ativo volta a andar e o que nasceu suspenso continua suspenso. — reversão: reverter.

3. **As rotas das telas** — `backend/rotas_telas.py`: `POST /envios/{id}/suspender` (de `ativo` ou
   `parado_nota`; grava `suspenso_por=<login>`, `suspenso_em`; 422 nos outros); `POST /envios/{id}/religar`
   passa a aceitar também `suspenso` e grava quem religou nas mesmas colunas; `PUT /ajustes/segurar-envio`
   `{ligado}` grava `{"ligado", "por": login, "em"}`; `GET /envios` devolve `segurado` (`{ligado, por, em}`)
   e cada envio leva `suspenso_por`/`suspenso_em`. Login pelo `Depends(usuario)` que as outras rotas
   usam. — verificação: estender `test_envios_lista_detalhe_e_religar` (suspender um ativo, religar,
   422 em concluído) e teste novo do segurar (liga, a lista diz quem; desliga). — reversão: reverter.

4. **A saúde do recepcionista** — `backend/recepcionista.py` `/saude`: `envio_segurado` com `{ligado,
   por, em}`. — verificação: teste no `test_recepcionista` ou no do item 2. — reversão: reverter.

5. **O script registra também** — `scripts/suspender_envio.py`: grava `suspenso_por='script:<USERNAME>'` e
   `suspenso_em`. — verificação: leitura (ele roda só em janela elevada). — reversão: reverter.

6. **A tela Envios** — `frontend/src/Envios.jsx`: interruptor "Segurar tudo" na linha dos filtros (com
   confirmação ao ligar); faixa vermelha no topo quando ligada ("Envio à carteira SEGURADO desde DD/MM
   HH:MM por Fulano. Nenhum convite sai."); no envio aberto, botão **Suspender** (ativo/parado_nota) e
   **Religar** (suspenso/parado_nota), com "suspenso por X em DD/MM HH:MM" ao lado; o select de envios
   mostra "· suspenso" no rótulo. Estilo pelas classes existentes (`aviso erro`, `secundario`). —
   verificação: `npm run build` sem erro; a tela lida pelo Playwright no servidor local depois do restart
   (passo 9). — reversão: reverter + build.

7. **O manual** — `docs/manuais/envios.md`: o "Manual de uso" da spec, e corrigir o passo 5 e a tabela
   de sinais (Religar não é só da nota; os estados `suspenso` e a faixa). A linha no `INDICE.md` já
   existe; conferir. — verificação: o caminho comum lido sem perguntar. — reversão: reverter.

8. **Bateria** — `test_envio`, `test_telas`, `test_migracoes`, `test_1188_porteiro`, `test_1207_status_do_dia`,
   com `--basetemp` próprio e a 5437 de pé. — verificação: tudo verde. — reversão: n/a.

9. **Subida** — commits com `#1169`, push; build já feito; restart do `axiaatende-recepcionista`
   (a 057 aplica) e do `axiaatende-backend` pela Porta-Ação **pelo dono** (o classificador barra a
   sessão). — verificação: `/saude` das telas lista a 057; `/saude` do recepcionista traz
   `envio_segurado.ligado=false`; a tela mostra o envio suspenso de 28/10 com o botão Religar. —
   reversão: ROLLBACK_PLAN da spec.

10. **A prova** — na tela: ligar "Segurar tudo" (a faixa aparece, a saúde diz `true` com quem), desligar;
    no envio suspenso de 28/10, ver "Religar" (sem clicar, para não soltar os 51 convites sem decisão
    sua). — verificação: as duas leituras. — reversão: desligar a chave.

11. **Devolver o #1169** com o manual. — verificação: o autor usa lendo só a devolução. — reversão:
    reabrir.

## O que só você pode fazer

- Os dois restarts (passo 9), recepcionista primeiro, com o bloco de sempre trocando o `servico=`.
- Decidir se o envio suspenso de 28/10 (51 clientes) deve ser religado; a prova não o solta.

## Riscos de execução identificados

- **057 sem o código:** colunas nulas e chave desligada; nada muda. Seguro.
- **Código no ar com a chave desligada:** o comportamento é o de hoje. Seguro em qualquer ponto.
- **Recepcionista reiniciado antes das telas:** a tela antiga não mostra a chave, mas ninguém a liga sem
  a tela nova. Seguro.
- **Fios da spec cobertos:** `receber_pedido` (2), `mandar_lotes` (2), religar da tela (3), o script (5),
  a nota da Meta (inalterada; o suspenso não é lido por ela), imagens e avisos (2, provados inalterados).

## Linha de abertura da sessão de execução

Executado nesta mesma sessão, a pedido do dono. Se cair: ler `C:\AxiaAtende\CLAUDE.md` e
`C:\SuporteAxia\docs\PADRAO-TRABALHO.md`; executar
`C:\AxiaAtende\docs\specs\2026-11-05-segurar-o-envio-a-carteira-plano.md` (spec ao lado); faixa:
aplicação de plano aprovado. Chamado #1169; todo commit cita `#1169`, e o primeiro ato é
`tratar 1169 --status em_andamento` pela skill `/demanda`. Não se reabrem: caminho B, pedido novo nasce
suspenso, imagens a quem pediu continuam, soltar não religa o que nasceu suspenso. Parar em "O que só
você pode fazer".
