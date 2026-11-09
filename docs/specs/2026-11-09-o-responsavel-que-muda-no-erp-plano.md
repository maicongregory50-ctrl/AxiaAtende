# Plano — O responsável que muda no ERP chega aos envios já gravados (o caso Ceres)
**Data:** 2026-11-09
**Chamado:** #1285
**Spec de origem:** docs/specs/2026-11-09-o-responsavel-que-muda-no-erp.md
**Status:** APROVADO
**Executável pelo agente:** não -- roda em produção, em janela elevada com o `.env.secrets`, e toca dois repositórios (AxiaMarketing e AxiaAtende)

## Contexto

A Ceres saiu; o cadastro do ERP já aponta os clientes dela ao dono. O AxiaAtende guarda o responsável
em cada linha de envio e lê dali o botão da direta, o aviso de recusa, o resumo do lote e a frase do
portão da carteira. Caminho A da spec: um script no marketing escreve o CSV dos responsáveis de hoje
pela regra que já existe; um script no AxiaAtende mostra, regrava e desfaz. Nenhuma migração, nenhum
restart, nenhum laço novo.

## Passos

1. **Medir antes de escrever** — janela elevada, `AXIAATENDE_AMBIENTE=producao`, banco do atendimento
   (somente leitura): quantas linhas de `envio_destinatarios` têm o WhatsApp da Ceres, por envio, situação
   do envio e situação da linha; quantas estão no recorte da spec (envio não encerrado, ou convite nos
   últimos 30 dias, ou direta com convite); quantos `avisos` `lote_do_representante` pendentes
   (`enviado_em IS NULL AND nao_visto_em IS NULL`) para o número dela. Gravar em
   `docs/medicoes/2026-11-09-1285-ceres-antes.md`. — arquivos: o `.md` da medição — verificação: o
   número de linhas no recorte é o que o passo 5 vai mostrar em "muda" — reversão: nenhuma (leitura).

2. **O CSV dos responsáveis de hoje, no AxiaMarketing** — `C:\AxiaMarketing\scripts\responsaveis_de_hoje.py`:
   chama `erp.lista_envio(cfg)` e, para cada cliente (um por `codigo`, o comprador basta), aplica
   `envio_whatsapp._responsavel(cfg, c)`; escreve CSV UTF-8 com cabeçalho
   `erp_codigo,responsavel_nome,responsavel_whatsapp,responsavel_canal` (canal = `c["canal"]` ou
   vazio) na saída padrão. Sem o segredo do ERP, sai com a frase, código 2. — arquivos: o script e
   `tests/test_1285_responsaveis_de_hoje.py` (lista falsa por monkeypatch: representante com
   número, cliente de corretor vira o dono, canal vazio sai vazio) — verificação: `pytest
   tests/test_1285_responsaveis_de_hoje.py` verde; em produção (janela elevada do marketing), o CSV
   traz a DISAM com o responsável de hoje — reversão: apagar o arquivo; nada o importa.

