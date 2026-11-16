# A OlivIA conduz a conversa da vaga: ficha para quem não tem currículo
**Data:** 2026-11-16
**Chamado:** #1525
**Status:** APROVADO

## Contexto

**O pedido do dono (16/11/2026, depois da prova do #1520):** deixar a OlivIA mais esperta com os
candidatos. Devolver em espanhol (há candidatos venezuelanos); o público de chão de fábrica tem baixa
instrução e normalmente não tem currículo, então uma mini-entrevista bem simples que preenche uma ficha
de contato para a Fran; para operador o currículo é indispensável; para agrônomo é outro nível de
diálogo.

**O que existe hoje.**
- Quem chega pela vaga (anúncio, nó "Trabalhe conosco", ou de volta em 30 dias) cai no fluxo fixo,
  `backend/vaga.py: tratar`, que vem **antes** da OlivIA em `motor.tratar` (`motor.py:743`). Textos de
  cadastro (`atendimento.respostas_da_vaga`), só em português, pedindo PDF ou foto.
- A OlivIA do #1520 (`backend/olivia.py`) está no ar desde 16/11/2026, com cinco ferramentas, e só
  atende quem sai do fluxo da vaga ou escreve fora dele. O áudio de fora (D10) também está ligado.
- A candidatura (`atendimento.candidaturas`) nasce de um arquivo: PDF, ou foto desde a D5 do #1520.
- O cadastro da vaga (`atendimento.vagas`) tem título, requisitos, região, benefícios, anúncios e a
  chave da pré-triagem. Nada diz se a vaga aceita candidato sem currículo.
- A mensagem à Fran fora da janela de 24 h só leva PDF no cabeçalho; a foto vai embrulhada num PDF de
  uma página (`vaga.pdf_da_foto`).
- Na prova de 16/11 às 10:28, um áudio em espanhol foi transcrito em espanhol e respondido em português.

**A conversa de desenho (16/11/2026):**

| # | Pergunta | Decisão do dono |
|---|---|---|
| D1 | Quem conduz a conversa de quem chega pela vaga | **A OlivIA, a conversa inteira.** O fluxo fixo fica como reserva (chave desligada ou API fora) |
| D2 | O que a ficha pergunta | **Cinco perguntas fixas:** nome completo; cidade onde mora; no que já trabalhou; quando pode começar; se tem como chegar a Cunha Porã todos os dias. A pergunta do horário foi retirada por ele. Fora: idade, estado civil, nacionalidade, filhos, saúde |
| D3 | Como ela sabe o que cada vaga pede | **Um campo no cadastro da vaga, dois modos:** *ficha ou currículo* (Auxiliar de produção) e *currículo obrigatório* (Operador de empilhadeira; a Comercial, se reabrir). O operador sem currículo ouve isso com clareza e recebe a oferta da ficha para a vaga de Auxiliar, se aberta. A conversa técnica do agrônomo é chamado próprio |
| D4 | A ficha pela metade | **Um lembrete único, só dentro da janela de 24 h**; sem resposta, a parcial vai à Fran marcada como incompleta |
| D5 | A forma | **Caminho B:** a OlivIA conduz toda conversa de vaga; a ficha é uma candidatura sem arquivo e chega à Fran pelo caminho do currículo. Contra A (só a vaga de ficha) e C (perguntas editáveis por vaga) |

## Os fios que encostam

**Quem escreve o que esta etapa escreve.**

- `atendimento.candidaturas`. Hoje insere só `vaga.receber_arquivo` (`vaga.py:246`), chamado pelo fluxo
  fixo e pela ferramenta `encaminhar_curriculo` da OlivIA. Atualizam: a pré-triagem (`vaga.py:528`), o
  envio à Fran (`vaga.py:586`, `589`: `fran_*`), o retorno dela (`vaga.py:684` a `713`: `feedback*`,
  `espera_comentario`), o roteador (`roteador.py:340`) e o apagamento de 12 meses. A etapa acrescenta um
  segundo jeito de nascer: a ficha (`tipo_arquivo = 'ficha'`, sem `pdf`). **Quem lê para decidir:**
  `vaga.fim_da_conversa` e `motor.py:1132` (com ou sem currículo: a ficha passa a contar como "com");
  `olivia.travou` e `olivia.fechar_dia` (idem); o laço do envio à Fran (`vaga.py:539`, que hoje presume
  PDF ou imagem); `vaga._ultima_candidatura` ("vocês receberam meu currículo?"); a contagem por vaga da
  tela Destinos (`rotas_telas.py:468`); `leitura.py:205`.
- `atendimento.conversas`. Hoje `motor`, `vaga` (`trabalhe`, `vaga_id`, `vaga_declarou`, situação) e
  `olivia` (`conduzida_por`, `saida`). A etapa acrescenta o **rascunho da ficha** (`ficha`), a língua da
  conversa (`lingua`) e a hora do lembrete (`ficha_lembrada_em`). `vaga_id` ganha um escritor: a
  ferramenta `escolher_vaga`.
- `atendimento.vagas`. Hoje a tela Destinos (`fechar`, `triagem`) e as migrações. A etapa acrescenta
  `modo` e a rota que o troca.
- `atendimento.enviadas`. A OlivIA grava `olivia: fala`, `olivia: recusada`, `olivia: ferramenta ...`. A
  etapa acrescenta `olivia: aviso da ficha` e `olivia: lembrete da ficha`.
- **O papel de leitura da sessão (`axiaatende_ro`)** tem `SELECT` por coluna em `candidaturas` (migração
  025). A coluna nova `ficha` **não** entra no `GRANT`: é o mesmo cuidado da coluna do arquivo.

**Quem volta depois.**

- **O apagamento de 12 meses** (decisão 5 do #1098): apaga o arquivo, o texto, a triagem, o nome e o
  número. Passa a apagar também `candidaturas.ficha` e o rascunho em `conversas.ficha`.
- **A rotina do minuto do recepcionista**: ganha o lembrete da ficha e o envio da parcial.
- **O vigia das 23:40** (`olivia.fechar_dia`): a conversa de vaga conduzida por ela entra na conta; o
  resumo ao dono passa a dizer quantas fichas saíram incompletas.
- **A pergunta das 4h30 e `retomar_paradas`**: não tocam conversa de vaga nem conversa da OlivIA; nada
  muda.
- **A volta em 30 dias** (`vaga.volta`, `vaga.py:406`): com a chave ligada, quem volta escrevendo é
  atendido pela OlivIA, que tem a ferramenta de escolher a vaga. O defeito do #1522 (a volta marca a
  primeira vaga aberta) continua valendo no caminho de reserva e é corrigido lá.

## O universo medido

Medido em 16/11/2026 no banco de produção (papel de leitura), **desde 12/11/2026**, dia em que as duas
vagas abriram:

| Vaga | Conversas | Com currículo | Sem |
|---|---|---|---|
| Auxiliar de produção | 14 | 5 | 9 |
| Operador de empilhadeira | 15 | 3 | 12 |
| Sem vaga escolhida | 9 | 3 | 6 |
| **Total** | **38** | **11** | **27** |

- Das 27 sem currículo, em **8** a pessoa escreveu algum texto próprio; **19** não escreveram nada além
  da frase pronta do anúncio. É o motivo da D1: um desenho em que a OlivIA só entra quando a pessoa
  escreve alcança 8 de 27.
- Respostas fixas mandadas no período: 38 "pergunta do menu", 32 "abertura", 10 "currículo recebido",
  4 "região", 1 "sem PDF", 1 "apresentação".
- **6 números** abriram a conversa em espanhol.
- A OlivIA em 16/11 (primeiro dia): 4 conversas conduzidas, 12 falas, 1 frase recusada.
- **Não medido:** o conteúdo de `candidaturas` (quantas em foto, quantas triadas). O papel de leitura
  não vê a tabela inteira, de propósito.

**A medida de sucesso:** candidaturas (ficha ou currículo) sobre conversas de vaga, contra **11 de 38**,
uma semana depois de ligar. **O fracasso silencioso:** a OlivIA dizer que anotou ou encaminhou sem que
nada tenha chegado à Fran.

## Conformidade com o Manual legal

Lido: `C:\AxiaGestao\backend\services\manual_legal_fichas.py`, busca por LGPD, candidato, currículo,
recrutamento, trabalhista: **nenhuma ficha**. O Manual legal é fiscal. A regra desta etapa nasce sem
ficha lá, e o registro dela fica na política de IA da casa (abaixo). A lista do que a ficha não pergunta
(idade, estado civil, nacionalidade, filhos, saúde) é decisão do dono (D2) e repete o que a pré-triagem
já ignora por regra escrita (#1098, condição 3). Esta spec não afirma suficiência legal do aviso ao
candidato: o texto dele é do dono.

## Conformidade com a casa

Gatilhos tocados: **agente de IA** (R7) e **dado novo** (R2).

- **R7 — muda.** Lido: *"O que um agente pode fazer sozinho é decisão do código que o envolve (...) e a
  barreira mora lá, com quem a constrói. Esta responsabilidade é sobre governança: quem existe, o que
  pode, quem desliga, quem é avisado."* A OlivIA deixa de ter cinco ferramentas (D7 do #1520) e ganha
  três na conversa de vaga, uma delas gravando dado pessoal do candidato sem arquivo. **Passos do
  plano:** a linha da OlivIA no `inventario-agentes.md` (o que pode, e a chave nova); na
  `politica-uso-ia.md`, em *Pode sozinho*, a regra com fonte: *"Conduzir a conversa de vaga e gravar a
  ficha de contato do candidato, cinco campos fixos, com aviso antes da primeira pergunta, para a
  recrutadora e por 12 meses; decidido em 16/11/2026 (#1525)"*; e a regra do #1098 ganha "ou a ficha".
- **R2 — conforme.** Lido: *"Todo dado vivo tem cópia verificada, em disco e fora, e a restauração foi
  ensaiada."* A ficha mora no banco `axiaatende`, coberto por `backup_axiaatende_banco.ps1`.
- **R3 e R4 — não tocados:** nenhum segredo, serviço, porta ou exposição nova; a chave da API é a do
  recepcionista.
- `PROJETO.md` dos encostados: o AxiaSecurity recebe a mudança de inventário e política; o AxiaGestão
  não é tocado.

## Decisão

**Caminho B: com a chave ligada, a OlivIA conduz toda conversa de vaga de quem é de fora.**

**1. A entrada.** Em `motor.tratar`, antes de `vaga.tratar`: a mensagem de vaga de quem é de fora (o
anúncio, o toque "Trabalhe conosco", texto, arquivo ou áudio transcrito numa conversa de vaga em curso)
vai a `olivia.atender`. Se ela devolver `False` (API fora, erro antes da primeira fala), `vaga.tratar`
atende como hoje. Os toques `vaga:*` de mensagens antigas e o retorno da Fran continuam no fluxo fixo.

**2. O modo da vaga.** `vagas.modo`: `ficha_ou_curriculo` ou `curriculo` (padrão). A migração põe a
Auxiliar de produção em `ficha_ou_curriculo`. A tela Destinos mostra e troca o modo.

**3. As ferramentas, por estado da conversa.** O que não é oferecido não pode ser chamado:

| Ferramenta | Quando é oferecida | O que faz |
|---|---|---|
| as cinco do #1520 | sempre | como hoje |
| `escolher_vaga` | conversa de vaga, com vaga aberta | marca a vaga da conversa (lista fechada das abertas) |
| `comecar_ficha` | a vaga da conversa é `ficha_ou_curriculo`, e o aviso ainda não foi mandado | manda o **aviso de cadastro** (texto do dono, em português ou espanhol) e registra `olivia: aviso da ficha` |
| `anotar_ficha` | depois do aviso | grava no rascunho um ou mais dos cinco campos (`nome`, `cidade`, `experiencia`, `quando_comeca`, `como_chega`, texto de até 200 letras) e a `lingua` (`pt` ou `es`). Com os cinco preenchidos, **o código** cria a candidatura e devolve "ficha completa e encaminhada" |

Na vaga `curriculo`, `comecar_ficha` e `anotar_ficha` não existem na lista: sem arquivo não há
candidatura. A instrução diz o que falar a esse candidato (o currículo é indispensável; pode ser foto) e
manda oferecer a vaga de ficha, se houver uma aberta.

**4. A ficha é uma candidatura.** `candidaturas.tipo_arquivo = 'ficha'`, `ficha` (os cinco campos, a
língua, e `faltou` quando parcial), sem `pdf`, `triagem_erro = 'ficha: sem triagem'`. Vai à Fran pelo
laço de hoje, como uma página (`vaga.pdf_da_ficha`, no molde de `pdf_da_foto`): vaga, as respostas como
a pessoa deu, "respondeu em espanhol" quando for o caso, e **"incompleta: faltou X e Y"** quando parcial.
Sem botões de triagem (não houve); com o botão de conversar. Doze meses, como o currículo.

**5. A ficha pela metade (D4).** Na rotina do minuto: rascunho com ao menos o nome, incompleto, sem
candidatura, com a última mensagem da pessoa há 2 h ou mais e a janela de 24 h aberta, e sem lembrete
ainda → **um** lembrete de cadastro ("Faltou só ... para eu passar a sua ficha à equipe", na língua da
conversa). Quatro horas depois do lembrete sem resposta, ou quando a janela fechar, a parcial vira
candidatura e vai à Fran. Rascunho sem nome não vira candidatura; conta como "sem saída" no vigia. Os
dois tempos são ajustes (`olivia.ficha_lembrete_h`, `olivia.ficha_parcial_h`).

**6. A trava contra o "anotei" falso.** Código, não instrução: a fala que afirma ter anotado,
encaminhado ou passado à equipe, numa conversa de vaga sem candidatura gravada nesta mensagem nem antes,
é recusada (`olivia: recusada: promessa`) e sai no lugar a frase de cadastro que diz o que ainda falta.
Conta no vigia como as outras recusadas.

**7. Espanhol.** A instrução passa a dizer: responda na língua da **última** mensagem da pessoa,
inclusive quando ela é a transcrição de um áudio. O aviso, o lembrete e a frase do que falta existem nas
duas línguas no cadastro.

**8. A chave.** `olivia.conduz_vaga`, ajuste no banco, nasce `false`, liga e desliga por script sem
restart, e só vale com `OLIVIA_FALA` ligada. Desligada, a conversa de vaga é a de hoje.

**Por que B e não A:** a vaga de currículo obrigatório é a de pior conversão (12 de 15 sem currículo) e
ficaria no texto fixo em português. **Por que não C:** perguntas editáveis por vaga antes de a Fran ver
uma ficha real é construir flexibilidade no escuro.

## Escopo desta etapa

**Dentro:** a entrada antes do fluxo fixo; `vagas.modo` e a tela Destinos; as três ferramentas por
estado; o rascunho e a candidatura em ficha; a página à Fran; o lembrete único e a parcial; a trava da
promessa; a língua; a chave; o apagamento de 12 meses cobrindo a ficha; o vigia contando ficha e
incompleta; inventário e política; manuais; a medição de uma semana.

**Fora:** a conversa técnica do agrônomo (terceiro modo); perguntas da ficha editáveis por vaga; os
textos longos do fluxo fixo (#1524); o defeito da vaga trocada no caminho de reserva (#1522); pré-triagem
da ficha por IA; o candidato reconhecido como cliente.

## Impacto em produção

`axiaatende-recepcionista` (a conversa) e `axiaatende-backend` (a tela Destinos e a migração). Uma
migração nova: colunas em `vagas`, `conversas` e `candidaturas`, o `CHECK` de `tipo_arquivo` reescrito,
ajustes e textos de cadastro; sem perda. Restart dos dois serviços. Custo de API: a conversa de vaga
passa a usar o Sonnet (medido em `uso_ia`, função `conversa`); eram 38 conversas em 5 dias.

## ROLLBACK_PLAN

1. Desligar a chave `olivia.conduz_vaga` pelo script: na hora, sem restart, a conversa de vaga volta ao
   fluxo fixo. As fichas já gravadas ficam como candidaturas, e a Fran já as recebeu.
2. Rascunhos em curso no momento do desligamento: o envio da parcial continua rodando (não depende da
   chave), então quem deu o nome ainda chega à Fran.
3. Desfazer o código: `git revert` dos commits do chamado e a `_VOLTA` da migração, que recusa se houver
   candidatura em ficha (como a 062 recusa com currículo); nesse caso as fichas são apagadas antes, por
   decisão do dono.
4. Inventário e política: revert no AxiaSecurity.

## Manual de uso

**Manuais que mudam:** `docs/manuais/olivia.md` e `docs/manuais/trabalhe-conosco.md`. O texto abaixo
entra no `trabalhe-conosco.md`, seção nova "A ficha de contato".

1. **Para que serve.** Quem quer trabalhar na Renascer e não tem currículo deixa de ficar sem saída: a
   OlivIA faz cinco perguntas simples e a Fran recebe uma ficha de contato. Quem tem currículo continua
   mandando o PDF ou a foto.
2. **Quem usa e quando.** O candidato, a qualquer hora, pelo WhatsApp. A Fran recebe a ficha como
   recebe o currículo. Quem cadastra a vaga escolhe, na tela Destinos, se ela aceita ficha.
3. **O caminho comum.**
   1. A pessoa chega pelo anúncio ou pelo menu. A OlivIA diz qual é a vaga e pergunta se ela tem
      currículo.
   2. Tem: manda o PDF ou a foto, e a Fran recebe.
   3. Não tem, e a vaga aceita ficha: a OlivIA avisa que as respostas vão à equipe de seleção e ficam
      guardadas por 12 meses, e pergunta o nome, a cidade, no que já trabalhou, quando pode começar e
      se tem como chegar a Cunha Porã todos os dias.
   4. Respondidas as cinco, a Fran recebe a ficha.
   5. Se a pessoa parar no meio, recebe um lembrete, uma vez só. Sem resposta, a Fran recebe o que há.
4. **Sinais.**
   - Na mensagem à Fran, **"Ficha de contato"** no lugar do currículo. **"Incompleta: faltou ..."** quer
     dizer que a pessoa parou de responder: o que falta não foi perguntado de novo, e ela tem o número
     para chamar.
   - **"Respondeu em espanhol"**: as respostas estão como a pessoa escreveu ou falou.
   - Ficha não tem pré-triagem: não há "Triagem certa" nem "Triagem errada".
   - Na tela Destinos, cada vaga mostra **Ficha ou currículo** ou **Currículo obrigatório**.
   - No resumo diário ao dono, "N fichas incompletas".
5. **O que NÃO faz.** Não pergunta idade, estado civil, nacionalidade, filhos nem saúde. Não aceita
   ficha em vaga de currículo obrigatório: ali, sem arquivo, não há candidatura, e a OlivIA oferece a
   vaga que aceita ficha, se houver. Não insiste: o lembrete é um só, e só nas primeiras 24 horas. Não
   avalia o candidato: a ficha vai à Fran como foi respondida. Com a chave desligada no servidor, a
   conversa de vaga volta aos textos fixos de antes, que pedem PDF ou foto.

**O que os manuais passam a dizer errado:** `trabalhe-conosco.md` ("o candidato manda PDF ou foto" como
único caminho; "a conversa de vaga é do fluxo fixo"); `olivia.md` ("cinco ferramentas"; "a conversa de
vaga vem antes dela").

## Próximo passo
/writing-plans
