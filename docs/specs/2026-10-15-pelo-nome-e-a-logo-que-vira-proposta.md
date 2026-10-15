# Pelo nome, e a logo que vira proposta
**Data:** 2026-10-15
**Chamado:** #1036
**Status:** APROVADO

## Contexto

Dois pedidos do dono em 15/10/2026, **no mesmo chamado por decisão dele** — eu registrei a ressalva
de que são esteiras diferentes na prática (uma mudança de texto e um fluxo que atravessa projeto), e
ele decidiu juntar.

**1. Tratar quem é da casa pelo nome.** O menu da casa, que nasceu hoje no #1031, diz *"Você é da
equipe. O que precisa?"* — impessoal, **tendo o nome na mão**: `internos.quem_e` já o devolve, e
`envio.primeiro_nome()` já resolve o problema da caixa alta do ERP (`BENEDITO  VASKEVICZ` → `Benedito`).

**2. A logo de cliente que sumiu.** Às 15:27 de hoje o Benedito usou o menu da casa pela primeira
vez em produção, tocou **📸 Foto do campo** e mandou a logo de um cliente em PDF. **Recebeu
silêncio.** Duas coisas se somaram, e nenhuma é defeito isolado:

- **documento não é mídia**: `motor` cria `e.midia` só para `image` e `video` (linha 99), então
  `campo.receber` nunca foi chamado;
- **para quem é da equipe, a linha curta não sai**, de propósito — decisão do dono em 12/10/2026,
  escrita no código: *"quem e da equipe com o canal de campo ligado nao recebe esta linha: o que ele
  manda e material, e a duvida fica no log"*.

Resultado: a logo ficou só em `eventos_meta`, e **nem ele nem ninguém foi avisado**. É o fracasso
silencioso que este projeto combate, aplicado a quem é de dentro. E já havia acontecido antes: ele
mandou a mesma logo às 07:36, e naquela hora recebeu `nao entendo: document`, antes do #1027.

