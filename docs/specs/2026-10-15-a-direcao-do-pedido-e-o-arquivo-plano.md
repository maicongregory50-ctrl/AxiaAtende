# Plano — A direção do pedido, e o arquivo que ninguém abre
**Data:** 2026-10-15
**Chamado:** #1027
**Spec de origem:** `docs/specs/2026-10-15-a-direcao-do-pedido-e-o-arquivo.md`
**Status:** APROVADO
**Executável pelo agente:** sim

> **Sem bloco `pos-entrega`:** a migração é do banco do atendimento, que **não está no catálogo da
> `Porta-Ação`** (só as fases do ERP, e cinco serviços que não incluem os dois do AxiaAtende). Ela é
> aplicada pelo próprio serviço ao subir, e o restart é da mão do dono (passo 6).

> **A ordem aqui NÃO é trava, ao contrário do #1031**, e isso é afirmação da spec que o plano
> confirma: código novo com descrições antigas só dá menos contexto à IA; código antigo com
> descrições novas também não quebra nada. Nenhum estado intermediário é perigoso.

## Passos

**1. As sete descrições** — arquivos: `backend/migracoes/019_direcao_do_pedido.sql` e
`019_direcao_do_pedido_VOLTA.sql` — `UPDATE` em sete linhas de `atendimento.menu`. **Duas são lidas
pelo cliente** (`comercial` e `fornecedores`, filhos da raiz, que sai em lista) e **cinco só pela
IA** (`comercial.produtor`, `comercial.revenda`, `comercial.corretor`, `fornecedores.ja`,
`fornecedores.ainda`, que saem em botão). O `_VOLTA` devolve os valores de hoje, **inclusive as
vazias** — verificação: as sete voltam no `SELECT`, nenhuma passa de **72 caracteres**
(`menu_descricao`), e `SELECT count(*) FROM atendimento.menu WHERE descricao = ''` cai de 23 para
**18** — reversão: o `_VOLTA` à mão (passo 6).

**2. A direção na instrução da IA** — arquivo: `backend/ia.py`, só `INSTRUCOES` — uma frase dizendo
que quem oferece não é quem pede. **Nada mais muda**: nem modelo, nem `enum`, nem esquema de saída,
nem tempo, nem esforço — é o que mantém o "conforme" da R7 verdadeiro (a IA continua podendo só
devolver uma chave de lista fechada) — verificação: `pytest tests/test_ia.py` passa, e um teste novo
confere que a instrução cita a direção — reversão: `git checkout`.

