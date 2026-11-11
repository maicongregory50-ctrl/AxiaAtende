# Anexo (PDF ou Word) na resposta do chamado chega ao WhatsApp do autor
**Data:** 2026-11-11  
**Chamado:** #1381  
**Status:** APROVADO

## Contexto

A pergunta ao autor (`comentar --pergunta`) e a devolução (`entregar --devolucao`) chegam ao WhatsApp
de quem abriu o chamado só como texto (#1222). No #1379, em 11/11/2026, a sessão gerou um roteiro em
Word para o Benedito e o dono teve de encaminhá-lo à mão. O dono pediu que o arquivo vá junto da
resposta.

O que existe hoje (lido em 11/11/2026):
- **ERP:** os anexos de chamado vivem em `axia.suporte_conversas_anexos` (`sessao_id` NOT NULL) e só
  nascem da conversa do autor (`routers/suporte_conversas.py:233`). Os tipos aceitos são PDF, imagem e XML
  (`utils/suporte_anexos.py:46`), até 10 MB, guardados em `C:\Dados\AxiaGestao\suporte_anexos`. Nada liga
  um arquivo a uma resposta de quem trata.
- **ERP → AxiaAtende:** `GET /demandas/whatsapp/saida` (`services/demandas_whatsapp_service.py:79-111`)
  devolve uma linha por evento que chega ao autor, só com `texto`.
- **AxiaAtende:** `pendencias_erp.receber` (`backend/pendencias_erp.py:38-63`) grava a linha em
  `atendimento.pendencias_mensagens`; `pendencias._mandar_numero` (`backend/pendencias.py:99-135`) manda
  o texto. `Saida.documento` (`backend/saida.py:183-191`) já manda arquivo, mas com o tipo fixo em PDF.
- **Precedente no AxiaAtende:** a ficha do frete (#1128, `backend/logistica_erp.py:85-144`) baixa o PDF do
  ERP para `envios_pasta` na volta do ERP, e o recepcionista o manda com `saida.documento`.
- **Skill `demanda`:** não tem opção de arquivo; fala JSON com o ERP (`demanda.py:148-201`).

## Os fios que encostam

**Quem mais escreve:**
- A tabela nova `axia.demandas_anexos` (ERP) só é escrita pela rota nova de envio e pelo vínculo dentro de
  `POST /demandas/{id}/eventos` e `POST /demandas/{id}/entregar-ao-autor`. Ninguém mais a escreve.
- `axia.demandas_eventos` não muda de forma: o vínculo fica na tabela nova (`evento_id`).
- `atendimento.pendencias_mensagens` (AxiaAtende) ganha a coluna `anexo` (jsonb, nula). Ela é escrita só
  por `pendencias_erp.receber`. As outras filas que gravam nessa tabela (aprovação, #1276) não a tocam
  e continuam com nulo.

**Quem lê para decidir:**
- `pendencias._mandar_numero` passa a mandar o documento depois do texto quando `anexo` não é nulo.
- `demandas_whatsapp_service.saida` passa a incluir o anexo do evento na linha.

**Quem volta depois:**
- O descarte de 7 dias (`pendencias.mandar`, linha 154) descarta a mensagem e o anexo vai junto (não sai).
- O backup da nuvem copia `C:\Dados\AxiaGestao` todo dia (`backup_cloud_documentos.ps1:38`), e com ele a
  pasta nova `C:\Dados\AxiaGestao\demandas_anexos`.
- A cópia baixada no AxiaAtende (`envios_pasta\chamados`) é cópia de trabalho; a original fica no ERP.

## O universo medido

- Eventos que chegam ao autor nos últimos 30 dias: 8 perguntas (`comentario` com `pergunta`) e 79
  entregas (medido em `axia.demandas_eventos`, 11/11/2026). É esse o universo que pode levar anexo.
- Usuários com WhatsApp cadastrado: 8 (`axia.usuarios.whatsapp`). Quem não tem WhatsApp não recebe nada
  pelo WhatsApp, com ou sem anexo.
- Anexos de chamado hoje: 279, sendo 203 PNG, 66 PDF, 7 JPEG e 3 XML (`axia.suporte_conversas_anexos`).
  Nenhum Word, porque a regra atual não aceita. A tabela antiga não muda.
- Nenhum registro existente muda de estado: a mudança só vale para respostas novas que trouxerem arquivo.

## Conformidade com o Manual legal

não se aplica: é canal de mensagem, sem regra tributária nem documento fiscal.

## Conformidade com a casa

- **R2 (dado vivo com cópia) — conforme.** Trecho lido: "Todo dado vivo tem cópia verificada, em disco e
  fora". O arquivo novo fica em `C:\Dados\AxiaGestao\demandas_anexos`, dentro da origem `C:\Dados\AxiaGestao`
  da rotina `backup-documentos-nuvem` (`backups\backup_cloud_documentos.ps1:38`). A linha da tabela
  fica no banco `renascer`, coberto por `backup-postgresql-*`.
- **R4 (superfície de rede) — conforme.** Trecho lido: "A superfície de rede é a declarada: ACL do
  Tailscale, binds em loopback, firewall". Nenhuma porta nova: o AxiaAtende já fala com a 8001 pelo
  agente ATENDIMENTO com `SUP.WPP` (`routers/demandas_whatsapp.py`), e a rota nova de baixar o arquivo
  fica nesse mesmo prefixo e com essa mesma atividade.
- Segredo, agente de IA, sessão e projeto novo: não tocados.

## Decisão

Caminho A, escolhido pelo dono em 11/11/2026: a sessão manda o arquivo junto da pergunta ao autor ou
da devolução, pela skill `demanda` (`--anexo <arquivo>`). O botão de anexar na tela de chamados
(caminho B) fica para depois e não exige refazer nada.

O desenho:
1. **ERP, fase644:** tabela `axia.demandas_anexos` (`id`, `demanda_id`, `evento_id` nulo até o vínculo,
   `usuario_id`, `nome_original`, `caminho`, `media_type`, `tamanho_bytes`, `criado_em`).
2. **ERP, `POST /demandas/{id}/anexos`** (multipart; `SUP.TRATA` ou `SUP.EXEC`): valida (PDF ou Word
   `.docx`, até 10 MB, conteúdo conferido pelo cabeçalho do arquivo e não só pelo nome), grava em
   `C:\Dados\AxiaGestao\demandas_anexos` com nome gerado e devolve o `id`. O arquivo nasce sem evento.
3. **ERP, vínculo na mesma transação:** `EventoCreate` (só com `pergunta`) e `EntregarAoAutorCreate`
   ganham `anexo_id` opcional. A rota liga o anexo ao evento que acabou de gravar
   (`UPDATE ... SET evento_id WHERE id AND demanda_id AND evento_id IS NULL`); se não ligar exatamente uma
   linha, recusa tudo (400). Comentário sem `pergunta` recusa `anexo_id`, porque não chega ao autor.
4. **ERP, `saida`:** a linha do evento ganha `anexo: {id, nome, media_type}` quando há anexo.
5. **ERP, `GET /demandas/whatsapp/anexos/{id}`** (`SUP.WPP`): devolve o arquivo, só se ele estiver ligado
   a um evento.
6. **AxiaAtende, migração 061:** `atendimento.pendencias_mensagens.anexo jsonb` (nula).
7. **AxiaAtende, `pendencias_erp.volta`:** ao receber uma linha com anexo, baixa o arquivo para
   `envios_pasta\chamados\<evento_id>-<nome>` com o mesmo token da volta e grava
   `{"arquivo", "nome", "media_type"}` em `anexo`. Se o download falhar, a linha não é gravada e o
   cursor não anda: tenta na volta seguinte, como a ficha do frete.
8. **AxiaAtende, `pendencias._mandar_numero`:** depois do texto do lote, cada mensagem com anexo sai
   como documento (`saida.documento`, com legenda "Chamado #N" e o tipo do arquivo). `Saida.documento`
   ganha o parâmetro `mime_type` (padrão PDF, e os dois chamadores atuais não mudam). Se o documento
   falhar, o texto já saiu: o erro vai para `pendencias_mensagens.erro` e para o log, e o arquivo
   continua no chamado do ERP. Fora da janela de 24 h, o anexo espera junto com o texto.
9. **Chave:** `pendencias.anexo_ligado` (ajuste do AxiaAtende, padrão ligado). Desligada, a mensagem sai
   só com o texto.
10. **Skill `demanda`:** `comentar --pergunta --anexo <arquivo>` e `entregar --devolucao @f --anexo <arquivo>`
    enviam o arquivo primeiro (multipart) e passam o `anexo_id`. Sem `--pergunta`, `--anexo` é recusado.

## Escopo desta etapa

**Dentro:** fase644 e as três rotas do ERP; vínculo nos dois atos; migração 061 e o envio no AxiaAtende;
`--anexo` na skill; testes dos dois lados; manual.

**Fora:**
- Botão de anexar na tela de chamados (caminho B).
- Mostrar o anexo novo na caixa do autor dentro do ERP: hoje a caixa lista os anexos da conversa
  (`suporte_conversas_anexos`), e este anexo fica guardado no chamado e chega pelo WhatsApp. Chamado
  próprio, se for pedido.
- Outros tipos (imagem, planilha) e mais de um arquivo por resposta.
- Comentário comum (sem `--pergunta`): não chega ao autor, então não leva anexo.

## Impacto em produção

- ERP (8001): fase644 aplicada pelo dono **antes** do restart da 8001 (fase aditiva: tabela nova). Build
  do frontend não é necessário: não há tela.
- AxiaAtende: migração 061 (aditiva), aplicada pelo próprio serviço ao subir; restart pela Porta-Ação.
- Skill `demanda` (SuporteAxia): só o script; nenhuma sessão precisa reiniciar.
- Nenhum dado gravado muda. Pasta nova: `C:\Dados\AxiaGestao\demandas_anexos` (criada pela rota no
  primeiro envio, com a ACL herdada de `C:\Dados\AxiaGestao`).

## ROLLBACK_PLAN

1. Desligar o envio do documento: ajuste `pendencias.anexo_ligado = false` no AxiaAtende. A mensagem
   volta a sair só com o texto, sem restart.
2. Reverter os commits do AxiaAtende e da skill (`git revert`), e o restart do AxiaAtende pela Porta-Ação.
3. Aplicar `061_anexo_na_pendencia_VOLTA.sql` (remove a coluna).
4. Reverter o commit do ERP, aplicar `schema_axia_fase644_demandas_anexos_VOLTA.sql` (remove a tabela) e
   reiniciar a 8001. Os arquivos em `C:\Dados\AxiaGestao\demandas_anexos` ficam no disco; apagá-los é
   decisão do dono.

## Manual de uso

Para quem trata a fila (a sessão e o dono). O autor não vê tela nova: ele recebe um documento no WhatsApp.

1. **Para que serve:** mandar a quem abriu o chamado um arquivo (roteiro, relatório, laudo) junto da
   pergunta ou da devolução, sem encaminhar à mão.
2. **Quem usa e quando:** a sessão que trata o chamado, no momento de perguntar ao autor ou de devolver
   o trabalho.
3. **O caminho comum:**
   1. Gere o arquivo em PDF ou Word (`.docx`), até 10 MB.
   2. Pergunta: `comentar N --pergunta --ok-do-dono "<o que o dono disse>" --motivo @f --anexo <arquivo>`.
      Devolução: `entregar N --devolucao @f --anexo <arquivo>`.
   3. O autor recebe o texto e, logo depois, o documento com a legenda "Chamado #N".
4. **O que significa cada sinal:** a saída da skill diz "anexo #X enviado com a resposta". Se o envio do
   arquivo for recusado (tipo ou tamanho), nada é gravado e a resposta não sai. Fora da janela de 24 h
   do WhatsApp, o documento espera junto com o texto e sai quando o autor abrir a conversa.
5. **O que NÃO faz:** não anexa em comentário comum; não manda imagem nem planilha; não manda mais de
   um arquivo por resposta; não mostra o arquivo na caixa do ERP; não chega a quem não tem WhatsApp
   cadastrado.

Manual a atualizar: o da skill `demanda` (tabela de subcomandos) e o do AxiaAtende sobre o chamado no
WhatsApp (#1222), se houver seção de envio.

## Próximo passo

/writing-plans (na mesma sessão, a pedido do dono).
