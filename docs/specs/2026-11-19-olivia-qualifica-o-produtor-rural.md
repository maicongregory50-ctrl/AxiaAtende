# A OlivIA qualifica o produtor rural e entrega a ficha a quem atende (piloto SC e RS)
**Data:** 2026-11-19
**Chamado:** #1660
**Status:** APROVADO

## Contexto

Desde 18/11/2026 (#1589) a OlivIA, na conversa de quem quer comprar, só recebe e direciona: diz "temos"
ou "não temos", oferece indicar o representante, pergunta a categoria e o estado, apresenta quem atende
e entrega o cartão. Ninguém é avisado e nada do que a pessoa disse chega ao representante. Na conversa
do produtor de Xanxerê (18/11, 20:35) o cartão saiu em um minuto e o representante recebeu um contato
vazio.

O dono quer o degrau seguinte da escada de vendas: **qualificar**. Nas palavras dele (19/11/2026):
"pegar um nicho específico", "fazer essa qualificação antes", "disparar para mim no meu WhatsApp essa
ficha", "um resumozinho da conversa e um link", e a OlivIA dizer ao produtor que o vendedor "está
recebendo um briefing" e entregar o cartão. Ele atende, devolve como foi, e as etapas seguintes são
desenhadas em cima dos casos reais. O produtor foi escolhido por ser o mais difícil: "o produtor vai
exigir o atendimento técnico".

Pesquisa de 19/11/2026 (blogs de fornecedores, não estudo independente): em chat a recomendação comum é
quatro perguntas ou menos; do BANT servem aqui necessidade e prazo.

## Os fios que encostam

**Quem mais escreve o que a mudança escreve**

- `atendimento.leads` (tabela NOVA): só as duas ferramentas novas da OlivIA escrevem. Ninguém mais.
- `atendimento.conversas` (`situacao`, `destino_id`, `link_em`, `pergunta_em`): o cartão continua saindo
  por `motor.escolher`, o mesmo caminho do toque no menu e do `passar_contato` de hoje. Nenhuma coluna
  ganha escritor novo.
- `atendimento.enviadas`: a ficha mandada ao representante ganha uma linha, com `para` = o número dele,
  como já fazem os avisos (`envio._aviso_como_texto`) e a candidatura à Fran.
- `atendimento.menu.destino_id` das folhas `comercial.produtor.sc` e `comercial.produtor.rs`: quem
  escreve é a tela Destinos (em produção a SC está no Djeison e o RS no dono; a instalação nasceu
  diferente e foi trocada pela tela). **Esta etapa não escreve aí**: a troca da SC para o dono é dele, na
  tela (passo de mão).

**Quem lê para decidir**

- `olivia.travou`: fora da conversa de vaga, conta as falas dela sem toque de botão e, a partir de
  `FALAS_SEM_AVANCO`, marca a conversa como travada (e na segunda vez forte manda o menu e ela se cala).
  Quatro perguntas respondidas por texto são quatro falas sem toque: **a qualificação seria lida como
  conversa travada**. A conversa com lead em curso precisa ficar fora dessa contagem, como já ficam a
  ficha da vaga (`conversa.ficha`) e a conversa de vaga (#1543).
- `olivia.fechar_dia` (o vigia): lê `situacao`/`saida` para dizer se a conversa terminou bem. Com o
  cartão entregue ela já conta como bem; o vigia passa a contar também os leads do dia e os incompletos.
- `envio.janela_aberta` (fonte: `eventos_meta`): decide se a ficha vai como texto livre ou pelo modelo.
  Lê as mensagens que o representante mandou ao número da empresa; a ficha não muda essa leitura.
- `olivia.promessa_sem_candidatura`: só olha conversa de vaga; a frase "anotei tudo" na venda não passa
  por ela. A trava equivalente desta etapa é nova (ver Decisão, D6).

**Quem volta depois**

- A pesquisa das 4h30 ("você recebeu o atendimento que precisava?") continua indo ao produtor, marcada
  por `motor.escolher`. Nada muda.
- `vaga.limpar` apaga ficha e rascunho de candidato depois de 12 meses. O lead ganha a mesma regra, na
  mesma rotina.
- O backup do banco do atendimento (`rotina:backup-axiaatende-banco` e `-nuvem`) leva a tabela nova sem
  mudança: é o banco inteiro.

## O universo medido

Medido em 19/11/2026, pelo papel de leitura, últimos 30 dias:

- Conversas que terminaram numa folha do Comercial: 17. Por folha: produtor SC 5, revenda SC 2, produtor
  PR Cascavel 2, Comercial (sem folha) 2, produtor RS 1, corretor 1, produtor SP 1, revenda outro 1,
  produtor outro 1, revenda RS 1.
- **O nicho do piloto (produtor SC e RS): 6 conversas em 30 dias.** Duas das de SC e a do RS já foram
  conduzidas pela OlivIA.
- Conversas de fora sem número de telefone (`wa_id` nulo): **0 de 318**. O link para o representante
  tocar existe sempre.
- A janela do dono (554991505565): ele escreveu ao número da empresa em **11 dos últimos 14 dias**. A
  ficha completa, por texto livre, será a regra.
- Modelos aprovados que servem fora da janela, sem aprovação nova: `olivia_resumo` (uso
  `aviso_olivia_resumo`, UTILITY, uma variável: "Resumo da OlivIA: {{1}} O detalhe está na tela
  Recepção."). Não há modelo de lead.
- Destino das folhas hoje: `comercial.produtor.sc` = Djeison de Oliveira; `comercial.produtor.rs` =
  Maicon Gregory.

## Conformidade com o Manual legal

Não se aplica: nenhum imposto, código fiscal, texto legal impresso ou régua fiscal é tocado.

## Conformidade com a casa

- **R7 (agentes de IA): muda.** Trecho lido: "a política nomeia o provedor como parte (o que vai ao
  modelo é processado e guardado por ele) e classifica o dado em cinco classes; cada uso de IA de
  `design\agentes.json` diz o provedor e a classe mais alta que manda". A OlivIA ganha um modo
  (qualificar o produtor) e duas ferramentas, e passa a mandar mensagem a um interno por conta própria.
  A linha `olivia-anonima` de `C:\AxiaSecurity\design\agentes.json` e a regra da venda em
  `docs\governanca\politica-uso-ia.md` mudam no mesmo plano, com o inventário regravado. O dado que vai
  ao modelo é o mesmo de hoje (a conversa da pessoa de fora); a classe não sobe.
- **R2 (dado vivo com cópia): conforme.** Trecho lido: a prova mecânica lista
  `rotina:backup-axiaatende-banco` e `rotina:backup-axiaatende-banco-nuvem`. A tabela nova mora no banco
  do atendimento, que essas rotinas já copiam inteiro.
- **R3, R4, R9: não tocadas.** Nenhum segredo novo, nenhuma porta ou serviço novo, nenhum processo que
  hospeda sessão de agente.

## Decisão

Caminho A (dono, 19/11/2026): as perguntas, a ficha guardada, o envio ao representante e uma chave. Sem
classificação de lead e sem tela, que ficam para depois de umas dez fichas reais.

- **D1. O nicho.** Produtor rural de **SC e do RS** (dono: "b"). Revenda, corretor e produtor de outros
  estados continuam como no #1589. Os estados do piloto ficam num ajuste
  (`olivia.qualifica_estados`, nasce `["SC", "RS"]`), para ampliar sem código.
- **D2. Quem recebe.** O cartão e a ficha vão para a mesma pessoa: o destino da folha
  (`comercial.produtor.<uf>`). No piloto é o dono nos dois estados; a troca da SC é dele, na tela
  Destinos. A ficha segue o destino da folha: quem trocar o destino depois troca quem recebe a ficha.
- **D3. As perguntas, antes do cartão** (dono: "perguntar antes"). Depois do "temos" e de saber que é
  produtor de SC ou RS, ela pede licença ("para o nosso consultor já te atender sabendo do que você
  precisa, posso te fazer quatro perguntas rápidas?") e pergunta, uma por mensagem, só o que ainda não
  foi dito: (1) qual semente e para quê (cobertura, pastagem, grão); (2) a área ou a quantidade;
  (3) quando pretende plantar; (4) o município. O nome continua valendo como hoje.
- **D4. Quem não quer responder** (dono: "A"). Disse "só quero o contato", ignorou uma pergunta ou
  mostrou pressa: o cartão sai na hora e a ficha vai com o que houver, marcada **incompleta**, dizendo o
  que faltou. Ela não insiste.
- **D5. A ficha ao representante.** Vai ao WhatsApp dele, mandada pelo código, **antes** da fala final
  dela. Dentro da janela de 24 h dele: texto livre com o nome, as quatro respostas (ou "não disse"), um
  resumo de até duas linhas da conversa escrito por ela, e o link `wa.me` do produtor. Fora da janela
  (dono: "a"): o modelo `olivia_resumo`, com tudo numa linha e o telefone do produtor escrito. Um modelo
  próprio, com botão de conversar, fica para depois.
- **D6. O que ela diz ao produtor acompanha o que aconteceu.** A ferramenta que fecha o lead devolve se a
  ficha SAIU. Saiu: "anotei tudo; o nosso consultor <nome> está recebendo agora o resumo da nossa
  conversa. Segue o contato dele; se quiser dar uns 5 minutinhos, ele já vai saber do que tratamos."
  Não saiu: ela apresenta quem atende e entrega o cartão, sem dizer que ele foi avisado. A regra 26 do
  #1589 ("não diga que avisou") ganha esta única exceção. **Trava no código, não só instrução:** fala
  que afirma que o representante foi avisado, numa conversa sem ficha enviada, é trocada pela frase de
  apresentação simples (o molde é `promessa_sem_candidatura`).
- **D7. A apresentação garantida.** Se o cartão sair sem fala dela na mesma resposta (aconteceu em
  19/11, 09:30, conversa de Cacequi), o código manda a frase de apresentação antes do cartão. Vale para
  toda a venda, não só para o piloto.
- **D8. A chave.** `olivia.qualifica_produtor` (ajuste no banco, nasce `false`), ligada e desligada por
  `scripts\olivia.py ligar-qualifica` / `desligar-qualifica`, sem reinício. Só vale com
  `olivia.conduz_venda` ligada. O `/saude` a publica.
- **D9. A conversa de qualificação não é conversa travada.** Com lead em curso, `travou` só considera o
  "não é isso" e a repetição de mensagem longa, como na vaga.
- **D10. Guarda e apagamento.** A ficha fica em `atendimento.leads` e é apagada depois de 12 meses, na
  rotina que já apaga a ficha do candidato.

## Escopo desta etapa

**Dentro:** a tabela `atendimento.leads` e a chave (migração); as ferramentas `anotar_lead` e
`fechar_lead` (oferecidas só com a chave ligada, fora da conversa de vaga); as regras do modo de
qualificação na instrução; o envio da ficha (texto na janela, `olivia_resumo` fora); a trava de D6 e a
apresentação garantida de D7; a exceção em `travou`; o vigia do dia contando leads; o apagamento em 12
meses; `/saude`; `scripts\olivia.py`; testes; manual; a governança (R7).

**Fora:** classificar o lead (quente, morno, frio); tela de leads; modelo próprio na Meta; avisar o
Djeison ou qualquer outro representante além do destino da folha; revenda, corretor e outros estados;
responder dúvida técnica além do que o #1589 já permite; preço, estoque e negociação; o retorno do
representante ("como foi") dentro do sistema, que por ora o dono traz à sessão.

## Impacto em produção

- Serviço: `axiaatende-recepcionista` (o código da OlivIA) e `axiaatende-backend` (aplica a migração).
  Um reinício de cada, pela Porta-Ação.
- Dados: tabela nova, vazia; um ajuste novo, desligado. Nada existente muda de valor.
- Enquanto a chave estiver desligada, o comportamento é o de hoje, mais a apresentação garantida (D7).
- Custo: a ficha fora da janela é um modelo UTILITY pago, um por lead; pelo medido, minoria dos casos.
- Sem janela de manutenção.

## ROLLBACK_PLAN

1. Desligar o piloto, sem reinício: `scripts\olivia.py desligar-qualifica`. Ela volta a receber e
   direcionar; as fichas já guardadas ficam.
2. Se a SC foi passada ao dono na tela Destinos e for o caso de voltar: a mesma tela, destino Djeison.
3. Desfazer o código: `git revert` dos commits do #1660 e reinício do recepcionista pela Porta-Ação.
4. Desfazer o banco: a `_VOLTA` da migração apaga a tabela `atendimento.leads` e o ajuste. Só depois do
   passo 3, e sabendo que as fichas guardadas se perdem.

## Manual de uso

**Para que serve.** O produtor rural de SC e do RS que procura semente pelo WhatsApp passa a responder
quatro perguntas rápidas antes de receber o contato do consultor, e o consultor recebe no próprio
WhatsApp um resumo do que foi conversado, com o link para falar com o produtor.

**Quem usa e quando.** O consultor que atende a região (no piloto, o dono), toda vez que a OlivIA fecha
uma conversa com um produtor desses estados. Não há tela: tudo chega no WhatsApp.

**O caminho comum.**
1. Chega no seu WhatsApp, do número da empresa, uma mensagem "Lead da OlivIA" com o nome do produtor, o
   que ele procura e para quê, a área ou a quantidade, quando planta, o município, duas linhas de resumo
   e um link.
2. Toque no link para abrir a conversa com o produtor. Ele também recebeu o seu cartão e pode chamar
   antes.
3. Atenda. Depois, conte na sessão como foi (um print serve): é com isso que as próximas etapas são
   desenhadas.

**O que significa cada sinal.**
- **"Ficha incompleta: faltou ..."**: o produtor teve pressa ou não respondeu; o cartão saiu assim mesmo.
- **"não disse"** ao lado de uma pergunta: ela não perguntou de novo, de propósito.
- **Mensagem de uma linha começando com "Resumo da OlivIA: Lead ..."**: você estava há mais de 24 horas
  sem escrever ao número da empresa, e a ficha veio pelo modelo curto, com o telefone escrito em vez do
  link. Escrever qualquer coisa ao número reabre a forma completa para as próximas.
- **Nenhuma ficha, e o produtor te chamou pelo cartão**: o envio falhou. Ele não ouviu que você tinha
  sido avisado; a falha está no registro e aparece na análise do atendimento.

**O que isto NÃO faz.** Não classifica o produtor, não responde preço, estoque nem prazo, não agenda
nada e não avisa outro representante. Não vale para revenda, corretor nem para produtor de outros
estados. Não substitui a sua conversa com ele.

**Como ligar e desligar.** `scripts\olivia.py ligar-qualifica` e `desligar-qualifica`, sem reinício. O
`/saude` mostra `olivia_qualifica`.

O que o manual `docs\manuais\olivia.md` passa a dizer errado: "não guarda ficha de quem quer comprar e
não avisa o representante" e "não avisa o representante: quem chama é a pessoa, pelo cartão" deixam de
valer para o produtor de SC e RS com a chave ligada.

## Próximo passo

`/writing-plans`
