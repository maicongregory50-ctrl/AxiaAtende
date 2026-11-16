# Plano — A OlivIA conduz a conversa da vaga: ficha para quem não tem currículo
**Data:** 2026-11-16
**Chamado:** #1525
**Spec de origem:** docs/specs/2026-11-16-olivia-conduz-a-vaga-ficha-e-curriculo.md
**Status:** APROVADO
**Executável pelo agente:** não -- os textos de cadastro são do dono, a Fran lê as perguntas antes de ligar, os restarts são da janela dele e o pedido à Fran sai com o texto aprovado por ele

> Ordem por dependência: migração → chave → cadastro da vaga → ferramentas → candidatura em ficha →
> página à Fran → entrada → toque único → trava → apagamento → vigia → lugar das funções → testes →
> documentos → a ida → ligar. **A chave `olivia.conduz_vaga` nasce `false` e só liga no passo 18**: até
> lá tudo o que sobe é inerte, e a bateria de hoje passa igual. Manual legal: nenhuma ficha sobre o
> assunto (spec, *Conformidade com o Manual legal*); nada a alterar lá.

## Passos

1. **Migração 067** — `backend/migracoes/067_olivia_conduz_vaga.sql` + `_VOLTA.sql`:
   `vagas.modo text NOT NULL DEFAULT 'curriculo' CHECK IN ('ficha_ou_curriculo','curriculo')`, e a
   Auxiliar de produção (id 2) em `ficha_ou_curriculo`; `conversas.ficha jsonb`, `conversas.lingua text
   CHECK IN ('pt','es')`, `conversas.vaga_lembrada_em timestamptz`; `candidaturas.ficha jsonb`,
   `candidaturas.quer_visita boolean NOT NULL DEFAULT false`, e o `CHECK` de `tipo_arquivo` reescrito
   com `'ficha'`; ajustes `olivia.conduz_vaga = false`, `olivia.vaga_toque_h = 2`,
   `olivia.ficha_parcial_h = 4`; em `respostas_da_vaga`, as chaves novas em `pt` e `es` com texto
   provisório marcado `[TEXTO DO DONO]`: `ficha_aviso`, `toque_ficha_falta`, `toque_convite`,
   `toque_curriculo`, `ficha_falta`; `vagas.beneficios` das vagas abertas sem "salário atrativo" (D8).
   **O `GRANT` por coluna do papel `axiaatende_ro` não ganha `ficha`** (ganha `quer_visita` e nada mais).
   — verificação: a bateria aplica no 5437; `\d` mostra as colunas; `SELECT modo FROM vagas` dá
   `ficha_ou_curriculo` só na 2; o papel de leitura toma "permissão negada" em `SELECT ficha`. —
   reversão: a `_VOLTA`, que **recusa** se houver candidatura `tipo_arquivo = 'ficha'` (molde da 062) e
   desfaz a 067 antes das antigas nos testes de volta (como a 065 pediu, commit fe5a5de).

2. **A chave na mão** — `scripts/olivia.py` (molde de `scripts/audio.py`): `ligar-vaga`,
   `desligar-vaga`, `mostrar` (a chave e os dois tempos). `backend/olivia.py: conduz_vaga(con)` lê o
   ajuste. O `/saude` do recepcionista ganha `olivia_vaga: ligada|desligada`. — verificação: teste do
   script no banco de teste; `/saude` mostra o campo. — reversão: revert.

3. **O modo no cadastro da vaga (D3)** — `backend/rotas_telas.py`: a leitura das vagas devolve `modo`;
   `PUT /vagas/{vaga_id}/modo`. `frontend/src/Destinos.jsx`: cada vaga mostra **Ficha ou currículo** ou
   **Currículo obrigatório**, com o botão de trocar, ao lado do da pré-triagem. — verificação: tela em
   `127.0.0.1:8009`; trocar e conferir no banco de teste. — reversão: revert.

