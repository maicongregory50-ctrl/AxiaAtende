# Plano: o aviso de classe 1 do painel vai ao WhatsApp do dono
**Data:** 2026-11-12
**Chamado:** #1434
**Spec:** `docs/specs/2026-11-12-aviso-do-painel-no-whatsapp.md`
**Executável pelo agente:** sim

## Passos

1. AxiaAtende, `backend/migracoes/063_aviso_painel.sql` (e `_VOLTA`): tipo `painel_classe1` e uso
   `aviso_painel_classe1` nos CHECKs reescritos inteiros; modelo `aviso_painel` (UTILITY, `{{1}}`);
   ajuste `painel_para` copiado de `integracoes_para`; conferência no fim.
2. `backend/config.py`: `painel_pedidos` (`C:\Logs\Seguranca\revisao\avisos`) e `painel_devolucao`
   (`C:\Dados\AxiaAtende\painel`); nos ambientes de teste, pastas em `C:\Dados\AxiaAtende\<amb>\`.
3. `backend/painel_avisos.py`: `ir` lê os `.json` da pasta (inválido é pulado e dito no log; pasta
   ausente é `OrigemIndisponivel`), `devolver` grava a devolução de forma atômica.
4. `backend/auditoria_erp.py`: `Canal.precisa_erp` (padrão `True`); `volta` só deixa de fora os
   canais do ERP quando a ligação com o ERP está desligada; `volta_do_canal` aceita
   `OrigemIndisponivel`; o canal `painel_classe1` em `CANAIS`. O teste do #350 que espera
   `{"erro": ...}` com o ERP desligado continua passando (canais de teste só do ERP).
5. `tests/test_1434_aviso_painel.py`: a migração; pedido vira aviso para o destino do ajuste;
   devolução ENVIADO e FALHOU no arquivo; o mesmo pedido não repete; pasta ausente é erro do canal
   e não para os outros; ERP desligado não para o painel. Rodar a bateria do AxiaAtende.
6. AxiaSecurity, `scripts/revisao_painel.ps1`: com `aviso_ativo=true`, item com `aviso` grava o
   pedido (contador `aviso_seq` no `estado.json`, uma vez por chave por dia, texto no molde da
   `lista-notificacao.md` §3); lê as devoluções para o resumo (`avisos_pedidos`, `avisos_enviados`,
   `avisos_falharam`); apaga pedido com devolução de mais de 7 dias. Casos no
   `conferir_revisao_painel.ps1` para a função pura do texto e da decisão.
7. Manuais (`revisao-do-painel.md`, avisos do AxiaAtende), `RESPONSABILIDADES.md` R1, `PROJETO.md`
   do AxiaAtende (Ofereço) e do AxiaSecurity (Exijo), `lista-notificacao.md` §2.
8. Commits citando #1434 nos dois projetos, push.
9. Restart do `axiaatende-backend` pela Porta-Ação, **só com a árvore do AxiaAtende sem obra de
   outra sessão**; conferir no log das telas que a 063 entrou e o canal `painel_classe1` roda sem erro.
10. Prova real: um pedido de teste na pasta (texto "[TESTE] aviso do painel, #1434") chega ao
    WhatsApp do dono e a devolução diz ENVIADO. Depois, `aviso_ativo=true`.

## Pós-entrega

O dono confirma que recebeu o aviso de teste.

## Rollback

`aviso_ativo=false`; `git revert` nos dois projetos; restart pela Porta-Ação; 063 fica (VOLTA à mão).
