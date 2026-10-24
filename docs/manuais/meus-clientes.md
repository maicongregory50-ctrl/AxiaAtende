# Meus clientes: contar a visita pelo WhatsApp da Renascer

> Para o consultor que está no piloto (#1090 etapa 3, desde 23/10/2026; hoje, o Maicon). A spec é
> `C:\AxiaGestao\docs\specs\2026-10-23-relacionamento-etapa3-visita-pelo-whatsapp.md`. O que acontece
> no sistema depois está no manual do Relacionamento, `C:\AxiaGestao\docs\manuais\relacionamento.md`.

## 1. Para que serve

Você fala com o cliente e conta pelo WhatsApp da Renascer como foi. A OlivIA põe no sistema do jeito
que a tela do Relacionamento pede, e você não precisa abrir o sistema. Os clientes vêm um por vez, na
ordem da sua fila: os atrasados primeiro.

## 2. Quem usa e quando

O consultor que está no piloto, quando vai trabalhar a carteira: de manhã, antes das ligações, ou
entre uma visita e outra.

## 3. O caminho comum

1. Escreva *meus clientes* para o **WhatsApp da Renascer (49 3664 0121)**. Também vale escrever
   *bom dia* (ou *menu*) e tocar **📋 Meus clientes**.
2. Vem **um cliente**: nome, cidade, faixa, o contato, os meses em que ele compra, o que comprou na
   última safra e na atual, e se o contato é de **campanha** (com a versão: recompra ou apresentação)
   ou de **cortesia**. Toque **Chamar <nome> no WhatsApp** para abrir a conversa com ele, ou toque no
   telefone para ligar.
3. Depois de falar, conte aqui **por escrito**, do seu jeito, em uma ou mais mensagens:
   *"liguei pro Márcio, vão querer +Palha e aveia no inverno, passo lá dia 5 com preço"*.
   A OlivIA responde **"Recebi."** e espera você parar de escrever (meio minuto).
4. Se faltar alguma coisa, ela pergunta com botões, uma por vez: **como foi** (visita, ligação,
   WhatsApp), **se ofereceu a campanha**, **a resposta**, e, em recusa, **o motivo**.
5. Vem o cartão **"Confere?"** com o registro montado. Toque **✅ Confere**. Em seguida vem
   **"Gravado no sistema ✔"** e o próximo cliente. Se algo estiver errado, toque **✏️ Corrigir** e
   escreva de novo, completo.
6. **⏭ Depois** deixa o cliente para amanhã e manda o próximo. **🛑 Parar por hoje** encerra; para
   voltar, escreva *meus clientes* (ou *próximo*), e ele continua de onde parou. Com um cliente
   aberto, *meus clientes* repete a ficha dele.

## 4. O que significa cada sinal

| Sinal | O que quer dizer |
|---|---|
| **cortesia** | não há campanha aberta para aquele cliente: não há "ofereceu", nem recusa com motivo |
| **campanha *X* · recompra / apresentação** | há oferta a fazer; a versão é a que o histórico de compra dele indica |
| **⏰ atrasado N dias** | passou do prazo de contato de pessoa |
| **próximo contato: 05/11** | o que você disse; **(sugerido)** = você não disse, e vale o ritmo do cliente, como na tela |
| **"Anotado. Vai ao sistema agora."** | você conferiu; falta o sistema receber |
| **"Gravado no sistema ✔"** | entrou no histórico do cliente, com "pelo WhatsApp" ao lado do seu nome |
| **"O sistema não aceitou…"** | o sistema recusou com a frase dele (por exemplo, um pedido que não é desse cliente); escreva de novo |
| **"Sua lista ainda não chegou do sistema"** | a cópia da sua fila não chegou; ela vem a cada 10 minutos |
| **"Acabaram os clientes da sua lista por hoje"** | todos já foram contados ou deixados para depois hoje |

## 5. O que NÃO faz

- **Não grava nada sem o seu Confere.**
- **Não manda nada ao cliente:** quem fala com ele é você.
- **Não entende áudio, foto nem print** nesta primeira versão (vem na segunda).
- **Não muda o responsável nem a fila:** a ordem é a do Relacionamento.
- **Não chama você sozinha de manhã:** por enquanto, a conversa abre quando você escreve.

**Pré-requisitos:** estar no piloto (tabela `atendimento.clientes_consultores`, por ora pela mão de
quem cuida do sistema); ter login no ERP ligado ao seu cadastro comercial; o agente ATENDIMENTO com a
atividade CRM.WPP.

Se algo sair diferente do que está aqui, avise.
