# Plano — A janela de 24 h: o porteiro dos avisos internos e o modelo de reabertura
**Data:** 2026-10-28
**Chamado:** #1188
**Spec de origem:** docs/specs/2026-10-28-a-janela-de-24h-e-o-porteiro-dos-avisos.md
**Status:** APROVADO
**Executável pelo agente:** não — o dono executa em sessão própria (28/10/2026)

Os fios da spec viram passos: os seis escritores de `atendimento.avisos` não mudam (todos passam pelo
mesmo leitor, `Envio.mandar_avisos`, que é onde o porteiro entra — passo 5); a última mensagem da
pessoa (passo 3); o toque (passo 6); a tela Envios e a rota do marketing que pergunta pelo aviso
(passo 8: `enviado_em` continua sendo "saiu"). O universo não medido pela sessão é o passo 1.
Conformidade com o Manual legal e com a casa: não se aplica (spec).

## Passos

1. **Abrir e medir** — `tratar 1188 --status em_andamento` (skill `/demanda`). A medição (avisos por
   tipo e por número nos últimos 30 dias, e quantos tinham mensagem da pessoa nas 24 h anteriores) é
   leitura do banco de PRODUÇÃO, fechado à sessão: escrever `scripts/medir_avisos.py` (só SELECT) e
   deixá-lo em "O que só você pode fazer"; o resultado entra no comentário do chamado. Não bloqueia
   os passos seguintes — verificação: o script roda no banco de dev sem erro — reversão: apagar o
   script.

2. **A migração 039** (`backend/migracoes/039_porteiro_dos_avisos.sql` + `_VOLTA`):
   - `atendimento.avisos` ganha `guardado_em timestamptz`, `nao_visto_em timestamptz`,
     `como text` (`modelo` | `texto`, nulo enquanto não saiu) e `reabertura_id bigint` (o aviso de
     reabertura que o guardou);
   - o CHECK `modelos_uso` (e a regra uso × categoria da 003/008) aceita `reabertura`, categoria
     UTILITY;
   - o modelo no cadastro: `reabrir_avisos`, UTILITY, uso `reabertura`, sem imagem, variáveis
     `{n_avisos}`, botão de resposta rápida `ver`, texto **"Você tem {{1}} aviso(s) da Sementes
     Renascer. Toque em Ver para receber."** (aprovado pelo dono em 28/10; não começa nem termina em
     variável — a regra da Meta da 004);
   - conferir os CHECKs do tipo do aviso (`avisos_tipo`) — não mudam.
   - verificação: o teste de migração (ida, VOLTA, ida) e `tests/test_login.py` com a 039 na lista de
     mudanças (a lição da 037) — reversão: a VOLTA.

3. **A janela da pessoa** — uma função só, `janela.aberta(con, numero, agora) -> bool`: a última
   mensagem RECEBIDA daquele número (de `atendimento.eventos_meta` tipo `mensagem`, pelo número do
   `corpo`, ou `conversas.ultimo_toque_em` — escolher UMA e provar com um interno que só manda foto)
   há menos de 24 h. O canal de campo continua com a dele (fora do escopo) — verificação: testes com
   mensagem há 23 h (aberta), 25 h (fechada), toque de botão (conta), nenhuma (fechada) — reversão:
   `git revert`.

4. **O texto livre do aviso** — `texto_do_aviso(con, aviso) -> str`: o texto do modelo do tipo
   (`modelo_do_uso(con, "aviso_" + tipo)`), com os mesmos parâmetros que `mandar_avisos` monta hoje,
   em texto corrido (o botão de link, quando o modelo tem, vira o endereço no fim) — verificação:
   teste por tipo (`recusa`, `sem_atendimento`, `lote_do_representante`, o do vigia, o do plano):
   o texto sai igual ao do modelo, sem `{{n}}` sobrando — reversão: `git revert`.

5. **O porteiro em `mandar_avisos`**, atrás da chave `AXIAATENDE_PORTEIRO` (XML do serviço que manda;
   `config.py` primeiro, XML depois — senão o `extra='forbid'` derruba o import; nasce `off`):
   - chave desligada: exatamente como hoje (teste de não-regressão);
   - janela aberta: `saida.texto(numero, texto_do_aviso)`, `como = 'texto'`, `enviado_em`;
   - janela fechada: o aviso fica `guardado_em`; se aquele número NÃO tem reabertura pendente, sai
     UMA `reabrir_avisos` com o total guardado (`botoes` com a carga `reabrir:<numero>`), gravada em
     `atendimento.enviadas`; se já tem, o aviso só se soma ao guardado;
   - guardado há 7 dias sem toque: `nao_visto_em` (não sai mais; não some).
   - verificação: testes com a Saída falsa: dois avisos ao mesmo número fora da janela = UMA
     reabertura com "2"; dentro da janela = dois textos e nenhum modelo; o oitavo dia = não visto —
     reversão: desligar a chave.

