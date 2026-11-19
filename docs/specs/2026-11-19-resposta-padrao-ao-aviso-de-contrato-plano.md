# Plano — A resposta padrão ao cooperante que responde a um aviso automático do contrato
**Data:** 2026-11-19
**Chamado:** #1664
**Spec de origem:** docs/specs/2026-11-19-resposta-padrao-ao-aviso-de-contrato.md
**Status:** APROVADO

**Executável pelo agente:** não -- o AxiaAtende é executado em sessão com pessoa, e ligar a chave e a prova real são do dono.

Conformidade com o Manual legal e com a casa: não se aplicam (a spec diz por quê). D3 fechada pelo dono
em 19/11/2026: o tratamento sem gênero ("Bom dia, Alfonso!").

## Passos

1. **A migração** — `backend/migracoes/NNN_resposta_ao_cooperante.sql` e `_VOLTA.sql`, com o próximo
   número livre (em 19/11/2026 a 072 já é do #1660; conferir a pasta). Quatro ajustes:
   `cooperante.resposta_padrao` = false; `cooperante.dias` = 7; `cooperante.texto` (o texto de D2, com
   `{saudacao}`, `{nome}` e `{contato}`); `cooperante.destino` = o id do destino de nome "Maicon Gregory"
   (a migração falha, com mensagem clara, se esse destino não existir). — verificação:
   `tests/test_migracoes.py`; aplica e a `_VOLTA` desfaz no banco de teste (5437). — reversão: a `_VOLTA`.

2. **O desvio** — `backend/cooperante.py` (novo, pequeno): `ligado(con)`;
   `aviso_de_contrato_recente(con, numero, agora)` (a linha mais nova de `termos_reprovacao` com
   `para_whatsapp` = o número, `enviado_em` dentro de `cooperante.dias` e estado diferente de `falhou`; é
   o ponto único onde os próximos avisos entram); `tratar(con, saida, e, agora) -> bool`. Em
   `backend/motor.py`, em `tratar`, logo depois do ramo `termo:ciente:` e antes do portão do cliente:
   com a chave ligada, sem toque de botão e com aviso recente, chama `cooperante.tratar` e retorna. A
   resposta: o texto do ajuste com a saudação pela hora de Brasília (bom dia, boa tarde, boa noite), o
   primeiro nome do `produtor_nome` com a caixa arrumada (`primeiro_nome`) e o primeiro nome do destino;
   depois `saida.contato` com o destino. Registra em `enviadas` com o resumo
   `aviso de contrato: resposta padrao (termo <numero>)`. — verificação: testes em
   `tests/test_cooperante.py`: com aviso recente sai o texto e o cartão, e o portão do cliente não é
   chamado; sem aviso, com aviso de mais de 7 dias ou com a chave desligada, tudo como hoje; o toque
   `termo:ciente:` continua indo a `termo_erp.tocar`; toque de menu segue o menu. — reversão: revert.

3. **O aviso ao contato** — `cooperante.avisar(con, saida, aviso, e, agora) -> bool`: com
   `envio.janela_aberta` do destino, `saida.texto` com "Cooperante respondeu ao aviso", o nome, o número
   do termo, o que ele escreveu (texto; para áudio, foto ou documento, o tipo) e o link `wa.me` dele;
   fora da janela, `saida.modelo` com `modelo_do_uso(con, "aviso_olivia_resumo")` e uma linha só, com o
   telefone escrito. Registra em `enviadas`; qualquer falha é registrada e devolve False, sem segurar a
   resposta ao produtor. Se a execução do #1660 já tiver criado um auxiliar para "texto na janela,
   `olivia_resumo` fora", usar o mesmo em vez de duplicar. — verificação: três testes (janela aberta,
   janela fechada, saída que falha). — reversão: revert.