**3. A linha nova de arquivo** — arquivo: `backend/motor.py` — uma constante e a escolha por
`e.tipo` em `('document', 'audio', 'video')`; os outros tipos seguem na linha de 12/10. **Imagem
fica fora** (0 casos medidos de cliente; de equipe é o canal de campo) e **`unsupported` também**
(os 13 são do robô do #1028, e chamá-lo de arquivo seria dizer algo falso) — verificação:
`pytest tests/test_motor.py` — reversão: `git checkout`.

**4. Os testes** — arquivos: `tests/test_motor.py`, `tests/test_ia.py` — quatro: documento recebe a
linha nova; figurinha continua com a genérica; `unsupported` continua com a genérica; e a instrução
da IA cita a direção. **Mais um que é o caso do chamado**: a lista que a IA recebe
(`folhas_e_menus` + `ia._lista`) passa a conter a palavra "vender" nas opções de Fornecedores — é a
prova de que o insumo mudou, que é o que esta etapa faz — verificação: os cinco passam, e a suíte
inteira passa — reversão: apagar os casos.

**5. O manual** — arquivo: `docs/manuais/recepcao.md` — as três linhas novas na tabela de sinais
(as duas descrições que o cliente lê, e a linha de arquivo). **Nada no manual de hoje fica falso**,
e o `INDICE.md` não muda (o manual já está indexado; o índice daqui tem duas colunas) —
verificação: alguém de fora entende por que "Comercial" agora diz "comprar" — reversão:
`git checkout`.

**6. [SÓ O DONO] Os dois restarts e a prova** — detalhe abaixo — reversão: o `ROLLBACK_PLAN` da spec.

**7. Devolver a demanda** — fechar o #1027 com o que mudou e o manual. **Nenhum pré-requisito de
cadastro**: ninguém precisa preencher nada para a etapa servir — verificação: quem abriu entende
lendo só a devolução — reversão: reabrir a demanda.

## O que só você pode fazer

**1. Reiniciar os DOIS serviços** (janela elevada; a migração entra ao subir):

```powershell
Restart-Service axiaatende-recepcionista
Restart-Service axiaatende-backend
```

**2. A prova, em dois atos.** O primeiro é visual e não gasta IA:

- abra o WhatsApp da empresa e escreva **menu**: no menu principal, **Comercial** deve dizer que é
  para *comprar* sementes, e **Fornecedores**, *vender para a Renascer*;
- depois, a prova da direção, que **gasta uma chamada de IA** (US$ 0,10 por milhão de tokens de
  entrada — centavos): escreva, de um número que **não** é da equipe, algo como *"represento uma
  empresa de embalagens, posso apresentar nossos preços?"*. A proposta deve ser **Fornecedores**.
  Se vier Comercial, me diga: o conserto é texto de descrição, não código, e sai numa migração 020.

**3. A prova do arquivo, se quiser:** mande um PDF de um número de fora. Deve chegar *"Não consigo
abrir arquivo por aqui…"*, e não a frase genérica.

Nada mais pede a sua mão: nenhum segredo, nenhuma tarefa agendada, nenhuma fase do ERP.

## Riscos de execução identificados

| Passo | O que quebra se interromper no meio | É seguro ficar parado ali? |
|---|---|---|
| 1 (migração no disco) | nada: o serviço só a aplica ao **subir** | **sim** |
| 2 e 3 (código) | nada: o serviço roda o código antigo até o restart | **sim** |
| 4 e 5 | nada: teste e documento | **sim** |
| 6 (os dois restarts) | se só um subir, um fica com schema novo e outro com o antigo. A migração é **transacional e com trava** (`pg_advisory_xact_lock`): não há aplicação parcial | **sim**, terminando o segundo |

**O único passo que escreve em dado de produção é o 1, e ele é o mais delicado desta etapa porque
ALTERA linha existente** (o #1031 só inseriu). Três coisas o tornam seguro: é transacional; o
`_VOLTA` carrega os **valores literais de hoje**, copiados do banco antes de escrever o arquivo, e
não um "apague" genérico; e **mudança aplicada não se edita** — se o arquivo mudar depois, o serviço
não sobe e diz qual, então corrigir a 019 é escrever a 020.

**O fio da coluna com dois públicos é o risco de desenho, não de execução:** uma descrição boa para
a IA que caísse numa linha de lista apareceria na tela do cliente. O passo 1 separa as sete em dois
grupos justamente por isso, e a verificação do passo 1 confere o limite de 72 caracteres, que é o que
a tela suporta.

## Linha de abertura da sessão de execução

> Leia o `C:\AxiaAtende\CLAUDE.md` inteiro e o `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. Faixa:
> **aplicação de plano aprovado** — execute
> `C:\AxiaAtende\docs\specs\2026-10-15-a-direcao-do-pedido-e-o-arquivo-plano.md`, com a spec ao lado
> (mesmo nome, sem `-plano`). Chamado **#1027**: todo commit cita `#1027`, com o prefixo
> `[axiaatende]`, e o primeiro ato é `tratar 1027 --status em_andamento` pela skill `/demanda`. **As
> decisões que NÃO se reabrem:** o conserto da direção é **cadastro E instrução**, não um dos dois;
> as **16** descrições de nome de estado continuam vazias de propósito; a linha nova de arquivo vale
> para `document`, `audio` e `video` — **imagem e `unsupported` ficam fora**, e o motivo está medido;
> nenhum arquivo é encaminhado a ninguém; nada muda no modelo, no `enum` ou no esquema de saída da
> IA. **A descrição tem dois públicos** (lista mostra, botão não): escreva cada uma para quem a lê, e
> respeite os 72 caracteres do `menu_descricao`. Pare no passo 6 — os dois restarts e a prova são da
> mão do dono. O que vai para a tela durante a execução está no `PADRAO-TRABALHO.md` §1: decisão do
> dono, incidente que merece chamado próprio, e passo que depende da mão dele. Conserto de caminho
> feito dentro do planejado não se narra.