4. **As ferramentas por estado e a instrução** — `backend/olivia.py`:
   - `ferramentas(con, conversa)` passa a depender da conversa: as cinco de hoje sempre;
     `escolher_vaga` (enum das abertas) quando a conversa é de vaga; `comecar_ficha` quando a vaga da
     conversa é `ficha_ou_curriculo` e não há `olivia: aviso da ficha` em `enviadas`; `anotar_ficha`
     depois do aviso; `marcar_visita` quando já existe candidatura na conversa. A lista é refeita a
     cada volta do laço (o estado muda dentro da mesma mensagem).
   - `escolher_vaga`: grava `conversas.trabalhe = true, vaga_id`. `comecar_ficha`: manda `ficha_aviso`
     na língua pedida (`lingua`: `pt`|`es`, obrigatório), grava `conversas.lingua` e registra
     `olivia: aviso da ficha`. `anotar_ficha`: campos opcionais `nome`, `cidade`, `experiencia`,
     `quando_comeca`, `como_chega` (texto, até 200 letras) e `lingua`; grava no rascunho
     `conversas.ficha`; com os cinco, chama `vaga.receber_ficha` (passo 5) e devolve "ficha completa e
     encaminhada"; senão devolve o que falta. `marcar_visita`: passo 6.
   - `instrucao`: o bloco das vagas ganha o modo, os benefícios (D8) e o arquivo da função quando
     existe (passo 12); regras novas: a conversa de vaga (perguntar se tem currículo; ficha só na vaga
     que aceita; na de currículo obrigatório, dizer que é indispensável, que pode ser foto, e oferecer
     a vaga de ficha se houver); as cinco perguntas, uma por vez, nas palavras dela, **e só elas**; a
     oferta da visita depois da candidatura, uma vez; *"responda na língua da ÚLTIMA mensagem da
     pessoa, inclusive quando ela é a transcrição de um áudio"* (D7 da spec, item 7).
   — verificação: passo 13. — reversão: revert; com a chave `false` a conversa de vaga não chega a ela.

5. **A ficha vira candidatura** — `backend/vaga.py: receber_ficha(con, conversa, pessoa, ficha, agora,
   parcial=False)`: insere `candidaturas` com `tipo_arquivo = 'ficha'`, `ficha` (os campos, `lingua`,
   e `faltou` quando parcial), sem `pdf`, `triagem_em = agora`, `triagem_erro = 'ficha: sem triagem'`,
   `apagar_em = agora + 12 meses`; fecha a conversa como `curriculo_recebido`. Uma por conversa (a
   segunda chamada devolve a mesma). **Os leitores**: `fim_da_conversa`, `motor.py` (o `EXISTS` de
   candidatura), `olivia.travou` e `olivia.fechar_dia` já contam qualquer candidatura; conferir por
   teste que a ficha conta. `_ultima_candidatura` + a resposta `recebemos` ("Recebemos, sim") valem
   para a ficha: conferir o texto. `rotas_telas.py` (a contagem por vaga da tela Destinos) passa a
   dizer "N currículos, M fichas". — verificação: passo 13 (a), (d). — reversão: revert.

6. **A página à Fran e a visita** — `backend/vaga.py`: `pdf_da_ficha(con, c) -> bytes` (molde de
   `pdf_da_foto`, sem biblioteca nova): "Ficha de contato", a vaga, as respostas como a pessoa deu,
   "Respondeu em espanhol" quando `lingua = 'es'`, **"Incompleta: faltou X e Y"** quando parcial, e
   "Quer visitar a empresa" quando marcado. `mandar_a_fran` trata `tipo_arquivo = 'ficha'`: a página no
   cabeçalho do modelo, **sem** os botões de triagem, com o de conversar (como a foto). `_triar` pula a
   ficha. `olivia.py: marcar_visita` grava `candidaturas.quer_visita = true`; se `fran_em` já está
   preenchido, insere o aviso de uma linha para a Fran pelo caminho de avisos (`vigia._avisar`, tipo
   novo `vaga_visita`), senão a marca vai na própria página. — verificação: passo 13 (e), (f); a
   página aberta num leitor de PDF, com acento. — reversão: revert.

