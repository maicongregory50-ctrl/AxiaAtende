# Custos — o que paga por uso, por função

> Quanto a Renascer paga por mês a cada serviço cobrado por uso, e **qual função gerou cada gasto**. No
> AxiaAtende: **http://127.0.0.1:8009**, aba **Custos** (#1223, 31/10/2026). Só aparece para o login do
> dono.

## Para que serve

Três serviços cobram por uso: a **Meta**, pelas mensagens pagas do WhatsApp; a **Anthropic**, pela OlivIA
(Claude); e o **Google**, pelo Gemini do Marketing. A tela mostra quanto cada função custou no mês, para
decidir se ela compensa o que custa. O que roda na assinatura do Claude (o suporte, os agentes da esteira,
as sessões) não aparece aqui, porque não é cobrado por uso.

## Quem usa e quando

Só o dono. No começo do mês, para fechar o anterior, ou quando uma função nova entra no ar e ele quer ver
quanto ela pesa. A aba some para qualquer outro login.

## O caminho comum

1. Abrir **Custos** no menu à esquerda.
2. Escolher o mês nas setas (abre no mês corrente). Os três cartões do alto dão o total de cada serviço.
3. Ler a tabela: uma linha por função, com o serviço, o item (a categoria que a Meta cobrou, ou o modelo
   de IA), a quantidade (mensagens ou chamadas, com os tokens) e o valor.
4. Na Meta, descer até **Calculado × cobrado, por dia** e comparar o valor calculado aqui com o que a
   própria Meta informa.
5. Quando a Meta ou o Google mudarem o preço: **Preços** → escolher o serviço → o item (a lista sugere o
   que já apareceu) → a data em que o preço passou a valer → o valor → **Lançar preço**. O preço antigo
   continua valendo para os dias anteriores.

**Os preços já vêm lançados** (31/10/2026), marcados "(semente)" na aba Preços:

- **Meta**, por mensagem, em dólar (a conta é faturada em dólar): marketing **US$ 0,0625** e utilidade
  **US$ 0,0068**, conferidos contra o que a própria Meta cobrou da nossa conta em 28, 29 e 30/10, com
  diferença zero. marketing_lite e autenticação pela tabela da Meta.
- **Claude** (Haiku 5.5): US$ 0,10 por milhão de tokens de entrada e US$ 0,50 de saída.
- **Gemini**: o do olhar sobre a foto (gemini-3.8-flash), US$ 0,75 e 3,75 até 31/12/2026, e **US$ 1,50 e
  7,50 a partir de 01/01/2027**. Esse aumento já está lançado, e a tela troca sozinha na virada. O do
  editor (gemini-2.5-flash-image), US$ 0,30 de entrada e US$ 30,00 de saída, que é o preço do token de
  imagem (cerca de US$ 0,039 por imagem).

Só é preciso lançar preço quando a Meta ou o Google mudarem a tabela, ou quando aparecer um modelo novo
como "sem preço" (o nome na tela é o que o Google devolveu; lance com esse nome).

## O que significa cada sinal

| Sinal | Quer dizer |
|---|---|
| **sem preço** | a quantidade é real, mas falta o preço daquele item naquela data. **Não é US$ 0**: lance o preço e o valor aparece. "+ 3 sem preço" quer dizer que três ficaram de fora da soma. |
| **sem função** | mensagem que a Meta cobrou e que o sistema não sabe de qual função saiu. Até 30/10/2026 isso é esperado (antes, o modelo de cada envio não era registrado). Depois, se aparecer, é defeito: abra chamado. |
| **pelo resumo** | mensagem de antes de 30/10 cuja função foi tirada do resumo do envio (convite, comunicação direta), e não do registro do modelo. É boa, mas indireta. |
| **conferido** | a Meta informou o valor daquele dia. Diferença pequena entre calculado e cobrado é arredondamento ou câmbio; diferença grande quer dizer preço desatualizado na tabela. |
| **sem acesso** | a Meta não deixou ler o valor oficial. O calculado continua valendo. **"—" na coluna Cobrado não é zero.** |
| **erro na leitura** | a Meta respondeu de um jeito que o sistema não entendeu. O detalhe aparece ao parar o mouse no selo. |
| **sem conferência** | o dia ainda não foi lido. A conferência roda uma vez por dia, depois das 06:00, e relê os 3 dias anteriores, porque a Meta fecha o dia com atraso. |

A categoria da Meta é **a que ela cobrou**, não a do cadastro do modelo: em 30/10/2026 a Meta cobrou como
marketing um modelo cadastrado como utilidade. É o que vale para a fatura.

## O que a tela NÃO faz

- **Não é a fatura.** O valor oficial é o da Meta, da Anthropic e do Google.
- **Não barra nem avisa** quando o gasto sobe. O teto de US$ 10 por mês do Gemini continua no
  AxiaMarketing, e ele decide pela estimativa de lá, não pelo valor desta tela.
- **Não mostra o custo do Claude e do Gemini antes de 31/10/2026**, porque ninguém o registrava. A Meta
  vem desde 09/10/2026.
- **Não mostra a assinatura do Claude Code**, que não é cobrada por uso.
- **Não substitui a previsão da tela Envios.** O "Custo US$" de lá é a previsão do envio; o fato, depois
  das mensagens saírem, está aqui.

## Quando parar de registrar

O registro do modelo de cada mensagem depende do ajuste `enviadas.guardar_texto` (o texto exato do que
mandamos, #1205). Desligado, as mensagens novas aparecem como **sem função**, de forma visível. A
conferência com a Meta desliga sozinha pelo ajuste `custos.conferir_meta`, sem reiniciar nada.
