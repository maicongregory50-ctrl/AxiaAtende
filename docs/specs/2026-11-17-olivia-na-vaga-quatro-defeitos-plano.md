# Plano — OlivIA na vaga: quatro defeitos da primeira noite
**Data:** 2026-11-17
**Chamado:** #1543
**Spec de origem:** — (bug sem spec: o desenho está na descrição do chamado; a spec do que se conserta é docs/specs/2026-11-16-olivia-conduz-a-vaga-ficha-e-curriculo.md, #1525)
**Status:** APROVADO
**Executável pelo agente:** não -- o restart do recepcionista é da janela do dono, e a hora do toque é decisão dele

> Manual legal: não se aplica (atendimento ao público). Conformidade com a casa: nenhum agente, segredo,
> serviço ou dado novo; a OlivIA perde uma opção de menu que oferecia a si mesma, e não ganha ferramenta.

## Passos

1. **O laço do "Sim"** — `backend/olivia.py: _opcoes_do_menu`: com a chave `olivia.conduz_vaga` ligada,
   os nós do menu de ação `vaga` (o "Trabalhe conosco") saem do que ela pode oferecer (da lista da
   instrução, do `enum` da ferramenta e da validação em `_oferecer`). Quem atende a vaga é ela: não há
   botão a oferecer. `REGRAS_DA_VAGA` ganha a regra 18: o que ela não sabe da vaga (as tarefas, pagamento),
   a equipe explica no contato; ela segue pedindo o currículo ou a ficha. O botão antigo que já está na
   tela de alguém (`ia:sim:trabalhe`) continua chegando a ela como "[tocou: Trabalhe conosco]", e ela não
   tem mais como devolvê-lo. — verificação: teste (o `enum` não tem `trabalhe`; `_oferecer("trabalhe")`
   responde "não existe"; com a chave desligada, tem). — reversão: revert.

2. **A vaga e a língua do toque** — `backend/olivia.py: tocar_vagas`: sem vaga na conversa, vale a vaga da
   conversa de vaga anterior da mesma pessoa nas últimas 48 h; só sem nenhuma é que o convite da ficha
   sai. A língua deixa de depender de `conversas.lingua` (só a ficha a grava): `_lingua_da_conversa` usa a
   coluna quando existe e, sem ela, a língua das últimas falas da própria OlivIA naquela conversa (ela
   responde na língua da pessoa), com os textos da pessoa como desempate. `_frase_do_que_falta` usa a
   mesma função. — verificação: testes (a pessoa que disse Empilhadeira na conversa anterior recebe o
   toque do currículo; conversa em espanhol sem ficha recebe o toque em espanhol). — reversão: revert.

3. **A hora do toque** — `tocar_vagas` só manda entre `olivia.toque_hora_de` e `olivia.toque_hora_ate`,
   hora de Brasília (padrão no código: 7 e 21; viram ajuste no banco quando alguém quiser mudar). Fora
   do horário o toque **espera**; sai na primeira volta dentro do horário, se a janela de 24 h ainda
   estiver aberta. — verificação: teste (às 23:56 não sai; às 07:00 seguintes sai; às 07:00 com a janela
   já fechada não sai). — reversão: revert.

4. **O "travou" na conversa de vaga** — `backend/olivia.py: travou`: na conversa de vaga, com a chave
   ligada, a contagem de falas (`fraco`) não vale: perguntar e ouvir resposta é a conversa andando. E a
   repetição só conta como `forte` quando a mensagem repetida tem mais de três palavras (um segundo "Sim"
   ou "Tenho" não é a pessoa presa). "Não é isso" continua valendo. — verificação: testes (seis respostas
   curtas seguidas não marcam `travou`; dois "Sim" seguidos não dão o menu; "não é isso" marca). —
   reversão: revert.

5. **Bateria** inteira, sozinha no 5437 (`pg_isready -p 5437`; `-p no:cacheprovider
   --basetemp=C:/Temp/<único>`).

6. **Manual** — `docs/manuais/olivia.md`: o toque só sai das 7h às 21h; ela não oferece o botão Trabalhe
   conosco na conversa de vaga; o "travou" na vaga. `INDICE.md`: a linha já existe. — verificação: quem
   lê sabe por que um toque das 23h só chegou às 7h. — reversão: revert.

7. **Commit** citando `#1543`, nomeando os arquivos, e **push**.

8. **No ar**: `Restart-Service axiaatende-recepcionista` (dono). — verificação: `/saude` responde; a
   próxima conversa de vaga não traz `fala (travou)` nem o botão.

9. **Devolver**: o que mudou e o manual; `entregar 1543 --devolucao @arquivo.txt` e `fechar 1543`.

## O que só você pode fazer

- **O restart**, em janela elevada: `Restart-Service axiaatende-recepcionista`
- **Dizer se 7h às 21h serve** para o toque; outro horário é um ajuste, sem código.

```pos-entrega
dono=Restart-Service axiaatende-recepcionista; confirmar o horario do toque (7h as 21h)
```

## Riscos de execução identificados

- **Passos 1 a 7 interrompidos:** nada muda em produção até o restart.
- **Passo 3, o horário (decidido pelo dono em 17/11/2026, depois do plano):** das **6h às 21h**, e *"às 21
  horas mandas todos os toques da fila se forem vencer antes das 6h do dia seguinte"*. Com a rotina
  rodando a cada minuto, o silêncio de 21h a 6h (9 horas) nunca consome a janela de 24 h de quem escreveu
  dentro do horário; a última chamada das 21h cobre o toque que ficou na fila por serviço parado. O que
  este risco dizia antes ("quem escreveu às 6h59 perde o toque") estava errado: esse toque sai às 8h59.
- **Passo 4:** tirar o `fraco` da vaga deixa a conversa de vaga sem o aviso de "mude de abordagem"; o
  vigia diário continua contando a conversa de vaga sem ficha nem currículo como sem saída.

## Linha de abertura da sessão de execução

Executado na mesma sessão que escreveu o plano, com o dono (17/11/2026, "Bug abrir e rodar aqui").
Chamado **#1543**; todo commit cita `#1543`.
