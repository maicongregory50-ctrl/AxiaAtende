# Plano — O que cita um chamado vai ao chamado
**Data:** 2026-11-23
**Chamado:** #1722
**Spec de origem:** `C:\AxiaAtende\docs\specs\2026-11-23-arquivo-e-texto-citando-chamado.md`
**Status:** APROVADO
**Executável pelo agente:** não -- chamado do axiaatende (o EXECUTOR não tem raiz lá, #976), com restart elevado e prova no WhatsApp do dono.

## Contexto

Em 23/11 o PDF que a Fran devolveu deslizando a pergunta do chamado 1541 virou "logo de cliente", e a
resposta de texto dela foi descartada duas vezes. A spec decidiu (caminho A, sem chave nova): D1
arquivo citado nunca desce a corrente; D2 texto citando pergunta entra sempre; D3 aviso no sintoma;
D4 limpeza do que ficou pendurado. **Prazo: a logo 6 completa 24 h em 24/11/2026 15:06** e passa a
ser oferecida ao AxiaMarketing (`logos.pendentes`). Por isso a limpeza vai primeiro, em deploy
próprio: a migração roda no arranque do serviço (`migracoes.aplicar`, `recepcionista.py:292`).

Conformidade com o Manual legal e com a casa: a spec diz "não se aplica" nas duas; nada a virar passo.

## Passos

**Parte 1 — a limpeza (antes de 24/11 15:06)**

1. **Pegar o chamado.** `demanda.py tratar 1722 --status em_andamento`; `git status` no AxiaAtende.
   — verificação: o chamado aparece em andamento. — reversão: nenhuma.

2. **Escrever a migração de limpeza e a volta.** `backend/migracoes/0NN_limpeza_1722.sql` e
   `_VOLTA.sql`, com o próximo número **lido da pasta na hora** (hoje a última é a 073).
   - mensagem do FGTS: `UPDATE atendimento.pendencias_mensagens SET estado = 'a_entregar' WHERE id = 136
     AND estado = 'descartada' AND texto LIKE 'No caso da rescis%'`;
   - logo: `UPDATE atendimento.logos_de_cliente SET pergunta_pendente = NULL, puxada_em = now(),
     erro = 'nao era logo: PDF devolvido ao chamado 1541 (#1722)'` na linha cujo `wamid` é o do evento
     8851 (terminado em `...MjI4MENEMTY0MjMxMwA=`). `resultado` fica nulo (não é anunciada). `arquivo`
     vai a NULL **só se a coluna aceitar** (conferir o NOT NULL em `information_schema` antes);
   - guardas pelo conteúdo, não só pelo id: no banco de teste (5437) as linhas não existem e a migração
     tem de passar sem tocar nada;
   - afirmação de saída: `DO $$ ... RAISE NOTICE '0NN OK: ...'`, que levanta exceção se a logo daquele
     wamid existir e ainda tiver `pergunta_pendente`.
   — arquivos: os dois `.sql`, `tests/test_migracoes.py` se ele enumera as migrações.
   — verificação: `pg_isready -p 5437`; a migração aplica e desfaz no 5437; os testes de migração passam.
   — reversão: apagar os dois arquivos (antes de aplicada em produção).

3. **Commit e push da migração** (`git commit -- <arquivos>`, mensagem `[axiaatende] #1722 ...`).
   — verificação: `git log -1`, push aceito. — reversão: `git revert`.

4. **[SÓ O DONO] Reiniciar o recepcionista** para a migração entrar (comando em *O que só você pode
   fazer*). — verificação (sessão, só leitura, `axiaatende_ro`): `logos_de_cliente` 6 com
   `pergunta_pendente` nulo e `puxada_em` preenchido; mensagem 136 em `a_entregar` e, um minuto
   depois, `entregue`; no chamado 1541 aparece "(pelo WhatsApp) No caso da rescisão do Lucas não terá
   guia de FGTS a recolher." (`demanda.py ver 1541`); log do recepcionista sem erro depois do arranque.
   — reversão: a `_VOLTA` da migração (ROLLBACK_PLAN 2 da spec). O comentário no 1541 fica.

5. **[SÓ O DONO] Apagar o PDF da pasta de logos.** A sessão resolve o caminho completo pela config
   (`campo.pasta` + `logos/2026-11-23/...`) e entrega o `Remove-Item` pronto.
   — verificação: `Test-Path` devolve False. — reversão: não há, e não deve haver.

6. **Explicar o "1541" no chamado 1541.** `demanda.py comentar 1541` dizendo que "(pelo WhatsApp) 1541"
   foi resposta à pergunta da logo, que nenhum arquivo chegou, e que o PDF mandado era o termo da
   rescisão, não o relatório do 13º: a pergunta precisa ser refeita.
   — verificação: o comentário aparece no 1541. — reversão: nenhuma (histórico).

**Parte 2 — os consertos de código**

7. **D2: texto que cita PERGUNTA entra sempre.** `backend/pendencias.py`, `tratar`, ramo `else` (hoje
   linhas 379-385): a consulta do `alvo` passa a trazer a `classe` da mensagem citada; se alguma é
   `pergunta` e a pendência é `chamado`, chama `_anotar_resposta` (já existe, linha 249) em vez de
   gravar `descartada`. Citou `informativo` ou `entrega`: como hoje.
   — verificação: testes novos em `tests/test_pendencias.py`: (a) citou pergunta sem espera → mensagem
   `a_entregar` e "Anotado no chamado N"; (b) citou informativo sem espera → `descartada` e "só aviso"
   uma vez; (c) citou pergunta com espera → igual a hoje. Teste antigo que afirme o descarte ao citar
   pergunta é ajustado e dito no commit.
   — reversão: `git revert`.

8. **D1 + D3: arquivo citado nunca desce a corrente, e o aviso no sintoma.** `backend/arquivo_volta.py`,
   `tratar`: antes do `if not ligado(con)`, se a mensagem é arquivo (`arquivo_da_mensagem`) **com**
   `contexto` que casa uma mensagem `saiu` de pendência deste número (qualquer tipo):
   - reenvio da Meta (mesmo `wamid` já gravado) → `True`, sem repetir;
   - chave ligada → segue o caminho de hoje, sem mudança;
   - chave desligada, chamado → frase nova `DESLIGADA` ("Não estou recebendo arquivo por aqui agora.
     Anexe no chamado %s, no sistema."), linha de rastro por `_linha` (`arquivo_recusado`, motivo
     `desligada`, `avisado: true`), e o aviso: `vigia._avisar(con, "arquivo_sem_antivirus", [...])` se
     o ajuste `pendencias.arquivo_desligada_aviso_em` não é de hoje, gravando o ajuste;
   - pendência de aprovação → `pendencias.SO_AVISO_APROVACAO`.
   Nada é baixado. Texto e arquivo sem citar com a chave desligada: `False`, como hoje.
   — verificação: testes novos em `tests/test_pendencias_arquivo.py`: (a) chave desligada + PDF citando
   pergunta → frase, rastro, 1 aviso, `saida.baixar` não chamado, e **nenhuma linha em
   `logos_de_cliente`** rodando pelo `motor.tratar`; (b) segundo arquivo no mesmo dia → frase, sem
   segundo aviso; (c) chave desligada + PDF sem citar → vira logo como hoje; (d) chave ligada → os
   testes existentes do #1528 seguem verdes.
   — reversão: `git revert`.

9. **Bateria inteira.** `pg_isready -p 5437`; `pytest -p no:cacheprovider --basetemp=C:/Temp/1722-<único>`.
   — verificação: tudo verde; o número de testes é dito no commit. — reversão: n/a.

10. **Manual.** `docs/manuais/chamado-no-whatsapp.md`: a seção "Devolver um arquivo" e a de respostas
    ganham as quatro frases da spec (*Manual de uso*, item 4) e o limite ("texto entra sempre; arquivo
    só com pergunta aberta"); a parte "Para quem cuida" da chave `pendencias.arquivo_volta` ganha a
    linha da frase e do aviso diário. Caçar o que ficou falso (a afirmação de que arquivo deslizado
    sempre é anotado). Conferir que a linha do manual já está no `docs/manuais/INDICE.md`.
    — verificação: quem lê só o manual sabe o que cada uma das quatro respostas quer dizer.
    — reversão: `git revert`.

11. **Commit e push do código, dos testes e do manual** (um commit por conserto, todos citando `#1722`).
    — verificação: push aceito, árvore limpa nos arquivos tocados.

12. **[SÓ O DONO] Reiniciar o recepcionista** de novo, para o código valer.
    — verificação: log sem erro depois do arranque; `/saude` responde.

13. **Prova real.** A sessão lê o estado da chave (`ajustes`, só leitura) e a conversa pelo
    `ler_conversa.py`:
    - **D2**, sempre: o dono desliza uma pergunta já respondida de um chamado dele e escreve um texto →
      "Anotado no chamado N. ✓", e o comentário aparece no chamado.
    - **D1 + D3**, só se a chave ainda estiver desligada: o dono desliza uma mensagem de chamado e
      manda um PDF → ouve a frase nova, recebe o aviso "Volta com arquivo: está desligada...", e nenhuma
      logo nasce. Depois ele liga a chave. **Se a chave já estiver ligada, não se desliga produção para
      provar:** a prova de D1/D3 fica nos testes do passo 8, e isso é dito na devolução.
    - Conferir na Meta (leitura) se o modelo `arquivo_sem_antivirus` saiu de PENDING; se não, o aviso só
      sai dentro da janela de 24 h do dono, e isso vai escrito no chamado.
    — reversão: ROLLBACK_PLAN 1 da spec.

14. **Devolver o #1722**, com o manual. `demanda.py entregar 1722` com o texto para quem abriu: o que
    mudou, as quatro respostas que a pessoa pode ouvir, e que a volta com arquivo depende da chave
    ligada. — verificação: o chamado fecha. — reversão: reabrir.
    E a linha em `C:\AxiaAtende\logs\sessions.log`.

## O que só você pode fazer

Janela **elevada** do PowerShell.

Passos 4 e 12 (reiniciar o recepcionista):
```powershell
Restart-Service axiaatende-recepcionista
Get-Service axiaatende-recepcionista
```

Passo 5 (apagar o PDF): a sessão entrega o `Remove-Item` com o caminho completo na hora.

Ligar a volta com arquivo (quando quiser; depois do passo 13 se for provar D1/D3 de verdade):
```powershell
cd C:\AxiaAtende
$env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
.\.venv\Scripts\python.exe scripts\chamado_no_whatsapp.py ligar-arquivo
```

Sem bloco `pos-entrega`: os serviços do AxiaAtende não estão no catálogo da Porta-Ação.

## Riscos de execução identificados

- **Passo 4 interrompido** (restart no meio): a migração é uma transação; ou entra inteira ou não
  entra. Seguro parar antes ou depois. Entre os passos 4 e 12 o recepcionista roda o código de hoje
  com a limpeza feita: estado válido, pode ficar assim até outra sessão.
- **Outra sessão pega o mesmo número de migração:** o número é lido na hora do passo 2; se colidir no
  push, renumera antes de aplicar. Migração aplicada não se edita (sha gravado): conserto vira a seguinte.
- **A mensagem 136 chega ao ERP e acorda o FIO** no 1541: esperado, é a resposta dela. O FIO pode
  responder no chamado; não é incidente.
- **Prazo de 24/11 15:06 perdido:** a logo passa a aparecer para o AxiaMarketing como "a conferir". Se
  o passo 4 não puder acontecer a tempo, avisar o dono antes das 15:00 para ele não aceitar a logo lá.
- **Fio não coberto por passo:** `pendencias_erp.conferir` continua fechando a espera por comentário
  do autor. Está fora por decisão (chamado #1735).
- **O rastro do arquivo recusado por chave desligada conta no teto de 20 por dia** (`_do_dia`). Aceito:
  é uma linha por tentativa, e a pessoa foi mandada ao sistema.

## Linha de abertura da sessão de execução

```
AxiaAtende: aplicação de plano aprovado. Leia C:\AxiaAtende\CLAUDE.md e C:\SuporteAxia\docs\PADRAO-TRABALHO.md, e execute o plano C:\AxiaAtende\docs\specs\2026-11-23-arquivo-e-texto-citando-chamado-plano.md (a spec está ao lado, sem o "-plano"). Chamado #1722; todo commit cita #1722, e o primeiro ato é `tratar 1722 --status em_andamento` pela skill /demanda. PRAZO: a Parte 1 (passos 1 a 6, a limpeza) tem de estar em produção antes de 24/11/2026 15:06, quando a logo 6 passa a ser oferecida ao AxiaMarketing; faça a Parte 1 inteira antes de abrir a Parte 2. Decisões que NÃO se reabrem: sem chave nova (caminho A); o PDF da rescisão não vai ao chamado 1541; a regra pergunta_aberta do ERP está fora (#1735); o aviso usa o tipo arquivo_sem_antivirus que já existe, sem modelo novo na Meta; não desligar a chave em produção para provar. Pare e me entregue o comando pronto nos passos marcados [SÓ O DONO] (restart do recepcionista nos passos 4 e 12, apagar o PDF no passo 5). O que vai para a tela durante a execução está no PADRAO-TRABALHO.md §1.
```
