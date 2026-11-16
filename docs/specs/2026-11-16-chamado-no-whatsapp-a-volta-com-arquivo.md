# O chamado no WhatsApp: a volta com arquivo
**Data:** 2026-11-16
**Chamado:** #1528
**Status:** APROVADO

## Contexto

**O pedido do dono (16/11/2026):** *"Precisa chegar no WhatsApp o pedido da Fran, bem como receber os
documentos de volta por lá."* O caso que pede é o #1525: as descrições de função estão com a Fran, o
pedido a ela sai pelo chamado no WhatsApp, e a devolução dos arquivos por lá não existe. E a condição
que ele pôs: *"importante a segurança, nestes retornos"*.

**O que existe hoje.**
- **A ida** (#1222, #1381): o chamado chega ao WhatsApp de quem o recebe, e pode levar um PDF ou Word
  (até 10 MB, um por resposta). O arquivo é guardado no ERP (`axia.demandas_anexos`, pasta
  `C:\Dados\AxiaGestao\demandas_anexos`) e ligado ao evento do chamado.
- **A volta só aceita texto.** `backend/pendencias.py: tratar`, linha 334: `if not e.texto or e.toque:
  return False`. A mensagem sem texto sai dali antes de se olhar se ela cita um chamado. O manual diz o
  mesmo: *"Não lê foto ou arquivo como resposta de chamado"* (`docs/manuais/chamado-no-whatsapp.md`, §5).
- **No ERP**, a rota da volta (`POST /demandas/whatsapp/{id}/resposta`, atividade `SUP.WPP`, agente
  `ATENDIMENTO`) recebe só `numero` e `texto`. A rota que recebe arquivo (`POST /demandas/{id}/anexos`)
  é de quem trata, e valida PDF e Word **pelo conteúdo** (`utils/demandas_anexos.py`: o PDF abre no
  pypdf; o Word é um ZIP que tem de conter `word/document.xml`; nome no disco gerado; caminho confinado).
- **O arquivo de quem é da casa já tem dois destinos:** a logo de cliente (#1036) e o material do canal
  de campo (#970). O roteador (#1238) administra os assuntos abertos da pessoa, mas só para texto e
  áudio transcrito.
- **O recepcionista confere a assinatura da Meta** em cada aviso (`X-Hub-Signature-256`,
  `backend/recepcionista.py`), e a resposta de chamado só vale do número cadastrado no usuário
  (`pendencias.py:352`).

**A conversa de desenho (16/11/2026):**

| # | Pergunta | Decisão do dono |
|---|---|---|
| D1 | Como a pessoa diz de qual chamado é o arquivo | **Deslizando a mensagem do chamado; e, sem deslizar, a pergunta de confirmação** ("É para o Chamado N?"), pelo mecanismo de botões do roteador |
| D2 | Que tipos voltam | **PDF, Word, foto e planilha Excel**, até 10 MB cada |
| D3 | Vários arquivos | **A rajada entra junta, com teto:** arquivos seguidos em até 5 minutos entram no mesmo chamado; no máximo 10 por rajada e 20 por pessoa por dia |
| D4 | A segurança | **É condição, não acessório.** As oito regras da seção *Decisão* |
| D5 | A forma | **Caminho B:** o arquivo vai ao chamado no ERP, validado duas vezes. Contra A (fica só no AxiaAtende) e C (leitura automática por IA) |

## Os fios que encostam

**Quem escreve o que esta etapa escreve.**

- `atendimento.pendencias_mensagens` (AxiaAtende). Hoje escrevem `pendencias_erp.receber` (o que sai),
  `pendencias._entrou` (o que volta, texto) e o roteador (`roteador.py:340`, a correção). A etapa
  acrescenta a linha de arquivo que voltou, com o estado da rajada. **Quem lê para decidir:**
  `pendencias_erp._a_entregar` e `volta` (o que levar ao ERP), a tela Envios, `pendencias.oferecer` e o
  roteador (o retrato dos assuntos abertos).
- `atendimento.pendencias` (`espera`, `ultima_em`). Hoje a resposta em texto fecha a espera
  (`_anotar_resposta`). A rajada de arquivos passa a fechar também.
- `axia.demandas_anexos` (AxiaGestão). Hoje só `POST /demandas/{id}/anexos` insere (quem trata, a ida),
  e `demandas_anexos_service.ligar` liga ao evento. A etapa acrescenta um segundo escritor: o agente
  `ATENDIMENTO`, pela rota nova da volta. **Quem lê:** `dos_eventos` (um anexo por evento, hoje), a
  rota `/demandas/whatsapp/anexos/{id}` (a ida ao WhatsApp), a gaveta do chamado.
- `axia.demandas_eventos`. O comentário do autor pelo WhatsApp é gravado por
  `demandas_whatsapp_service.responder`. A etapa grava **um** comentário por rajada, com os arquivos
  ligados a ele.

**Quem volta depois.**

- **O gatilho do FIO**: comentário do autor acorda o agente FIO (`axia.demandas_gatilhos`). Por isso a
  rajada vira **um** comentário e não um por arquivo: dez arquivos não podem ser dez gatilhos.
- **`/demandas/whatsapp/saida`**: leva ao WhatsApp o que quem trata escreve ao autor. O comentário que
  a própria pessoa mandou pelo WhatsApp não volta para ela (regra de hoje para o texto; conferir que
  vale para o comentário com arquivo).
- **A carência do roteador** (`roteador.carencia_minutos`): o texto que foi a um chamado espera antes de
  ir ao ERP, para caber a correção. O arquivo usa a própria janela da rajada como carência.
- **O material de campo e a logo**: o arquivo que não é de chamado continua indo a eles; a ordem em
  `motor.tratar` é o que decide, e é trava.
- **A limpeza**: o anexo do ERP que nunca foi ligado a um evento precisa ter fim (arquivo validado de
  uma rajada que não fechou). O arquivo baixado no AxiaAtende é apagado quando o ERP aceita ou recusa.
- **A cópia de segurança**: ver *Conformidade com a casa*, R2.

## O universo medido

Medido em 16/11/2026, banco de produção do AxiaAtende (papel de leitura), 30 dias:

| Pressuposto | Contagem |
|---|---|
| pessoas com chamado no WhatsApp | 5 números |
| pendências | 30 de chamado (1 esperando resposta agora), 9 de aprovação |
| respostas que voltaram em texto | 18 (7 entregues ao ERP, 6 descartadas, 5 em escolha) |
| mensagens que saíram | 58 enviadas |
| foto, documento, vídeo ou áudio **citando** uma mensagem de chamado | **0** |
| foto de quem tem chamado com espera (em qualquer momento do período) | 14, de 1 pessoa |
| documento de quem tem chamado com espera | 1 |

**O que os números dizem.** Ninguém tentou devolver arquivo deslizando: a demanda nasce do caso do
#1525, não de tentativa frustrada. E as 14 fotos de uma pessoa só são o choque previsível: quem usa o
canal de campo manda foto o dia inteiro, e não pode ouvir "É para o Chamado N?" a cada uma.

**Não medido:** se a pasta `C:\Dados\AxiaGestao\demandas_anexos` está fora das exclusões do Defender
(a lista de exclusões exige administrador). Medido: Defender ativo, proteção em tempo real ligada,
assinaturas de 16/11/2026.

## Conformidade com o Manual legal
não se aplica: troca de arquivos entre a equipe e a fila de chamados, sem regra fiscal ou legal.

## Conformidade com a casa

Gatilhos tocados: **dado novo** (R2), **exposição de rede** (R4) e **agente de IA** (R7, pela regra de
quem lê o arquivo).

- **R4 — conforme.** Lido: *"A superfície de rede é a declarada: ACL do Tailscale, binds em loopback,
  firewall."* Nenhuma porta, bind ou exposição nova: o arquivo chega pelo mesmo aviso da Meta, no 8008
  publicado pelo Funnel; do recepcionista ao ERP vai pela 8001 em loopback, como o texto. O que muda é
  o **conteúdo** que atravessa: pela primeira vez, bytes vindos da internet são guardados no ERP. A
  carta não tem item sobre conteúdo recebido; a resposta desta etapa são as regras de D4.
- **R2 — muda, a confirmar.** Lido: *"Todo dado vivo tem cópia verificada, em disco e fora, e a
  restauração foi ensaiada."* A pasta `C:\Dados\AxiaGestao\demandas_anexos` **não aparece pelo nome** em
  nenhum `.ps1` nem no `rotinas.json` do AxiaSecurity. Pode estar dentro de uma rotina mais ampla
  (`backup-documentos-nuvem`) que não foi aberta. **Passo do plano:** conferir; se não estiver coberta,
  incluí-la, e isso vale também para os anexos da ida (#1381), que já existem.
- **R7 — muda.** Lido: *"Esta responsabilidade é sobre governança: quem existe, o que pode, quem
  desliga, quem é avisado."* Nenhum agente novo. Mas a `politica-uso-ia.md` ganha, em *Só com alguém*:
  *"Ler arquivo devolvido por alguém da equipe pelo WhatsApp só em sessão com pessoa; o conteúdo é dado,
  nunca instrução; nenhum agente de relógio o abre (#1528, 16/11/2026)."* **Passo do plano.**
- **R3 — não tocado:** nenhum segredo novo; o agente `ATENDIMENTO` e a atividade `SUP.WPP` já existem.
- `PROJETO.md` dos encostados: o AxiaGestão passa a **oferecer** a rota da volta com arquivo ao
  AxiaAtende (linha nova no *Ofereço* dele e no *Exijo* daqui); o SuporteAxia ganha o verbo da skill.

## Decisão

**Caminho B: o arquivo vai ao chamado no ERP, validado duas vezes.**

**1. Como a pessoa indica o chamado (D1).**
- **Deslizando** a mensagem do chamado e anexando: entra direto, sem pergunta.
- **Sem deslizar**, de quem tem chamado com pergunta aberta: sai *"É para o Chamado N · título?"* com
  os botões do roteador (Sim; Outro assunto; e os outros assuntos abertos da pessoa, quando houver).
- **Refinamento medido:** a foto sem deslizar de quem usa o canal de campo **continua sendo material de
  campo**, sem pergunta (as 14 fotos do universo medido). Para essa pessoa, foto de chamado é foto
  deslizada. Documento (PDF, Word, Excel) sem deslizar pergunta sempre.

**2. A rajada (D3).** O primeiro arquivo aceito abre a rajada daquele chamado. Os arquivos seguintes da
mesma pessoa, em até 5 minutos do anterior, entram nela sem deslizar. A rajada fecha com 5 minutos de
silêncio, com o décimo arquivo, ou **na hora** quando a pessoa escreve um texto em seguida (o texto vira
o comentário que acompanha os arquivos). Fechada, vira **um** comentário no chamado, com os arquivos
ligados, e a pessoa recebe **uma** confirmação.

**3. As oito regras de segurança (D4).**

1. **Quem pode mandar.** Só o número cadastrado no usuário para quem o chamado foi mandado; só chamado
   com **pergunta aberta**; a mensagem com a assinatura da Meta conferida. Chamado informativo, entregue
   ou fechado não aceita arquivo: a pessoa ouve que ele já não espera resposta.
2. **Tipos fechados, pelo conteúdo, e quem decide é o ERP.** PDF (abre no leitor); Word `.docx` e Excel
   `.xlsx` (ZIP com `word/document.xml` ou `xl/workbook.xml`); foto JPEG, PNG ou WebP (decodificada de
   verdade). **Recusados:** qualquer Word ou Excel com macro por dentro (`vbaProject.bin`), `.docm`,
   `.xlsm`, os formatos antigos `.doc` e `.xls`, compactados, executáveis e tudo o mais. O tipo
   declarado pelo WhatsApp e a extensão não decidem nada.
3. **Antivírus antes de ligar ao chamado.** O ERP passa o arquivo pelo Defender do servidor; se acusar,
   recusa. **Se a verificação não puder rodar, recusa também** (falha fechada): arquivo não conferido não
   entra.
4. **Limites.** 10 MB por arquivo (o recepcionista confere o tamanho que a Meta declara antes de
   baixar, e o real depois); 10 por rajada; 20 por pessoa por dia. Acima, a pessoa ouve o limite.
5. **Rastro.** Cada arquivo aceito: quem, quando, de qual número, para qual chamado, o nome original e
   a impressão digital (SHA-256). Cada recusa: o mesmo, com o motivo. A tela Envios mostra os dois.
6. **Nenhuma IA lê o arquivo sozinha.** A OlivIA, o FIO, o PLANEJADOR e o EXECUTOR não abrem esses
   arquivos. Quem lê é quem trata o chamado, ou a sessão com uma pessoa no teclado.
7. **Guarda.** No ERP, com nome gerado, na pasta dos anexos, de onde nada é executado; servido só como
   download. O arquivo recusado **não é guardado**: fica o registro. A cópia baixada no AxiaAtende é
   apagada assim que o ERP responde.
8. **Chave própria.** `pendencias.arquivo_volta`, ajuste no AxiaAtende, nasce `false`. Desligada, o
   arquivo segue os caminhos de hoje e o texto do chamado no WhatsApp não muda.

**4. O caminho do arquivo.** No AxiaAtende, `pendencias.tratar` passa a aceitar mensagem com arquivo que
cita uma mensagem de chamado: confere a regra 1 e a 4, baixa (`saida.baixar`) para a pasta de trânsito e
grava a linha `entrou` com estado `arquivo_a_validar`. As telas (o processo que fala com o ERP) mandam
cada arquivo à rota nova `POST /demandas/whatsapp/{id}/arquivo` (`SUP.WPP`): o ERP aplica as regras 2 e
3, guarda **sem ligar** e devolve o `anexo_id`, ou recusa com o motivo. Fechada a rajada, as telas chamam
`POST /demandas/whatsapp/{id}/resposta` com os `anexo_ids` e o texto (se houve): **uma transação**, um
comentário, os anexos ligados. Só então o recepcionista manda a confirmação.

**5. O que a pessoa ouve.** *"Anotado no chamado N: 3 arquivos. ✓"* depois que o ERP aceitou. A recusa,
na hora em que o ERP recusa, em linguagem simples: *"Não aceitei 'planilha.xlsm': arquivo com macro"*,
*"passou de 10 MB"*, *"tipo de arquivo não aceito"*, *"não consegui conferir o arquivo; tente de novo
mais tarde"*. Rajada com um arquivo recusado e dois aceitos: os dois entram, e a confirmação diz quais.

**6. Quem vê.** Na gaveta do chamado no ERP, o comentário mostra os arquivos, com download. A skill da
fila ganha `anexos N` (lista e baixa para uma pasta que a pessoa indica); `ver N` mostra os nomes.

**7. O fracasso silencioso a evitar.** A pessoa ouvir "anotado" e o arquivo não estar no chamado. A
confirmação nasce da resposta do ERP à transação do item 4, nunca do recebimento. Arquivo que ficou em
trânsito (ERP fora) é tentado de novo; passada uma hora sem o ERP, a pessoa é avisada de que não entrou.

**Por que B e não A:** o resumo de cada função é escrito a partir do chamado; arquivo guardado só no
atendimento fica onde ninguém que lê o chamado procura. **Por que não C:** contraria a regra 6.

## Escopo desta etapa

**Dentro:** o arquivo citado e a pergunta de confirmação; a rajada com teto; as oito regras; as duas
rotas no ERP e a validação ampliada (Excel, foto, macro, antivírus); um comentário por rajada com vários
anexos; a gaveta do chamado; o verbo `anexos N` da skill; a tela Envios; a chave; a cobertura de backup
da pasta de anexos; a política de IA; os manuais; a medição.

**Fora:** leitura automática do arquivo por IA; arquivo de cliente ou de quem é de fora; arquivo em
chamado sem pergunta aberta; vídeo e áudio como anexo; arquivos acima de 10 MB; abrir chamado novo pelo
WhatsApp; a foto sem deslizar de quem usa o canal de campo (continua material de campo).

## Impacto em produção

Três projetos. **AxiaAtende:** `axiaatende-recepcionista` e `axiaatende-backend`, uma migração (o estado
do arquivo em `pendencias_mensagens`, o registro das recusas, o ajuste da chave). **AxiaGestão:**
`axiagestao-backend` (duas rotas, validação), uma fase de banco (os tipos novos e o tamanho em
`axia.demandas_anexos`; vários anexos por evento na leitura) e a gaveta do chamado no frontend.
**SuporteAxia:** a skill da fila. Restart dos três backends. Sem perda de dado.

## ROLLBACK_PLAN

1. `pendencias.arquivo_volta = false` no AxiaAtende: na hora, sem restart, o arquivo volta aos caminhos
   de hoje. Os arquivos já ligados continuam no chamado.
2. Rajada aberta no momento do desligamento: os arquivos já validados são ligados (a transação do item 4
   não depende da chave); os não validados são apagados do trânsito e a pessoa é avisada.
3. Desfazer o código: `git revert` nos três repositórios; a `_VOLTA` da migração do AxiaAtende; a
   `_VOLTA` da fase do ERP **recusa** se houver anexo de tipo novo ligado a evento (arquivo já entregue
   não se apaga por rollback; é decisão do dono).
4. Política de IA e backup: revert no AxiaSecurity.

## Manual de uso

**Manual que muda:** `docs/manuais/chamado-no-whatsapp.md`. Seção nova, "Devolver um arquivo", e três
frases de hoje que passam a dizer errado.

1. **Para que serve.** Quando um chamado pede um documento seu, você devolve o arquivo pelo próprio
   WhatsApp, e ele entra no chamado.
2. **Quem usa e quando.** Quem recebeu uma **pergunta** de chamado pelo WhatsApp (a mensagem que termina
   com "Para responder, deslize esta mensagem para o lado"), enquanto ela estiver sem resposta.
3. **O caminho comum.**
   1. Deslize a mensagem do chamado para o lado, toque no clipe e escolha o arquivo.
   2. Tem mais de um? Mande os outros em seguida, sem deslizar de novo. Você tem 5 minutos entre um e
      outro.
   3. Se quiser explicar alguma coisa, escreva logo depois.
   4. Volta **"Anotado no chamado N: 3 arquivos. ✓"**.
   5. Mandou sem deslizar? O sistema pergunta **"É para o Chamado N?"**. Toque em **Sim**.
4. **Sinais.**
   - **"Anotado no chamado N: 3 arquivos. ✓"**: os arquivos estão no chamado.
   - **"Não aceitei 'nome': ..."**: aquele arquivo não entrou, e a frase diz por quê. Os outros entraram.
   - **"Este chamado não espera resposta"**: ele já foi respondido ou era só aviso; o arquivo não entrou.
   - **Silêncio por até 5 minutos** depois do último arquivo é normal: o sistema espera para ver se vem
     mais um. Escrever um texto encerra a espera na hora.
   - Na tela Envios, cada arquivo aparece como ← com "no chamado" ou "recusado: motivo".
5. **O que NÃO faz.** Aceita só PDF, Word (.docx), Excel (.xlsx) e foto, até 10 MB cada, 10 por vez e 20
   por dia. Não aceita arquivo com macro, nem os formatos antigos (.doc, .xls), nem compactado. Não
   aceita arquivo em chamado que já foi respondido. Quem manda foto de campo: a foto só vai ao chamado
   se você deslizar a mensagem dele; sem deslizar, continua sendo foto de campo. Nenhum robô lê o
   arquivo: quem abre é a pessoa que trata o chamado.

**O que o manual passa a dizer errado:** §5, *"Não lê foto ou arquivo como resposta de chamado"* e *"O
arquivo só vai da equipe para você"*; §3, o item 3, que só fala em escrever.

## Próximo passo
/writing-plans
