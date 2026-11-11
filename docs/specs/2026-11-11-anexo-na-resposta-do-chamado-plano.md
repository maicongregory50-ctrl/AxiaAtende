# Plano — Anexo (PDF ou Word) na resposta do chamado chega ao WhatsApp do autor
**Data:** 2026-11-11
**Chamado:** #1381
**Spec de origem:** docs/specs/2026-11-11-anexo-na-resposta-do-chamado.md
**Status:** APROVADO

**Executável pelo agente:** não -- execução na mesma sessão, a pedido do dono, com fase .sql e prova real que dependem dele.
real que dependem dele.

Releitura da spec: Manual legal não se aplica. Conformidade com a casa: R2 e R4 conformes, nada muda
na carta. Todos os fios da spec viraram passos: a tabela nova, o vínculo, a saída, a coluna no
AxiaAtende, o descarte de 7 dias (passo 6, teste) e o backup (passo 9, conferência).

## Passos

1. **ERP, fase644** — arquivos: `C:\AxiaGestao\schema_axia_fase644_demandas_anexos.sql` e `_VOLTA.sql`
   (tabela `axia.demandas_anexos`, índice por `evento_id`, FK para `demandas` e `demandas_eventos`) —
   verificação: os dois arquivos existem, e `python scripts/...` não se aplica; o ensaio é do dono no
   passo 8 — reversão: apagar os arquivos.
2. **ERP, a validação do arquivo** — `backend/utils/demandas_anexos.py` (PDF pelo cabeçalho `%PDF`, Word
   `.docx` pelo ZIP com `word/document.xml`, até 10 MB, nome gerado, pasta
   `C:\Dados\AxiaGestao\demandas_anexos`, `caminho_seguro`) — verificação: teste unitário com PDF, docx,
   docx falso (zip sem `word/`), exe renomeado e arquivo grande — reversão: apagar o módulo.
3. **ERP, as rotas e o vínculo** — `routers/demandas.py` (`POST /{id}/anexos`; `anexo_id` em
   `registrar_evento` e `entregar_ao_autor`, ligado na mesma transação, recusa sem `pergunta`),
   `schemas/demandas.py` (`anexo_id` opcional nos dois corpos), `services/demandas_whatsapp_service.py`
   (`anexo` na linha da saída), `routers/demandas_whatsapp.py` (`GET /anexos/{id}`, só ligado a evento)
   — verificação: testes de rota (envio, vínculo, recusa de anexo alheio, recusa em comentário comum,
   saída com e sem anexo, download só ligado) — reversão: `git revert`.
4. **ERP, bateria** — `pytest` dos testes de demandas e do WhatsApp do chamado, com `--basetemp` no
   rascunho — verificação: verde, ou vermelho só nos já conhecidos (`reference_achados_sem_chamado`)
   — reversão: nenhuma.
5. **AxiaAtende, migração 061 e `Saida.documento`** — `backend/migracoes/061_anexo_na_pendencia.sql` e
   `_VOLTA.sql` (`pendencias_mensagens.anexo jsonb`; ajuste `pendencias.anexo_ligado = true`),
   `backend/saida.py` (`mime_type` com padrão PDF) — verificação: os chamadores atuais (`vaga.py:487`,
   `logistica_erp.py:136`) não mudam; teste da saída falsa com o mime — reversão: `git revert` e VOLTA.
6. **AxiaAtende, a ida e o envio** — `backend/erp.py` (`chamado_anexo(cfg, token, id) -> bytes`),
   `backend/pendencias_erp.py` (`volta` baixa para `envios_pasta\chamados` antes de `receber`; download
   falho = linha não gravada e cursor parado), `backend/pendencias.py` (`_mandar_numero` manda o
   documento depois do texto, só com a chave ligada; erro vai a `erro` e ao log) — verificação: testes
   (linha com anexo grava o arquivo; download falho não anda o cursor; texto e documento saem na ordem;
   chave desligada manda só o texto; descarte de 7 dias descarta junto) — reversão: `git revert`.
7. **AxiaAtende, bateria** — `pytest` inteiro — verificação: verde, ou só os 5 vermelhos conhecidos do
   #1289 — reversão: nenhuma.
