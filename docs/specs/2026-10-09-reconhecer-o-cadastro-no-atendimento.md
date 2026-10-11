# Reconhecer o cadastro no atendimento
**Data:** 2026-10-09
**Chamado:** #969
**Status:** APROVADO

Primeira etapa do #969 (evolução do atendimento, escopo amplo). Maquete aprovada pelo dono em
09/10/2026: `docs/specs/2026-10-09-reconhecer-cliente-maquete/1-recepcao.png` ("pode fechar assim,
ficou boa").

## Contexto

O atendimento do WhatsApp da empresa (49 3664 0121) está no ar desde 09/10/2026 (#950). Ele não
sabe quem é quem: a Recepção mostra o número e o nome do perfil do WhatsApp. A coluna
`atendimento.conversas.erp_codigo` existe desde a migração 001 e ninguém a preenche.

O dono quer **começar a reconhecer, sem ainda tratar diferente**: quando quem chama já está no
cadastro do ERP, gravar a ligação (qual cadastro, que papel, por qual contato chegou) e mostrar na
Recepção, "para a gente ir olhando quem está ali". O jeito de tratar (saudação, atalho para o
responsável, aviso ao representante) vem numa etapa seguinte.

Decisão do dono: reconhecer **todos os cadastros**, não só clientes. A equipe interna
(representante, qualidade, produção) também: há um chamado nascendo de stories em que a equipe
manda imagem pelo WhatsApp, e reconhecer quem é da equipe é a base dele. "Uma coisa é ter a
ferramenta, outra é fazer a equipe usar", então aqui só se registra.

## Os fios que encostam

**Quem escreve o que esta etapa escreve:**
- `atendimento.conversas` (AxiaAtende): só o recepcionista (`backend/motor.py`, `_nova_conversa`).
  As colunas novas são gravadas por ele, na criação da conversa, e por ninguém mais.
- `atendimento.agenda` (tabela nova, AxiaAtende): só a leitura diária do ERP, pelo serviço das
  telas (`axiaatende-backend`, LocalSystem, que lê o `.env.secrets`). O recepcionista só lê.
- No ERP **nada é escrito** pela rotina: a leitura é um `GET` novo, com um agente novo
  (`ATENDIMENTO`, só `STK.R`). A fase cria o usuário e o perfil, no molde da fase 546 (agente
  MARKETING).

**Quem lê para decidir:** ninguém, nesta etapa. O motor não muda de caminho por causa do
reconhecimento (decisão do dono). Só a tela Recepção lê.

**Quem escreve os dados de origem no ERP** (e, portanto, muda o que se reconhece):
- `axia.stakeholders_contatos` (setor, nome, telefone, `saida_em`): a tela de cadastro e o mutirão
  do #952/#967, que está acontecendo agora;
- `axia.stakeholders.whatsapp_comercial` e `whatsapp_fiscal`: a tela de cadastro;
- os papéis: `stakeholders_cliente`, `_fornecedor`, `_produtor`, `_comercial` e `axia.colaboradores`
  (`data_desligamento`).

**Quem volta depois:** a leitura diária (06:00 e a cada vez que o serviço das telas sobe) refaz a
agenda inteira. A conversa guarda o retrato do momento em que chegou: se o cadastro mudar depois,
a conversa antiga continua mostrando o que era verdade quando ela chegou. Nada mais revisita.

**O que a leitura do ERP NÃO traz, de propósito:** valor, crédito, salário, cargo, CPF/CNPJ,
endereço. Só número, código, nome, papéis e o contato (setor e nome). `colaboradores` tem salário:
dele sai só "existe e está ativo".

## O universo medido

Medido no ERP em 09/10/2026 (leitura `axia_dev`), contando celular válido (55 + DDD + 9 + oito
dígitos) em `stakeholders_contatos` (sem `saida_em`), `whatsapp_comercial` e `whatsapp_fiscal`:

| Papel | No cadastro | Com celular válido (reconhecíveis hoje) |
|---|---|---|
| Clientes | 1.115 | 443 |
| Fornecedores | 2.827 | 681 |
| Produtores | 30 | 21 |
| Representantes (`stakeholders_comercial`) | 8 | 6 |
| Equipe (colaboradores ativos) | 11 | 7 |
| Qualquer cadastro | 3.278 | 884 |

- 862 celulares distintos; **23 aparecem em mais de um cadastro** (viram "número em N cadastros",
  sem escolher um).
- Contatos por setor: COMERCIAL 2.164 (893 marcados WhatsApp), FINANCEIRO 33 (28).
- Dos seis atendentes do menu, **só dois** (Maicon e Djeison) são reconhecidos pelo número: Willian,
  Fran, Alisson e Benedito não têm o celular no cadastro deles. É cadastro, não código.
- A Meta manda o celular brasileiro **sem o 9** (554991505565, medido no #950): a comparação passa
  pelo `com_nove`.

## Conformidade com o Manual legal

Não se aplica: nada tributário, fiscal ou de texto legal. O dado pessoal (número de telefone) já
está no ERP e passa a ter uma cópia no banco do atendimento, que tem backup cifrado na nuvem (G6 do
#950).

## Decisão

1. **ERP:** fase nova com o agente `ATENDIMENTO` (perfil `AGENTE-ATENDIMENTO`, só `STK.R`, concessão
   na tela, como todo agente) e o endpoint `GET /atendimento/agenda` (`STK.R`): uma linha por
   (celular, cadastro), com código, nome (fantasia, senão razão social), papéis e o contato de onde
   o número saiu (setor e nome do contato; `whatsapp_comercial` = comercial, `whatsapp_fiscal` =
   fiscal).
2. **AxiaAtende:** a leitura diária grava `atendimento.agenda` (troca a tabela inteira numa
   transação). ERP fora do ar: a agenda de ontem continua valendo, e a tela diz a data da última
   leitura.
3. **Na chegada:** o recepcionista procura `com_nove(wa_id)` na agenda e grava na conversa o código,
   o nome, os papéis e o contato; com mais de um cadastro, grava só "N cadastros".
4. **Na Recepção** (maquete 1): o nome e o código na coluna Quem, as etiquetas de papel e de
   contato, "fora do cadastro" e "número em N cadastros"; o cartão "Do nosso cadastro"; o filtro
   todos / só do cadastro / só fora dele.
5. **O que a pessoa recebe no WhatsApp não muda.**

Etiqueta de papel, nesta ordem: Equipe (colaborador ativo), Representante (comercial), Cliente,
Produtor, Fornecedor. Equipe e Representante em azul; os de fora em verde.

## Escopo desta etapa

**Dentro:** a fase do agente e o endpoint no ERP; a migração 006 (agenda e colunas na conversa), a
leitura diária e o reconhecimento na chegada no AxiaAtende; a tela Recepção da maquete; o manual da
Recepção.

**Fora (etapas seguintes do #969):** tratar diferente quem é reconhecido (saudação, atalho para o
responsável, aviso ao representante); receber imagem da equipe para os stories (chamado próprio);
reconhecer conversas antigas (as de antes desta etapa ficam como estão); qualquer escrita no ERP.

## Impacto em produção

- **ERP:** uma fase (usuário e perfil, sem concessão) e um endpoint de leitura; restart do
  `axiagestao-backend`. Nenhum dado existente muda.
- **AxiaAtende:** migração 006 (tabela nova e colunas novas, todas anuláveis); restart dos dois
  serviços. O atendimento para alguns segundos no restart do recepcionista (a Meta reentrega).
- **Segredo:** o do agente no `AGENTE_SEGREDOS` do ERP e no `.env.secrets` do AxiaAtende
  (`AXIAATENDE_ERP_SEGREDO`), em janela elevada, pelo dono. Sem ele, nada é reconhecido e a tela
  diz "leitura do cadastro não ligada"; o atendimento segue igual.
- **Custo:** nenhum. Nenhuma chamada paga.

## ROLLBACK_PLAN

1. Desligar o agente `ATENDIMENTO` na tela de usuários do ERP: a leitura para no dia seguinte e a
   agenda de ontem continua; ou apagar `AXIAATENDE_ERP_SEGREDO` e reiniciar o `axiaatende-backend`.
2. Voltar o código do AxiaAtende ao commit anterior e reiniciar os dois serviços: a tela volta a
   mostrar só número e perfil (as colunas novas ficam, vazias de leitura).
3. Se for preciso tirar a tabela e as colunas: `006_..._VOLTA.sql`, à mão.
4. No ERP: a `_VOLTA.sql` da fase (apaga usuário e perfil) e o código anterior do endpoint.

Nenhum passo apaga atendimento já gravado nem consentimento.

## Manual de uso

**Atualiza `docs/manuais/recepcao.md`.** O que ele passa a dizer:

1. **Para que serve (acréscimo):** quando quem chamou já está no cadastro do ERP, a Recepção mostra
   quem é: o nome, o código e o papel (cliente, fornecedor, produtor, representante, equipe), e por
   qual contato do cadastro o número foi achado.
2. **Quem usa e quando:** sem mudança.
3. **O caminho comum (acréscimo):** para ver só quem já é da casa, escolha "Só quem está no
   cadastro" no último filtro; para ver os contatos novos (os leads), "Só quem não está".
4. **O que significa cada sinal:**
   - **Nome · código** e as etiquetas verdes (Cliente, Fornecedor, Produtor) ou azuis (Equipe,
     Representante): o número está no cadastro; a etiqueta "contato comercial: João" diz de qual
     contato ele veio.
   - **fora do cadastro**: o número não está em nenhum cadastro. Pode ser um contato novo, ou alguém
     da casa cujo celular não foi cadastrado.
   - **número em 2 cadastros**: o mesmo celular está em mais de um cadastro; o sistema não escolhe.
     Vale conferir o cadastro no ERP.
   - **Cartão "Do nosso cadastro"**: quantos dos que chegaram no período estão no cadastro.
   - O cadastro é lido uma vez por dia (06:00): quem foi cadastrado hoje é reconhecido amanhã.
5. **O que a tela NÃO faz:** não muda o que a pessoa recebe no WhatsApp; não corrige o cadastro (a
   correção é no ERP); não reconhece de novo conversas antigas; não mostra valor, crédito nem
   documento de ninguém.

**O que o manual atual passa a dizer errado:** a linha da coluna Quem que diz "(não é cliente)" para
quem não foi reconhecido vira "fora do cadastro".

**Pré-requisito de cadastro (vai na devolução):** só é reconhecido quem tem o celular no cadastro
do ERP. Hoje, dos seis atendentes do menu, só dois.

## Próximo passo
/writing-plans


## Etapa 2 — uma pergunta por dia (dono, 10/10/2026)

**O que aconteceu:** em 09/10 o dono simulou três atendimentos no mesmo dia e recebeu três vezes a
pergunta "recebeu o atendimento?", uma por conversa com link. Pedido dele: "durante um dia uma sessão
ativa só", com o tempo contado da **última interação** do cliente, e a sequência (pergunta e nota)
**uma vez só**.

**Decisão:**
- A pergunta sai **uma vez por pessoa por dia** (dia de calendário, horário de Brasília), na conversa
  com link mais nova, **4h30 depois da última mensagem** da pessoa. Toda mensagem que chega empurra a
  hora da pergunta ainda não feita.
- As outras conversas com link da pessoa naquele dia ficam **cobertas** por essa pergunta: a resposta
  (Sim, Não, a nota) vale para todas. O aviso do "Não" ao gestor leva todos os assuntos do dia.
- Se a pergunta do dia já saiu e a pessoa abre outra conversa com link, a nova fica coberta sem
  mensagem nova. No dia seguinte, a pergunta volta.
- A janela de 24h da Meta passa a contar da última mensagem da pessoa (em qualquer conversa).
- **Só em horário comercial** (dono, 10/10/2026, na mesma conversa): segunda a sábado, das 08:00 às
  11:00 e das 14:00 às 17:00 (ajuste `pergunta_janela`, na migração 007). Fora disso a pergunta
  espera a próxima faixa; se a faixa chegar mais de 23h depois da última mensagem, não se pergunta
  (a Meta não deixa mensagem livre). O sábado entra para quem chama sexta à tarde não perder a
  pergunta até segunda. "Um dia" é o dia do atendimento: quem chamou quinta à tarde e já foi
  perguntado quinta não é perguntado de novo sexta.
- **A nota continua logo depois do "Sim".** Pesquisado (10/10/2026): não há estudo sério de horário
  para pesquisa por WhatsApp; o que as fontes concordam é que pesquisa curta, perto do atendimento,
  responde mais, e que a manhã até as 10h e a tarde depois das 14h, em dia útil, respondem melhor
  (SurveyMonkey, sobre os próprios envios). A nota é um toque a mais no embalo do "Sim": separar
  perde quem já está com o celular na mão.

**Fios:** escreve `atendimento.conversas` (`ultimo_toque_em` a cada mensagem, `pergunta_em`,
`pergunta_feita_em`, a coluna nova `pergunta_da`, `recebeu`, `satisfacao`, `aviso_nao_em`) e a fila
`atendimento.avisos`; só o motor escreve nessas colunas, e quem lê para decidir é a própria rotina do
minuto (a pergunta, "parou no meio" em 30 min) e a Recepção. "Parou no meio" passa a contar também a
mensagem escrita, e não só o toque. **Medido:** em 09/10 três conversas do dono com link, três
perguntas.

**Migração 007:** `pergunta_da` (a conversa que levou a pergunta); as já perguntadas apontam para si
mesmas. Volta: `007_uma_pergunta_por_dia_VOLTA.sql`.

**Manual:** a linha "Disseram que foram atendidos" muda (uma vez por dia, da última mensagem) e entram
dois sinais na coluna da pergunta: "já perguntado hoje, em outra conversa" e "não perguntado (mais de
24h sem mensagem)".


## Etapa 2b — a nota em três botões (dono, 11/10/2026)

**O pedido:** a pesquisa "ir aberta na tela". O ideal seriam cinco botões, e o WhatsApp só deixa três
na própria mensagem (a lista leva dez, com um toque a mais para abrir e outro para confirmar). Dono:
"Ruim, Normal, Bom, reduz calibragem, mas ficaria mais simples".

**Decisão:**
- Depois do "Sim", a nota sai em **três botões** na mensagem: Bom, Normal, Ruim. Um toque.
- Gravada 3, 2 e 1 em `conversas.satisfacao`. Nenhuma nota tinha sido gravada na escala de cinco.
- Quem ainda tem a lista antiga na conversa e toca nela: 5 e 4 valem Bom, 3 vale Normal, 2 e 1, Ruim.
- **O "Ruim" avisa o gestor** no WhatsApp, como o "Não" já avisa (dono: "avisar é interessante sim"),
  com os mesmos três dados: quem, sobre o quê, o contato. Um aviso só, mesmo com dois toques.
- Juntar a pergunta e a nota numa mensagem só não cabe: seriam quatro respostas.

**Fios:** o motor escreve `satisfacao` (como antes) e a fila `atendimento.avisos`, com o tipo novo
`avaliacao_ruim`; quem volta depois é o despachante de avisos (`envio.mandar_avisos`), que procura o
modelo do uso `aviso_avaliacao_ruim`. **Medido:** nenhuma conversa com nota em produção em 11/10 (a
Recepção mostrava um "Sim" sem nota).

**Migração 008:** o tipo de aviso, o uso de modelo e o modelo `aviso_avaliacao_ruim` (Utilidade).
Volta: `008_nota_em_tres_botoes_VOLTA.sql`. **Depende da mão do dono:** a Meta precisa aprovar o
modelo (`python -m backend.modelos_meta --propor`); até lá a nota Ruim aparece na Recepção e o aviso
fica na fila com o erro.

**Manual:** a linha da pergunta diz os três botões, e entram os sinais "Bom", "Normal" e "Ruim · você
foi avisado".

**Fora desta etapa (dono, 11/10/2026):** medir quando o atendente começa o atendimento (aviso ao
atendente com botão que anota o toque). "Por hora não vamos medir o atendimento interno, no futuro
talvez."


## Etapa 3 — o vigia do endereço público (dono, 11/10/2026)

**O que aconteceu:** de 09/10 às 22:31 até 11/10 às 11:08 o recepcionista não recebeu nenhuma mensagem.
O nome público do Funnel (`serverrenascer.taild57672.ts.net`) devolvia "domínio inexistente" no Google,
na Cloudflare, no Quad9 e no servidor de nomes do Tailscale, com o Funnel ligado no nó e a marca
"Funnel" no painel. A Meta não achava o endereço; o Opa continuou recebendo. Voltou uns dez minutos
depois de religar o Funnel e reiniciar o serviço do Tailscale; a causa do sumiço não é conhecida.
Ninguém foi avisado: de dentro do servidor o nome resolve pela rede interna mesmo sem existir lá fora.

**Os caminhos pesados com o dono:** A, vigiar o endereço atual; B, túnel da Cloudflare com
`atende.sementesrenascer.com.br` (o DNS do domínio inteiro iria para a Cloudflare, que passaria a ler
as mensagens no caminho); C, um servidor pequeno na nuvem como porta de entrada (máquina exposta para
manter, mensalidade). Apontar o subdomínio direto para a empresa ficou fora: abriria a 443 do servidor
do ERP. **Decisão do dono: A.** "Me parece que o A já é uma solução sólida, todas têm riscos."

**Decisão:**
- A cada 5 minutos o recepcionista pergunta a dois resolvedores públicos, por HTTPS, se o nome existe.
- **Dois "não existe" seguidos** = fora do ar: um aviso no WhatsApp do gestor (o mesmo do "Não"), pela
  fila de avisos. O aviso sai do servidor para a Meta e não depende do endereço que caiu.
- Quando o nome volta, outro aviso, com quanto tempo ficou fora.
- Não conseguir perguntar (sem internet, resolvedor fora) não é "fora": sem resposta, nada se afirma.
- A saúde do recepcionista (`/saude`) passa a dizer `endereco`: no ar ou fora, desde quando.
- **O vigia de fora** (serviço gratuito que abre `/saude` pela internet a cada 5 minutos e avisa por
  e-mail ou aplicativo) cobre o que este não vê. É conta do dono, feita pela mão dele.

**O que este vigia não vê:** a internet da empresa ou o servidor caídos (ele mora no servidor). O
nome existir e o Funnel não repassar passou a ser visto no reforço, abaixo.

**Fios:** escreve a tabela nova `atendimento.vigia_endereco` (uma linha; só o vigia escreve, a saúde
lê) e a fila `atendimento.avisos`, com os tipos novos `endereco_fora` e `endereco_voltou`; quem volta
depois é o despachante de avisos (`envio.mandar_avisos`), pelos modelos dos usos
`aviso_endereco_fora` e `aviso_endereco_voltou`. O destinatário é o do ajuste `avisado_no_nao`. Do
mesmo nome dependem o endereço cadastrado no app da Meta, o botão `/falar/` (dentro dos modelos
aprovados) e a vitrine do AxiaMarketing na porta 10000: o aviso vale para os três.

**Medido:** 37 horas sem nenhuma chegada (09/10 22:31 a 11/10 11:08); o contador de chegadas da saúde
em zero aceitas e zero recusadas nesse intervalo; em 11/10 às 12h o vigia devolve "existe" para o nome
real e "não existe" para um nome inventado na mesma rede.

**Migração 009:** a tabela do vigia, os dois tipos de aviso e os dois modelos de Utilidade. Volta:
`009_vigia_do_endereco_VOLTA.sql`. **Depende da mão do dono:** a Meta aprovar os dois modelos
(`python -m backend.modelos_meta --propor`); até lá o aviso fica na fila com o erro e só a saúde mostra.

**Manual:** não há tela nova. O que fazer quando o aviso chega está no `PROJETO.md`, em "Se o
endereço público cair".

### Reforço: o Funnel repassa? (dono, 11/10/2026, "sim, reforço")

O dono perguntou se o vigia de dentro podia cobrir o que ficava com o de fora. Uma das duas lacunas
pode: existindo o nome, o vigia abre a própria saúde pelo **IP público** que o resolvedor devolveu (a
entrada do Funnel), com o nome no TLS. O pedido sai para a internet e volta, como o da Meta; pelo nome
ele iria pelo atalho da rede interna. Qualquer resposta HTTP vale como "repassa"; não conectar conta
como "não", e continuam valendo os dois seguidos antes do aviso. Os avisos e os modelos são os mesmos.

**Medido em 11/10:** pelo IP público 209.177.145.137 a saúde respondeu 200 em 1,2 s; um IP que não
atende devolve "não".

**Risco aceito:** a outra lacuna (internet da empresa ou servidor caídos) continua sem aviso. Só um
vigia de fora cobre. Decisão do dono: "vou fazer se tivermos mais uma queda".

**Sem migração.** Entra no ar com o reinício do recepcionista.
