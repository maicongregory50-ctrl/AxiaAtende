# Plano — O lote novo não entra no grupo fechado
**Data:** 2026-10-22
**Chamado:** #1099
**Spec de origem:** docs/specs/2026-10-22-o-lote-novo-nao-entra-no-grupo-fechado.md
**Status:** APROVADO
**Executável pelo agente:** sim

Faixa: aplicação de plano aprovado, **na mesma sessão** (dono, 22/10/2026: o planejador está parado).
**A migração deixa de ser a 025 da spec e passa a ser a 028**: a 025, a 026 e a 027 entraram hoje
(#1098 e #1097). A entrega 2 do #1097 vem depois deste chamado, com a 029.

## O que o código mostrou (leitura de 22/10, `backend/campo.py`)

- `Campo._lider` (`:276`): primeiro a conversa **aberta** (sem fechar, 24 h); senão, a primeira linha
  do número **recebida** nos últimos 10 min (`RODADA`), **fechada ou não** — é o defeito.
- `receber` (`:216`): a frase de antes é a última de `campo_frases` sem uso, **recebida** nos últimos
  10 min; a foto herda classe, data e `fechado_em` do líder.
- `responder` (`:537`), ramo "texto solto": com grupo **aberto** e sem pergunta, o texto vira legenda
  do grupo. É o que já serve à frase mandada logo depois da foto quando ela chega na ordem; o que
  falta é o caso fora de ordem (a frase que chega antes da foto dela), que hoje vira "frase da próxima".
- `Entrada` não traz a hora de envio: `ler_mensagem` ignora `msg.timestamp`.
- `CHECK material_pergunta`: `legenda, data, qual_dia, bastidor, produto, fase`. `campo_frases` não
  tem hora de envio.
- Os testes mandam `timestamp` fixo (`1760040000`, 09/10/2025): com a regra nova, toda foto de teste
  "foi mandada no mesmo segundo, um ano antes". **Os ajudantes passam a mandar a hora do passo.**

## Passos

**1. A migração 028 e a VOLTA** — `backend/migracoes/028_lote_pelo_envio.sql`:
`material_de_campo.enviado_em` e `campo_frases.enviado_em` (aceitam vazio: as linhas antigas caem
na hora de chegada); `CHECK material_pergunta` + `mesmo`; `ajustes` `campo.lote_pelo_envio` = `true`.
VOLTA: `pergunta_pendente = 'mesmo'` vira `NULL` antes de o `CHECK` voltar; tira as duas colunas e a
linha de `ajustes`.
- **Verificação:** `test_migracoes`, `test_login` (a lista), e um teste da VOLTA com uma pergunta
  `mesmo` aberta.

**2. A hora de envio** — `motor.Entrada.enviado_em` lida de `msg.timestamp`; `campo.hora_de_envio(e,
agora)`: a hora da Meta quando existe e não passa de 5 min no futuro em relação à chegada; senão, a
chegada. Gravada em `receber` (foto) e `texto_de_interno` (frase). `tests/avisos_meta.py` e os
ajudantes de `test_campo` passam a mandar a hora do `agora` de cada passo.
- **Verificação:** a bateria inteira continua verde só com essa mudança, antes de qualquer regra nova
  (prova de que os ajudantes não mudaram o que os testes antigos provam).

**3. O lote pela hora de envio** — `_lider`, com a chave ligada: (1) a conversa aberta, como hoje
(a decisão 15c continua); (2) senão, a linha do número com envio a até **60 s** desta foto, **fechada
ou não** (é a mesma remessa que chegou atrasada); (3) senão, grupo novo. O ramo de 10 min pela
chegada sai. Chave desligada: o `_lider` de hoje, intacto.
- **Verificação:** testes: o álbum que chega 1 min depois de o grupo anterior fechar abre grupo novo
  (o caso das 10:25 de hoje); a foto do mesmo envio que chega atrasada entra no grupo dela, mesmo
  fechado; fotos soltas a 50 s uma da outra são um lote, a 90 s são dois.

**4. A frase pela hora de envio** — em `receber`, com a chave ligada: a frase sem uso do número com
envio **até 10 min antes** da foto, ou **até 60 s depois**; havendo as duas, a de antes. Assim a frase
que chegou antes da foto dela (celular sem rede) é achada quando a foto chega. Chave desligada: a
regra de hoje.
- **Verificação:** os três lotes de hoje, com as horas reais da tabela da spec: o álbum das 08:54
  leva a frase de Qualidade das 08:55 (19 s depois); o das 09:44 leva a de Beneficiamento das 09:44:46
  e não a das 08:55; o das 10:25 é lote novo e leva a das 10:25:46.

**5. A pergunta "É do mesmo assunto da anterior?"** — `_falta` devolve `mesmo` como primeira pergunta
quando o lote não tem legenda e o número fechou outro lote cujo envio foi até **10 min antes**. O
texto: *"É do mesmo assunto da anterior (<título curto>)?"*, botões **Sim** / **Outra coisa**. Sim:
herda legenda, classe, produto, fase, data e safra do anterior, "Anotado. Obrigado!" e fecha. Outra
coisa: o roteiro de sempre. Sem resposta: a lembrança de 2 h e a desistência de sempre (desistiu,
fecha sem herdar). Não conta no limite de três perguntas, como a data.
- **Verificação:** testes dos três ramos e o do Benedito de 14/10 (a foto 2 min depois de
  "Carregamento do dia" fechar: Sim herda).

**6. A leitura da sessão** — `scripts/ler_conversa.py` mostra a hora de envio quando ela difere da
chegada em mais de 60 s. **Verificação:** `test_ler_conversa`.

**7. Os manuais** — `docs/manuais/campo-equipe.md` (as quatro frases que a spec lista como erradas e
a linha nova da pergunta) e `docs/manuais/recepcao.md` (uma linha: o lote é pela hora de envio).

**8. Produção** — bateria inteira verde, commits com `#1099`, push; os dois restarts do dono
(recepcionista primeiro); depois, lido pelo `axiaatende_ro`: a 028 aplicada e a chave ligada.

**9. A prova** — com o dono: um álbum com a frase logo depois; outro álbum, sem frase, um minuto
depois de o primeiro fechar (deve vir "É do mesmo assunto da anterior?").

**10. Devolver o chamado** ao dono, com o manual.

## O que só você pode fazer

```powershell
Restart-Service axiaatende-recepcionista
Restart-Service axiaatende-backend
```

E a prova do passo 9, com o seu celular.

## Riscos de execução identificados

- **A regra nova errar o lote:** a chave `campo.lote_pelo_envio` desligada (um `UPDATE` em `ajustes`,
  sem restart) devolve a regra de hoje. Os dados novos (as duas colunas) ficam e não atrapalham.
- **Relógio do celular errado para a frente:** mais de 5 min no futuro, vale a chegada.
- **A migração interrompida:** é uma transação.
- **O `campo.py` muda de novo na entrega 2 do #1097:** ela vem depois e é remedida contra este código.

## Linha de abertura da sessão de execução

Execução nesta mesma sessão (dono, 22/10/2026). Se outra sessão retomar: ler `C:\AxiaAtende\CLAUDE.md`
e `C:\SuporteAxia\PADRAO-TRABALHO.md`; executar `C:\AxiaAtende\docs\specs\2026-10-22-o-lote-novo-nao-entra-no-grupo-fechado-plano.md`
(spec ao lado), faixa "aplicação de plano aprovado". Chamado #1099; todo commit cita `#1099`, e o
primeiro ato é `tratar 1099 --status em_andamento` pela skill `/demanda`. Não se reabrem: caminho B;
60 s entre fotos do mesmo lote; frase até 10 min antes ou 60 s depois, a de antes vence; a pergunta
"É do mesmo assunto da anterior?"; a hora de envio só quando plausível. A migração é a 028. Parar em
"O que só você pode fazer". O que vai para a tela está no `PADRAO-TRABALHO.md` §1.
