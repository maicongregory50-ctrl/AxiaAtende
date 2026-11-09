# O responsável que muda no ERP chega aos envios já gravados (o caso Ceres)
**Data:** 2026-11-09
**Chamado:** #1285
**Status:** APROVADO

## Contexto

A Ceres (CERES REPRESENTACOES, canal `representante`) se desligou. O dono atende a carteira dela por
hora, e o cadastro de vários clientes já foi trocado no ERP. A pergunta do dono em 09/11/2026 foi se
isso já atualiza o atendimento. Não atualiza, e o motivo está no desenho do envio à carteira (#950):

- **O responsável de cada cliente é gravado em `atendimento.envio_destinatarios` quando o pedido
  nasce** (`envio.receber_pedido`, `backend/envio.py:188-223`), com o que o AxiaMarketing leu do ERP
  naquele dia. O AxiaAtende não relê o ERP depois: a lista de um envio é a lista do dia em que ele
  nasceu (dito na devolução do #1197 e no manual de Envios).
- Cinco lugares leem `responsavel_nome`/`responsavel_whatsapp` **da linha gravada**, e não do ERP:
  o toque em "Falar com meu atendimento" (`envio.falar`, linha 103: abre o WhatsApp gravado, a
  qualquer hora, em mensagem de qualquer data); a cópia ao responsável (449); o resumo do lote ao
  representante (516-525); o aviso de recusa (564); e a **linha do representante do portão da
  carteira** (`linha_do_representante`, 594-602; `motor.portao_do_cliente`, 623-679), que diz ao
  cliente que escreveu nos últimos 30 dias *"Quem cuida de você é Ceres. Fale direto por aqui:
  wa.me/…"*.
- Os resumos de lote **guardados** para o número dela (#1271: esperam o representante escrever) sairiam
  se ela escrevesse ao número da empresa.

O que **já** segue o ERP, sem ajuste: a agenda de quem é da casa (relida todo dia às 06:00,
`agenda.atualizar`), a fila do "Meus clientes" (a cada 10 min, `clientes_erp.copiar_filas`) e todo
envio que o marketing pedir daqui em diante (`envio_whatsapp._responsavel` aplica a regra na hora).

Já existe o molde do ato: `scripts/religar_sem_responsavel.py` (#1197, 29/10/2026) recebe um CSV
com os responsáveis de hoje e devolve à fila quem estava "sem responsável". Ele não troca o
responsável de quem está `aguardando` nem de quem já recebeu, que é o caso de agora.

## Os fios que encostam

**Quem mais escreve `envio_destinatarios.responsavel_nome / responsavel_whatsapp / responsavel_canal`:**
só `envio.receber_pedido` (no nascimento) e `scripts/religar_sem_responsavel.py` (só nas linhas
`sem_responsavel`, à mão). Nenhuma rotina de relógio escreve nelas (`grep -n "responsavel_" backend/`).

**Quem lê para decidir:** os cinco pontos de `backend/envio.py` acima (103, 449, 516, 564, 596);
`rotas_telas.py:365-400` (a tela Envios filtra e lista por `responsavel_nome`); `eventos_erp.montar`
**não** manda o responsável ao ERP (só estados da mensagem), então nada volta ao ERP por este dado.

**Quem volta depois:** `envio.rotina` a cada minuto (lê `aguardando` para o lote, `resposta='quero'`
para as imagens, e os avisos pendentes); `motor.portao_do_cliente` a cada mensagem de cliente;
`envio.falar` a cada toque no link. Todos leem a linha no momento do ato, então **o UPDATE vale a
partir do minuto seguinte, sem restart**.

**`atendimento.avisos`:** `tipo='lote_do_representante'` com `enviado_em IS NULL AND nao_visto_em IS
NULL` para o número antigo são os guardados que ainda sairiam. `nao_visto_em` já é o estado "não sai
mais e não some" (#1188/#1271), e `erro` leva o motivo. Nenhuma coluna nova.

**Fora do AxiaAtende:** o CSV dos responsáveis de hoje é a regra do marketing
(`C:\AxiaMarketing\backend\envio_whatsapp._responsavel`: canal `dono`, `flutuante` ou `corretor` →
nome e WhatsApp do dono; `representante` → o representante; o resto → vazio). Ela **não** é
reescrita aqui: o CSV nasce de um script do marketing que chama essa função.

## O universo medido

- **Cinco** leitores do responsável gravado em `backend/envio.py` (contados por `grep` em 09/11); um
  deles, `falar`, lê em mensagem de **qualquer data** — é o que faz o recorte "só envios ativos"
  ser insuficiente.
- **Dois** escritores: `receber_pedido` e o script do #1197.
- **13** cadastros com a CERES como representante, medidos em 29/10/2026 no `axia_dev` (#1197):
  DISAM (7 cadastros), Agraria, Confiagro, P Bodnar, Conte Zanela. É o teto conhecido de clientes
  afetados; o número de **linhas** de envio com o WhatsApp dela **não foi medido** nesta sessão: o
  banco de produção do AxiaAtende fica atrás do `.env.secrets`, fechado à sessão de desenho. **O
  passo 1 do plano mede**, antes de qualquer escrita.
- **Zero** rotinas de relógio que reescrevem o responsável: a troca só acontece à mão. Este desenho
  **não** cria uma (ver Decisão).

## Conformidade com o Manual legal

não se aplica: dado de atendimento (quem fala com o cliente), nenhuma regra fiscal ou legal.

## Conformidade com a casa

não se aplica: nenhum segredo, serviço, porta, tarefa agendada ou agente novo. Os dois scripts rodam à
mão, em janela elevada, com os segredos que os processos já têm (o do AxiaAtende como o
`religar_sem_responsavel.py` do #1197; o do marketing com a leitura do ERP que ele já faz). Nenhum
dado novo nasce: o CSV "antes" é a reversão e vive em `docs/medicoes`, versionado.

## Decisão

Três caminhos olhados:

**A — Script de reatribuição, à mão (escolhido).** Um script no AxiaMarketing escreve o CSV dos
responsáveis de hoje pela regra que já existe; um script no AxiaAtende lê o CSV, mostra o que mudaria
e, com `--gravar`, regrava as linhas e marca os resumos guardados do número antigo como não vistos.
Reversível pelo CSV "antes" (`--desfazer`). Risco: a próxima saída de representante repete o ato à
mão. Quando escolher: agora, porque o cliente da Ceres está sendo mandado a um número que não atende.

**B — Laço de relógio no processo das telas.** A cada 15 min, ler os responsáveis do ERP e regravar.
Exigiria uma rota nova no ERP para o agente ATENDIMENTO **e** a regra do dono (número do dono) dentro
do AxiaAtende, que hoje mora só no marketing: um terceiro escritor da mesma régua. Moderada de
reverter (chave). Quando escolher: se a troca de responsável virar rotina mensal. Fica como
condição: **na segunda saída de representante em 6 meses**, abrir o chamado do laço.

**C — Não tocar o gravado; só os próximos envios.** Zero código. Deixa o portão apontando para a
Ceres por 30 dias e o botão da direta para sempre. Recusado pelo dono em 09/11 ("temos que ajustar o
atendimento").

**Recorte das linhas que o script regrava** (decisão deste desenho): toda linha cujo responsável no
CSV difere do gravado **e** que ainda decide alguma coisa: (a) envio não encerrado (qualquer
situação da linha), ou (b) `convite_em` nos últimos 30 dias (`Envio.PORTAO_DIAS`), ou (c) envio
`direta` com convite enviado, de qualquer data (o link vive na mensagem). Linha de envio encerrado,
material, com mais de 30 dias **fica como está**: é histórico do que foi mandado por quem. A tela
Envios mostra o responsável da linha, então nas linhas regravadas ela passa a mostrar o de hoje — e
é isso que o dono quer ver.

**A linha `sem_responsavel` que ganhou responsável válido volta a `aguardando`** pela regra do #1197
(consentimento, já recebeu, não é WhatsApp), chamando o que `religar_sem_responsavel.py` já faz, não
copiando.

## Escopo desta etapa

**Dentro:** o script do marketing que gera o CSV; o script do AxiaAtende que mede, regrava e desfaz;
os testes dos dois; a medição em produção antes e depois; a seção do manual de Envios; a devolução.

**Fora:** o laço de relógio (caminho B, com condição); mudar o que o ERP devolve; mexer no
`receber_pedido`; a tela Envios (nenhuma coluna nova); a desativação da Ceres no cadastro do ERP e
na tela Destinos (mão do dono, listada no plano); o histórico de envios encerrados.

## Impacto em produção

- `atendimento.envio_destinatarios`: UPDATE de `responsavel_nome`, `responsavel_whatsapp`,
  `responsavel_canal` (e `situacao` de `sem_responsavel` para `aguardando`) nas linhas do recorte.
- `atendimento.avisos`: `nao_visto_em` e `erro` nos resumos guardados do número antigo.
- Nenhum restart: `rotina`, `portao_do_cliente` e `falar` leem a linha no ato.
- Janela: qualquer hora fora das 9h30-17h de dia útil evita cruzar com o lote do dia; não é exigência,
  o UPDATE é por linha e o lote lê `aguardando` por linha.

## ROLLBACK_PLAN

1. `python scripts/reatribuir_responsavel.py --desfazer docs/medicoes/2026-11-09-1285-antes.csv --gravar`
   (janela elevada, `AXIAATENDE_AMBIENTE=producao`): devolve nome, WhatsApp, canal e situação de cada
   linha pelo id, e limpa `nao_visto_em`/`erro` dos avisos que o script marcou (ele grava os ids no
   mesmo CSV).
2. Conferir: `SELECT count(*) FROM atendimento.envio_destinatarios WHERE responsavel_whatsapp = '<número antigo>'`
   volta ao número do passo 1 do plano.
3. Os scripts são arquivos novos: `git revert` do commit os tira. Nada no caminho do envio depende deles.

## Manual de uso

Vai em `docs/manuais/envios.md`, seção nova **"Quando o responsável muda no ERP"**, para quem cuida
do sistema (não é tela: é procedimento), e corrige a frase do mesmo manual que hoje diz que corrigir o
cadastro só vale para os próximos envios.

1. **Para que serve.** Quando um representante sai ou um cliente muda de mão no ERP, os envios já
   criados continuam apontando para quem atendia antes: o botão "Falar com meu atendimento", o aviso
   de recusa, o resumo do lote e a frase "Quem cuida de você é…" que o cliente recebe ao escrever.
   Este procedimento faz o atendimento seguir o cadastro de hoje.
2. **Quem usa e quando.** Quem cuida do sistema, no dia em que o cadastro do ERP foi trocado. Antes,
   o cadastro: a tela Stakeholders → **Sem responsável** não pode listar os clientes trocados.
3. **O caminho comum.** (1) No AxiaMarketing, gerar a lista de hoje:
   `python scripts/responsaveis_de_hoje.py > C:\Temp\responsaveis.csv`. (2) No AxiaAtende, ver o
   que mudaria: `python scripts/reatribuir_responsavel.py C:\Temp\responsaveis.csv --antes
   docs\medicoes\AAAA-MM-DD-antes.csv`. (3) Conferir a lista na tela (cliente, envio, de quem para
   quem). (4) Gravar: o mesmo comando com `--gravar`. (5) Na tela Envios, filtrar pelo responsável
   novo: as linhas aparecem com ele.
4. **O que significa cada sinal.** *"muda: X → Y"*: a linha será regravada. *"fica: envio encerrado
   há mais de 30 dias"*: histórico, não muda. *"volta à fila"*: estava sem responsável e agora tem.
   *"fica fora: recusou / já recebeu / não é WhatsApp"*: ganhou responsável mas não recebe, pelas
   travas de sempre. *"N resumos guardados do número antigo não saem mais"*: os avisos pendentes do
   representante que saiu foram marcados como não vistos.
5. **O que NÃO faz.** Não muda o cadastro do ERP (é lá que se corrige). Não reenvia nada a ninguém.
   Não cria envio. Não avisa o cliente de que trocou de atendente: a frase nova sai quando ele
   escrever de novo. Não tira o número antigo da tela Destinos nem da agenda da casa: isso é o
   cadastro do ERP (a agenda relê às 06:00) e a tela Destinos, à mão.

## Próximo passo

/writing-plans
