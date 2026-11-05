# Plano — O material na janela aberta
**Data:** 2026-11-05
**Chamado:** #1267
**Spec de origem:** `docs/specs/2026-11-05-material-na-janela-aberta.md`
**Status:** APROVADO
**Executável pelo agente:** não -- executado nesta sessão, a pedido do dono (05/11/2026).

## Passos

**1. Migração 057** — `backend/migracoes/057_material_na_janela.sql`: `envio_destinatarios` ganha
`sem_convite boolean NOT NULL DEFAULT false`; `_VOLTA` tira a coluna. — verificação: o banco de teste
aplica ao subir (`tests/test_migracoes.py` verde). — reversão: a `_VOLTA`.

**2. Teste vermelho** — `tests/test_1267_janela_aberta.py`: (a) quem aceitou num envio e escreveu há
1 h recebe o envio seguinte como texto e imagens, sem modelo, com `sem_convite` e `resposta` nula; (b)
quem aceitou mas não escreve há 25 h recebe o convite; (c) quem nunca aceitou, com a janela aberta,
recebe o convite; (d) a direta não muda; (e) o texto que falha cai no convite. — verificação: falha na
regra, não na fixture. — reversão: apagar.

**3. O caminho novo** — `backend/envio.py`: `inicio_da_janela(con, numero)` (a consulta de hoje de
`janela_aberta`, que passa a usá-la); em `mandar_lotes`, antes de `_mandar_um`, `_na_janela(...)` para
o material; `mandar_imagens_pendentes` aceita `sem_convite`. — verificação: os testes do passo 2 e
`tests/test_envio.py`, `test_1192_janela.py`, `test_1163_teto.py`, `test_envio_direto.py`,
`test_lote_pelo_envio.py`, `test_1142_fila_por_numero.py` verdes. — reversão: voltar o arquivo.

**4. A tela Envios** — `backend/rotas_telas.py` devolve `sem_convite`; o frontend mostra "sem
convite (janela aberta)"; `npm run build`. — verificação: a rota no teste da tela; o build. — reversão:
voltar os arquivos.

**5. Manual** — `docs/manuais/envios.md`: a seção da janela aberta (do `## Manual de uso` da spec) e a
linha no quadro dos sinais. — verificação: lido sem perguntar. — reversão: voltar.

**6. Commit, restart e devolução** — `[axiaatende] #1267 ...` com os arquivos listados; restart do
`axiaatende-backend` (aplica a 057) e do `axiaatende-recepcionista` pelo dono, em janela elevada (os
serviços do AxiaAtende estão fora do catálogo da Porta-Ação), fora de lote em curso; conferir a 057
aplicada. Fechar o #1267 depois do primeiro envio sem convite.

## O que só você pode fazer

- Agendar os pacotes da Campos Gerais: o primeiro com convite; os seguintes para dentro das 24 h do
  "Quero receber" dela (ou de qualquer mensagem dela).

```pos-entrega
dono=reiniciar axiaatende-backend (aplica a 057) e axiaatende-recepcionista em janela elevada, fora de lote em curso; depois conferir na tela Envios a linha "sem convite (janela aberta)"
```

## Riscos de execução identificados

- **Passo 3:** o laço é o do recepcionista, o processo exposto; só com os testes verdes e o restart
  fora de lote em curso. Interrompido no meio, o pior é o convite de sempre.
- **A janela errada** custaria um texto recusado pela Meta (131047): o caminho novo cai no convite.

## Linha de abertura da sessão de execução

Executado na sessão que desenhou, a pedido do dono. Chamado #1267; todo commit cita `#1267`.
