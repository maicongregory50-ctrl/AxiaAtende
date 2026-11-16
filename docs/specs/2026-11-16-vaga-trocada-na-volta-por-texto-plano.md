# Plano — quem volta por texto não cai na primeira vaga aberta

**Chamado:** #1522
**Data:** 16/11/2026
**Executável pelo agente:** não — executado em sessão, com o dono no teclado (o PLANEJADOR não lê este projeto e o EXECUTOR está parado até o reboot do servidor).

## O problema

Quem já teve conversa de vaga e volta escrevendo texto era posto na primeira vaga aberta do
cadastro, sem escolher (`backend/vaga.py`, `volta`). Com duas vagas abertas, quem queria a segunda
recebia a região, o pedido de currículo e a triagem da primeira. Caso lido em 16/11: o candidato
escreveu "queria ver se tem só vaga pra empilhadeira" e recebeu a abertura da Vaga Auxiliar de
produção. O #1474 criou a lista de escolha para quem vem pelo menu; `volta` ficou com a vaga única.

## O universo medido

Contado no chamado: 1 caso nas 21 conversas lidas de 13/11 13h a 16/11 08h. Não foi contado quantas
conversas passaram por `volta` desde que há duas vagas abertas, nem se alguma candidatura já seguiu
para triagem com a vaga errada — fica como conferência do dono (abaixo).

## Os fios que encostam

- `vaga_aberta(con)` sem anúncio (a de id menor) era usada em três pontos sem escolha: `volta`,
  o toque de vaga numa conversa antiga e o botão "esta vaga" sem vaga na conversa. Os três mudam.
- `_responder_texto`: com a conversa sem vaga e mais de uma aberta, as respostas que dependem da
  vaga (região, salário, retorno, apresentação, sem PDF, pedido do PDF) saíam em branco ou com a
  vaga de outro. Passam a devolver a lista das vagas.
- "Outras áreas" (banco de currículos) também deixa a conversa sem vaga, de propósito: não é
  tratado como falta de escolha.
- Com UMA vaga aberta nada muda. Quem vem por anúncio continua na vaga do anúncio.
- Vale com a voz da OlivIA desligada (#1520): é o caminho do menu de hoje. O #1525 (a OlivIA conduz
  a vaga) mexe no mesmo arquivo e ainda não tem código.

## Passos

**1. Código** — `backend/vaga.py`: `_vaga_unica` (a vaga quando há uma só) e `_falta_escolher`;
`volta` usa a vaga da conversa anterior se continua aberta, senão a única, senão nenhuma;
`_responder_texto` devolve a lista quando falta escolher; o toque em conversa antiga e o botão
"esta vaga" deixam de assumir a primeira do cadastro.
- Verificação: `python -m pytest tests/test_vaga.py tests/test_motor.py` verde.
- Reversão: reverter o commit.

**2. Testes** — `tests/test_vaga.py`: o caso de 16/11 (lista em vez da primeira vaga, o "Sim" não
abre vaga, a escolha vale até a candidatura); quem já tinha escolhido continua na vaga dele; a vaga
única só existe com uma aberta.

**3. No ar** — restart do `axiaatende-recepcionista` pela Porta-Ação.
- Verificação: `http://127.0.0.1:8008/saude` responde depois do restart.

**4. Devolver.**

O restart não vai no bloco abaixo: a skill `/demanda` não conhece os serviços do AxiaAtende (a
Porta-Ação conhece, desde o #973), então ele é pedido direto à porta, nesta sessão.

```pos-entrega
dono=listar as candidaturas desde 12/11 que vieram de conversa de volta e conferir a vaga com o candidato ou a Fran
```

## Riscos de execução

- O conserto não corrige candidatura que já seguiu com a vaga errada: é dado a jusante.
- Quem volta e já tinha vaga na conversa anterior continua nela mesmo que hoje queira outra; ele
  troca tocando "Era outro assunto" e voltando pelo menu. É escolha de desenho desta etapa.