7. **A entrada (D1)** — `backend/motor.py: tratar`, **antes** de `vaga.tratar`: `if olivia is not None
   and olivia.conduz_vaga(con) and olivia.e_de_fora(...)` e a mensagem é de vaga (anúncio de vaga
   aberta, toque `menu:trabalhe`, ou conversa de vaga em curso com texto, PDF, foto ou transcrição de
   áudio) e **não** é toque `vaga:*` → `olivia.atender(...)`; `True` encerra; `False` segue para
   `vaga.tratar` (a reserva). O retorno da Fran e os toques `vaga:*` de mensagens antigas ficam onde
   estão. `olivia.atender` deixa de devolver `False` para conversa de vaga quando a chave está ligada,
   e marca `conduzida_por = 'olivia'`. — verificação: passo 13 (a), (b), (h), (i). — reversão: revert.

8. **O toque único e a parcial (D4, D6)** — `backend/olivia.py`: `tocar_vagas(con, saida, agora)` e
   `enviar_parciais(con, agora)`, chamadas por `recepcionista.rotina_do_minuto`.
   `tocar_vagas`: conversa `trabalhe`, `conduzida_por = 'olivia'`, sem candidatura,
   `vaga_lembrada_em IS NULL`, última mensagem **da pessoa** há `olivia.vaga_toque_h` ou mais e há
   menos de 24 h (`envio.janela_aberta`) → manda **um** texto de cadastro pela língua da conversa
   (`toque_ficha_falta` com o que falta; `toque_convite`; `toque_curriculo`, pelo estado da spec
   item 5), registra `olivia: toque da vaga` e grava `vaga_lembrada_em`. Só com a chave ligada.
   `enviar_parciais`: rascunho com `nome`, sem candidatura, e (`vaga_lembrada_em` há
   `olivia.ficha_parcial_h` ou mais **ou** janela fechada) → `vaga.receber_ficha(..., parcial=True)`.
   **Roda mesmo com a chave desligada** (rollback da spec, item 2). — verificação: passo 13 (c), (g).
   — reversão: revert.

9. **A trava da promessa** — `backend/olivia.py: _falar`: numa conversa de vaga sem candidatura
   gravada (nesta mensagem ou antes), a fala que afirma ter anotado, encaminhado ou passado à equipe
   (`PROMESSA`: lista curta, em português e espanhol, sem acento) é recusada: registra
   `olivia: recusada: promessa` e manda `ficha_falta` (o que ainda falta) no lugar. — verificação:
   passo 13 (j). — reversão: revert.

10. **Os doze meses** — `backend/vaga.py: limpar`: além do que já apaga, zera `candidaturas.ficha` e o
    rascunho `conversas.ficha` da conversa; rascunho sem candidatura com mais de 12 meses também sai.
    — verificação: teste com candidatura em ficha vencida. — reversão: revert.

11. **O vigia e a medição** — `olivia.fechar_dia`: o resumo ganha "N fichas incompletas" (candidaturas
    `ficha` com `faltou` no dia); a conversa de vaga dela sem ficha nem currículo é `sem_saida`.
    `scripts/medir_olivia.py`: conversas de vaga, fichas completas e parciais, currículos, toques
    únicos mandados e quantos tiveram resposta depois, "quer visitar", contra os 11 de 38 de 16/11.
    — verificação: teste do vigia; o script roda pelo papel de leitura (sem ler `ficha`). — reversão:
    revert.

12. **O lugar do que cada função faz (D9)** — `docs/olivia/funcoes/LEIAME.md` (o que entra: um arquivo
    `<vaga_id>.md` por vaga, curto, cada afirmação com fonte e data, corrigido pelo dono; números e
    valores ficam fora) e `backend/olivia.py: funcao_da_vaga(vaga_id)`, que lê o arquivo quando existe
    e relê quando o `mtime` muda. Nenhum arquivo de vaga nasce nesta etapa. — verificação: teste com um
    arquivo temporário (entra na instrução; sem arquivo, não entra). — reversão: revert.

