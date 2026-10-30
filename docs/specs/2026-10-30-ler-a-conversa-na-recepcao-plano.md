# Plano — Ler a conversa na Recepção, com o texto que nós mandamos
**Data:** 2026-10-30
**Chamado:** #1205
**Spec de origem:** `C:\AxiaAtende\docs\specs\2026-10-30-ler-a-conversa-na-recepcao.md`
**Status:** APROVADO (dono, 30/10/2026)
**Executável pelo agente:** sim

## Contexto
Clicar numa linha da Recepção abre uma janela com o histórico inteiro daquele número (cliente de um
lado, nós do outro, o atendimento clicado em destaque). O recepcionista passa a guardar o texto
exato de cada envio, capturado num ponto só (a `SaidaMeta`), por `wamid`, numa tabela à parte com um
escritor. Cada abertura da janela fica registrada. Caminho B, aprovado em 30/10.

Releitura da spec: os fios (um escritor na tabela nova, um no log novo, nenhum leitor que decide)
viram os passos 1, 2 e 5; a Conformidade com a casa diz R2 **conforme** e nada **muda** nem **cria**:
nenhum passo de carta/painel. Manual legal: não se aplica.

## Passos

1. **Migração 047** — `backend/migracoes/047_texto_do_envio.sql` + `_VOLTA.sql`: tabela
   `atendimento.enviadas_texto` (`wamid` PK, `tipo`, `texto`, `opcoes jsonb`, `modelo`, `variaveis
   text[]`, `legenda`, `gravado_em`) e o ajuste `enviadas.guardar_texto = true`; afirmação de saída
   `RAISE NOTICE '047 OK'`. `tests/test_login.py` ganha a 047 na lista. — verificação: a migração
   sobe no banco de teste (a bateria cria o banco do zero) e `test_saude_diz_que_nao_responde_ninguem`
   passa; o `axiaatende_ro` enxerga a tabela pelo default privilege do #981 (teste em
   `test_ler_conversa`/conferência após o restart). — reversão: `_VOLTA`.

2. **A captura** — `backend/texto_enviado.py` (novo): `guardar_no_banco(cfg)` devolve a função que,
   numa conexão própria e curta (`banco.conexao`), lê o ajuste e faz `INSERT ... ON CONFLICT (wamid)
   DO NOTHING`; qualquer exceção vira `print` no log e retorna. `backend/saida.py`: `SaidaMeta`
   ganha `guardar=None`; cada um dos 8 métodos de envio, depois do `.id`, chama `self._guardar(wamid,
   tipo, conteúdo)` com o conteúdo exato (texto; títulos dos botões; botão e linhas da lista com
   descrição; rótulo e url do link; nome do contato; legenda e nome do arquivo da imagem/documento;
   nome do modelo, variáveis e botões). Sem `wamid` (Meta recusou) não grava. — verificação:
   `tests/test_saida_meta.py` (transporte falso): grava o texto de cada forma; ajuste `false` não
   grava; a função de gravar levantando erro **não** impede o envio nem muda o `wamid` devolvido. —
   reversão: reverter o commit.

3. **Ligar a captura nos 4 construtores** — `backend/recepcionista.py`, `backend/pergunta_agora.py`,
   `scripts/portao_retroativo.py`, `scripts/prova_agora.py` passam `guardar=guardar_no_banco(cfg)`.
   — verificação: `grep -n "SaidaMeta(" backend scripts` mostra os 4 com `guardar=`; bateria passa.
   — reversão: reverter o commit (ou o ajuste em `false`, sem restart).

4. **A montagem em itens** — `backend/leitura.py` (novo): a lógica de `ler_conversa.conversa()` e
   `descrever_entrada` sai para cá e devolve itens (`quando`, `lado` cliente|nos|marco, `tipo`,
   `texto`, `opcoes`, `estado`, `resumo` quando não há texto guardado, `conversa_id`). Envio junta
   `enviadas_texto` por `wamid`; modelo é montado com `modelos.texto` e as variáveis. `scripts/
   ler_conversa.py` passa a formatar esses itens em linhas (mesma saída de hoje, mais o texto quando
   houver). — verificação: `tests/test_ler_conversa.py` passa sem mudar o esperado das linhas antigas;
   teste novo: envio com texto guardado aparece com o texto, sem, aparece o resumo. — reversão:
   reverter o commit.

