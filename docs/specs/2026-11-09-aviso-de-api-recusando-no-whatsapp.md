# O aviso de API externa recusando chega ao WhatsApp do dono
**Data:** 2026-11-09
**Chamado:** #1337
**Status:** APROVADO

## Contexto

O #1280 (AxiaGestão) pôs no ERP um vigia que, quando uma API externa recusa 3 vezes seguidas ou passa
2 h sem resposta boa, abre alerta fiscal, chamado bug e **deixa um aviso PENDENTE** em
`axia.integracoes_avisos`, com o texto pronto (*"A integração com <provedor> está recusando desde
HH:MM (N recusas seguidas). Motivo: … Chamado #N aberto."*, `integracoes_service.py:253-256`). O ERP
publica `GET /atendimento/integracoes-avisos` e `PATCH /atendimento/integracoes-avisos/{id}` na
atividade `AUD.AVISO`, que o agente `ATENDIMENTO` já tem (`routers/atendimento.py:37-51`).

Deste lado, quem puxa aviso do ERP e manda ao WhatsApp é `backend/auditoria_erp.py` (#350): a cada
minuto, no processo das TELAS, busca os pendentes da auditoria de estoque, grava um
`atendimento.avisos` por destino do ajuste `auditoria_estoque_para`, correlaciona em
`atendimento.avisos_auditoria_erp` (PK `erp_aviso_id`) e devolve ENVIADO/FALHOU. Quem manda é a volta
de sempre dos avisos (`envio.mandar_avisos`): com o porteiro ligado, texto dentro da janela de 24 h e a
**reabertura** fora dela (o modelo pago "Você tem N aviso(s)", e o texto sai no toque em Ver ou quando
a pessoa escreve). O módulo conhece **um** tipo: `auditoria_estoque`, com rota, ajuste e partes fixos.
Sem este chamado o aviso do vigia fica PENDENTE no ERP para sempre: é o fracasso silencioso que o
plano do #1280 nomeou.

**Um achado que corrige o #1280.** O chamado diz *"até o modelo ser aprovado na Meta, o aviso sai só
dentro da janela"*. Não é assim com o porteiro: `AXIAATENDE_PORTEIRO=on` no XML do recepcionista
(`servicos/axiaatende-recepcionista.xml:28`), e fora da janela o porteiro manda a **reabertura**, não
o modelo do tipo. O que o código exige é a **linha** do modelo no cadastro (`envio.py:661-664` levanta
`nenhum modelo cadastrado para aviso_<tipo>` sem ela), não a aprovação na Meta. A aprovação só
importaria com o porteiro desligado.

## Os fios que encostam

**O que a mudança escreve, e quem mais escreve lá:**

- `atendimento.avisos`: escrevem `envio.py` (recusa, resumo, reabertura, status do dia),
  `auditoria_erp.py` e `pendencias_erp.py`; o CHECK `avisos_tipo` foi alterado pela última vez na 049
  (`auditoria_estoque`). Ganha `integracao_recusada`. Quem lê para decidir: `envio.mandar_avisos` e o
  porteiro (`tipo` → `modelo_do_uso("aviso_" + tipo)`), a tela Envios (aba de avisos).
- `atendimento.modelos`: linha nova `aviso_integracao` (UTILITY, uso `aviso_integracao`, variável
  `aviso1`). O CHECK de `uso` foi alterado pela 049 e pela 033; ganha o uso novo. Quem lê:
  `modelo_do_uso`, `modelos_meta.propor`.
- `atendimento.avisos_auditoria_erp`: hoje só `auditoria_erp.py` escreve e lê (e o teste). Passa a
  ter a coluna `canal` (`auditoria_estoque` | `integracao_recusada`), PK `(canal, erp_aviso_id)`:
  os ids do ERP vêm de tabelas diferentes e colidem.
- `atendimento.ajustes`: chave nova `integracoes_para` (lista de ids de `destinos`), ao lado de
  `auditoria_estoque_para`. Quem lê: só o canal novo.
- No ERP: `axia.integracoes_avisos.estado` passa a ser escrito por este lado via PATCH (hoje nada o
  escreve além do INSERT do vigia).

**Quem volta depois:** o laço `avisos_da_auditoria` do `main.py` (1 min) para os dois canais; o
porteiro dos avisos (a cada minuto do recepcionista); o vigia do ERP, que **não** relê o estado do
aviso (ele só cria); a tela Envios mostra o aviso na aba.

## O universo medido

- **1** canal hoje em `auditoria_erp.py`, com rota, ajuste, tipo e partes fixos em código; a volta tem
  **60 linhas** e a lógica de correlação/situação/devolução é toda reaproveitável. Copiar o módulo
  seria o segundo escritor da mesma régua.
- **`AXIAATENDE_PORTEIRO=on`** em produção (XML do recepcionista): o caminho fora da janela é a
  reabertura. **0** modelos de aviso precisaram de aprovação na Meta para sair desde o #1188.
- **Texto do ERP ≤ ~420 caracteres** (300 do motivo + a moldura); a Meta aceita até 1.024 por
  variável e o texto da janela é livre: cabe sem cortar.
- **0** avisos `integracao_recusada` pendentes no ERP em 09/11 (o vigia acabou de subir e a prova
  `--valendo` limpou o ensaio). O primeiro real será a prova de efeito.

## Conformidade com o Manual legal

não se aplica: aviso operacional ao dono; nenhuma régua fiscal.

## Conformidade com a casa

não se aplica: nenhum segredo, serviço, porta ou agente novo. O canal usa o mesmo agente
`ATENDIMENTO`, a mesma atividade `AUD.AVISO`, o mesmo laço de 1 min e a mesma volta de avisos. O
dado novo é uma coluna e uma linha de modelo no banco do atendimento, já coberto pelo backup do
projeto (R2 do #950).

## Decisão

**Generalizar o canal, não copiar o módulo.** `auditoria_erp.py` passa a trabalhar sobre uma lista de
canais, cada um dizendo: `nome` (o `canal` da correlação e o `tipo` do aviso), `ir` (a função de
`erp.py` que busca os pendentes), `devolver`, `ajuste` (chave dos destinos) e `partes(p)` (as
variáveis do modelo a partir do pendente). `volta(cfg)` itera os canais; cada um devolve a própria
contagem, e um canal fora do ar não para o outro. O canal da auditoria fica **idêntico** no
comportamento (mesmos testes verdes, sem mudar). O canal novo:

| | `integracao_recusada` |
|---|---|
| `ir` | `erp.integracoes_pendentes` → `GET /atendimento/integracoes-avisos` (`avisos[]`, token) |
| `devolver` | `erp.estado_do_aviso_integracao` → `PATCH /atendimento/integracoes-avisos/{id}`; 409 = já respondido, tratado como o 404 da auditoria |
| `ajuste` | `integracoes_para` (nasce com o dono: o mesmo destino que abre `auditoria_estoque_para`) |
| `partes` | `[texto]` do ERP, já pronto, sem remontar |
| modelo | `aviso_integracao`, UTILITY, `{{1}}` = o texto; **cadastrado na migração**, proposto à Meta só se o porteiro for desligado |

Com o porteiro ligado: dentro da janela sai o texto; fora, a reabertura e o texto no Ver. Sem
destino configurado, FALHOU com *"Ninguém configurado para receber o aviso (ajuste integracoes_para)"*,
como a auditoria faz. O ERP recebe ENVIADO quando ao menos um destino recebeu, FALHOU quando todos
falharam ou ficaram não vistos (7 dias).

**Alternativa recusada:** `integracoes_erp.py` como cópia de `auditoria_erp.py` trocando rota e tipo.
Duas voltas iguais, dois lugares para corrigir o mesmo defeito.

## Escopo desta etapa

**Dentro:** migração 060 (tipo, uso, modelo, coluna `canal`, ajuste `integracoes_para`); os dois
clientes em `erp.py`; a generalização de `auditoria_erp.py` com os dois canais; testes do canal novo
e os da auditoria intactos; manual de Envios (seção dos avisos à equipe); devolução.

**Fora:** mudar o texto do aviso (é do ERP); outros destinos além do dono; o tile do painel (#1338);
aprovar o modelo na Meta (só se o porteiro for desligado; fica anotado em "O que só você pode fazer").

## Impacto em produção

- Migração 060 no banco do atendimento, com `_VOLTA`.
- Restart de `axiaatende-backend` (as TELAS, onde o laço roda). O recepcionista não muda.
- O primeiro aviso real só sai quando o vigia do ERP abrir episódio: a prova de efeito usa
  `conferir_1280_vigia.py --valendo` do ERP, que cria um aviso real e o recusa depois.

## ROLLBACK_PLAN

1. Tirar o canal da lista em `auditoria_erp.py` (uma linha) ou `git revert`; restart das TELAS. O
   aviso volta a ficar PENDENTE no ERP, visível, sem perda.
2. `060_aviso_integracao_VOLTA.sql`: remove a linha do modelo, o uso e o tipo dos CHECKs, a coluna
   `canal` (só com a tabela sem linhas do canal novo) e o ajuste. Só depois do passo 1.
3. Avisos já enviados ficam no histórico; o ERP já recebeu o estado deles.

## Manual de uso

Em `docs/manuais/envios.md`, na seção dos avisos que o sistema manda à equipe, uma entrada
**"API externa recusando"** (tabela dos tipos e "O que NÃO faz"):

1. **Para que serve.** Quando um serviço de fora (Receita, SEFAZ, bancos, Focus, Clicksign…) para de
   aceitar o que o AxiaGestão manda, o dono fica sabendo no WhatsApp em até 1h30, com o motivo e o
   número do chamado que já nasceu.
2. **Quem usa e quando.** O dono, ao receber; quem cuida do sistema, para conferir na tela Envios se o
   aviso saiu.
3. **O caminho comum.** O aviso chega como texto se você falou com o número da empresa nas últimas
   24 h; senão chega "Você tem N aviso(s)", e o texto vem ao tocar **Ver**. O chamado citado já está
   na fila; o detalhe fica em Contabilidade → Manual legal → Mudanças de lei a tratar, no AxiaGestão.
4. **O que significa cada sinal.** *Enviado*: saiu para o seu número. *Guardado*: espera o toque em
   Ver. *Não visto*: 7 dias sem toque, não sai mais e o ERP recebe FALHOU. *FALHOU por "ninguém
   configurado"*: o ajuste `integracoes_para` está vazio.
5. **O que NÃO faz.** Não manda a mais ninguém além dos destinos do ajuste. Não repete: um aviso por
   episódio, do lado do ERP. Não avisa quando o serviço volta (isso vai ao chamado, não ao celular).
   Não conserta nada.

## Próximo passo

/writing-plans
