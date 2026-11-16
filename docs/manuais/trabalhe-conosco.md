# Trabalhe conosco — manual de uso

**Chamado:** #1098 · **Spec:** `docs/specs/2026-10-22-trabalhe-conosco-vaga-e-pre-triagem.md`
· **Foto como currículo e a OlivIA:** #1520 (`docs/manuais/olivia.md`)
· **A ficha de contato e a OlivIA conduzindo a vaga:** #1525 (`docs/specs/2026-11-16-olivia-conduz-a-vaga-ficha-e-curriculo.md`)

> **Dois jeitos de a conversa da vaga acontecer.** Com a chave `olivia.conduz_vaga` **ligada** (#1525), a
> OlivIA conduz a conversa inteira de quem chega pela vaga, com as palavras dela, e aceita a **ficha de
> contato** na vaga que permite (seção 6). Com a chave **desligada**, ou se a IA não responder, vale o
> fluxo fixo descrito nas seções 3 a 5, com os textos aprovados, que pede PDF ou foto. O fluxo fixo é a
> reserva: nada dele foi apagado.

## 1. Para que serve

Receber os candidatos da vaga aberta pelo WhatsApp da empresa (49 3664 0121) sem ocupar ninguém. O
atendimento explica a vaga, responde as dúvidas mais comuns com textos aprovados, recebe o currículo
em PDF **ou em foto** e entrega cada um à Fran: o PDF já com uma pré-triagem, a foto sem ela (#1520). A
decisão sobre o candidato é sempre dela.

**Desde o #1520**, quem é de fora e escreve **fora** da conversa da vaga (por exemplo, depois de tocar
*Era outro assunto* por engano) conversa com a OlivIA, que reconhece o currículo em PDF ou em foto e o
encaminha à Fran do mesmo jeito: não há mais "não consigo abrir arquivo" para o candidato. Isso vale com
a chave `OLIVIA_FALA` ligada; a foto dentro da conversa da vaga vale sempre.

## 2. Quem usa e quando

- **O candidato**, quando chama o 49 3664 0121 pelo anúncio da vaga ou toca *Trabalhe conosco* no menu.
- **A Fran**, quando chega cada currículo no WhatsApp dela.
- **O dono**, na Recepção (para ver quantos chegaram) e na tela Destinos (para fechar a vaga ou
  desligar a pré-triagem).

## 3. O caminho comum

**O candidato:**
1. Quem vem pelo anúncio cai direto na vaga, sem o menu: vê os quatro requisitos e o pedido do
   currículo **em PDF**, com o aviso de que ele é guardado e lido por uma ferramenta de análise, e
   que a decisão é de uma pessoa. Há um botão só, *Era outro assunto*. **O candidato não é perguntado
   se atende aos requisitos:** quem analisa é a pré-triagem e a Fran (dono, 22/10/2026).
2. Quem toca *Trabalhe conosco* no menu escolhe antes: **a vaga aberta**, que segue como no item 1,
   ou **Outras áreas**: o atendimento pede o PDF e avisa que ele fica guardado para as próximas
   vagas. Esse currículo vai à Fran como *Banco de currículos*, sem pré-triagem. **Com mais de uma
   vaga aberta** (#1474, 12/11/2026: *Auxiliar de produção* e *Operador de empilhadeira*), a pergunta
   vem como **lista** — *Ver as vagas* — com uma linha por vaga (o nome e o primeiro requisito), mais
   *Outras áreas* e *Era outro assunto*; a escolhida segue como no item 1, com os requisitos dela.
   Quem vem pelo anúncio continua caindo direto na vaga daquele anúncio. Cabem até 8 vagas na lista.
3. Mandou o PDF **ou a foto do currículo**: recebe *"Recebemos o seu currículo ✅"*, com o aviso da
   pré-triagem e de que os pré-selecionados recebem retorno por ali. Word, áudio ou figurinha recebem
   *"Precisamos do seu currículo em PDF ou em foto"*.
4. Se escrever em vez de mandar, o atendimento responde com um dos textos aprovados: a região da vaga,
   salário e benefícios, prazo de retorno, "vocês receberam?", "não tenho PDF", falar com uma pessoa
   (o cartão da Fran). Fora disso, pede de novo o PDF, curto, sem repetir os requisitos (ou repete a
   pergunta do menu, se ela ainda não foi respondida). *Era outro assunto*, ou escrever *menu*, leva
   ao menu de sempre.
5. Quem volta em até 30 dias perguntando se o currículo chegou ouve *"Recebemos, sim ✅ (em 22/10)"*.

**A Fran:**
1. Chega uma mensagem **"Novo currículo · Vaga Comercial"**, com o PDF anexado.
2. Leia a pré-triagem: cada requisito diz *consta*, *não* ou *não consta no currículo*, e de onde a
   informação saiu.
3. Abra o PDF e decida. A pré-triagem é ajuda, não decisão.
4. Toque **Triagem certa** ou **Triagem errada**. Se errada, escreva em uma linha o que ela errou: é
   assim que as próximas ficam melhores.
5. Para falar com o candidato: no botão **Conversar** chega o cartão de contato dele; na mensagem que
   chega pelo modelo (quando você não escreveu para o número da empresa nas últimas 24 horas), o botão
   **Conversar com o candidato** abre a conversa direto.
6. **Currículo em foto** (#1520): chega como **imagem**, com a legenda *"Currículo em foto (sem
   pré-triagem) · Vaga: … · Candidato: … · Escreveu: …"* e só o botão **Conversar** — não há triagem a
   avaliar. Se você não escreveu para o número da empresa nas últimas 24 horas, a foto chega dentro de um
   **PDF de uma página** (*curriculo-foto.pdf*) na mensagem de sempre, com "Sem pré-triagem (foto: sem
   triagem)"; os botões Triagem certa/errada dessa mensagem são do modelo aprovado e podem ser ignorados.

**O dono:** na tela **Destinos**, cartão *Trabalhe conosco*: **Desligar pré-triagem** e **Fechar vaga**,
e o modo de cada vaga, **Ficha ou currículo** ou **Currículo obrigatório**, com o botão de trocar
(*Aceitar ficha* / *Exigir currículo*; #1525). A contagem diz "N currículos, M fichas".
Na tabela dos motivos, a pessoa de *Trabalhe conosco* é quem recebe os currículos.

## 4. O que significa cada sinal

| Sinal | Quer dizer |
|---|---|
| *consta* | o currículo mostra o requisito, e a linha diz onde |
| *não* | o currículo mostra o contrário (ex.: mora em outra cidade) |
| *não consta no currículo* | o currículo **não fala** disso. Não quer dizer que a pessoa não tenha |
| "Disse nos botões: não foi perguntado" | só na mensagem que chega pelo modelo: a pergunta saiu em 22/10, mas o texto aprovado na Meta ainda tem a linha. Na mensagem comum a linha não aparece |
| "Disse nos botões: (não) atende a todos os requisitos" | currículo de quem respondeu à pergunta antiga, antes de 22/10 |
| **Banco de currículos** no título | o candidato escolheu *Outras áreas* no menu, ou não havia vaga aberta |
| "Sem pré-triagem (pré-triagem desligada / a IA não respondeu / banco de currículos, sem vaga)" | o currículo chegou igual, sem a leitura da IA, pelo motivo entre parênteses |
| "Não consegui ler o arquivo" | o PDF é imagem ruim ou está protegido; abra e leia você |
| "Sem pré-triagem (foto: sem triagem)" / "Currículo em foto (sem pré-triagem)" | o candidato mandou a foto do currículo; a IA não lê foto para a triagem (#1520, D5) |
| "Escreveu: …" no resumo | o que o candidato escreveu na conversa antes de mandar o PDF |
| Na Recepção, **currículo recebido** | o PDF ou a foto chegou e vai à Fran |
| Na Recepção, **sem currículo** | a pessoa conversou e não mandou o currículo |

**O currículo que não chegou à Fran ainda:** enquanto a Meta não aprovar o modelo da mensagem, ele só
sai quando a Fran tiver escrito para o número da empresa nas últimas 24 horas. Os outros esperam na
fila, tentando uma vez por hora, e não se perdem.

## 5. O que NÃO faz

- **Não aprova, não reprova e não dá nota:** quem decide é a Fran.
- **Não pergunta ao candidato se ele atende aos requisitos:** quem confere é a pré-triagem.
- **Não faz pré-triagem do banco de currículos** (*Outras áreas*): não há requisitos contra os quais ler.
- **Não faz pré-triagem do currículo em foto** (#1520): a Fran olha a foto.
- **Não responde ao candidato o resultado:** o retorno é da Fran.
- **Não aceita Word ou texto como currículo:** só PDF ou foto (a foto passou a valer em 13/11/2026, #1520).
  Quem não tem currículo, na vaga que aceita, deixa a **ficha de contato** (seção 6, #1525).
- **Não inventa resposta:** a cada pergunta escolhe um texto aprovado pelo dono; o que não está na
  lista volta para a pergunta da vaga.
- **Não guarda o currículo para sempre:** em 12 meses o arquivo é apagado, com o nome e o número;
  ficam a data, a vaga e o retorno da Fran.
- **Não tem tela de candidatos:** a lista é o WhatsApp da Fran.
- **Não abre vaga nova nem muda requisitos ou textos:** isso é chamado.

## 6. A ficha de contato (#1525)

**Para que serve.** Quem quer trabalhar na Renascer e não tem currículo deixa de ficar sem saída: a OlivIA
faz cinco perguntas simples e a Fran recebe uma ficha de contato. Quem tem currículo continua mandando o
PDF ou a foto.

**Quem usa e quando.** O candidato, a qualquer hora, pelo WhatsApp. A Fran recebe a ficha como recebe o
currículo. Quem cadastra a vaga escolhe, na tela Destinos, se ela aceita ficha.

**O caminho comum.**
1. A pessoa chega pelo anúncio ou pelo menu. A OlivIA diz qual é a vaga e pergunta se ela tem currículo.
2. Tem: manda o PDF ou a foto, e a Fran recebe.
3. Não tem, e a vaga aceita ficha: a OlivIA avisa que as respostas vão à equipe de seleção e ficam
   guardadas por 12 meses, e pergunta o nome, a cidade, no que já trabalhou, quando pode começar e se tem
   como chegar a Cunha Porã todos os dias.
4. Respondidas as cinco, a Fran recebe a ficha.
5. Recebida a ficha ou o currículo, a OlivIA diz que a pessoa pode vir conhecer a empresa. Se ela quiser,
   a Fran é avisada e combina o dia.
6. Se a pessoa parar no meio, ou nem começar, recebe uma mensagem, uma vez só, nas primeiras 24 horas
   (duas horas depois da última mensagem dela). Sem resposta em quatro horas, ou fechadas as 24 horas, a
   Fran recebe o que houver da ficha, desde que a pessoa tenha dito o nome.

**Sinais.**
- Na mensagem à Fran, **"Ficha de contato"** no lugar do currículo: uma página em PDF
  (*ficha-de-contato.pdf*) com a vaga, o número e as cinco respostas como a pessoa deu, e só o botão
  **Conversar**. Fora das 24 horas da Fran, a página vem na mensagem de sempre, com "Ficha: <nome>" e
  "Sem pré-triagem (ficha: sem triagem)"; os botões Triagem certa/errada dessa mensagem são do modelo
  aprovado e podem ser ignorados.
- **"Incompleta: faltou ..."** quer dizer que a pessoa parou de responder: o que falta não foi perguntado
  de novo, e a Fran tem o número para chamar.
- **"Respondeu em espanhol"**: as respostas estão como a pessoa escreveu ou falou.
- **"Quer visitar a empresa"**: a pessoa aceitou o convite; o dia é combinado pela Fran. Se ela aceitou
  depois de a ficha ter ido, a Fran recebe uma linha à parte: *"O candidato ... quer visitar a empresa.
  Combine o dia com ele."*
- Ficha não tem pré-triagem: não há "Triagem certa" nem "Triagem errada" a avaliar.
- Na tela Destinos, cada vaga mostra **Ficha ou currículo** ou **Currículo obrigatório**.
- No resumo diário ao dono, "N fichas incompletas".

**O que NÃO faz.** Não pergunta idade, estado civil, nacionalidade, filhos nem saúde. Não aceita ficha em
vaga de currículo obrigatório: ali, sem arquivo, não há candidatura, e a OlivIA oferece a vaga que aceita
ficha, se houver. Não insiste: a mensagem de volta é uma só por conversa, e só nas primeiras 24 horas;
depois, o contato é abandonado. Não marca dia nem horário de visita. Não fala de salário nem de valor. Não
avalia o candidato: a ficha vai à Fran como foi respondida. A ficha é apagada em 12 meses, como o currículo.
Com a chave desligada no servidor, a conversa de vaga volta aos textos fixos de antes, que pedem PDF ou
foto; a ficha que já tinha nome ainda chega à Fran.

**Pré-requisito.** A vaga cadastrada e aberta, com o modo escolhido na tela Destinos, e a pessoa de
*Trabalhe conosco* (a Fran) na tabela dos motivos. A chave liga e desliga pelo `scripts\olivia.py` (manual
`olivia.md`, seção 6).