5. **A rota da janela** — `backend/rotas_telas.py`: `GET /api/recepcao/conversa/{id}` (com login):
   acha a conversa, monta os itens da pessoa (por `wa_id` e `bsuid`), marca os da conversa clicada, e
   grava uma linha em `cfg.logs / "telas" / "leituras.jsonl"` (quando, login, conversa, itens).
   Conversa inexistente: 404. — verificação: `tests/test_telas.py`: sem login 401; com login devolve
   os itens em ordem com o destaque certo; o arquivo de leitura ganha uma linha por chamada
   (`cfg.logs` em `tmp_path`). — reversão: reverter o commit.

6. **A janela** — `frontend/src/Recepcao.jsx` (+ `atende.css`): clique na linha abre um modal
   (exceto na célula *Quem*, que continua sendo o link do WhatsApp Web: `stopPropagation`); balões,
   faixa de início de cada atendimento, rola até o destacado, "resumo" em itálico, estado do envio,
   fecha no X e no Esc; tema claro/escuro pelos tokens já existentes (#1200). — verificação:
   `npx vite build` sem erro; a conferência na tela fica no passo 9. — reversão: reverter o commit e
   rebuildar.

7. **Bateria inteira** — `.venv\Scripts\python.exe -m pytest tests` (com `--basetemp` no scratchpad)
   — verificação: tudo passa (hoje 426). — reversão: n/a.

8. **Manual** — `docs/manuais/recepcao.md` ganha "Ler a conversa" (o texto do *Manual de uso* da
   spec), e caça o que ficou falso (a frase de que só o nome/número é clicável); `docs/manuais/
   leitura-da-sessao.md` diz que o texto dos envios passa a aparecer. `INDICE.md`: a rota `/recepcao`
   já está lá — conferir, sem linha nova. — verificação: o caminho comum é executável lendo só o
   manual; a linha da Recepção no índice continua no formato de três colunas. — reversão: reverter.

9. **Commit, push, restart e as três provas** — commits citando `#1205`, nomeando arquivos; push.
   Depois do seu restart: (efeito) `/saude` da 8009 lista a 047; o próximo envio real tem linha em
   `enviadas_texto` (consulta pelo `axiaatende_ro`); (a jusante) a janela abre a conversa da Copermap
   com os resumos antigos, o recepcionista segue `pendentes: 0` e sem erro, `ler_conversa.py` roda;
   (subiu) processos criados depois da hora dos arquivos. — reversão: ver ROLLBACK da spec.

10. **Devolver o chamado #1205** — você é o autor: comentário com o que mudou e o manual, e
    `fechar`. — verificação: você usa a janela lendo só a devolução. — reversão: reabrir.

## O que só você pode fazer
Depois do passo 8 (commit e push feitos), numa janela elevada — o recepcionista primeiro:
```powershell
Restart-Service axiaatende-recepcionista; Restart-Service axiaatende-backend
```
Se o restart do `332f4ea` (esconder a linha do portão) ainda não foi feito, este o cobre.
Sem bloco `pos-entrega`: os serviços do AxiaAtende não estão no catálogo da Porta-Ação.

> **Emenda da execução (30/10/2026): a linha acima estava ERRADA.** Os dois serviços do AxiaAtende
> estão no catálogo da Porta-Ação desde o #973 (29/10/2026, `$SERVICOS` em
> `C:\AxiaSecurity\scripts\porta_acao.ps1`). O restart **não** é mão do dono: a sessão pede
> `reiniciar` pela porta (`portas.pedir(portas.ACAO, "reiniciar", {"servico": ..., "motivo": ...})`),
> o recepcionista primeiro. Foi assim que a execução reiniciou, às 10:14, a pedido do dono.

## Riscos de execução identificados
- **Passos 1–8**: só repositório e banco de teste; parar no meio deixa código não commitado, sem efeito em produção.
- **Restart do recepcionista antes do backend**: o recepcionista aplica a 047 ao subir e passa a
  gravar; as telas antigas não leem a tabela — seguro ficar assim até o segundo restart.
- **Captura em produção**: falha ao gravar não derruba envio (passo 2 prova); se gravar algo errado,
  o ajuste em `false` para na hora, sem restart.

## Linha de abertura da sessão de execução
Leia `C:\AxiaAtende\CLAUDE.md` e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`; execute o plano
`C:\AxiaAtende\docs\specs\2026-10-30-ler-a-conversa-na-recepcao-plano.md` (spec ao lado), faixa
"aplicação de plano aprovado". Chamado #1205; todo commit cita `#1205`, e o primeiro ato é `tratar
1205 --status em_andamento` pela skill `/demanda`. Não se reabrem: a pessoa inteira na janela; o
texto capturado na `SaidaMeta` por `wamid` em tabela própria com um escritor; cada abertura
registrada; mídia sem baixar; nada se responde pela janela. Pare em "O que só você pode fazer". O que
vai para a tela durante a execução está no `PADRAO-TRABALHO.md` §1.
