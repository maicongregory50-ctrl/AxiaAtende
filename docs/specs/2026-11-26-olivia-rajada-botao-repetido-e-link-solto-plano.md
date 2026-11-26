# Plano — a OlivIA espera a rajada, não repete o botão e não conversa com link solto

**Chamado:** #1929
**Data:** 26/11/2026
**Executável pelo agente:** não — executado em sessão, com o dono no teclado (o PLANEJADOR não lê este projeto).

## O problema

Três defeitos do motor, lidos nas conversas 370, 375, 381 e 382 (24 a 26/11/2026):

1. **Rajada.** Cada mensagem é processada sozinha, em até 1 s. Quem escreve "Olá!" e "Boa tarde" em
   seguida recebe duas respostas; na conversa 381, seis mensagens em 20 s tiveram seis voltas dela.
2. **Botão repetido.** `_oferecer` (`backend/olivia.py`) manda a mesma opção do menu de novo com a
   anterior ainda sem toque: "Posso te passar para Financeiro › Financeiro?" saiu 5 vezes em 20 s.
3. **Link solto.** A mensagem que é só um link, de quem não está em conversa, vai ao modelo e ganha
   resposta (conversa 382, dois links de golpe às 05:07 e 05:40).

## O universo medido

De 24/11 a 26/11: 11 conversas com fala da OlivIA; 3 com rajada (370, 375, 381), 1 com o botão
repetido (381), 1 de link solto (382). Os intervalos das rajadas lidas: 0 s, 0 s, 2 s, 3 s. O tempo de
resposta dela hoje é de 1 s.

## Os fios que encostam

- `recepcionista.processar_pendentes` é o único leitor da fila `eventos_meta` (um laço, a cada 1 s).
  O evento adiado fica sem `processado_em`; a lista de adiados mora na memória do processo, e um
  restart só faz o evento ser lido na hora, como hoje.
- `olivia.atender` é chamado de três pontos de `motor.tratar` (vaga, carteira, de fora). A espera vale
  nos três e só para texto digitado; toque de botão, arquivo e áudio não esperam.
- `olivia.historico` já junta mensagens seguidas da pessoa num turno só: a resposta à última mensagem
  da rajada lê todas.
- `travou` compara a mensagem com a anterior já processada: não muda.
- Quem lê `enviadas.resumo` das ofertas (`_ja_falou`, o vigia, a tela Recepção) não muda: a oferta
  recusada não grava linha.
- A linha fixa do link solto é gravada em `enviadas` sem conversa: não abre conversa, não aparece na
  Recepção e o vigia não a conta.

## Passos

**1. A rajada** — `backend/motor.py` (`Adiar`, `Entrada.chegou_em`), `backend/recepcionista.py`
(`processar_pendentes` guarda o adiado e não o marca processado), `backend/olivia.py` (`atender`: o
texto que ela responderia espera `olivia.espera_rajada_s` segundos da chegada, padrão 5; e a mensagem
que tem outra mais nova da mesma pessoa na fila cede a vez, sem responder).
- Reversão sem código: o ajuste `olivia.espera_rajada_s` em 0 (`scripts\olivia.py espera-rajada 0`).

**2. O botão repetido** — `backend/olivia.py`, `_oferecer`: a mesma opção, com a última oferta sem
toque, não sai de novo; a ferramenta devolve ao modelo que os botões já estão na tela.

**3. O link solto** — `backend/olivia.py`, `atender`: mensagem que é só link, de quem não tem conversa
em curso nem parada nas últimas 24 h, recebe uma linha fixa uma vez em 24 h ("Links não são tratados
neste canal…"), sem chamar o modelo; as seguintes, silêncio.

**4. Testes** — `tests/test_olivia_rajada.py`: duas mensagens na fila, uma resposta; a espera adia e
depois responde; a espera em 0 não adia; a oferta repetida não sai; o link solto ganha a linha uma vez
e depois silêncio; o link no meio de uma conversa vai ao modelo.
- Verificação: `python -m pytest tests/test_olivia_rajada.py tests/test_olivia.py tests/test_olivia_venda.py tests/test_olivia_lead.py tests/test_olivia_carteira.py` verde.

**5. Script e manual** — `scripts/olivia.py` ganha `espera-rajada N`; `docs/manuais/olivia.md` diz a
espera, o botão e o link.

**6. No ar** — restart do `axiaatende-recepcionista` pela Porta-Ação.
- Verificação: `http://127.0.0.1:8008/saude` responde.

**7. Devolver.**

- Reversão do conjunto: reverter o commit e reiniciar.

## Riscos de execução

- Toda resposta a texto digitado passa de 1 s para uns 6 s. É o preço da espera.
- Quem manda mensagens com mais de 5 s entre uma e outra continua recebendo uma resposta por mensagem.
- A linha fixa do link solto é decisão desta sessão sobre a frase do dono para a ordem de serviço
  ("informa que links não são tratados neste canal"); silêncio total é trocar uma linha.
