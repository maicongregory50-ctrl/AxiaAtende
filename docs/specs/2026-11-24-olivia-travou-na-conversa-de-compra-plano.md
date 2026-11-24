# Plano — a conversa de compra que anda por texto não leva a marca de travou

**Chamado:** #1784
**Data:** 24/11/2026
**Executável pelo agente:** não — executado em sessão, com o dono no teclado (o PLANEJADOR não lê este projeto).

## O problema

Na conversa 370 (24/11, 13:12 a 13:21) a pessoa quis comprar centeio, respondeu a tudo por texto e
saiu com o cartão do consultor. As três últimas falas da OlivIA foram gravadas como
`olivia: fala (travou)`. O sinal fraco de `travou` (`backend/olivia.py`) conta as falas dela desde o
último toque de botão, e na conversa de compra por texto não há toque: a partir da sexta resposta a
instrução leva a marca "a conversa travou". Com a marca posta, a repetição de qualquer mensagem,
inclusive um segundo "Sim", manda o menu e a cala.

A função já tira dessa contagem a conversa de vaga (#1543), a qualificação do produtor (#1660) e a
da carteira (#1754). A conversa de compra (#1589) ficou de fora.

## O universo medido

Desde 19/11/2026: 4 conversas com fala da OlivIA; 3 terminaram com cartão do comercial; 1 delas (a
370) teve a marca, em 3 das 8 falas; nenhuma virou menu. As outras duas com cartão tiveram menos de
seis falas. A conversa de compra completa tem no mínimo seis trocas.

## Os fios que encostam

- `travou` é lida em um ponto só (`atender`, `backend/olivia.py`): decide a marca na instrução, o
  resumo da fala (`olivia: fala (travou)`) e, no segundo sinal forte, o menu.
- `_ja_travou` lê o resumo gravado: conversa que já levou a marca antes do conserto continua com ela.
- O vigia das 23:40 e a tela Recepção não leem a marca de travou (leem `saida`): nada muda neles.
- Com `olivia.conduz_venda` desligada, nada muda: a contagem volta a valer para quem é de fora.
- Com a chave ligada, o sinal fraco deixa de existir para quem é de fora (vaga, qualificação,
  carteira e, agora, a conversa aberta). Ficam o "não é isso" e a repetição de mensagem de mais de
  três palavras.

## Passos

**1. Código** — `backend/olivia.py`, `travou`: a conversa que não é de vaga, com
`olivia.conduz_venda` ligada, entra na mesma regra da vaga.
- Verificação: `python -m pytest tests/test_olivia_venda.py tests/test_olivia.py tests/test_olivia_lead.py` verde.
- Reversão: reverter o commit.

**2. Teste** — `tests/test_olivia_venda.py`: sete respostas por texto sem nenhuma fala marcada; um
segundo "Sim" não manda o menu; "não é isso" continua pondo a marca.

**3. Manual** — `docs/manuais/olivia.md`, seção 3, item 5: a conversa de compra entra na frase da vaga.

**4. No ar** — restart do `axiaatende-recepcionista` pela Porta-Ação.
- Verificação: `http://127.0.0.1:8008/saude` responde depois do restart.

**5. Devolver.**

## Riscos de execução

- A conversa de fora que de fato não anda, com a venda ligada, só muda de abordagem com "não é
  isso" ou com a repetição de uma mensagem longa. É a mesma escolha feita para a vaga em 17/11.
