# Plano — A janela de envio aos clientes
**Data:** 2026-10-29
**Chamado:** #1192
**Spec de origem:** — (bug com o desenho no chamado: a decisão do dono vem abaixo)
**Status:** APROVADO
**Executável pelo agente:** sim

## O problema e a decisão

O laço do lote (`backend/envio.py`, `Envio.mandar_lotes`) abre o "lote do dia" assim que a data muda.
Em 29/10/2026 o lote seguinte de um envio aprovado às 16h de 28/10 saiu às **00h01**: o cliente
recebeu a mensagem da empresa de madrugada.

**Decisão do dono (29/10/2026):** o envio aos clientes só sai **de segunda a sexta, das 9h30 às 17h**,
horário de Brasília. O que não saiu dentro da janela fica para o próximo dia útil, às 9h30. Sábado e
domingo nada sai.

Conformidade com o Manual legal: não se aplica (horário de envio, não regra fiscal). Conformidade com
a casa: não se aplica (nenhum serviço, segredo, agente ou dado novo).

## Passos

1. **A janela no laço do lote.** `backend/envio.py`: as constantes `JANELA_INICIO` (9h30),
   `JANELA_FIM` (17h) e `DIAS_DA_JANELA` (seg a sex); `mandar_lotes` não manda nada fora da janela,
   no relógio de São Paulo. Dentro dela, tudo como antes: 20 por envio por dia, a nota verde, o teto do
   comprador e o resumo ao representante.
   - Teste: `tests/test_1192_janela.py` — 00h01 nada sai; 9h29 nada; 9h30 sai; 17h nada; sábado
     nada; o lote do dia seguinte começa às 9h30.
   - Verificação: a suíte do AxiaAtende.
   - Reversão: `git revert`.
2. **O manual.** `docs/manuais/envios.md`: a janela, e o que significa o envio parado fora dela.
   - Verificação: a frase diz o que o sistema faz.
   - Reversão: `git revert`.
3. **O restart e a prova.** O dono reinicia o `axiaatende-backend`; o envio de hoje segue às 9h30, e
   nada sai depois das 17h.
4. **Devolver o #1192** com o manual.

## O que só você pode fazer

- Reiniciar, no PowerShell como administrador:
  ```powershell
  'axiaatende-backend' | ForEach-Object { Restart-Service $_ -Force; Start-Sleep 3; Get-Service $_ | Select-Object Name,Status }
  ```

## Riscos de execução identificados

- O `backend/envio.py` tem mudança não comitada de outra sessão (#1189, o portão do cliente), em
  outra parte do arquivo. O commit leva só o trecho do #1192.
- Até o restart, o laço antigo continua valendo: o restart precisa vir antes das 00h de 30/10.

## Linha de abertura da sessão de execução

Executado na mesma sessão que o abriu (urgência: o próximo lote sairia à 00h01).