13. **Testes** — `tests/test_olivia_vaga.py`, com `IAFalsa.conversar` e as fixtures de `test_olivia`:
    (a) **ficha completa**: anúncio da Auxiliar → `comecar_ficha` (aviso em `enviadas`) → cinco
    `anotar_ficha` → candidatura `ficha`, conversa `curriculo_recebido`, a Fran recebe a página sem
    botões de triagem;
    (b) **currículo obrigatório**: na Empilhadeira, `comecar_ficha` e `anotar_ficha` **não estão na
    lista**; a foto entra como currículo;
    (c) **parcial**: nome e cidade, silêncio → um toque às 2 h → 4 h depois, candidatura parcial com
    `faltou`; segundo toque não sai nunca;
    (d) **uma por conversa**: `anotar_ficha` depois de completa não cria a segunda;
    (e) **espanhol**: `lingua = 'es'` → aviso e toque em espanhol, "Respondeu em espanhol" na página;
    (f) **visita**: `marcar_visita` antes do envio marca a página; depois do envio, a Fran recebe a
    linha;
    (g) **silêncio total**: só a frase do anúncio → `toque_convite` às 2 h; fora das 24 h, nada sai;
    sem nome, nenhuma candidatura e `sem_saida`;
    (h) **chave desligada**: `test_vaga` e `test_olivia` passam sem mudança; a conversa de vaga é a de
    hoje; `enviar_parciais` ainda manda a parcial de um rascunho deixado;
    (i) **API fora**: `atender` devolve `False` e `vaga.tratar` responde como hoje;
    (j) **promessa**: fala "anotei, a equipe vai te chamar" sem candidatura → recusada, `ficha_falta`
    no lugar;
    (k) **quem não passa por ela**: interno, cliente da carteira, consultor, o retorno da Fran e os
    toques `vaga:*` antigos.
    — verificação: `pytest tests/test_olivia_vaga.py` e a bateria inteira, **sozinha** no banco 5437
    (`pg_isready -p 5437` antes; `-p no:cacheprovider --basetemp=C:/Temp/<único>`). — reversão: apagar.

