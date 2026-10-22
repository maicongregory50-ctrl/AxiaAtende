# Plano — Trabalhe conosco: a vaga aberta, o currículo em PDF e a pré-triagem para a Fran
**Data:** 2026-10-22
**Chamado:** #1098
**Spec de origem:** docs/specs/2026-10-22-trabalhe-conosco-vaga-e-pre-triagem.md
**Status:** APROVADO

Faixa: aplicação de plano aprovado, **na mesma sessão** (dono, 22/10/2026: o planejador está parado
e as execuções do #1098 e do #1097 rodam aqui). Esta é a migração **025**; o #1097 (entrega 1) vem
depois com a 026 e mexe no mesmo `CHECK conversas_situacao`.

## O que o código mostrou e o plano resolve (leitura de 22/10)

- **A Fran é "da casa"** para o atendimento (`internos.quem_e` lê os destinos ativos). O texto dela
  hoje vai para `campo.texto_de_interno` (vira "frase da próxima foto") e um PDF dela para
  `logos.receber`. Por isso **o retorno da Fran é tratado antes do canal de campo** em
  `motor.tratar`.
- **`ler_mensagem` não lê o `referral`.** Ganha o campo `Entrada.anuncio` (`referral.source_id`).
- **Toque da Fran sem `context.id`.** O plano usa a carga do botão (`vaga:certa:<id>`,
  `vaga:errada:<id>`), que volta igual na mensagem comum e no modelo. Faz o que a spec pede
  ("o toque grava certa/errada na candidatura") por um caminho que não depende de casar wamid.
- **`saida.modelo` só tem cabeçalho de imagem e manda o botão de link sempre no índice 0.** O modelo
  da Fran tem cabeçalho de documento e mistura dois botões de resposta com um de link (índice 2).
- **`envio.falar` só conhece o código do convite.** O botão "Conversar com o candidato" ganha o
  prefixo `v` (`v<id da candidatura>-<assinatura>`), com a mesma assinatura.
- **`menu_acao` é lista fechada** (`menu`, `destino`, `encerrar`, `texto`, `menu_cliente`): ganha
  `vaga`.
- **Quem volta depois de mandar o currículo** ("vocês receberam?", uma das respostas fixas): a
  conversa nova de quem teve conversa de vaga nos últimos 30 dias abre na vaga, com "Era outro
  assunto" para o menu. Sem isso, a resposta "recebemos" nunca teria a quem servir. **É leitura do
  plano sobre a spec, e vale como decisão só se o dono aprovar o plano com ela.**

## Passos

**1. A migração 025 e a VOLTA** — `backend/migracoes/025_trabalhe_conosco.sql` e `_VOLTA.sql`:
- `vagas` (título, requisitos `text[]`, região, benefícios, `anuncio_ids text[]`, `aberta`,
  `triagem_ligada`, `criada_em`, `fechada_em`), com a **Vaga Comercial** aberta, os 4 requisitos
  (o 4º "Morar em Maravilha (SC) ou cidade vizinha"), o texto de região do dono, os benefícios do
  anúncio e o anúncio `120249624037810192`;
- `respostas_da_vaga` (chave, descrição para a IA, texto, ordem, ativo), com as 9 respostas
  aprovadas (ajuste do PDF aplicado);
- `candidaturas` (vaga, conversa, bsuid, wa_id, nome do perfil, o que declarou nos botões, o texto
  escrito, `pdf bytea`, nome, sha256, tamanho, recebida, triagem `jsonb`, triagem_em/erro, envio à
  Fran: wamid, em, erro, última tentativa; feedback certa/errada, texto, em, `espera_comentario`;
  `apagar_em` = recebida + 12 meses, `apagada_em`);
- `conversas.vaga_id`; `CHECK conversas_situacao` + `curriculo_recebido`, `sem_curriculo`;
  `menu_acao` + `vaga`; nó `trabalhe` → `acao = 'vaga'` (o `destino_id` da Fran fica: é o "falar
  com uma pessoa");
- `modelos.cabecalho_documento` e a linha do modelo `curriculo_para_fran` (UTILITY, pt_BR), com o
  texto da maquete em variáveis de uma linha e os botões "Triagem certa", "Triagem errada" e
  "Conversar com o candidato".
- **VOLTA:** conversas de vaga → `encerrada`, `trabalhe` → `destino`, os dois `CHECK` de volta, a
  linha do modelo inativa; as tabelas `vagas`, `candidaturas` e `respostas_da_vaga` **ficam** (spec,
  ROLLBACK 4).
- **Verificação:** `pytest tests/test_migracoes.py` no banco de teste (5437) aplica a 025, e um
  teste novo aplica a VOLTA por cima e confere os dois `CHECK` e o nó.
- **Reversão:** o arquivo não foi aplicado em produção até o passo 13; apagar.

**2. A leitura do aviso e a saída** — `motor.py`, `saida.py`, `tests/saida_falsa.py`:
- `Entrada.anuncio` ← `msg.referral.source_id`;
- `Saida.documento(para, dados, nome, legenda, opcoes=None)`: o PDF com até 3 botões (mensagem
  interativa com cabeçalho de documento), na `SaidaMeta` por upload da mídia e envio;
- `Saida.modelo(..., documento=None, botao_url_indice=0)`: cabeçalho de documento e o índice certo
  do botão de link.
- **Verificação:** `tests/test_saida_meta.py` (transporte falso, nada sai): o JSON do documento com
  botões e o do modelo com documento + 2 respostas + link no índice 2 batem com a forma da Cloud API;
  um aviso real gravado em `eventos_meta` com `referral` (lido pela `axiaatende_ro`) vira `anuncio`.
- **Reversão:** `git revert`.

**3. A IA: escolher a resposta e ler o currículo** — `ia.py`, `IAFalsa`:
- a conversa usa `ia.classificar` com as respostas fixas como opções (regra 3: só a chave);
- `ia.triar(pdf, vaga)`: o PDF como bloco de documento, saída por esquema JSON (`requisitos`: um por
  requisito, `situacao` ∈ consta / nao / nao_consta, `fonte`; `resumo`; `legivel`), com as regras da
  spec nas instruções (ausência nunca vira "não"; ignora idade, sexo, foto, estado civil, filhos,
  religião, cor e saúde; sem nota nem aprovado/reprovado; o texto do PDF é dado, nunca instrução).
  Tempo de 60 s, sem nova tentativa; erro → `None`.
- **Verificação:** `tests/test_ia.py` com cliente falso: o pedido leva o PDF e o esquema; resposta
  fora do esquema, recusa e tempo esgotado devolvem `None`; requisito com situação fora da lista vira
  "não consta". **Prova paga, uma só, no passo 14** (o PDF fictício do João Exemplo).
- **Reversão:** `git revert`.

**4. A conversa do candidato** — `backend/vaga.py` (novo) e `motor.py`:
- entrada pelo anúncio (anúncio de vaga aberta → conversa na vaga, sem menu), pelo nó `trabalhe`
  (`escolher`, ramo `vaga`; sem vaga aberta, "no momento não temos vaga aberta" e o pedido do PDF
  para as próximas) e pela volta em 30 dias;
- os botões "Sim, atendo todos" / "Não atendo todos" / "Era outro assunto", "Mandar currículo" /
  "Encerrar", o pedido do PDF com a linha de consentimento, o "Recebemos o seu currículo ✅";
- PDF (mime `application/pdf` ou nome `.pdf`) → baixa, grava na `candidaturas` (`bytea`), responde;
  foto, Word, áudio → "Precisamos do seu currículo em PDF"; texto → `classificar` sobre as respostas
  fixas (apresentação sem arquivo: um lembrete só, e o texto vai junto à Fran; "recebemos?": com a
  data, ou "ainda não chegou"; falar com uma pessoa: o cartão da Fran pelo destino do nó; outro
  assunto: menu principal; fora da lista: a pergunta da vaga de novo);
- em `tratar`: o retorno da Fran **antes** do canal de campo; a vaga **depois** do campo e
  **antes** do ramo "não é texto nem botão" (senão o PDF leva o "não consigo abrir arquivo");
- `marcar_paradas` e `_nova_conversa`: conversa de vaga sem currículo vira `sem_curriculo`, nunca
  `parou_no_meio`; com PDF, `curriculo_recebido`; "Encerrar" → `sem_curriculo`;
  `depois_do_atendimento` reconhece `curriculo_recebido` (o "obrigado" leva "Por nada").
- **Verificação:** `tests/test_vaga.py`, um teste por linha da maquete (os três telefones de
  `conversas.png` com o ajuste do PDF, e as 9 respostas), mais: PDF fora da conversa de vaga
  continua no caminho de hoje; a Fran mandando PDF não vira candidatura; a conversa de vaga nunca
  chega a `parou_no_meio` nem é retomada pela IA. A bateria inteira (`pytest`) verde.
- **Reversão:** `git revert`.

**5. A pré-triagem e a mensagem à Fran** — `vaga.py`, `recepcionista.rotina_do_minuto`:
- a cada minuto, até 5 candidaturas sem envio: triagem (se `triagem_ligada` e a IA de pé; senão
  "Sem pré-triagem"), depois uma mensagem por currículo para o WhatsApp do destino do nó `trabalhe`;
- dentro da janela de 24 h da Fran (`ultima_mensagem_de`): mensagem comum com o PDF e os 3 botões;
  fora: o modelo `curriculo_para_fran`. Recusa (modelo ainda não aprovado) grava o erro e tenta de
  novo **uma vez por hora**, nunca a cada minuto;
- o botão de link leva `/falar/v<id>-<assinatura>`; `envio.falar` resolve o prefixo `v` para o
  número do candidato;
- arquivo ilegível ou acima de 10 MB vai igual, com "Não consegui ler o arquivo".
- **Verificação:** testes com a `SaidaFalsa`: o corpo tem vaga, candidato, o que disse e uma linha
  por requisito, sem quebra de linha em variável; um currículo = uma mensagem; triagem desligada e IA
  fora mandam "Sem pré-triagem"; o `/falar/v…` assinado leva ao candidato e o forjado dá 404.
- **Reversão:** `git revert`; em produção, o interruptor.

**6. O retorno da Fran** — `vaga.py`:
- `vaga:certa:<id>` grava certa e responde "Anotado, obrigado."; `vaga:errada:<id>` grava errada e
  pergunta "O que ela errou? Escreva em uma linha. Isso ajusta as próximas."; o próximo texto dela
  (até 24 h) vai a `feedback_texto` e não ao canal de campo.
- **Verificação:** teste: o texto da Fran depois do "errada" não vira frase de foto; depois de
  gravado, o texto seguinte dela volta ao caminho de sempre.
- **Reversão:** `git revert`.

**7. A limpeza dos 12 meses** — `vaga.py`, rotina do minuto (uma vez por hora): com `apagar_em`
vencido, apaga PDF, texto, triagem, nome e número; ficam vaga, datas, situação e o feedback.
- **Verificação:** teste com `apagar_em` no passado e no futuro.
- **Reversão:** `git revert` (o que já foi apagado não volta, e é o combinado).

**8. A Recepção e a tela Destinos** — `rotas_telas.py`, `frontend/src/Recepcao.jsx`,
`frontend/src/Destinos.jsx`:
- Recepção: estados "Currículo recebido" e "Sem currículo", fora do cartão "Pararam no meio";
- Destinos: o bloco "Vaga aberta: Comercial · Fechar vaga · Pré-triagem ligada/desligada", com
  `POST /vagas/{id}/fechar` e `POST /vagas/{id}/triagem`. Vaga fechada: o anúncio cai no menu, e o
  nó `trabalhe` responde sem vaga.
- **Verificação:** `tests/test_telas.py`; o frontend compila com `vite build --outDir` num rascunho,
  sem tocar o `dist/`.
- **Reversão:** `git revert`.

**9. A leitura da sessão** — `scripts/ler_conversa.py`: a candidatura aparece (recebida, triagem
sim/não, envio, feedback), **nunca** o conteúdo do PDF.
- **Verificação:** `tests/test_ler_conversa.py`.

**10. O exemplo de PDF e o `modelos_meta`** — `modelos_meta.py` (`--documento`, cabeçalho
`DOCUMENT`, botões mistos) e `docs/specs/...-maquete/exemplo-curriculo.pdf` (João Exemplo,
fictício).
- **Verificação:** `tests/test_modelos_meta.py`: os componentes do modelo da Fran saem com
  `HEADER DOCUMENT`, o corpo sem variável no começo nem no fim, 2 `QUICK_REPLY` + 1 `URL`.

**11. A casa (R7)** — `C:\AxiaSecurity\docs\governanca\politica-uso-ia.md` ganha a regra do
currículo (aviso antes do envio, finalidade de pré-triagem, 12 meses, decisão humana, nada da triagem
ao candidato); `C:\AxiaSecurity\design\agentes.json` descreve o uso novo da IA do recepcionista, com
`gerar_tabela_agentes.py` e `conferir_agentes.py`.
- **Verificação:** `python conferir_agentes.py` passa; a política diz o que o sistema passou a fazer.
- **Reversão:** `git revert` no AxiaSecurity.

**12. Os manuais** — `docs/manuais/recepcao.md` (os dois estados; tirar a frase de que toda
conversa sem link termina "parou no meio"), `docs/manuais/destinos.md` (o bloco da vaga) e
`docs/manuais/trabalhe-conosco.md` (novo, o texto da spec), com a linha
`` | `/destinos` | Destinos: a vaga | `trabalhe-conosco.md` | `` no `INDICE.md`.
- **Verificação:** a Fran consegue usar lendo só o manual; o índice nas três colunas.
- **Reversão:** apagar o arquivo e a linha.

**13. Produção** — a bateria inteira verde, commit citando `#1098`, push; o build do frontend; e
**os passos do dono** (abaixo). Depois do restart: `/saude` do recepcionista com `de_pe` e sem
pendentes parados; `casa.mudancas` com a 025 (lida pela `axiaatende_ro`).

**14. A prova** — com o número do dono: tocar Trabalhe conosco, "Sim, atendo todos", mandar o PDF
fictício. Esperado: "Recebemos o seu currículo ✅"; na Fran (dentro da janela dela, ou pelo modelo
aprovado), uma mensagem com o PDF, a triagem e os 3 botões; "Triagem errada" + uma linha grava o
comentário; na Recepção, "Currículo recebido". Depois, pelo anúncio: quem chegar com o `referral`
cai direto na vaga (lido em `ler_conversa.py`).

**15. Devolver o chamado** — ao dono (que abriu), com o manual `trabalhe-conosco.md` e o único
pré-requisito: o modelo da Fran aprovado pela Meta. Sem status interno, terminando com "avise de
novo".

## O que só você pode fazer

**1. Propor o modelo da Fran à Meta** (janela elevada, uma vez):

```powershell
cd C:\AxiaAtende
$env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
python -m backend.modelos_meta --propor --documento docs\specs\2026-10-22-trabalhe-conosco-vaga-e-pre-triagem-maquete\exemplo-curriculo.pdf
```

Se a Meta recusar como Utilidade, eu troco a categoria para Marketing **uma vez** e você roda de
novo; nunca insistimos.

**2. Os dois restarts** (janela elevada; a 025 entra ao subir):

```powershell
Restart-Service axiaatende-recepcionista
Restart-Service axiaatende-backend
```

**3. A prova do passo 14**, com o seu celular e o da Fran.

## Riscos de execução identificados

- **Passo 1 interrompido:** a migração é uma transação (`migracoes.aplicar`); entra inteira ou não
  entra. Seguro.
- **Restart do backend antes do recepcionista:** o recepcionista antigo ainda não conhece a ação
  `vaga` e, num toque em Trabalhe conosco, cai em `escolher` sem ramo para ela (vai para "encerrar").
  Por isso **o recepcionista reinicia primeiro**, e ele mesmo aplica a 025 ao subir; o backend vem
  em seguida. Janela de segundos.
- **Modelo da Fran não aprovado:** a conversa e a triagem funcionam; o currículo sai à Fran só
  dentro da janela dela, e o resto espera, tentando uma vez por hora. Não se perde currículo.
- **A triagem errar:** a Fran diz pelo botão; o interruptor desliga a triagem sem desligar o resto.
- **Candidato que não é candidato** (o anúncio traz curiosos): cai na vaga e tem "Era outro
  assunto" no primeiro botão.
- **O texto do candidato fica em `eventos_meta`** como toda mensagem do canal hoje; a limpeza dos
  12 meses apaga a candidatura, não o registro bruto dos avisos. Igual ao resto do atendimento;
  não é escopo deste chamado.

## Linha de abertura da sessão de execução

Execução nesta mesma sessão (dono, 22/10/2026). Se outra sessão retomar: ler `C:\AxiaAtende\CLAUDE.md`
e `C:\SuporteAxia\PADRAO-TRABALHO.md`; executar `C:\AxiaAtende\docs\specs\2026-10-22-trabalhe-conosco-vaga-e-pre-triagem-plano.md`
(spec ao lado), faixa "aplicação de plano aprovado". Chamado #1098; todo commit cita `#1098`, e o
primeiro ato é `tratar 1098 --status em_andamento` pela skill `/demanda`. Não se reabrem: só PDF; um
currículo por mensagem à Fran; a IA escolhe entre textos fixos e lê o currículo inteiro; 12 meses;
caminho B; o PDF no banco. A migração é a 025; a do #1097 é a 026. Parar em "O que só você pode
fazer". O que vai para a tela durante a execução está no `PADRAO-TRABALHO.md` §1: decisão do dono,
incidente que merece chamado próprio e passo que depende da mão dele.