**O destino dela já existe, e é maduro.** A tela **Parceiras** do AxiaMarketing (#886, 08/10/2026)
guarda a logo byte a byte com o PNG para peça, o contato confirmado e **a autorização que trava a
peça**; e desde o #987 (13/10) *"a peça nova nasce sozinha para a revenda autorizada"*. **As artes
automáticas estão de pé.** O que não existe é a ponte do WhatsApp até lá.

**E o portão daquele lado não é convenção: é um `CHECK` do banco.**

```sql
CONSTRAINT parceiras_autorizada_com_documento CHECK (
    autorizacao <> 'autorizada'
    OR (autorizacao_arquivo IS NOT NULL AND autorizacao_assinada_em IS NOT NULL))
```

**Nenhum caminho torna uma parceira `autorizada` sem o arquivo da autorização e a data de
assinatura.** A decisão do dono — *a logo vira proposta, nunca aprovada* — é, portanto, a única que
o banco do marketing admite. Um fluxo que tentasse aprovar pelo WhatsApp seria recusado pelo
Postgres, não por regra de time. (E há pesquisa jurídica de 13/10 no AxiaMarketing sobre
responsabilidade solidária em arte que carrega as duas marcas, que é a razão de o portão existir.)

## Os fios que encostam

**Quem mais escreve o que esta mudança escreve.** Duas coisas:

| O que a etapa escreve | Quem mais escreve hoje |
|---|---|
| `atendimento.menu.pergunta` da raiz interna (migração) | só as migrações; a tela Destinos escreve **apenas** `destino_id` (`rotas_telas.py:255`) |
| `atendimento.logos_de_cliente` (tabela nova) | **ninguém** — nasce nesta etapa, com um escritor só |

**Quem lê para decidir.** `menu.pergunta` é lido por `perguntar` (vai à mensagem) e por mais ninguém
que decida. A tabela nova será lida pelo AxiaMarketing quando ele puxar — **e isso é a etapa
seguinte, não esta**.

**O fio real desta etapa é a ORDEM DE INTERCEPTAÇÃO em `motor.tratar`**, e ele é sutil. Hoje:

```
1. toque de envio        → envio.tratar_toque
2. e.midia (image/video) → campo.receber          ← documento NÃO entra aqui
3. campo.responder
4. campo.texto_de_interno
5. não é texto nem botão → se e_interno: log e SILÊNCIO; senão a linha curta (ou a de arquivo, #1027)
```

A logo precisa ser tomada **antes do 5**, senão cai no silêncio; e **não pode** ser tomada pelo
`campo.receber`, porque logo de cliente **não é material de campo** — misturá-las poria uma logo no
catálogo do marketing como se fosse foto de lavoura. Então nasce um interceptador próprio, ao lado
do 2, com o seu próprio depósito.

**Quem volta depois: o Marketing, puxando** — e é por isso que a tabela tem `puxada_em`. Nada mais
revisita. A agenda das 06:00 não toca nada disto.

## O universo medido

Medido em 15/10/2026 no banco de produção, como `axiaatende_ro`:

| Pressuposto | Contagem de hoje |
|---|---|
| logos que chegaram e se perderam | **2**, as duas do Benedito (07:36 e 15:27), o mesmo arquivo |
| peças no canal de campo | 24, **todas `foto`**, todas catalogadas — **nenhum documento** |
| `material_de_campo` com `mime` de PDF | **0** — a mistura que o desenho evita nunca aconteceu |
| pessoas reconhecidas como da casa que já escreveram | **3** — Maicon, Benedito, Alisson |
| textos que falam com interno e **não** usam o nome | **1** — a pergunta da `raiz_interna` |
| textos que **já** usam o nome | **1** — `ESSE_E_VOCE` (#1031), por `d["nome"].split()[0]` |
| `parceiras` no AxiaMarketing | `erp_codigo` **UNIQUE e NOT NULL**; `nome_marca` não vazio; logo em `pdf`, `svg`, `png` ou `jpg` |

**Duas leituras que decidiram o desenho:**

1. **A logo precisa de duas respostas, não de uma.** O banco do marketing liga a parceira pelo
   `erp_codigo` (*"não acha a empresa pelo nome"*) e exige `nome_marca`. Então o fluxo pergunta
   **o código do cliente** e **o nome da marca** — e sem o código a logo fica guardada, não descartada.
2. **A máquina de perguntas do canal de campo NÃO é reaproveitável.** Ela pende de uma linha de
   `material_de_campo` (`pergunta_pendente` naquela tabela, `campo._pendente`). Reusá-la exigiria
   criar uma linha de material de campo para uma logo — exatamente a mistura que a leitura 1 do
   *universo* mostra que nunca aconteceu e que não deve começar. A tabela nova tem a sua.

## Conformidade com o Manual legal

Não se aplica: a etapa não toca imposto, código fiscal, régua, texto legal em documento nem SPED.
*(O assunto "autorização de uso de marca" tem pesquisa jurídica no AxiaMarketing e é tratado pelo
`CHECK` daquele banco; esta etapa não decide nada sobre ele — ela só não o contorna.)*

## Conformidade com a casa

**Dois gatilhos tocados: "dado novo que alguém perderia se o disco morresse" (R2) e "serviço, porta
ou exposição de rede" (R4/R1).** Nenhum segredo novo (R3), nenhuma chamada a modelo de IA (R7 — a IA
não participa deste fluxo), nenhum processo que hospede sessão de agente (R9), nenhum projeto novo
(R8).

- **R2: conforme.** O dado novo (a tabela `logos_de_cliente` e os arquivos de logo) nasce **dentro do
  banco e do disco que já têm cópia verificada**: `rotina:backup-axiaatende-banco` e
  `backup_cloud_axiaatende_banco.ps1` (02:20 e 02:45, 30 e 90 dias). Trecho lido: *"Todo dado vivo
  tem cópia verificada, em disco e fora, e a restauração foi ensaiada"* — a prova mecânica lista
  `rotina:backup-axiaatende-banco`, que é esta base. **Os arquivos de logo ficam na mesma pasta de
  mídia do canal de campo**, pela mesma razão: é disco já coberto. Nada a mudar no backup.
- **R4 e R1: conforme, e a etapa REDUZ superfície em vez de criar.** Nenhuma porta, bind, serviço ou
  tarefa nova: a logo fica **esperando ser puxada** pela rota que o AxiaMarketing já chama, com a
  `chave_pedido` que já existe. Trecho lido de R4: *"A superfície de rede é a declarada: ACL do
  Tailscale, binds em loopback, firewall"* — e a declarada não muda. É o padrão do #267 do
  AxiaGestão: *"se chamasse, passaria a depender de este serviço estar de pé, nasceria um segredo
  novo... Puxar mantém a seta na direção que ela já tinha."*

Li o `PROJETO.md` do AxiaAtende e o do AxiaMarketing. O *Ofereço* do marketing confirma que a tela
Parceiras e a peça da revenda são dele, e o *Exijo* do AxiaAtende já lista *"o pedido de envio e a
lista com o responsável de cada cliente"* vindo do marketing — a direção que esta etapa reaproveita.

## Decisão

**1. A OlivIA chama quem é da casa pelo nome.** A pergunta da `raiz_interna` passa a trazer
`{nome}`, formatado pelo código com `primeiro_nome()`; e o `ESSE_E_VOCE` do #1031 passa a usar a
mesma função, em vez de `.split()[0]` — hoje ele acerta só porque o nome vem da tela Destinos, que é
bem escrita; pelo ERP sairia `BENEDITO`.

**O texto continua cadastro e o nome continua código**, e isso é deliberado: a frase fica editável
sem deploy, e `mostrar_menu_interno` tolera a ausência do `{nome}` — quem apagar o marcador recebe a
frase sem o nome, não um erro.

**2. A logo de cliente é colhida, e vira proposta.** Documento de quem é da casa deixa de cair no
silêncio: a OlivIA confirma que recebeu, **pergunta o código do cliente no ERP e o nome da marca**, e
guarda tudo em `atendimento.logos_de_cliente` com o arquivo ao lado. **Nada é aprovado, e nada é
mandado a ninguém** — a linha nasce esperando o Marketing puxar.

**Sem o código do ERP a logo NÃO é descartada:** fica na tabela sem `erp_codigo`, visível, para
alguém completar. Descartar seria repetir em outra forma o defeito que esta etapa conserta.

**3. Interceptar antes do silêncio, e em lugar próprio.** O interceptador novo fica ao lado do
`campo.receber`, **não dentro dele**: logo de cliente não é material de campo, e misturá-las poria
uma logo no catálogo do marketing como foto de lavoura. Medido: **0 documentos** em
`material_de_campo` — a mistura nunca começou, e não começa aqui.

## Escopo desta etapa

**DENTRO**

1. `backend/migracoes/020_pelo_nome_e_a_logo.sql` (+ `_VOLTA`) — a pergunta da `raiz_interna` com
   `{nome}`, e a tabela `atendimento.logos_de_cliente`.
2. `backend/motor.py` — o nome no menu da casa; `ESSE_E_VOCE` por `primeiro_nome`.
3. `backend/logos.py` (novo) — colher o documento, as duas perguntas, o depósito do arquivo.
4. `backend/motor.py` — o interceptador, ao lado do `campo.receber` e **antes** do ramo do silêncio.
5. `tests/` — a logo não se perde; o nome aparece; e **o teste que prova que nenhuma logo entra em
   `material_de_campo`**.
6. `docs/manuais/recepcao.md` e `docs/manuais/campo-equipe.md`.

**FORA**

- **O lado do AxiaMarketing: puxar a logo e mostrar a proposta na tela Parceiras.** Outro
  repositório, outro manual, outra esteira — **chamado próprio**. Sem ele a logo deixa de se perder
  e fica numa fila que ninguém esvazia ainda; com ele, chega à tela. Dito agora para não entregar
  meia ponte chamando de ponte.
- **Aprovar, autorizar ou gerar arte.** O `CHECK` do banco do marketing impede, e está certo.
- **Mandar a logo a alguém** por WhatsApp.
- **O nome nos textos do canal de campo** (`"Recebi."`, `"Anotado. Obrigado!"`, `ANOTADO_FRASE`) —
  são do fluxo do canal, e entram quando o dono quiser; esta etapa trata o menu da casa e o cartão.
- **Imagem como logo.** Logo que chega como **foto** continua indo ao canal de campo, porque é
  indistinguível de foto de lavoura sem perguntar. Quem manda logo manda arquivo — foi o caso das
  duas medidas. Se aparecer logo em JPG, é chamado próprio.
- **Ler ou converter o PDF** (gerar o PNG para peça): isso é do gerador do marketing.

## Impacto em produção

- **`axiaatende-recepcionista`** (8008) e **`axiaatende-backend`** (8009): migração 020 aplicada pelo
  serviço ao subir; reiniciar os **dois**.
- **Banco:** migração 020 — **uma tabela nova** e **um `UPDATE`** numa linha de `menu`.
- **Disco:** os arquivos de logo vão para a pasta de mídia do canal de campo, já coberta por backup.
- **Janela:** qualquer hora. Para cliente, **nenhum efeito**: o fluxo todo é de quem é da casa.

## ROLLBACK_PLAN

1. `git revert <commit>`.
2. O `_VOLTA` à mão, em janela elevada — **não há verbo `voltar`** no módulo de migrações:
   `psql -f backend\migracoes\020_pelo_nome_e_a_logo_VOLTA.sql`. Ele devolve a pergunta da
   `raiz_interna` ao texto de hoje e **apaga a tabela**.
3. `Restart-Service axiaatende-recepcionista` e `axiaatende-backend`.
4. Conferir: um "oi" de interno traz o menu da casa sem o nome, e um documento volta ao silêncio.

**O que se perde ao reverter, e precisa ser dito:** as logos já colhidas, porque a tabela é apagada.
**Antes de reverter, salve-as** — `COPY (SELECT * FROM atendimento.logos_de_cliente) TO ...` e a
pasta dos arquivos. É o único lugar desta etapa em que reverter destrói dado que não existia antes.

**Rollback parcial:** as duas metades são independentes — dá para reverter só o nome (código) ou só a
colheita, porque nenhuma depende da outra.

## Manual de uso

**1. Para que serve.** Duas coisas para quem é da equipe: a OlivIA passa a chamar você **pelo nome**,
e a **logo de um cliente** mandada no WhatsApp deixa de se perder — ela é guardada e fica esperando
entrar na tela Parceiras do marketing, onde as artes com a marca da revenda são autorizadas.

**2. Quem usa e quando.** Quem atende, ao receber de um cliente a logo dele para a arte
personalizada — hoje isso acontece no WhatsApp e acabava no nada.

**3. O caminho comum.**
1. Mande o arquivo da logo (PDF, SVG, PNG ou JPG) para o WhatsApp da Renascer.
2. A OlivIA confirma que recebeu e pergunta **de qual cliente é** — o **código do ERP**, porque é por
   ele que o marketing liga a parceira (nome não serve).
3. Depois pergunta **o nome da marca**, como ela deve aparecer na arte.
4. Pronto. Ela diz que a logo está guardada e que a autorização é na tela Parceiras — **ela não
   autoriza nada**.
5. Não sabe o código agora? Responda qualquer coisa ou deixe passar: **a logo fica guardada**, e
   alguém completa depois. Ela não é descartada.

**4. O que significa cada sinal.**

| O que você vê | O que quer dizer |
|---|---|
| *"Olá, Benedito!"* no menu da casa | você foi reconhecido, e pelo primeiro nome do cadastro |
| A OlivIA confirma a logo e **pergunta o código** | o arquivo chegou e está guardado. A pergunta é só para ligar ao cliente certo |
| *"A autorização é na tela Parceiras"* | é o limite: nenhuma arte sai da logo sem a autorização escrita do cliente, e isso não se faz por WhatsApp |
| **Silêncio** depois de mandar um arquivo | não deve mais acontecer. Se acontecer, me avise: era o defeito deste chamado |
| A logo sem código na lista | ninguém disse de qual cliente era. Está guardada, não perdida |

**5. O que a tela NÃO faz.**
- **Não autoriza e não gera arte.** Só colhe e guarda. A autorização é a tela Parceiras, com documento.
- **Não manda a logo a ninguém.**
- **Não aparece na tela Parceiras sozinha** — ainda. Puxar é a etapa seguinte, em chamado próprio.
- **Não trata logo mandada como foto**: logo é arquivo. Foto vai para o canal de campo, como sempre.
- **Não lê o PDF** nem gera a versão em branco da logo: isso é do gerador do marketing.

**O que o manual de hoje passa a dizer errado:** nada fica falso. A seção *O menu da casa* ganha o
nome, e o `campo-equipe.md` ganha a diferença entre mandar **foto** (canal de campo) e mandar
**arquivo de logo** (este caminho novo).

## Próximo passo

`/writing-plans`.
