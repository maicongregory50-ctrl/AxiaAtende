# Trabalhe conosco: a vaga aberta, o currículo em PDF e a pré-triagem para a Fran
**Data:** 2026-10-22  
**Chamado:** #1098  
**Status:** APROVADO

Maquetes: `docs/specs/2026-10-22-trabalhe-conosco-vaga-e-pre-triagem-maquete/` (`conversas.png`,
`fran.png`). **Onde a maquete diz "PDF ou foto", vale esta spec: só PDF** (dono, 22/10/2026).

## Contexto

Em 20/10/2026 o AxiaMarketing publicou a Vaga Comercial (`C:\AxiaMarketing\docs\pecas\vagas\2026-10-20-comercial.md`,
pedido do Financeiro no #933), com anúncio patrocinado que manda o candidato ao WhatsApp 49 3664 0121,
"Trabalhe conosco". Hoje esse nó do menu (`menu` id 6, chave `trabalhe`) é `acao = 'destino'` → Fran:
manda o cartão de contato dela e acaba. Documento de quem não é da casa recebe a linha
`NAO_ABRO_ARQUIVO` ("não consigo abrir arquivo por aqui", #1027) e não é guardado.

Em 21/10 o canal recebeu 59 conversas, 42 vindas do anúncio. Sete pessoas pararam no menu sem tocar
em nada; três candidatos mandaram currículo em PDF e receberam "não consigo abrir arquivo"; três
perguntaram "para que região é a vaga", que o anúncio não responde.

Pedido do dono: atendimento próprio para o Trabalhe conosco, focado em receber o candidato e o
currículo, com regras de atendimento por IA; sem tela de trabalho por ora; o currículo vai um a um ao
WhatsApp da Fran, já pré-triado pela IA, e a decisão é dela; ouvir o que ela diz da triagem.

## Os fios que encostam

**Quem mais escreve o que esta mudança escreve** (medido em 22/10/2026, `grep` em `backend/` e
`migracoes/`):
- `atendimento.menu`: escrito pelas migrações (002, 018, 019) e pela tela Destinos
  (`rotas_telas.py:255`, só `destino_id`). A mudança troca a `acao` do nó `trabalhe` por migração;
  a tela Destinos continua trocando o destino (a Fran) e passa a valer para o "falar com uma pessoa".
- `atendimento.conversas.situacao`: escrita por `motor.escolher` (com_link, encerrada),
  `motor.marcar_paradas` (parou_no_meio, 30 min sem toque) e a retomada (#989). **Lida para decidir**
  por: `marcar_paradas` (só `em_curso`), `retomar_paradas` (só `parou_no_meio`), a pergunta das 4h30
  (#969, só `com_link`), os cartões e a lista da Recepção (`rotas_telas.py:106,121`). O CHECK
  `conversas_situacao` hoje aceita `em_curso, com_link, parou_no_meio, encerrada, envio`: a etapa
  acrescenta `curriculo_recebido` e `sem_curriculo`. Nenhum dos leitores de decisão lê essas duas,
  então a conversa do candidato **não** vira "parou no meio", **não** é retomada pela IA e **não**
  recebe a pergunta "recebeu o atendimento?" — de propósito.
- O documento recebido: hoje `logos.receber` (só da casa) e, para os outros, a linha do #1027. A
  ordem nova: dentro de uma conversa de vaga, o PDF é da candidatura; fora dela, nada muda.
- Tabelas novas (`vagas`, `candidaturas`, `respostas_da_vaga`) não têm outro escritor.

**Quem volta depois:** o laço de 1 minuto do recepcionista (`marcar_paradas`, `retomar_paradas`,
avisos) — acrescenta-se a ele a limpeza dos 12 meses e o envio à Fran; o backup do banco
(`backup-axiaatende-banco` e `-nuvem`), que passa a levar os PDFs; a leitura da sessão
(`ler_conversa.py`), que passa a mostrar a candidatura sem o conteúdo do PDF.

## O universo medido

- Conversas "Trabalhe conosco": 1 em 16/10, **42 em 21/10** (41 pessoas), 1 em 22/10.
- Mensagens com `referral` do anúncio desde 20/10: **42**, todas `source_type = ad`,
  `source_id = 120249624037810192` (o anúncio da vaga). A frase "Olá! Posso ter mais informações
  sobre isso?" abriu 48 conversas desde 20/10.
- Documentos recebidos desde 15/10: 11; de candidatos, 3 PDFs (21/10) e 1 foto.
- O que os candidatos escreveram desde 20/10 (fora a frase do anúncio): região da vaga ×3, "mandei o
  currículo, não sei se receberam" ×1, uma apresentação em texto, cumprimentos e agradecimentos.
- Tamanho do PDF: **não medido** (a pasta `C:\Dados\AxiaAtende` não é legível pela sessão);
  estimativa de 100–500 KB por currículo, ~20 MB para 50 currículos no banco.
- Modelos ativos: 8; nenhum com cabeçalho de documento (o da Fran é o primeiro).

## Conformidade com o Manual legal

Não se aplica ao Manual legal da operação (é fiscal: impostos, códigos e documento fiscal). O
assunto legal aqui é **LGPD** (dado pessoal de candidato): a etapa trata com o aviso ao candidato
antes do envio, finalidade única (pré-triagem desta seleção e de vagas seguintes), guarda de 12
meses com apagamento automático do arquivo, e decisão sempre humana (a IA não aprova nem reprova).
Não há ficha a criar no Manual legal; a regra vai para a política de IA da casa (abaixo).

## Conformidade com a casa

- **R7 (agentes de IA) — muda.** A política (`C:\AxiaSecurity\docs\governanca\politica-uso-ia.md`)
  diz, sobre o atendimento, que "nada sai do servidor e nada vai a modelo externo" (uso das conversas
  lidas pela sessão, #981). O recepcionista já manda o texto do cliente ao modelo para escolher a
  opção (#950, Haiku); **o currículo inteiro ao modelo é novo**. Decisão do dono (22/10/2026,
  opção a): pode, com aviso ao candidato antes do envio, finalidade de pré-triagem, guarda de 12
  meses e decisão humana. **Passo próprio do plano:** a política ganha essa regra, e o inventário de
  agentes (`design\agentes.json`) a descrição nova do uso da IA do recepcionista.
- **R2 (backup) — conforme, por escolha do desenho.** "Todo dado vivo tem cópia verificada, em disco
  e fora." Os arquivos de `C:\Dados\AxiaAtende` (campo, logos) **não** estão em nenhuma rotina
  (`grep` em `C:\AxiaSecurity\backups`: nada); por isso o PDF do currículo fica **dentro do banco**
  (`bytea`), coberto por `backup-axiaatende-banco` e `backup-axiaatende-banco-nuvem`. A falta de
  backup das pastas de campo e logos é achado à parte, fora deste chamado.
- **R3 (segredo) — conforme.** Usa a chave Anthropic que o recepcionista já tem; não nasce segredo.
- **R4 (rede) — conforme.** Nada de porta, serviço ou exposição nova: roda no recepcionista.

## Decisão

Caminho **B** (dono, 22/10/2026): tudo junto, com um interruptor na triagem.

As decisões do dono, na ordem em que vieram:
1. Atendimento próprio do Trabalhe conosco; **sem tela de trabalho por ora**; o "falar com uma
   pessoa" é o cartão de contato da Fran.
2. IA = **(A)** entende e escolhe entre textos fixos aprovados + **(C)** lê o currículo e faz a
   pré-triagem. A regra 3 do projeto ("a IA não tem ferramenta, só devolve uma chave") **continua
   valendo na conversa com o candidato**; a pré-triagem é texto da IA, mas vai só à Fran, nunca ao
   candidato.
3. A pré-triagem vai em texto à Fran, **um currículo por mensagem**; a decisão é dela; ela responde
   "Triagem certa / Triagem errada" e, se errada, uma linha do que errou — o canal de feedback.
4. A IA vê **o currículo inteiro**, com aviso ao candidato antes do envio.
5. **Aceita de todos**, inclusive quem declara não atender a todos os requisitos (vai à Fran
   marcado); **guarda 12 meses**, depois apaga o arquivo e mantém só o registro.
6. Região: "Precisa residir em Maravilha SC ou cidade vizinha. Atuar na unidade e em visitas
   comerciais e técnicas aos cooperantes multiplicadores de Sementes da empresa, que compreende RS,
   SC, PR, MS e GO."
7. **Só PDF, sempre.** Foto, Word ou texto → "Precisamos do seu currículo em PDF". Sem PDF, não vai à
   Fran.
8. Textos e mensagem da Fran **aprovados** como na maquete (com o ajuste 7); calibrar depois.

## Escopo desta etapa

**Dentro:**
1. **A vaga** como linha de cadastro (`vagas`): título, requisitos (lista), texto da região,
   benefícios, `anuncio_ids` (os `source_id` da Meta), aberta/fechada, triagem ligada/desligada.
   Nasce por migração com a Vaga Comercial aberta e o anúncio 120249624037810192.
2. **A entrada**: mensagem com `referral.source_id` de uma vaga aberta abre a conversa **direto na
   vaga**, sem o menu. O nó `trabalhe` do menu passa a abrir a mesma conversa (com vaga aberta); sem
   vaga aberta, diz "no momento não temos vaga aberta" e pede o PDF para as próximas.
3. **A conversa** (textos da maquete, com o ajuste do PDF):
   - abertura com os 4 requisitos — o 4º passa a ser "Morar em Maravilha (SC) ou cidade vizinha" —
     e os botões "Sim, atendo todos" / "Não atendo todos" / "Era outro assunto" (→ menu principal);
   - "Não atendo todos" → "pode mandar assim mesmo, fica para as próximas vagas" (Mandar currículo /
     Encerrar);
   - pedido do PDF com a linha de consentimento: "Ao enviar, você autoriza a Renascer a guardar o
     currículo e a usar uma ferramenta de análise para a pré-triagem; a decisão é sempre de uma
     pessoa da equipe.";
   - PDF recebido → "Recebemos o seu currículo ✅ … pré-triagem … retorno aos pré-selecionados";
   - texto livre → a IA escolhe UMA das respostas fixas (`respostas_da_vaga`): região, "recebemos?"
     (com a data, ou "ainda não chegou"), apresentação sem arquivo (um lembrete só), "não tenho PDF"
     ("precisamos do currículo em PDF"), salário/benefícios ("valores conversados com os
     pré-selecionados"), prazo de retorno, falar com uma pessoa (cartão da Fran), outro assunto
     (menu principal), fora da lista (menu da vaga de novo);
   - arquivo que não é PDF → "Precisamos do seu currículo em PDF".
4. **A candidatura** (`candidaturas`): conversa, vaga, nome do perfil e número, o que disse nos
   botões, o texto que escreveu, o PDF (`bytea`, sha256, nome), a triagem (texto + por requisito), o
   envio à Fran (wamid, quando), o feedback dela (certa/errada, comentário, quando), `apagar_em`
   (recebida + 12 meses).
5. **A pré-triagem**: o PDF vai ao modelo do recepcionista com as regras da maquete (`fran.png`):
   os 4 requisitos, um por linha, *consta / não / não consta no currículo* com a fonte; ausência nunca
   vira "não"; ignora idade, sexo, foto, estado civil, filhos, religião, cor e saúde; sem nota, sem
   "aprovado/reprovado"; arquivo ilegível vai à Fran com "não consegui ler o arquivo". Interruptor
   desligado ou IA fora → vai à Fran sem triagem, dizendo isso.
6. **A mensagem à Fran**, uma por currículo: modelo **Utilidade** novo com cabeçalho de documento (o
   PDF), corpo com vaga, candidato, o que disse nos botões e a triagem, e botões "Triagem certa",
   "Triagem errada" e "Conversar com o candidato" (URL `/falar/<código>` do recepcionista, como os
   modelos aprovados — `wa.me` direto é recusado pela Meta). Dentro da janela de 24 h da Fran sai como
   mensagem comum. O texto da triagem vai em variáveis de uma linha (a Meta recusa quebra de linha em
   variável). Se a Meta recusar como Utilidade, refaz uma vez como Marketing e nunca insiste (regra 6).
7. **O feedback**: o toque da Fran (resposta ao modelo, pelo `context.id`) grava certa/errada na
   candidatura; "errada" pede "O que ela errou? Escreva em uma linha" e grava o texto seguinte dela.
8. **A Recepção**: as conversas de vaga terminam como **Currículo recebido** ou **Sem currículo**
   (nunca "parou no meio"); o cartão "Pararam no meio" não as conta.
9. **A limpeza**: no laço do recepcionista, candidatura com `apagar_em` vencido tem o PDF e o texto
   apagados; ficam vaga, data, situação e o feedback.
10. **O interruptor e a vaga** na tela Destinos (bloco pequeno, sem tela nova): "Vaga aberta:
    Comercial · Fechar vaga · Pré-triagem ligada/desligada".
11. A política de IA (R7) e o inventário de agentes atualizados; o manual.

**Fora:**
- Tela de trabalho de candidatos (lista, filtros, marcar pré-selecionado) — "não vamos investir em
  tela de trabalho ainda".
- A vaga vinda do AxiaMarketing (caminho C) e várias vagas com fluxo próprio: o cadastro aceita mais
  de uma linha, mas a etapa só cria a Comercial.
- Retorno automático ao candidato (pré-selecionado ou não): é a Fran, pelo "Conversar com o
  candidato".
- Backup das pastas `C:\Dados\AxiaAtende\campo` e `logos` (achado, vai à fila).

## Impacto em produção

- **Serviços:** `axiaatende-recepcionista` (conversa, triagem, envio à Fran, limpeza) e
  `axiaatende-backend` (Recepção e Destinos); restart dos dois; migração 025 aplicada no restart do
  backend.
- **Banco** `axiaatende` (5436): tabelas novas `vagas`, `candidaturas`, `respostas_da_vaga`; CHECK
  `conversas_situacao` ampliado; nó `trabalhe` do menu com `acao` nova. Nada apagado de dado
  existente.
- **Meta:** um modelo Utilidade novo para aprovação (com documento no cabeçalho). Até aprovar, a
  conversa e a triagem funcionam e o envio à Fran sai só dentro da janela de 24 h dela; o que não
  puder sair fica na fila e sai quando o modelo for aprovado.
- **Custo:** ~US$ 0,008 por currículo (Utilidade) + a leitura do PDF pelo modelo do recepcionista.
- **Janela:** fora do horário comercial; os candidatos do anúncio chegam a qualquer hora, e a
  conversa em curso no restart retoma no próximo toque.

## ROLLBACK_PLAN

1. **Só a triagem dá problema:** desligar o interruptor na tela Destinos. Os PDFs seguem à Fran sem
   triagem. Nada a migrar.
2. **A conversa da vaga dá problema:** "Fechar vaga" na tela Destinos. O nó `trabalhe` volta a mandar
   o cartão da Fran (a `acao` lê a vaga aberta), e o anúncio cai no menu principal como antes.
3. **Voltar o código:** reverter os commits do chamado e reiniciar recepcionista e backend.
4. **Voltar o banco:** `025_trabalhe_conosco_VOLTA.sql` — o nó `trabalhe` volta a `acao = 'destino'`
   (Fran); conversas `curriculo_recebido`/`sem_curriculo` passam a `encerrada` antes de o CHECK
   voltar; as tabelas novas **não** são apagadas pela volta (são currículos com consentimento e
   feedback da Fran; apagar é decisão do dono, por arquivo próprio).
5. **Modelo da Meta:** fica aprovado e sem uso; nada a desfazer na conta.

## Manual de uso

**Para que serve.** Receber os candidatos da vaga aberta pelo WhatsApp da empresa sem ocupar
ninguém: o atendimento explica a vaga, responde as dúvidas mais comuns, recebe o currículo em PDF e
entrega cada um à Fran já com uma pré-triagem, para ela decidir.

**Quem usa e quando.**
- **O candidato**, quando chama o 49 3664 0121 pelo anúncio ou toca "Trabalhe conosco".
- **A Fran**, quando chega cada currículo no WhatsApp dela.
- **O dono**, na Recepção (para ver quantos chegaram) e na tela Destinos (para fechar a vaga ou
  desligar a pré-triagem).

**O caminho comum (Fran).**
1. Chega uma mensagem "Novo currículo · Vaga Comercial", com o PDF anexado.
2. Leia a pré-triagem: cada requisito diz *consta*, *não* ou *não consta no currículo*, e de onde a
   informação saiu.
3. Abra o PDF e decida. A pré-triagem é ajuda, não decisão.
4. Toque **Triagem certa** ou **Triagem errada**. Se errada, escreva em uma linha o que ela errou:
   é assim que as próximas ficam melhores.
5. Para falar com o candidato, toque **Conversar com o candidato**.

**O que significa cada sinal.**
- *consta*: o currículo mostra o requisito, e a linha diz onde.
- *não*: o currículo mostra o contrário (ex.: mora em outra cidade).
- *não consta no currículo*: o currículo **não fala** disso. Não quer dizer que a pessoa não tenha.
- "Disse nos botões: não atende a todos os requisitos": o próprio candidato declarou; ele quis mandar
  mesmo assim.
- "Sem pré-triagem": a triagem estava desligada ou a IA não respondeu; o currículo chegou igual.
- "Não consegui ler o arquivo": o PDF é imagem ou está protegido; abra e leia você.
- Na Recepção: **Currículo recebido** = o PDF chegou e foi à Fran; **Sem currículo** = a pessoa
  conversou e não mandou PDF.

**O que NÃO faz.**
- Não aprova, não reprova e não dá nota: quem decide é a Fran.
- Não responde ao candidato o resultado; o retorno é da Fran, pelo botão de conversar.
- Não aceita foto, Word ou texto como currículo: só PDF.
- Não inventa resposta: a cada pergunta o atendimento escolhe um texto aprovado pelo dono; o que não
  está na lista volta para as opções da vaga.
- Não guarda o currículo para sempre: em 12 meses o arquivo é apagado.
- Não tem tela de candidatos: a lista é o WhatsApp da Fran.

**O que o manual da Recepção passa a dizer errado:** que toda conversa sem link termina "parou no
meio" — as de vaga terminam "Currículo recebido" ou "Sem currículo". A tela Destinos ganha o bloco da
vaga.

## Próximo passo

/writing-plans