4. **Uma vez por aviso** — na segunda mensagem em diante depois do mesmo aviso (reconhecida pelo resumo
   em `enviadas`, posterior ao `enviado_em` do aviso), a linha curta ("<nome>, o <contato> já foi avisado
   da sua mensagem; o contato dele está logo acima.") e novo repasse ao contato. Um aviso novo ao mesmo
   produtor reinicia a contagem. — verificação: teste com três mensagens seguidas (uma resposta padrão,
   duas linhas curtas, três repasses) e com um segundo termo. — reversão: revert.

5. **Os comandos** — `scripts/cooperante.py ligar|desligar|mostrar` (recusa quando o ajuste não existe;
   `mostrar` diz a chave, o prazo, o contato e o texto). `/saude` do recepcionista ganha
   `cooperante_resposta`. — verificação: teste do script e da saúde. — reversão: revert.

6. **A bateria e o manual** — bateria inteira do AxiaAtende, uma por vez. Manual novo
   `docs/manuais/resposta-ao-cooperante.md` (o texto é o `## Manual de uso` da spec) e a linha de três
   colunas no `docs/manuais/INDICE.md`, se o índice do AxiaAtende seguir esse formato; conferir se o
   manual do termo de reprovação (do #1542) diz algo que esta etapa torna falso sobre a resposta do
   produtor. — verificação: tudo verde; quem não participou do desenho segue o caminho comum sem
   perguntar. — reversão: revert.

7. **Subir** — commits citando `#1664`, push; reinício de `axiaatende-backend` (migração) e de
   `axiaatende-recepcionista` pela Porta-Ação, conferindo a hora de subida no `/saude`. — verificação:
   `/saude` de pé com `cooperante_resposta: desligada`. — reversão: ROLLBACK_PLAN da spec.

8. **[SÓ O DONO] Ligar e provar** — ver abaixo. A prova é o próximo produtor que responder a um termo;
   antes disso, um ensaio com um termo de teste enviado a um número do dono, se a Qualidade puder gerar
   um. — verificação: a resposta padrão e o cartão na conversa do produtor, e o aviso no WhatsApp do
   dono. — reversão: `scripts\cooperante.py desligar`.

Depois da prova: `entregar 1664 --devolucao @arquivo.txt`, com o manual.

## O que só você pode fazer

1. Ligar, em PowerShell administrador:
   ```
   cd C:\AxiaAtende; $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'; .\.venv\Scripts\python.exe scripts\cooperante.py ligar
   ```
2. A prova: o próximo termo de reprovação que sair, ou um de teste ao seu número.

```pos-entrega
dono=rodar scripts\cooperante.py ligar em PowerShell administrador
dono=prova com o proximo termo de reprovacao enviado, ou um de teste ao numero do dono
```

## Riscos de execução identificados

- Passos 1 a 6: nada sobe; parar no meio é seguro.
- Passo 7: com a chave desligada, o código novo não muda nada. Reiniciar o backend antes do
  recepcionista; o inverso também é seguro (o ajuste não existe e `ligado` lê false).
- Outra sessão executa o #1660 no mesmo repositório e reinicia o mesmo serviço: conferir `git status`
  antes de comitar (só os arquivos desta etapa, com `git add -- <arquivos>`), o número da migração antes
  de criar e de novo antes de subir, e a hora de subida no `/saude` depois de cada pedido à Porta-Ação,
  que é de slot único.
- O desvio fica antes do portão do cliente: um erro ali calaria o atendimento de quem recebeu termo. Por
  isso o `tratar` do cooperante só assume a mensagem quando conseguiu responder; em exceção, registra e
  devolve False, e o caminho de hoje segue.

## Linha de abertura da sessão de execução

Leia `C:\AxiaAtende\CLAUDE.md` e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md` (o que vai para a tela durante a execução está no §1). Execute o plano `C:\AxiaAtende\docs\specs\2026-11-19-resposta-padrao-ao-aviso-de-contrato-plano.md` (spec ao lado, D1 a D8): é aplicação de plano aprovado. Chamado #1664; todo commit cita `#1664`, e o primeiro ato é `tratar 1664 --status em_andamento` pela skill `/demanda`. Não se reabrem: texto fixo, sem IA; o gatilho é o aviso enviado (`termos_reprovacao`), não o cadastro; tratamento sem gênero; o contato é o destino do ajuste (o dono) e é avisado na hora; uma resposta padrão por aviso e linha curta depois; fora do escopo reconhecer o cooperante pelo cadastro, os outros avisos e o conteúdo do termo. Outra sessão executa o #1660 no mesmo repositório: comite só os seus arquivos e confira o número da migração. Pare no passo 8: ligar a chave e a prova são do dono.
