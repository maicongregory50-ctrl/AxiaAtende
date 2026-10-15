# Conversar pelo WhatsApp a partir da coluna QUEM da Recepção
**Data:** 2026-10-15
**Chamado:** #1025
**Status:** APROVADO

## Contexto

Na tela **Recepção** do AxiaAtende (`127.0.0.1:8009`, aba Recepção), a coluna **QUEM** diz quem chamou
o 49 3664 0121. Quando o atendente precisa chamar essa pessoa de volta, não há caminho: ele lê o que
está na tela e vai procurar o número em outro lugar.

Hoje a coluna tem **dois ramos** (`frontend/src/Recepcao.jsx:13`):

- **quem está no cadastro do ERP** — nome, código, papéis e o contato de onde o número veio. **Nenhum
  número aparece**;
- **quem está fora** — o número **mascarado** (`+55 46 9…·4421`) e o nome do perfil do WhatsApp.

A máscara é decisão escrita, não acidente: `mascarar()` em `backend/rotas_telas.py:19` carrega o
comentário *"o bastante para reconhecer, nunca o numero inteiro na tela"*, e o manual da tela
(`docs/manuais/recepcao.md:44`) já a documenta como *"o número com o meio escondido"*. **O número
inteiro nunca sai do servidor hoje.** Um link de WhatsApp precisa dele, e é por isso que este pedido
— que parece de uma linha — é uma decisão.

Há na casa um desenho que entrega o clique sem entregar o número: o `/falar/<codigo>` do
recepcionista (`backend/envio.py:15`), um endereço nosso que redireciona para o `wa.me`. Ele existe
assim porque está na internet, sem login, e por isso o código é assinado por HMAC com o
`meta_app_secret` — segredo que o processo das **telas** não tem.

Os três caminhos foram pesados com o dono em 15/10/2026. Ele escolheu o do meio: **a máscara
continua sendo o que se lê, e o número inteiro vai no endereço do link.**

## Os fios que encostam

**Quem mais escreve: ninguém, porque esta etapa não escreve.** Nenhuma tabela, nenhuma coluna,
nenhum `INSERT` e nenhum `UPDATE`. A mudança é leitura e apresentação.

**Quem lê o mesmo dado para decidir.** O dado lido é `atendimento.conversas.wa_id`. Quem o lê para
decidir alguma coisa hoje, medido por `grep`:

| Quem | O que decide com ele |
|---|---|
| `agenda.reconhecer` | procura o número na agenda do cadastro, pela forma `com_nove` (com o nono dígito) |
| `campo.quem_e`, `campo._lider`, `campo.ultima_mensagem_de` | se quem mandou foto é da equipe, de qual rodada e quando falou |
| `envio.tratar_toque`, `envio.tratar_texto_de_convidado` | casa o toque e o texto com a linha do destinatário do envio |

Nenhuma delas muda: a etapa não escreve `wa_id`, não altera a forma guardada e não toca a agenda.

**Quem consome a rota alterada.** `GET /api/recepcao` tem **um** consumidor —
`frontend/src/Recepcao.jsx:58` — e dois testes que leem a mesma resposta (`tests/test_telas.py:48`,
`tests/test_agenda.py:104`). O campo novo é **aditivo**: nenhum dos três quebra por ele existir.
`mascarar()` tem **um** chamador (`rotas_telas.py:110`) e dois testes (`test_telas.py:44-45`), e
continua devolvendo exatamente o que devolve hoje.

**Quem volta depois: ninguém.** Nenhuma rotina revisita a conversa por causa do link. Nada é
agendado, nada é recalculado, nada muda de estado.

## O universo medido

Medido em 15/10/2026 no banco de produção (`127.0.0.1:5436`, `axiaatende`), como `axiaatende_ro`:

| Pressuposto | Contagem de hoje |
|---|---|
| conversas na tabela | **33** — todas dos últimos 30 dias (o projeto nasceu em 09/10) |
| pessoas distintas | **12** |
| linhas no cadastro (`erp_cadastros = 1`) | **9** — hoje **sem número nenhum** na coluna; passam a ter o link |
| linhas fora do cadastro, ou não conferidas | **24** — o número mascarado passa a ser o link |
| `wa_id` nulo ou vazio | **0** |
| `wa_id` não numérico | **0** |
| `wa_id` que a máscara recusa (menos de 10 dígitos) | **0** |

**O número é opcional por desenho, ainda que hoje nunca falte.** A coluna `wa_id` é `NULL`-ável e a
regra 7 do projeto diz que a conversa é chaveada pelo **BSUID**, não pelo telefone. Zero hoje não é
zero sempre: a etapa responde por essa linha (sem link, e o texto continua *"sem número"*), e o teste
cobre o caso que a contagem não tem.