3. **O script de reatribuição, no AxiaAtende** — `scripts/reatribuir_responsavel.py`, molde do
   `religar_sem_responsavel.py`: lê o CSV (mesmo `ler`, aceitando canal vazio como "sem responsável
   hoje"); seleciona as linhas do recorte da spec cujo (nome, WhatsApp, canal) difere do CSV; para cada
   uma imprime `envio, posição, cliente, situação, de → para, o que acontece`; linha `sem_responsavel`
   com responsável válido passa pela régua do #1197 (`_ultimo_consentimento`, `_ja_recebeu`,
   `_nao_e_whatsapp`, importadas) e vira `aguardando` ou "fica fora: motivo"; avisos pendentes do
   número antigo contados. `--antes <csv>` (obrigatório com `--gravar`): grava `id, campo, valor_antigo`
   das linhas e `aviso_id` dos avisos antes de qualquer UPDATE. `--gravar`: UPDATE das linhas numa
   transação; avisos: `nao_visto_em = now(), erro = 'responsável saiu do atendimento (#1285)'`.
   `--desfazer <antes.csv> --gravar`: devolve cada campo pelo id e limpa `nao_visto_em`/`erro` dos
   avisos listados. Sem `--gravar`, só mostra. — arquivos: o script;
   `tests/test_1285_reatribuir_responsavel.py` com seis casos: (a) linha `aguardando` de envio ativo
   muda; (b) linha de envio encerrado, material, convite há 40 dias **não** muda; (c) linha de
   direta com convite há 90 dias muda; (d) `sem_responsavel` que ganhou responsável vira
   `aguardando`, e com recusa anterior fica fora; (e) aviso guardado do número antigo ganha
   `nao_visto_em`; (f) `--desfazer` devolve tudo (campos e aviso) e o CSV "antes" tem uma linha por
   campo mudado. — verificação: `pytest tests/test_1285_reatribuir_responsavel.py` verde, no banco de
   teste 5437 com `--basetemp` próprio (ver `tests/conftest.py`) — reversão: apagar o script e o
   teste; nada no caminho do envio os importa.

4. **Commits** — `[axiamarketing] #1285 scripts/responsaveis_de_hoje.py ...` e `[axiaatende] #1285
   scripts/reatribuir_responsavel.py, tests/...` (arquivos nomeados; `git status` antes, para não levar
   arquivo de outra sessão: hoje há `frontend/dist.antes-1200/` e `tmp/` untracked no AxiaAtende). —
   verificação: `git log -1 --stat` em cada repositório mostra só os arquivos do passo — reversão:
   `git revert`.

5. **Mostrar em produção, sem gravar** — janela elevada:
   `$env:AXIAATENDE_AMBIENTE='producao'; $env:AXIAATENDE_PROCESSO='recepcionista'` e
   `C:\AxiaAtende\.venv\Scripts\python.exe scripts\reatribuir_responsavel.py C:\Temp\responsaveis.csv --antes docs\medicoes\2026-11-09-1285-antes.csv`.
   Comparar com o passo 1: o "muda" tem o mesmo número de linhas; nenhuma linha de cliente que não era
   da Ceres aparece (se aparecer, é outra troca de cadastro: anotar e seguir, porque o CSV é o ERP de
   hoje e é isso que se quer). — verificação: a saída gravada em
   `docs/medicoes/2026-11-09-1285-ensaio.txt` — reversão: nenhuma (leitura).

6. **Gravar** — o mesmo comando com `--gravar`. Depois, somente leitura:
   `SELECT count(*) FROM atendimento.envio_destinatarios WHERE responsavel_whatsapp = '<número da Ceres>'`
   igual ao "fica" do passo 5; `SELECT responsavel_nome, responsavel_whatsapp FROM atendimento.envio_destinatarios WHERE erp_codigo = <DISAM> ORDER BY convite_em DESC LIMIT 1`
   traz o responsável de hoje (é a linha que `convidado_recente` devolve ao portão); os avisos
   pendentes do número antigo somam zero. Commitar `docs/medicoes/2026-11-09-1285-antes.csv`, o
   `ensaio.txt` e o `.md` da medição. — verificação: as três consultas — reversão: ROLLBACK_PLAN da
   spec, passo 1.

7. **Manual** — `docs/manuais/envios.md`: seção "Quando o responsável muda no ERP" com o texto da
   spec; trocar a frase da seção "O que NÃO faz" que diz que o responsável se corrige só no ERP para
   dizer também que o já gravado segue o cadastro por este procedimento; o INDICE.md já tem a linha
   de `/envios` → `envios.md`, nada muda nele. — verificação: alguém de fora roda o caminho comum
   pela seção sem perguntar; `grep -n "próximos envios\|proximos envios" docs/manuais/envios.md` não
   deixa frase que diga que o gravado não muda — reversão: `git revert`.