6. **O toque em Ver** — `motor.py`, junto do `envio:` (~565): `reabrir:<numero>` solta os guardados
   daquele número (não vistos inclusive? NÃO: o não visto fica como está), em ordem de `criado_em`,
   como texto, cada um com `como = 'texto'` e `enviado_em`; o toque não abre o menu nem a OlivIA — e
   o toque de um número que não é o da carga é ignorado — verificação: teste do toque com três
   guardados = três textos, na ordem; segundo toque = nada — reversão: `git revert`.

7. **O cadastro na Meta** — `modelos_meta.EXEMPLOS["n_avisos"] = "3"`; o `componentes()` conhece o
   uso `reabertura` (resposta rápida, sem imagem); `tests/test_modelos_meta.py` com o modelo novo na
   contagem — verificação: o teste do `--propor` com a Meta falsa manda `reabrir_avisos` com o botão
   — reversão: `git revert`.

8. **A tela Envios mostra os avisos** — `rotas_telas.py` (`/envios`) e a página: os avisos dos últimos
   30 dias com o estado **Enviado (texto)**, **Enviado (modelo)**, **Guardado**, **Não visto**,
   **Erro**, o nome e quando; a rota do marketing que pergunta pelo aviso (`rotas_pedido.py` ~188)
   continua respondendo por `enviado_em`/`erro`, e ganha `guardado` — verificação: teste da rota e a
   tela em dev — reversão: `git revert`.

9. **A bateria** — `python -m pytest` inteiro (`--basetemp` curto, `AXIAATENDE_BANCO_TESTE` próprio se
   outra sessão estiver rodando) — verificação: verde — reversão: —.

10. **O manual** — `docs/manuais/envios.md`: a seção dos avisos (o que a spec escreveu em *Manual de
    uso*), e caçar o que ficou falso ("cada aviso sai por um modelo", "o resumo do lote… precisa do
    modelo aprovado na Meta" continua verdade para quem está fora da janela; reescrever com as duas
    saídas). Linha do `INDICE.md` já existe; conferir — verificação: alguém de fora entende "Não
    visto" sem perguntar — reversão: `git revert`.

11. **Commit e push**, citando `#1188`. **A chave fica `off` no XML.**

12. **Devolver a demanda** — depois do passo 13 do dono (modelo aprovado e chave ligada): o que muda
    para o representante (o "Você tem N avisos… Ver"), o "Não visto" na tela Envios, e o manual —
    verificação: o dono lê só a devolução e sabe o que o representante vai ver — reversão: reabrir.

## O que só você pode fazer
1. **Medir** (passo 1), em PowerShell como administrador:
   ```powershell
   cd C:\AxiaAtende
   $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
   .\.venv\Scripts\python.exe scripts\medir_avisos.py
   ```
2. **Reiniciar os dois serviços do AxiaAtende** (não estão na Porta-Ação), como administrador:
   ```powershell
   Restart-Service axiaatende-backend; Restart-Service axiaatende-recepcionista
   ```
3. **Mandar o modelo à Meta** — PRIMEIRO ver o que existe (o `--ver` APLICA as migrações pendentes; é
   o que se quer aqui, a 039):
   ```powershell
   cd C:\AxiaAtende
   $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
   .\.venv\Scripts\python.exe -m backend.modelos_meta --ver
   .\.venv\Scripts\python.exe -m backend.modelos_meta --propor
   ```
   (o `--propor` manda TODOS os do cadastro que a Meta não tem; o `--ver` mostra quais)
4. **Quando a Meta aprovar** `reabrir_avisos`: `AXIAATENDE_PORTEIRO` = `on` no XML do serviço que
   manda os avisos (validar o XML com `[xml]` antes; `--` em comentário derruba o WinSW) e reiniciar
   esse serviço.

## Riscos de execução identificados
- Chave ligada ANTES de o modelo estar aprovado: a reabertura falha na Meta, os avisos ficam
  guardados com `erro` — ninguém recebe. Por isso a chave nasce `off` e só liga no item 4 acima.
- Migração interrompida: uma transação só (`migracoes.py`). Seguro.
- O `--ver` aplica migração: rodar só depois do commit e do restart (a 039 já no disco e testada).
- O texto livre de um tipo sai diferente do modelo: o representante lê outra frase; o teste do passo
  4 segura.

## Linha de abertura da sessão de execução
Leia `C:\AxiaAtende\CLAUDE.md` e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Aplicação de plano
aprovado: execute `C:\AxiaAtende\docs\specs\2026-10-28-a-janela-de-24h-e-o-porteiro-dos-avisos-plano.md`
(a spec está ao lado). Chamado #1188; todo commit cita `#1188`, e o primeiro ato é `tratar 1188
--status em_andamento` pela skill `/demanda`. Não se reabre: só os avisos INTERNOS (o cliente fica
fora — é o #1189); o texto do modelo é o aprovado pelo dono ("Você tem {{1}} aviso(s) da Sementes
Renascer. Toque em Ver para receber.", botão Ver); 7 dias sem toque = "não visto", que não some; a
chave `AXIAATENDE_PORTEIRO` nasce desligada e só liga com o modelo aprovado na Meta; o `--ver` do
`modelos_meta` aplica migração pendente (lição da 037). O que vai para a tela durante a execução está
no `PADRAO-TRABALHO.md` §1. Pare em "O que só você pode fazer".