14. **Inventário e política (R7, muda)** — `C:\AxiaSecurity\docs\governanca\inventario-agentes.md`: a
    linha da OlivIA passa a dizer as ferramentas da conversa de vaga, a ficha e a chave
    `olivia.conduz_vaga`. `politica-uso-ia.md`, em *Pode sozinho*: regra nova, *"Conduzir a conversa de
    vaga e gravar a ficha de contato do candidato, cinco campos fixos, com aviso antes da primeira
    pergunta, para a recrutadora e por 12 meses; decidido em 16/11/2026 (#1525)"*, com a fonte; a regra
    do #1098 ganha "ou a ficha"; a do #1520 deixa de dizer "cinco ferramentas". — verificação:
    `python scripts/conferir_inventario_agentes.py --politica` passa. — reversão: revert no AxiaSecurity.

15. **Manuais** — `docs/manuais/trabalhe-conosco.md`: a seção nova "A ficha de contato" (o texto da
    spec) e o que passou a ser falso ("PDF ou foto" como único caminho; "a conversa de vaga é do fluxo
    fixo"); `docs/manuais/olivia.md` ("cinco ferramentas"; "a conversa de vaga vem antes dela"; a
    chave nova; o toque único; a visita). `INDICE.md`: as linhas já existem; conferir que continuam
    casando. — verificação: alguém de fora lê "A ficha de contato" e sabe o que a Fran recebe e o que
    quer dizer "incompleta". — reversão: revert.

16. **Commit** citando `#1525` (067, código, testes, manuais, `docs/olivia/funcoes/LEIAME.md`), nomeando
    os arquivos (`git commit -- a b`), e **push**; o AxiaSecurity em commit próprio.

17. **A ida: o pedido à Fran (D9)** — um chamado endereçado a ela, pela skill:
    `python C:\SuporteAxia\skills\demanda\demanda.py abrir --sistema axiaatende --tipo tarefa
    --destinatario <id do usuário da Fran> --titulo "Descricoes de funcao das vagas abertas"
    --descricao @pedido.txt`. O texto, **mostrado ao dono antes de sair**: *"Fran, estamos ensinando a
    OlivIA a explicar ao candidato o que cada função faz. Você consegue nos mandar as descrições de
    função de Auxiliar de produção e de Operador de empilhadeira? Pode ser o arquivo que você já tem.
    Em breve vai dar para devolver o arquivo aqui mesmo pelo WhatsApp; por enquanto, diga só se tem e
    onde está."* — verificação: a mensagem aparece na tela Envios (tabela *Chamados no WhatsApp*) como
    saída para o número dela. — reversão: recusar o chamado. **Não depende da chave nem do passo 18.**

18. **Ligar, na janela do dono**: (a) o dono escreve os cinco textos de cadastro em português e
    espanhol (`ficha_aviso`, `toque_ficha_falta`, `toque_convite`, `toque_curriculo`, `ficha_falta`) e
    confirma o de benefícios; (b) a Fran lê as cinco perguntas; (c) `Restart-Service
    axiaatende-backend` (aplica a 067) e `Restart-Service axiaatende-recepcionista`, com a chave ainda
    `false`: nada muda para quem escreve; (d) conferir a tela Destinos (o modo das duas vagas);
    (e) `python scripts\olivia.py ligar-vaga`, sem restart. — verificação: `127.0.0.1:8008/saude` diz
    `olivia_vaga: ligada`; nenhum texto `[TEXTO DO DONO]` sobra em `respostas_da_vaga` (o script
    `ligar-vaga` **recusa ligar** enquanto sobrar).

19. **Prova real**: um número de fora (não da casa, não cliente) chega pela Auxiliar de produção, diz
    que não tem currículo e responde as cinco; outro responde duas e some; um terceiro, em espanhol,
    pede a Empilhadeira sem currículo. Lido com `python -X utf8 scripts/ler_conversa.py --numero N`. —
    verificação: a Fran recebeu a ficha completa; o toque único saiu uma vez; a parcial chegou marcada;
    o de espanhol foi respondido em espanhol e recebeu a oferta da vaga de ficha. As conversas, coladas
    no chamado.

20. **Uma semana depois**: `python scripts/medir_olivia.py`: fichas e currículos sobre conversas de
    vaga contra 11 de 38; toques mandados e respondidos; "quer visitar". Comentar no chamado. —
    verificação: os números no comentário.

21. **Devolver** ao dono: o que mudou, o manual, a medição, e o estado do pedido à Fran;
    `entregar 1525 --devolucao @arquivo.txt` e `fechar 1525`.

## O que só você pode fazer

- **Escrever os cinco textos de cadastro**, em português e espanhol: o aviso antes da ficha (as
  respostas vão à equipe de seleção e ficam guardadas por 12 meses), os três toques e a frase do que
  falta. A sessão deixa um rascunho de cada; o que vale é o seu.
- **Confirmar o texto de benefícios** das duas vagas, sem "salário atrativo".
- **Levar as cinco perguntas à Fran** antes de ligar.
- **Aprovar o texto do pedido à Fran** (passo 17) e dizer qual é o usuário dela.
- **Os restarts e a chave**, na ordem do passo 18 (janela elevada para os restarts):
  ```
  Restart-Service axiaatende-backend; Restart-Service axiaatende-recepcionista
  # conferir a tela Destinos; depois:
  python scripts\olivia.py ligar-vaga
  ```
- **A prova real** de três números de fora (passo 19) e a leitura da medição (passo 20).

```pos-entrega
dono=escrever os cinco textos de cadastro em pt e es; confirmar o texto de beneficios; a Fran le as cinco perguntas; aprovar o pedido a Fran; Restart-Service axiaatende-backend e axiaatende-recepcionista com a chave desligada; conferir a tela Destinos; python scripts\olivia.py ligar-vaga; prova de tres numeros de fora
```

## Riscos de execução identificados

- **Passos 1 a 16 interrompidos no meio:** nada muda em produção; a chave está `false` e os serviços no
  ar são os de antes. Seguro parar em qualquer ponto antes do 18.
- **Passo 1, a `_VOLTA` depois de ligar:** recusa se houver ficha gravada. É de propósito: a ficha é
  dado de candidato que a Fran já recebeu; apagar é decisão do dono.
- **Passo 7, a API cai no meio de uma conversa de vaga:** a mensagem seguinte cai no fluxo fixo, que
  pede PDF ou foto e não conhece a ficha. O rascunho fica; `enviar_parciais` ainda o leva à Fran se já
  houver nome. A pessoa vê a mudança de tom; não fica sem resposta.
- **Passo 8, o toque fora de hora:** 2 h depois da última mensagem pode cair de madrugada. A spec não
  fixou horário; se o dono quiser janela de horário, é ajuste novo, e a execução **pergunta** antes de
  inventar.
- **Passo 8, a janela de 24 h:** quem chegou pelo anúncio abriu a janela com a própria mensagem; o toque
  cabe. Passadas as 24 h nada sai, e não há modelo pago nesta etapa.
- **Passo 6, a página à Fran fora da janela dela:** vai pelo modelo com PDF no cabeçalho, como o
  currículo. Se o modelo for recusado pela Meta, vale o de hoje: nova tentativa em uma hora.
- **Passo 9, a trava recusa demais:** uma frase inocente com "anotei" antes da ficha completa vira
  `ficha_falta`. O vigia conta as recusadas; se passar de poucas por dia, a lista `PROMESSA` é ajustada.
- **Passo 17, o pedido sai e a volta ainda não existe (#1528):** por isso o texto pede só "tem e onde
  está". Se a Fran mandar o arquivo pelo WhatsApp antes do #1528, ele não entra no chamado.
- **O fio `_ultima_candidatura`:** quem deixou ficha e pergunta "vocês receberam meu currículo?" ouve
  "Recebemos, sim". É verdade para a ficha; o teste do passo 5 confere a frase.
- **O #1522 (vaga trocada na volta):** continua no caminho de reserva; com a chave ligada, quem volta é
  atendido pela OlivIA, que escolhe a vaga pela ferramenta.

## Linha de abertura da sessão de execução

Leia `C:\AxiaAtende\CLAUDE.md` e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md` §1. Execute o plano
`C:\AxiaAtende\docs\specs\2026-11-16-olivia-conduz-a-vaga-ficha-e-curriculo-plano.md` (spec ao lado,
mesma data), faixa "aplicação de plano aprovado". Chamado **#1525**; todo commit cita `#1525`, e o
primeiro ato é `python C:\SuporteAxia\skills\demanda\demanda.py tratar 1525 --status em_andamento` pela
skill `/demanda`. Decisões que NÃO se reabrem (D1 a D9 da spec): a OlivIA conduz toda conversa de vaga
e o fluxo fixo é reserva; ficha de cinco perguntas fixas (nome, cidade, no que já trabalhou, quando
pode começar, se tem como chegar a Cunha Porã), sem idade, estado civil, nacionalidade, filhos ou
saúde; modo por vaga no cadastro (ficha ou currículo; currículo obrigatório); um toque único por
conversa de vaga sem candidatura, só dentro das 24 h, e a parcial com nome vai à Fran marcada como
incompleta; a visita é oferta no fim e a OlivIA não agenda; benefícios do cadastro sem a palavra
salário; o pedido das descrições de função sai à Fran (a ida) e a volta com arquivo é o #1528; chave
`olivia.conduz_vaga` nasce `false`. A ordem dos passos é por dependência e a chave só liga no passo 18.
O que vai para a tela durante a execução está no `PADRAO-TRABALHO.md` §1: decisão do dono, incidente
que merece chamado próprio, e passo que depende da mão dele. Pare em "O que só você pode fazer". A
bateria do AxiaAtende roda **sozinha** no banco 5437 e leva cerca de 22 minutos.