8. **Skill `demanda`, `--anexo`** — `C:\SuporteAxia\skills\demanda\demanda.py` (envio multipart antes
   do ato; `comentar --pergunta --anexo` e `entregar --devolucao --anexo`; sem `--pergunta`, recusa sem
   gravar) e a tabela de subcomandos do `SKILL.md` — verificação: `--help` mostra a opção; recusa sem
   `--pergunta` não chama a API — reversão: `git revert`.
9. **Produção** — o dono aplica a fase644 (seção abaixo); a sessão reinicia `axiagestao-backend` e o
   AxiaAtende pela Porta-Ação, nessa ordem — verificação: `GET /health` da 8001; AxiaAtende sobe com a
   migração 061 aplicada; a pasta nova aparece dentro de `C:\Dados\AxiaGestao` (coberta pelo backup) —
   reversão: ROLLBACK_PLAN da spec.
10. **Prova real** — `comentar 1381 --pergunta --ok-do-dono ... --anexo <PDF de teste>`: o autor do
    #1381 é o dono, então o documento chega ao WhatsApp dele — verificação: o dono recebe o texto e o
    documento com a legenda "Chamado #1381"; `pendencias_mensagens` mostra `enviada` sem erro —
    reversão: nenhuma (é uma mensagem).
11. **Manual** — o `SKILL.md` da `demanda` (feito no passo 8) e o manual do chamado no WhatsApp do
    AxiaAtende (`docs/manuais/`), a partir do `## Manual de uso` da spec, caçando a frase "só texto" —
    verificação: quem não participou do desenho manda um anexo lendo só o manual — reversão: reverter
    o texto.
12. **Devolver o #1381** — `entregar 1381 --devolucao @f` com o caminho comum e o limite — verificação:
    o dono usa lendo só a devolução — reversão: reabrir.

## O que só você pode fazer

Aplicar a fase644, em janela elevada, **antes** do restart da 8001 (fase aditiva):

```powershell
. C:\AxiaSecurity\scripts\_segredos.ps1
$env:PGPASSWORD = Get-SegredoAxia PG_PASSWORD
$env:PGCLIENTENCODING = "UTF8"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h 127.0.0.1 -d renascer -v ON_ERROR_STOP=1 `
  -f "C:\AxiaGestao\schema_axia_fase644_demandas_anexos.sql"
```

```pos-entrega
dono=fase644 do ERP (C:\AxiaGestao) aplicada pelo dono antes do restart da 8001; restart da 8001 e do AxiaAtende pela Porta-Acao; a prova real no WhatsApp do dono
```

## Riscos de execução identificados

- Passo 9 interrompido entre a fase e o restart: a tabela existe e ninguém a usa. Seguro ficar parado.
- Restart da 8001 sem a fase: o código novo só toca a tabela quando chega um anexo. Envio de anexo dá
  erro 500 e nada mais quebra. Seguro, mas não deve ficar assim.
- AxiaAtende com o código novo e o ERP antigo: a linha da saída não traz `anexo`, e tudo segue como
  hoje. Seguro.
- Passo 10 falha no documento: o texto já saiu, e o erro fica registrado. Desliga-se a chave e se
  investiga.

## Linha de abertura da sessão de execução

Execução na mesma sessão, a pedido do dono (11/11/2026). Se cair: ler `C:\AxiaAtende\CLAUDE.md`,
`C:\AxiaGestao\CLAUDE.md` e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`; executar
`C:\AxiaAtende\docs\specs\2026-11-11-anexo-na-resposta-do-chamado-plano.md` (spec ao lado), em faixa de
aplicação de plano aprovado. Chamado #1381; todo commit cita `#1381`, e o primeiro ato é
`tratar 1381 --status em_andamento` pela skill `/demanda`. Não se reabrem: caminho A (sem tela), PDF e
Word, um arquivo por resposta, só pergunta e devolução, o arquivo não aparece na caixa do ERP. O que vai
para a tela durante a execução está no `PADRAO-TRABALHO.md` §1. Parar no passo 9 até o dono aplicar a
fase.
