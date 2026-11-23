# O que cita um chamado vai ao chamado: o arquivo não vira logo, o texto não é descartado
**Data:** 2026-11-23
**Chamado:** #1722
**Status:** APROVADO

## Contexto

Em 23/11/2026 a Fran devolveu um PDF pelo WhatsApp deslizando a pergunta do chamado 1541, e ouviu
"Recebi a logo ... De qual cliente ela é?". O arquivo não entrou no chamado. Na mesma conversa, a
resposta de texto dela sobre o FGTS da rescisão foi descartada duas vezes.

Dois defeitos, medidos em produção (5436, só leitura):

1. **A volta com arquivo (#1528) está desligada desde 17/11/2026 10:45** (`pendencias.arquivo_volta =
   false`, 19 minutos depois de o #1528 ser fechado como entregue; sem commit, sem linha no
   `sessions.log`, sem comentário: não se sabe quem desligou). Com a chave desligada,
   `arquivo_volta.tratar` devolve `False` na primeira linha, `pendencias.tratar` devolve `False`
   porque não há texto, e o documento desce a corrente do motor até `logos.receber` (`motor.py:805`).
   Nada avisou: o manual e a entrega do #1528 dizem que a volta funciona, e as perguntas dos chamados
   continuaram pedindo "mande o PDF aqui".
2. **A espera é do chamado, não da mensagem.** Às 13:58 nasceu uma pergunta no 1541 (saiu às 14:00).
   Às 13:59 a Fran respondeu "veio o PDF." citando uma mensagem antiga do mesmo chamado; como a
   pendência já estava com `espera = 'resposta'`, o texto foi anotado e a espera fechou. Às 14:23 ela
   deslizou a pergunta de verdade e respondeu; `pendencias.tratar` achou a pendência sem espera,
   gravou `descartada` e disse "Esta mensagem é só um aviso". Às 14:24 ela repetiu, e a segunda
   descartada saiu sem frase nenhuma (`avisou_informativo` já era `true`).

O que ficou pendurado em produção:

- `logos_de_cliente` id 6: o PDF da rescisão, `pergunta_pendente = 'erp_codigo'`. O próximo texto da
  Fran sem citar nada pode ser tomado como nome de cliente (`logos.responder`, `motor.py:792`). **E
  em 24/11/2026 às 15:06 a linha completa 24 h e passa a ser oferecida ao AxiaMarketing como logo
  largada** (`logos.pendentes`, `ABANDONADA`): um termo de rescisão de funcionário iria ao catálogo de
  logos para conferência.
- `pendencias_mensagens` 135 e 136: a resposta do FGTS, `descartada`.
- Chamado 1541: o comentário "(pelo WhatsApp) 1541", que foi a resposta dela à pergunta da logo.

## Os fios que encostam

**Quem escreve `atendimento.pendencias_mensagens`** (medido por grep em `backend/`):
`pendencias.py` (`_entrou`, os toques, `mandar`), `arquivo_volta.py` (`_linha`, `_cabeca`, `entrar`,
`mandar`), `pendencias_erp.py` (`receber`, `levar_arquivos`, a entrega das respostas, o pedido
decidido) e `roteador.py` (a correção escrita). Esta etapa acrescenta um escritor que já existe por
outro ramo: a resposta citada passa a chamar `_anotar_resposta` onde hoje grava `descartada`.

**Quem escreve `atendimento.pendencias.espera`:** `pendencias_erp.receber` (abre, pela classe da
linha do ERP), `pendencias._anotar_resposta`, os toques `pend:ok`, o motivo do "Não ficou bom",
`pendencias.mandar` (7 dias guardada), `pendencias_erp.conferir`, `pendencias_erp.levar_arquivos` e
`roteador.py:473` (desfazer). **Quem lê para decidir:** `pendencias.tratar` (a resposta citada),
`pendencias.oferecer` e `_pendencias_da_pessoa` (o texto sem citar), `arquivo_volta.tratar`,
`roteador.py:116`, `rotas_telas.py:136` e `:365` (a tela). Esta etapa não muda quem escreve a espera
nem o que ela significa.

**Quem volta depois:**
- `pendencias_erp.volta`, a cada 60 s, leva ao ERP toda mensagem `entrou` em `a_entregar`. É por ela
  que a resposta do FGTS recolocada pela limpeza chega ao 1541. No ERP,
  `demandas_whatsapp_service.responder` só exige que o número seja o do autor: **não exige pergunta
  aberta** (lido em 23/11/2026). O comentário acorda o FIO (`acorda_fio=True`).
- `pendencias_erp.conferir` fecha a espera quando o autor comenta depois do evento da pergunta. É o
  que torna inviável, só no AxiaAtende, a regra "resposta a mensagem antiga não fecha a pergunta
  nova": o ERP fecha por conta própria na volta seguinte. Fica fora (ver Escopo).
- `logos.pendentes` (o AxiaMarketing puxa): oferece a logo com o diálogo terminado, ou largada há
  mais de 24 h. É o prazo da limpeza da logo 6.
- `envio.py` manda as linhas de `atendimento.avisos` pelo modelo `aviso_<tipo>`. O aviso novo usa o
  tipo `arquivo_sem_antivirus`, que já está no CHECK e tem modelo cadastrado ("Volta com arquivo:
  {{1}} O detalhe está na tela Envios.", id 21, UTILITY): sem tipo novo, sem modelo novo na Meta.

**Quem escreve `atendimento.logos_de_cliente`:** só `logos.py` (`receber`, `responder`, `puxada`,
`mandar_avisos`). A limpeza escreve uma linha, uma vez.

## O universo medido

Medido em 23/11/2026, produção, papel `axiaatende_ro`:

| Pressuposto | Contagem |
|---|---|
| Textos que citaram uma mensagem de chamado da classe `pergunta` | 6: 4 entregues, **2 descartados** (os dois da Fran, 1541, 23/11) |
| Textos que citaram um `informativo` | 2: 1 entregue, 1 sem linha correspondente. Não mudam nesta etapa |
| Respostas `entrou` por estado, no total | 11 entregues, 9 descartadas, 6 em `escolher` |
| Arquivo ou foto recebidos desde 17/11 10:45 | 4; **1 citava mensagem de chamado** (o PDF de 23/11), e virou logo |
| Linhas `classe = 'arquivo'` desde que a chave foi desligada | 0 (as 3 que existem são de 17/11, antes das 10:45) |
| Perguntas de chamado enviadas com a chave desligada | 7, e as 7 falam em PDF, arquivo, anexo, foto ou print |
| Logos esperando o nome do cliente | 1 (a id 6) |
| Modelo da Meta para o aviso | 1 cadastrado e ativo aqui (`arquivo_sem_antivirus`); em 17/11 estava PENDING na Meta, a conferir no plano |

Nenhum caso que hoje termina bem muda de destino: os 4 textos entregues citavam pergunta com espera
aberta e seguem o mesmo ramo; os 2 descartados passam a entrar.

## Conformidade com o Manual legal

não se aplica: a mudança é do roteamento de mensagens do WhatsApp, sem regra tributária ou legal.

## Conformidade com a casa

não se aplica: nenhum segredo, serviço, porta, tarefa agendada, agente, chamada a modelo de IA, dado
novo ou sessão de agente. O aviso ao dono usa o caminho de avisos que já existe (tabela, tipo e
modelo). A limpeza remove um arquivo que não deveria estar na pasta de logos; nada novo a guardar.

## Decisão

Caminho A (dono, 23/11/2026): os consertos entram direto no código do recepcionista, sem chave nova.
Só mudam casos que hoje terminam em perda, e uma chave a mais repetiria o defeito que originou o
chamado (chave desligada sem ninguém notar).

**D1. Arquivo que cita mensagem de pendência nunca desce a corrente.** Em `arquivo_volta.tratar`,
antes do teste da chave: documento ou foto com `contexto` que é o `wamid` de uma mensagem `saiu` de
pendência deste número é tratado ali, sempre.
- Chave ligada: o caminho de hoje, sem mudança.
- Chave desligada, pendência de chamado: a pessoa ouve *"Não estou recebendo arquivo por aqui agora.
  Anexe no chamado N, no sistema."*, fica uma linha de rastro, e nasce um aviso ao dono (D3).
- Pendência de aprovação (nunca recebe arquivo): a frase de sempre do aviso de aprovação.
Em nenhum dos três o arquivo é baixado.

**D2. Texto que cita uma PERGUNTA de chamado entra sempre no chamado.** No ramo "sem espera" de
`pendencias.tratar`: se a mensagem citada é da classe `pergunta` e a pendência é de chamado, o texto
entra por `_anotar_resposta` ("Anotado no chamado N. ✓") e vai ao ERP como comentário. Citou
`informativo` ou `entrega`: como hoje ("só aviso", uma vez).

**D3. O aviso no sintoma.** Quando D1 recusa por chave desligada, grava-se um aviso
`arquivo_sem_antivirus` ao destino de avisos de sempre, com o texto *"está desligada, e <quem> tentou
mandar um arquivo no chamado N, <hora>. Para ligar: chamado_no_whatsapp.py ligar-arquivo."* No máximo
um por dia (ajuste `pendencias.arquivo_desligada_aviso_em`). Ninguém tentou, nenhum aviso.

**D4. A limpeza de 23/11**, por migração com volta:
- a mensagem 136 (a resposta do FGTS, texto das 14:24) volta a `a_entregar`; a 135 fica `descartada`;
- a logo 6 fecha: `pergunta_pendente = NULL`, `puxada_em = now()`, `resultado` nulo (não é oferecida
  ao marketing nem anunciada a quem mandou), `arquivo = NULL`, `erro = 'nao era logo: PDF devolvido
  ao chamado 1541 (#1722)'`. O arquivo no disco é apagado em passo próprio do plano.
- o PDF **não** vai ao chamado (dono): não é o que a pergunta pedia e levá-lo por fora pularia o
  antivírus e a conferência do ERP.
- um comentário no 1541, pela skill, dizendo que "(pelo WhatsApp) 1541" foi resposta à pergunta da
  logo e que o arquivo não chegou.

## Escopo desta etapa

**DENTRO:** D1 a D4; os testes de D1, D2 e D3; o manual `docs/manuais/chamado-no-whatsapp.md`.

**FORA:**
- A regra do ERP sobre pergunta aberta (`pergunta_aberta`: qualquer comentário do autor depois do
  evento da pergunta a fecha, mesmo escrito antes de a pergunta chegar a ele). Caso raro, é do
  AxiaGestão, e vai em chamado próprio.
- A espera por mensagem (caminho B da segunda pergunta, recusado).
- Descobrir quem desligou a chave em 17/11. Ligar de volta é ato do dono, em janela elevada.
- Painel ou aviso por relógio para a chave desligada (caminhos B e C da terceira pergunta, recusados).

## Impacto em produção

- Serviço afetado: `axiaatende-recepcionista` (restart para o código valer; a migração roda no
  arranque, como as outras). As telas não mudam de código, mas são elas que levam a mensagem 136 ao
  ERP na volta seguinte.
- Dados tocados pela migração: 1 linha de `pendencias_mensagens` (136) e 1 de `logos_de_cliente` (6).
- No ERP: nasce 1 comentário no chamado 1541 em nome da Fran (a resposta do FGTS), que acorda o FIO.
- Sem janela de manutenção. **Prazo:** a logo 6 tem de fechar antes de 24/11/2026 15:06.

## ROLLBACK_PLAN

1. Reverter o commit do código e reiniciar `axiaatende-recepcionista`: o arquivo citado volta a
   descer a corrente e o texto citado volta a ser descartado, como antes.
2. Rodar a `_VOLTA` da migração: a logo 6 volta a `pergunta_pendente = 'erp_codigo'` sem `puxada_em`
   e sem `erro` (o arquivo apagado não volta, e não deve); a mensagem 136, se ainda `a_entregar`,
   volta a `descartada`.
3. O que não se desfaz: o comentário da resposta do FGTS já gravado no 1541 e o comentário
   explicativo. São histórico do chamado e estão corretos.
4. O aviso ao dono para de nascer com o passo 1; o ajuste `pendencias.arquivo_desligada_aviso_em`
   sai na `_VOLTA`.

## Manual de uso

O manual `docs/manuais/chamado-no-whatsapp.md` passa a dizer errado, hoje, que quem desliza uma
mensagem de chamado e manda arquivo sempre tem o arquivo anotado. O que ele passa a dizer:

1. **Para que serve.** Quem recebe uma pergunta de chamado no WhatsApp responde por lá, com texto ou
   arquivo, e a resposta entra no chamado sem abrir o sistema.
2. **Quem usa e quando.** Quem abriu o chamado, quando chega uma pergunta com o rodapé "Para
   responder, deslize esta mensagem para o lado".
3. **O caminho comum.** (1) Deslize a pergunta. (2) Escreva, ou toque no clipe e mande o arquivo.
   (3) Espere o "Anotado no chamado N. ✓".
4. **O que significa cada resposta.**
   - *"Anotado no chamado N. ✓"*: entrou no chamado. Vale também quando a pergunta já tinha sido
     respondida antes: o texto entra do mesmo jeito.
   - *"Esta mensagem é só um aviso"*: você deslizou um aviso ou uma entrega, não uma pergunta. O texto
     não entrou.
   - *"Este chamado não espera resposta: o arquivo não entrou."*: arquivo só entra enquanto a
     pergunta está aberta. Texto entra sempre; arquivo, não.
   - *"Não estou recebendo arquivo por aqui agora. Anexe no chamado N, no sistema."*: a volta com
     arquivo está desligada. O suporte foi avisado; anexe pelo sistema.
5. **O que NÃO faz.** Não aceita arquivo em chamado sem pergunta aberta. Não avisa quando a volta com
   arquivo está desligada se ninguém tentar mandar arquivo. E arquivo mandado **sem deslizar** segue
   as regras de antes (a pergunta "É para o chamado N?", ou foto de campo, ou logo).

Para quem cuida: a seção da chave `pendencias.arquivo_volta` ganha a linha de que, desligada, o
arquivo deslizado recebe a frase acima e gera um aviso por dia ao dono.

## Próximo passo

/writing-plans