**A forma do número divergiu, e isso muda implementação.** Dos 33 `wa_id`, **31 têm 12 dígitos**
(`55` + DDD + oito dígitos, **sem** o nono) e **2 têm 13**. O `com_nove()` da casa *acrescenta* o nono
para casar com o cadastro do ERP, e `envio.py:353` monta um `wa.me/` com essa forma acrescentada —
ou seja, há **duas formas candidatas do mesmo número, divergentes em 31 das 33 linhas**. Esta etapa
linka pelo **`wa_id` como a Meta o entregou**, porque ele é o identificador da própria conta de
WhatsApp. É o único ponto que o código não prova: o plano traz um passo de **um clique real** do
dono, e a forma `com_nove` fica escrita aqui como alternativa caso o clique falhe.

## Conformidade com o Manual legal

Não se aplica: a etapa não toca imposto, código fiscal, régua, texto legal em documento nem SPED.

## Conformidade com a casa

Não se aplica: nenhum dos seis gatilhos da Fase 1c é tocado. Conferido um por um, porque a ausência
da seção não quer dizer conforme:

- **Segredo (R3): não toca.** A etapa não cria, move nem troca de leitor nenhum segredo. O caminho
  recusado — copiar o `/falar/<codigo>` do recepcionista, com código assinado — **exigiria** o
  `meta_app_secret` dentro do processo das telas, que hoje só guarda a senha do banco e a chave do
  pedido do Marketing (`.env.secrets`). Seria segredo mudando de leitor; não é o caminho escolhido.
- **Serviço, porta, tarefa, exposição de rede (R4 e R1): não toca.** Campo novo numa rota que já
  existe, no serviço `axiaatende-backend`, que já escuta em `127.0.0.1:8009` atrás do login. Nenhum
  bind, porta, tarefa agendada ou regra de firewall muda. O **recepcionista** (8008, o único que a
  internet alcança) não é tocado.
- **Dado novo (R2): não cria.** Decisão do dono: o clique não é registrado. Nenhuma tabela, nenhum
  arquivo, nada a copiar.
- **Agente ou modelo de IA (R7): não toca.** Nenhuma chamada a modelo.
- **Processo que hospeda sessão de agente (R9): não toca.**
- **Projeto novo (R8): não.**

## Decisão

**A máscara continua sendo o que se lê; o número inteiro vai no endereço do link, e o link aparece em
toda linha.** Em quatro pontos:

1. **Como o número chega ao WhatsApp:** o texto da coluna continua mascarado (`+55 46 9…·4421`), e o
   endereço do link carrega o número inteiro. **Consequência aceita, dita por extenso:** a partir
   desta etapa o número inteiro **sai do servidor** — está na resposta de `GET /api/recepcao` e no
   HTML da página, visível ao passar o mouse e ao copiar o endereço do link. O que a máscara passa a
   proteger é a **leitura** da tela (ombro, print, compartilhamento de ecrã), não mais o trânsito. A
   alternativa que mantinha o número dentro do servidor — uma rota nossa respondendo `302` — foi
   apresentada e recusada pelo dono por custo de desenho desproporcional ao ganho numa tela que já
   exige login e só escuta em loopback.
2. **Onde aparece:** em **toda** linha. Quem está no cadastro ganha uma pílula *Conversar* ao lado do
   nome (são 9 das 33, e hoje não têm número nenhum na linha); quem está fora tem o próprio número
   mascarado como link. Era o caso mais útil e o que estava faltando.
3. **Para onde vai:** `https://web.whatsapp.com/send?phone=<número>`, que abre a conversa direto no
   WhatsApp Web, sem a página intermediária do `wa.me`. É como o dono usa.
4. **Registro:** nenhum. O clique não é gravado; a tela já exige login e a rota não muda nada.

**Quem monta o endereço é o backend, não a tela.** A tela só desenha o que vier no campo; ela não sabe
formar endereço de WhatsApp. Isso dá duas coisas de graça: a forma do número e o endereço mudam num
lugar só, e tirar o campo do backend apaga todo link da tela — que é o rollback parcial da etapa.

## Escopo desta etapa

**DENTRO**

1. `backend/rotas_telas.py` — uma função ao lado de `mascarar()` que devolve
   `https://web.whatsapp.com/send?phone=<dígitos>` ou **nada**, e o campo novo (`conversar`) em cada
   linha de `/recepcao`. **O limiar é o mesmo da máscara** (menos de 10 dígitos = *sem número* = sem
   link), para texto e link nunca discordarem.
2. `frontend/src/Recepcao.jsx` — os **dois** ramos de `Quem`: a pílula ao lado do nome de quem está no
   cadastro, e o número mascarado como link de quem está fora. Sem o campo, nada aparece — nunca um
   link morto. Abre em aba nova, com `rel="noopener noreferrer"`.
3. `frontend/src/atende.css` — o estilo da pílula e do número como link.
4. `docs/manuais/recepcao.md` — a seção nova e a correção do que ele passa a dizer incompleto.
5. `tests/test_telas.py` — linha com número vira link; `wa_id` nulo **não** vira; a máscara continua
   idêntica.