8. **Devolver o chamado** — texto para quem abriu (o dono): o que acontecia (o cliente da Ceres era
   mandado ao número dela), o que mudou (as linhas seguem o cadastro de hoje; os resumos pendentes
   dela não saem), o que fica com ele ("O que só você pode fazer"), e o manual. Com
   `ESTEIRA_587_LIGADA` na 8001: `entregar 1285 --devolucao @arquivo.txt` e `fechar 1285`; sem a chave:
   `tratar 1285 --status resolvido --prova --motivo @arquivo.txt`. Antes: uma linha em
   `C:\AxiaAtende\logs\sessions.log`. — verificação: o chamado sai de Execução — reversão: reabrir.

## O que só você pode fazer

- **Ceres fora do cadastro ativo no ERP**: o colaborador/representante dela inativo (ou o contato de
  Relacionamento sem o celular). A agenda da casa relê às 06:00 do dia seguinte; até lá o número dela
  ainda é reconhecido como "da casa" se ela escrever.
- **Tela Destinos do AxiaAtende**: se o número dela estiver lá, tirar. É a camada 2 de
  `internos.py`: destino ativo conta como equipe mesmo fora do ERP.
- **No ERP, Stakeholders → Sem responsável**: deve estar sem os clientes dela. Quem ainda aparecer ali
  não entra no CSV com responsável e **fica como está** no AxiaAtende.
- **Os passos 1, 2 (produção), 5 e 6** rodam em janela elevada, na máquina dos serviços, com os
  comandos prontos acima. A sessão de execução escreve os scripts e os testes; a janela elevada é sua.

## Riscos de execução identificados

- Passo 6 interrompido no meio: o UPDATE das linhas é uma transação (tudo ou nada); os avisos vão em
  transação separada, depois. Se parar entre as duas, as linhas estão regravadas e os avisos
  pendentes ainda sairiam se a Ceres escrevesse: rodar de novo o passo 6 (o script é idempotente: o
  que já bate com o CSV não aparece em "muda").
- O lote do dia (`rotina`, a cada minuto, 9h30-17h) pode mandar um convite entre o passo 5 e o 6 com o
  responsável antigo: a cópia e o resumo iriam ao número antigo uma última vez. Rodar os dois fora
  da janela de envio evita isso.
- CSV do marketing com cliente que mudou de mão por outro motivo: ele muda junto, e é o que se quer
  (o CSV é o ERP de hoje). O "antes" guarda tudo para desfazer.
- A spec tem as duas seções do #667; nenhum fio ficou sem passo.

## Linha de abertura da sessão de execução

Leia `C:\AxiaAtende\CLAUDE.md` inteiro e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md` §1. Faixa:
aplicação de plano aprovado. Execute `C:\AxiaAtende\docs\specs\2026-11-09-o-responsavel-que-muda-no-erp-plano.md`
(spec ao lado, mesmo nome sem `-plano`). Chamado #1285; todo commit cita `#1285`, e o primeiro ato é
`python C:\SuporteAxia\skills\demanda\demanda.py tratar 1285 --status em_andamento --motivo "..."` pela
skill `/demanda`, rodado em `C:\AxiaAtende`. Decisões que não se reabrem: caminho A (scripts à mão,
sem laço de relógio); o recorte das linhas (envio não encerrado, ou convite nos últimos 30 dias, ou
direta com convite de qualquer data); a regra do responsável fica no marketing e o CSV nasce lá;
avisos pendentes do número antigo viram não vistos, não somem. Os passos 1, 2 em produção, 5 e 6
dependem de janela elevada: entregue os comandos prontos e pare em "O que só você pode fazer". O que
vai para a tela durante a execução está no `PADRAO-TRABALHO.md` §1: decisão do dono, incidente que
merece chamado próprio e passo que depende da mão dele; conserto de caminho dentro do planejado não
se narra.
