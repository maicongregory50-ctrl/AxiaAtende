# A fila de envio por número, o papel do contato, e o resumo ao representante no lugar da cópia
**Data:** 2026-10-26
**Chamado:** #1142
**Status:** APROVADO
**Pedido por:** `C:\AxiaMarketing\docs\specs\2026-10-26-cinco-publicos-criacao-e-publicacao.md` (#1103, APROVADA, caminho B do dono). O par deste chamado no ERP é o #1141, já no ar.

## Contexto

A campanha do marketing passou a falar com cinco públicos (#1103), e o ERP passou a entregar **uma
linha por contato** do cliente, com o papel — comprador ou técnico (#1141, no ar em 26/10). Duas
coisas daqui não acompanham isso.

**A fila é por CADASTRO.** `envio_destinatarios` tem `UNIQUE (envio_id, erp_codigo)`, então dois
contatos do mesmo cadastro no mesmo envio: o segundo é **descartado em silêncio** (o `INSERT` tem
`ON CONFLICT ... DO NOTHING`). O caso que isso quebra é a **cooperativa**, onde o comprador e o
departamento técnico recebem na mesma semana e a lista do marketing não separa por papel.

**A cópia ao responsável.** Cada convite de cada lote gera uma cópia ao responsável do cliente, com
os botões trocados por `envio:<id>:copia`, que `tratar_toque` ignora. No material às revendas o
responsável é **o dono** (o marketing o põe como responsável de toda revenda, porque "as parceiras
são relação do dono"), e foi assim que as artes da Agro Real e da Agro Símil chegaram ao WhatsApp
dele. Em 23/10 ele pediu que isso acabasse.

**E o manual já promete o contrário do que o código faz.** `docs/manuais/envios.md`, na seção "O que
ela não faz": *"Não avisa o responsável de quem quis receber: só de quem recusou."* A cópia nunca
entrou no manual — o código divergiu do que está escrito, e ninguém leu os dois lado a lado.

## Os fios que encostam

**Quem escreve a fila.** `envio.receber_pedido` (o único; chamado por `rotas_pedido` quando o
marketing entrega o pedido aprovado). Ele classifica cada destinatário na chegada — `sem_whatsapp`,
`sem_responsavel`, `recusou_antes`, `sem_aceite`, `ja_recebeu`, `nao_e_whatsapp`, `aguardando` — e
essa classificação **não muda** nesta etapa.

**Quem já é por NÚMERO, e continua.** `_ultimo_consentimento(numero)`, `_ja_recebeu(numero, peca)`,
`_nao_e_whatsapp(numero)`, `tratar_toque` (`WHERE envio_id = %s AND whatsapp = %s`) e
`atendimento.consentimentos` (chaveado por `whatsapp` e `bsuid`). A unicidade por cadastro era a
única peça fora dessa régua.

**Quem manda a cópia.** `Envio._copias_aos_responsaveis`, chamada no fim de `mandar_lotes`, uma vez
por responsável por envio (`vistos`), gravando `resumo = 'copia <envio_id>'` em
`atendimento.enviadas` para não repetir. `codigo_falar(..., copia=True)` e `ler_codigo` tratam o
código do link do responsável — e **continuam**, porque há mensagens com esse botão na rua.

**Quem avisa hoje, e é o molde do resumo.** `atendimento.avisos` (tipo, para_nome, para_whatsapp,
`sobre` com até três partes separadas por `|`, enviado_em, wamid, erro) e
`Envio.mandar_avisos`, que lê `modelo_do_uso(con, "aviso_" + tipo)` e manda até 20 por volta. É
assim que o aviso de recusa e os cinco outros avisos saem, e o resumo entra por esse caminho — não
por um caminho novo.

**Quem lê para decidir.** `eventos_erp.montar` (o que vai ao ERP a cada 15 min: `destinatario_id`,
`erp_codigo`, situação, as datas e a resposta) — o ERP passou a aceitar `papel` no evento (#1141), e
o campo fica nulo até sair daqui. A tela **Envios** (`rotas_telas`) e o manual dela.

**Quem volta depois.** A rotina do recepcionista a cada minuto (lotes de até 20 por dia, só com a
nota do número em verde); `eventos_erp.empurrar` a cada 15 min; e o job do ERP que lê os eventos.

## O universo medido

Lido em 26/10/2026, no código e no banco de **desenvolvimento** (porta 5437). **O banco de produção
(5436) não foi medido: ele pede o segredo, e a sessão de agente não o lê** — por isso a conferência
da unicidade nova vive DENTRO da migração, e diz o número quando o dono a aplica.

| O que | No dev |
|---|---|
| Envios | 1 |
| Destinatários | 5 |
| O mesmo número duas vezes no mesmo envio | **nenhum** |
| Mais de um destinatário sem número no mesmo envio | **nenhum** |
| Cópias já mandadas (`enviadas.resumo LIKE 'copia %'`) | 2 |
| Avisos por tipo | `sem_atendimento`: 1 |
| Modelos cadastrados | 8 (2 de envio, 6 de aviso) |
| Última migração | 032 (a 031 está reservada ao #1097) |

Em produção, a spec do #1103 mediu: **5 envios** entregues (envio:1 a 5, do #1113) e **11 clientes**
cuja cópia da direta iria ao dono (canal dono ou flutuante).

Não medido, e é a primeira medição do plano: se há, em produção, dois destinatários do mesmo envio
com o mesmo número — o que a unicidade nova recusaria.

## Conformidade com a casa

- **R2 (dado vivo tem cópia): conforme.** `papel` e `responsavel_canal` nascem no banco
  `axiaatende`, coberto por `backup_axiaatende_banco.ps1` (02:20) e
  `backup_cloud_axiaatende_banco.ps1` (02:45, cifrado).
- **R7 (agentes e IA): não se aplica.** Nenhum agente, nenhuma chamada de modelo nova. A IA do
  recepcionista não é tocada.
- **R4/R1 (serviço, porta, rede): não se aplica.** Nenhum processo, porta ou exposição nova. O
  pedido continua chegando pela porta local com a chave que já existe.
- **A regra 1 deste projeto (nada que arrisque o número na Meta): respeitada e é o ponto de atenção.**
  O resumo é **mensagem nova**, e toda mensagem fora da janela de 24 h é por modelo aprovado. Ele é
  **UTILITY** (regra 6: aviso interno é Utilidade), vai só a quem trabalha aqui, e **substitui** uma
  mensagem por cliente por uma por representante por lote — o volume de mensagens pagas **cai**.
  Aprovar o modelo na Meta é da mão do dono.
- **A regra 4 (consentimento não se apaga): intocada.** `atendimento.consentimentos` não é lida nem
  escrita de forma diferente, e o rollback não a toca.
- **Cria:** nada que a carta não cubra.

## Conformidade com o Manual legal

Não se aplica: atendimento e relacionamento comercial, sem imposto, código fiscal ou documento
fiscal. O resumo ao representante é mensagem **interna**, a quem trabalha na casa — não é marketing
a cliente, e não depende de aceite de cliente nenhum.

## Decisão

**(a) A fila passa a ser por NÚMERO.** `UNIQUE (envio_id, erp_codigo)` sai; entra
`UNIQUE (envio_id, whatsapp) WHERE whatsapp <> ''` — **parcial de propósito**: o destinatário sem
celular válido grava `whatsapp = ''`, e sem o `WHERE` dois deles colidiriam no mesmo envio, que é um
caso real e legítimo (`sem_whatsapp`). "Uma pessoa uma vez por envio" passa a ser garantia do banco,
e não cortesia de quem monta o pedido.

**(b) O destinatário diz o PAPEL e o CANAL do responsável.** `papel` (comprador | tecnico; nulo = o
que o pedido de antes manda) viaja do pedido ao evento do ERP. `responsavel_canal` (representante |
corretor | dono | flutuante) é o que decide a quem o resumo vai — **o AxiaAtende não sabe quem é o
dono** (não há número dele no config daqui), então quem diz é o marketing, que já tem o dado.

**(c) A cópia por cliente sai; entra UM RESUMO POR LOTE, só ao representante** (decisão do dono,
26/10/2026). Depois de um lote sair, um aviso por responsável de canal `representante` ou
`corretor`, pelo caminho que já existe (`atendimento.avisos` + `mandar_avisos`), com o tipo
`lote_do_representante` e o modelo `aviso_lote_do_representante` (UTILITY, sem imagem e sem botão).
**Nunca ao dono nem ao flutuante.** O texto diz quantos clientes dele receberam, o que receberam, e
que o acompanhamento é no Relacionamento do ERP — que é a tela dele; a tela Envios daqui roda em
`127.0.0.1:8009` e ele não a alcança.

O guarda de `envio:<id>:copia` em `tratar_toque` **fica**: há mensagens com esse botão na rua, e
tirar o guarda só acrescentaria risco.

**(d) O manual passa a dizer a verdade.** A linha "Não avisa o responsável de quem quis receber: só
de quem recusou" deixa de ser falsa por omissão e ganha o resumo ao lado.

## Escopo desta etapa

DENTRO (AxiaAtende): a migração 033 (o `papel`, o `responsavel_canal`, a unicidade por número, os
dois CHECK e a linha do modelo novo); `receber_pedido` gravando os dois campos e com o `ON CONFLICT`
por número; `_copias_aos_responsaveis` fora e `_resumo_ao_representante` dentro; `eventos_erp.montar`
mandando o papel; o manual `envios.md` e a linha dele no `INDICE.md` se mudar.

DENTRO (AxiaMarketing, uma linha em cada pedido): `envio_whatsapp.pedido_direta` e `pedido_material`
passam a mandar `papel` e `responsavel_canal` por cliente. **Sem isso o resumo nunca sai e o papel
nunca chega ao ERP** — por isso está dentro, e não num chamado à parte.

FORA: o texto final do modelo na Meta (é do dono, no Business Manager, e a linha do banco nasce com
o texto proposto); mudar a classificação do destinatário na chegada; o lote de 20 por dia, que não
muda; e a tela Envios, que já mostra o que precisa.

## Impacto em produção

Migração 033 (acréscimo, mais a troca de uma unicidade), backend das telas e do recepcionista,
frontend só se o manual pedir. **O AxiaAtende não está no catálogo da Porta-Ação**: a migração e o
restart são da mão do dono. No marketing, duas linhas e um restart do backend. Nenhum dado é
apagado: os 5 envios, os destinatários, os consentimentos e os avisos ficam como estão.

## ROLLBACK_PLAN

1. AxiaAtende: `git revert`; `033_*_VOLTA.sql` (devolve `UNIQUE (envio_id, erp_codigo)`, derruba
   `papel` e `responsavel_canal`, tira o tipo e o uso novos e a linha do modelo); reiniciar
   `axiaatende-backend` e `axiaatende-recepcionista`. **Antes da VOLTA**, se já houver dois
   destinatários do mesmo envio com o mesmo cadastro, a unicidade antiga não cabe: a VOLTA os conta
   e recusa com o número, em vez de falhar no meio.
2. Marketing: `git revert` das duas linhas; reiniciar o backend. O pedido volta a não mandar os dois
   campos, e o Atende os grava como nulos — a fila continua funcionando.
3. **O consentimento não se toca em nenhum dos dois sentidos** (regra 4).
4. Os avisos de `lote_do_representante` já gravados ficam na tabela; sem o tipo no CHECK, a VOLTA os
   apaga — e é por isso que ela os conta e diz quantos, antes.

## Manual de uso

**AxiaAtende › Envios (atualiza `docs/manuais/envios.md`)**
- *O que muda:* a linha de cada destinatário passa a dizer **quem é** no cliente — o comprador ou o
  técnico. Dois contatos do mesmo cliente podem estar no mesmo envio (é o caso da cooperativa), e
  cada um conta como um destinatário, com o lote e a resposta dele.
- *O que acaba:* a cópia de cada convite ao responsável. Ela não estava no manual, e o manual já
  dizia que o responsável só é avisado de quem **recusou** — agora é verdade.
- *O que entra:* **um resumo por lote ao representante** (não ao dono): quantos clientes dele
  receberam, o que receberam, e o lembrete de que o acompanhamento é no Relacionamento do ERP.
- *Sinais:* "sem responsável" continua querendo dizer que o canal comercial do cadastro está vazio
  no ERP. O mesmo número duas vezes no mesmo envio **não entra duas vezes** — o banco recusa, e
  quem monta o pedido já junta por número.
- *Não faz:* não avisa o representante de quem **quis** receber (só o resumo do lote e a recusa);
  não manda nada ao dono; não muda o lote de 20 por dia.

## Próximo passo

/writing-plans