6. **A prova do clique** — o dono clica uma vez num número conhecido e confirma que a conversa abre.
   É o único passo que o código não prova.

**FORA**

- **Mandar mensagem daqui.** A tela não fala com a Meta. O clique abre o WhatsApp *de quem está na
  tela*; a conversa é dele, com o número dele.
- O número por extenso na tela: a máscara **fica**.
- Registro do clique.
- A rota de redirecionamento (o caminho recusado).
- As telas **Envios** e **Destinos**, e qualquer outra coluna da Recepção.
- Reconhecer de novo conversas antigas, ou corrigir número no cadastro do ERP.

## Impacto em produção

- **Serviço `axiaatende-backend`** (`127.0.0.1:8009`, as telas): `npm run build` no `frontend` e
  `Restart-Service axiaatende-backend`. Segundos, e só as telas.
- **O recepcionista (`axiaatende-recepcionista`, 8008) não é tocado.** O atendimento no WhatsApp não
  para, e nada muda para quem chama o 49 3664 0121.
- **Banco:** nenhuma migração, nenhum dado escrito, nenhuma fase.
- **Janela:** qualquer hora. Ninguém fora do servidor usa a 8009.

## ROLLBACK_PLAN

1. `git revert <commit>` (ou `git checkout -- backend/rotas_telas.py frontend/src/Recepcao.jsx frontend/src/atende.css docs/manuais/recepcao.md`).
2. `npm run build` em `C:\AxiaAtende\frontend`.
3. `Restart-Service axiaatende-backend`.
4. Conferir: a coluna QUEM volta a ser texto sem link, e `GET /api/recepcao` volta a não trazer o
   campo `conversar`.

**Nada a desfazer no banco:** a etapa não escreve. **E há rollback parcial:** basta parar de mandar o
campo `conversar` no backend — todo link desaparece da tela, porque a tela não monta endereço nenhum
sozinha.

## Manual de uso

**1. Para que serve.** Quando você olha quem chamou a Renascer e precisa falar com essa pessoa, o
nome (ou o número) na coluna **Quem** agora é um link: um clique abre a conversa com ela no seu
WhatsApp Web, já no lugar certo. Antes era preciso sair da tela e procurar o número em outro sistema.

**2. Quem usa e quando.** Quem atende, ao revisar a Recepção — especialmente nas linhas **"Parou no
meio"** e nas que dizem **"Não · você foi avisado"**: são as pessoas que ficaram sem resposta e que
vale chamar de volta.

**3. O caminho comum.**
1. Abra a aba **Recepção** e escolha o período (e, se quiser, o filtro de situação).
2. Ache a linha da pessoa.
3. Na coluna **Quem**, clique no botão **Conversar no WhatsApp** (quando ela está no nosso cadastro)
   ou no **próprio número** (quando não está).
4. Abre uma aba nova com a conversa dela no WhatsApp Web. **Escreva você a primeira mensagem** — o
   sistema não manda nada.
5. Volte à aba da Recepção; ela continua como estava.

**4. O que significa cada sinal.**

| O que você vê | O que quer dizer |
|---|---|
| O nome com o botão **Conversar no WhatsApp** ao lado | a pessoa está no nosso cadastro; o botão abre a conversa com o número por onde ela chamou |
| O **número sublinhado** (`+55 46 9…·4421`) | ela não está no cadastro; o número é o link. O meio continua escondido de propósito — você clica, não lê o número inteiro |
| O número **sem** link, ou o nome **sem** o botão | não temos telefone dessa conversa (ela chegou só pelo identificador do WhatsApp). Não é erro, e não há como chamar por aqui |
| **"sem número"** no lugar do número | o mesmo caso acima, dito por extenso |
| A aba abre e o WhatsApp pede para ler o código QR | o seu WhatsApp Web não está conectado neste navegador; conecte e clique de novo |

**5. O que a tela NÃO faz.**
- **Não manda mensagem.** O clique só abre a conversa; quem escreve é você, do seu WhatsApp.
- **Não mostra o número inteiro**, nem com o clique: o que você vê continua mascarado.
- **Não registra** que você clicou, nem avisa a pessoa.
- **Não fala pelo número da empresa.** A conversa sai do **seu** WhatsApp, não do 49 3664 0121 — a
  pessoa vai ver que é você.
- **Não funciona sem o WhatsApp Web conectado** no navegador em que você está.

**O que o manual de hoje passa a dizer errado.** Nada fica falso, mas duas linhas ficam incompletas e
mudam no mesmo plano: a linha **"fora do cadastro"** (`docs/manuais/recepcao.md:44`) diz que *"aparece
o número com o meio escondido"* e precisa dizer que esse número agora é um link; e a linha
**Quem: "Agro Real Insumos · 5475"** (linha 43) descreve nome, código e etiquetas e não menciona o
botão **Conversar no WhatsApp**, que passa a existir ali.

## Próximo passo

`/writing-plans`.
