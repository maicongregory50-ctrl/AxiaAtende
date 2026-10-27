# Envios — manual de uso

> O acompanhamento de cada envio pelo WhatsApp aos clientes: quem recebeu, quem leu, quem quis, quem
> recusou e quanto custou. No AxiaAtende: **http://127.0.0.1:8009**, aba **Envios** (#950, 09/10/2026).
> O envio nasce e é aprovado no AxiaMarketing, tela **Publicações** (manual
> `C:\AxiaMarketing\docs\manuais\publicacoes.md`).

## 1. Para que serve

Ver, cliente por cliente, o que aconteceu com um envio aprovado. Há dois tipos:

- **Material para cliente** — a peça da esteira, com a versão de cada revenda. Vai um **convite** com
  a capa e os botões "Quero receber" / "Não quero receber"; quem toca "Quero receber" recebe as
  imagens na conversa, sem custo, e o aceite fica gravado.
- **Comunicação direta** — uma arte com o texto e o botão "Falar com meu atendimento": um toque e
  o cliente já está no WhatsApp do responsável dele, e o toque fica anotado. **Só vai a quem já
  aceitou.**

## 2. Quem usa e quando

Você, no computador, nos dias seguintes a um envio aprovado.

## 3. O caminho comum

1. Escolha o envio (tipo · campanha · data).
2. Leia a barra verde (o que é, quem aprovou e se está **enviando**, **concluído** ou **PARADO**) e os
   cartões.
3. Filtre por responsável ou por resposta.
4. Na lista, veja quem escreveu alguma coisa: o texto aparece ao lado.
5. Se a barra disser **PARADO pela nota do número**, leia o porquê abaixo antes de clicar **Religar o
   envio**.

## 4. O que significa cada sinal

| Sinal | Quer dizer |
|---|---|
| **Convidados / Enviados** | quantas mensagens pagas saíram (o convite, ou a comunicação direta) |
| **Entregues** e **Lidos** | a confirmação que a Meta devolve |
| **Quero receber** | tocou o botão: recebeu as imagens e o aceite ficou gravado |
| **Não quero** | tocou o botão: saiu da lista para sempre, e o responsável dele recebeu um aviso no WhatsApp para um contato direto |
| **Tocou em falar** (só na comunicação direta) | tocou "Falar com meu atendimento" e foi levado ao WhatsApp do responsável. Se ele mandou mensagem, isso acontece no WhatsApp do responsável: esta tela não vê |
| **Não entregues** | a Meta recusou, em geral porque o número não é WhatsApp; o cadastro do cliente precisa de correção no ERP |
| **Sem responsável** | o canal comercial do cadastro do cliente no ERP está vazio: ele **não recebe** até alguém preencher. A linha mostra o vendedor do último pedido como sugestão |
| **Comprador / Técnico** na linha (desde 26/10/2026, #1142) | **quem** é a pessoa no cliente: o comprador decide a compra; o técnico vai ao produtor e recomenda. Os dois podem estar no mesmo envio (é o caso da cooperativa, que recebe os dois materiais na mesma semana), e cada um conta como um destinatário, com o lote e a resposta dele |
| **O mesmo número não aparece duas vezes** | uma pessoa recebe **uma vez por envio**, mesmo sendo contato de vários cadastros. O banco recusa a segunda, e quem monta o pedido já junta por número antes |
| **Sem aceite** (só na comunicação direta) | o cliente nunca aceitou: precisa tocar "Quero receber" num material antes |
| **Na fila** | ainda vai receber, num dos próximos lotes |
| **Custo US$** | o valor estimado das mensagens pagas deste envio (cerca de US$ 0,07 cada) |
| **"sem WhatsApp"** | o cadastro não tem celular válido |
| **"recusou antes" / "já recebeu esta peça"** | não recebe de novo |
| **"fora: teto do mês (já recebeu duas)"** (#1163) | o **comprador** já recebeu duas mensagens nossas neste mês. Conta **um por envio recebido** (o convite do material ou a mensagem da direta, de qualquer envio); as imagens depois do "Quero receber" são parte do mesmo envio e não contam de novo. Ele não recebe esta, e volta a receber no mês seguinte. O mês é o do calendário, em Brasília, e a conta é feita na hora em que o lote sai. O técnico e o contato sem papel não entram no teto |
| **Imagens "3 de 3"** | todas as imagens chegaram a quem quis |
| **"—"** | ainda não aconteceu (não é zero) |
| **Nota do número: verde / amarela / vermelha** | a nota de qualidade que a Meta dá ao número da empresa. Só sai lote com verde |
| **PARADO pela nota do número** | a nota caiu para amarela ou vermelha: os envios param sozinhos para proteger o número. **Religar o envio** volta a mandar (só com a nota de volta ao verde) |

**Os lotes:** saem até 20 clientes por dia, na ordem do ranking de faturamento (Top 20, depois o 21º
ao 40º…), e só com a nota verde.

**O teto do comprador** (desde 27/10/2026, #1163): nenhum comprador recebe mais de **duas**
mensagens nossas no mês. Quem já recebeu duas fica **"fora: teto do mês"** naquele envio — com o
motivo escrito na linha — e o lote segue com os próximos da fila. A tela Publicações, no Marketing,
mostra antes de agendar quantos ficariam fora; quem decide de verdade é este envio, na hora de sair.

**O resumo ao representante** (desde 26/10/2026, #1142). Depois de cada lote, o **representante** (ou
o corretor) recebe **uma** mensagem no WhatsApp: quantos clientes dele receberam, o que receberam, e
o lembrete de que o que cada um respondeu aparece no **Relacionamento**, no ERP — que é a tela dele.

- **Uma por lote, não uma por cliente.** Cinco clientes num lote são uma mensagem, não cinco.
- **Nunca vai ao dono nem ao flutuante.** Até 23/10/2026 saía uma **cópia de cada convite** ao
  responsável, e no material às revendas o responsável é o dono — foi assim que as artes da Agro
  Real e da Agro Símil chegaram ao WhatsApp dele. A cópia acabou.
- **Se o resumo não chegar:** o modelo `aviso_lote_do_representante` precisa estar aprovado na Meta,
  na categoria **Utilidade**. Sem ele o aviso fica guardado com o erro escrito e **ninguém recebe** —
  nada se perde, e sai quando o modelo entrar.

## 5. O que a tela NÃO faz

- **Não cria nem aprova envio:** o envio nasce e é aprovado em Publicações, no AxiaMarketing.
- **Não reenvia imagem depois de 24 horas** do "Quero receber": a Meta só deixa mensagem grátis
  dentro dessa janela.
- **Não avisa o responsável de quem quis receber:** só de quem recusou — e o **resumo do lote**, que
  diz quantos receberam, sem dizer quem respondeu o quê. *(Até 26/10/2026 o código mandava uma cópia
  de cada convite ao responsável, contra o que esta linha já dizia; o #1142 fez o código cumprir o
  manual.)*
- **Não manda nada ao dono:** o resumo é só de representante e corretor.
- **Não manda comunicação direta a quem nunca aceitou.**
- **Não preenche o responsável:** isso é no cadastro do cliente, no ERP (o mutirão).
- **Não tira ninguém do teto do mês:** o comprador no teto volta a receber no mês seguinte; não há
  botão para mandar a terceira.
