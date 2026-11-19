# A resposta padrão ao produtor cooperante que responde a um aviso automático do contrato
**Data:** 2026-11-19
**Chamado:** #1664
**Status:** APROVADO

## Contexto

Em 19/11/2026, às 09:00, o primeiro termo de reprovação de lote (#1542) saiu pelo WhatsApp da empresa
para um produtor cooperante. Às 09:05 ele perguntou "Quais são todos os meus lotes de centeio e aveia?
Para saber qual espécie e volume que foi reprovado". O atendimento o tratou como cliente da carteira:
entregou o contato do representante comercial e perguntou se o assunto era "documento ou qualidade da
semente". Ninguém da equipe foi avisado. O dono viu por acaso e respondeu pelo WhatsApp pessoal, pedindo
desculpa pela "mensagem automática do nosso sistema, sem aviso prévio".

O dono decidiu (19/11/2026) o que o atendimento deve fazer nesse caso: dizer, pelo nome, que foi "um
envio automático do sistema sobre os andamentos do nosso contrato de multiplicação de sementes", que o
atendimento não tem os detalhes, e que quem atende na empresa é ele ("o contato legal lá no contrato sou
eu"), entregando o cartão. E a visão: aos poucos todas as etapas do contrato serão avisadas por ali
(contrato na plataforma de assinatura, carga recebida, análises, pagamento), e o produtor se acostuma.
Desta etapa fica **só a primeira escada: a mensagem padrão** (dono: "vamos fazer só a primeira escada").

## Os fios que encostam

**Quem mais escreve o que a mudança escreve**

- `atendimento.enviadas`: a resposta padrão, o cartão e o aviso ao contato ganham linhas, como qualquer
  envio. A resposta padrão é reconhecida depois pelo `resumo` (`aviso de contrato: resposta padrao`),
  sem coluna nova.
- `atendimento.termos_reprovacao`: **só leitura** nesta etapa. Quem escreve continua sendo
  `termo_erp` (as telas trazem do ERP; o recepcionista manda e grava estado e ciência).
- `atendimento.conversas`: a mensagem do produtor não abre conversa de menu. Nenhum escritor novo.

**Quem lê para decidir**

- `motor.tratar`: é onde o toque `termo:ciente:<id>` já é desviado antes do menu (#1542). O desvio novo
  entra logo depois dele e ANTES do portão do cliente, que hoje é quem responde a esse produtor.
- O portão do cliente e a retomada ("Pelo que entendi, você quer Qualidade. É isso?"): deixam de ver a
  mensagem de quem está dentro do prazo do aviso.
- A OlivIA: só atende quem não tem cadastro; não é tocada.

**Quem volta depois**

- `termo_erp.aplicar_status` e `termo_erp.tocar` (estado da Meta e ciência): seguem iguais; o toque no
  botão "Recebi e estou ciente" continua sendo tratado antes, e não recebe a resposta padrão.
- A pesquisa das 4h30 e a retomada da carteira: não são marcadas, porque não há conversa de menu.

## O universo medido

Medido em 19/11/2026, papel de leitura:

- Termos de reprovação enviados até hoje: **1**. Respostas de produtor a termo: **1** (a do caso).
- Nessa conversa: `erp_cadastros` = 7 e `erp_codigo`, `erp_nome`, `erp_papeis` nulos. O número casa com
  sete cadastros do ERP e o atendimento não diz quem é a pessoa. **Por isso o gatilho desta etapa não usa
  o cadastro**: usa o próprio aviso (`termos_reprovacao.para_whatsapp` e `enviado_em`), que já traz o
  número e o nome.
- O nome disponível é o `produtor_nome` do termo (a razão social, em caixa alta). Não há campo que diga
  se é senhor ou senhora.
- Avisos automáticos de contrato que existem hoje: só o termo de reprovação. Os outros são da visão.

## Conformidade com o Manual legal

Não se aplica: a etapa não muda o termo, a cobrança nem regra fiscal; só a resposta do atendimento a
quem escreve depois dele.

## Conformidade com a casa

Não se aplica: texto fixo mandado pelo código, sem agente nem modelo de IA; nenhum segredo, serviço,
porta ou dado novo (uma chave de ajuste no banco que já existe e é copiado).

## Decisão

- **D1. O gatilho.** Quem recebeu um aviso automático de contrato pelo número da empresa e escreve pelo
  mesmo número dentro do prazo (`cooperante.dias`, nasce 7) recebe a resposta padrão. Hoje "aviso de
  contrato" é a linha enviada de `termos_reprovacao`; o desenho deixa o ponto de entrada num lugar só
  (`aviso_de_contrato_recente(con, numero, agora)`), para os próximos avisos entrarem ali.
- **D2. O texto, fixo, sem IA** (aprovado pelo dono em 19/11/2026):
  "<Saudação>, <nome>! Essa mensagem foi um envio automático do nosso sistema, que passou a informar os
  andamentos do seu contrato de multiplicação de sementes. Aos poucos todas as etapas vão chegar por
  aqui. Eu não tenho os detalhes do seu contrato; quem atende na empresa é o <contato>. Segue o contato
  dele." O texto mora num ajuste (`cooperante.texto`), para mudar sem código. Um texto só serve também
  para a reação mais dura: ele já diz que é automático e quem sabe do contrato.
- **D3. O nome e o tratamento.** O primeiro nome do `produtor_nome` do aviso, com a caixa arrumada
  (`primeiro_nome`). O dono aprovou "Seu Alfonso" e "o senhor"; como o aviso não diz se é senhor ou
  senhora, a forma gravada é a sem gênero acima ("Bom dia, Alfonso!"), e "Seu/Dona" entra quando o ERP
  passar a mandar o tratamento. Confirmado pelo dono em 19/11/2026 ("a").
- **D4. O cartão.** O do contato legal do contrato: o destino nomeado no ajuste `cooperante.destino`
  (nasce apontando o destino "Maicon Gregory" da tela Destinos). Sai logo depois do texto.
- **D5. O contato é avisado na hora**, com o que o produtor escreveu, o nome, o número do aviso e o link
  dele: texto livre dentro da janela de 24 h do contato; fora dela, uma linha pelo modelo `olivia_resumo`
  (o mesmo recurso do #1660). Falha no aviso não segura a resposta ao produtor; fica no registro.
- **D6. Uma vez por aviso.** A resposta padrão sai na primeira mensagem depois de cada aviso. Nas
  seguintes, dentro do prazo, ele recebe uma linha curta ("<nome>, o <contato> já foi avisado da sua
  mensagem; o contato dele está logo acima.") e cada mensagem é repassada ao contato. Áudio, foto e
  documento contam como mensagem.
- **D7. O que não muda.** O toque em "Recebi e estou ciente" (tratado antes). Toque em botão de menu que
  ele já tinha na tela segue o menu.
- **D8. A chave.** `cooperante.resposta_padrao` (ajuste, nasce `false`), com
  `scripts\cooperante.py ligar|desligar|mostrar`, sem reinício.

## Escopo desta etapa

**Dentro:** o desvio em `motor.tratar`; o texto, o cartão, a linha curta e o aviso ao contato; os quatro
ajustes (chave, dias, texto, destino) por migração; o script; testes; o manual.

**Fora:** reconhecer o cooperante pelo cadastro (os sete cadastros do mesmo número); saber do contrato,
dos lotes ou do que foi reprovado; responder sobre o contrato; os outros avisos da jornada (contrato para
assinatura, carga recebida, análises, pagamento), que são do AxiaGestão, um chamado por aviso; mudar o
termo para levar espécie e volume, ou decidir se ele sai sem contato prévio (#1542, AxiaGestão); a
OlivIA atender cooperante.

## Impacto em produção

- Serviço: `axiaatende-backend` (aplica a migração) e `axiaatende-recepcionista`, um reinício de cada
  pela Porta-Ação.
- Dados: quatro ajustes novos; a chave nasce desligada. Nenhuma tabela nova.
- Com a chave desligada, tudo como hoje.

## ROLLBACK_PLAN

1. `scripts\cooperante.py desligar` (sem reinício): o produtor volta a cair no portão do cliente.
2. `git revert` dos commits do #1664 e reinício do recepcionista pela Porta-Ação.
3. A `_VOLTA` da migração apaga os quatro ajustes.

## Manual de uso

**Para que serve.** O produtor cooperante que responde a um aviso automático do contrato (hoje, o termo
de reprovação de lote) recebe uma explicação curta de que aquilo foi um envio automático, e o contato de
quem o atende. Quem o atende é avisado na hora, com o que ele escreveu.

**Quem usa e quando.** O contato legal dos contratos de multiplicação (hoje o dono), sempre que um
produtor escreve ao número da empresa nos dias seguintes a um aviso.

**O caminho comum.**
1. O produtor responde ao aviso.
2. Ele recebe a mensagem padrão e o seu cartão.
3. Você recebe no WhatsApp: "Cooperante respondeu ao aviso", com o nome, o aviso, o que ele escreveu e o
   link para falar com ele.
4. Você responde a ele, pelo cartão ou pelo link.

**O que significa cada sinal.**
- **Mensagem de uma linha, "Resumo da OlivIA: cooperante ..."**: você estava há mais de 24 horas sem
  escrever ao número da empresa; veio a forma curta, com o telefone escrito.
- **Mais de um aviso seguido do mesmo produtor**: ele continuou escrevendo; cada mensagem é repassada, e
  ele ouve que você já foi avisado.
- **Nenhum aviso, e o produtor te chamou**: a chave está desligada, ou o prazo de dias já passou e ele
  caiu no atendimento comum.

**O que isto NÃO faz.** Não responde nada sobre o contrato, o lote ou a cobrança. Não reconhece o
produtor que escreve sem ter recebido um aviso recente. Não muda o termo.

**Como ligar e desligar.** `scripts\cooperante.py ligar`, `desligar` e `mostrar`. O prazo, o texto e o
contato são ajustes (`cooperante.dias`, `cooperante.texto`, `cooperante.destino`).

## Próximo passo

`/writing-plans`
