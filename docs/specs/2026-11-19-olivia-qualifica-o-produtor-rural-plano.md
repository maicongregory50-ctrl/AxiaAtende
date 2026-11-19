# Plano — A OlivIA qualifica o produtor rural e entrega a ficha a quem atende (piloto SC e RS)
**Data:** 2026-11-19
**Chamado:** #1660
**Spec de origem:** docs/specs/2026-11-19-olivia-qualifica-o-produtor-rural.md
**Status:** APROVADO

**Executável pelo agente:** não -- o AxiaAtende é executado em sessão com pessoa, e há passos de mão do dono (a tela Destinos, ligar a chave e a prova real).

Conformidade com o Manual legal: não se aplica (a spec diz por quê). Conformidade com a casa: R7 muda
(passo 9); R2 conforme.

## Passos

1. **A migração** — `backend/migracoes/NNN_leads_da_olivia.sql` e `_VOLTA.sql`, com o próximo número
   livre (em 19/11/2026 é 072; conferir a pasta antes). Cria `atendimento.leads` (id; `conversa_id`
   único; `destino_id`; nome, produto, finalidade, tamanho, quando, municipio, uf; `resumo`; `completa`;
   `faltou` text[]; `criado_em`; `enviada_em`, `enviada_como` 'texto'|'modelo', `wamid`, `erro`) e os
   ajustes `olivia.qualifica_produtor` = false e `olivia.qualifica_estados` = ["SC","RS"], com a
   conferência dentro da transação. O papel `axiaatende_ro` ganha SELECT na tabela nova, no molde das
   migrações anteriores. — verificação: `tests/test_migracoes.py`; aplica e a `_VOLTA` desfaz no banco
   de teste (5437). — reversão: a `_VOLTA`.

2. **As ferramentas** — `backend/olivia.py`: `qualifica(con)` (a chave, e só com `conduz_venda`),
   `_estados_do_piloto(con)`, e em `ferramentas()` duas novas, só com a chave ligada e fora da conversa
   de vaga: `anotar_lead` (campos opcionais: nome, produto, finalidade, tamanho, quando, municipio, uf;
   cria ou atualiza a linha da conversa) e `fechar_lead` (chave da folha, restrita por enum a
   `comercial.produtor.<uf>` dos estados do piloto, e `resumo` de até 300 letras). `fechar_lead` grava o
   resumo, calcula `completa` e `faltou`, manda a ficha (passo 3), entrega o cartão por `motor.escolher`
   e devolve ao modelo, em palavras, se a ficha saiu ou não. `passar_contato` continua existindo para o
   resto. — verificação: testes em `tests/test_olivia_lead.py`: chave desligada, as ferramentas não
   aparecem; chave ligada na conversa de vaga, não aparecem; enum só com SC e RS. — reversão: revert.

3. **O envio da ficha** — `backend/lead.py` (novo, pequeno): `texto_da_ficha(con, lead, numero)` (nome,
   as quatro respostas ou "não disse", "Ficha incompleta: faltou ..." quando for o caso, o resumo e o
   link `https://wa.me/<numero>`), `linha_da_ficha(...)` (uma linha, sem quebra, com o telefone escrito,
   cortada para caber no modelo) e `mandar(con, saida, lead, destino, agora) -> bool`: com
   `envio.janela_aberta` do destino, `saida.texto`; senão `saida.modelo` com `modelo_do_uso(con,
   "aviso_olivia_resumo")`. Registra em `atendimento.enviadas` (resumo `lead da olivia: ficha`) e em
   `leads` (`enviada_em`, `enviada_como`, `wamid`); qualquer falha grava `erro` e devolve False, sem
   exceção para cima. O destino que é a própria pessoa (`internos.destino_proprio`) não recebe ficha.
   — verificação: três testes (na janela sai texto com o link; fora sai o modelo com uma linha; a saída
   que falha devolve False e grava o erro). — reversão: revert.

4. **As regras do modo** — `backend/olivia.py`: bloco `REGRAS_DA_QUALIFICACAO`, que entra na instrução só
   com a chave ligada: para produtor rural dos estados do piloto, depois do "temos", pedir licença para
   quatro perguntas rápidas; uma por mensagem; não perguntar o que já foi dito; anotar com `anotar_lead`
   a cada resposta; pressa, recusa ou silêncio numa pergunta → `fechar_lead` na hora, sem insistir; a
   fala final conforme o resultado da ferramenta (D6). A regra 26 ganha a exceção. Categoria ou estado
   fora do piloto: as regras do #1589, sem mudança. — verificação: teste do texto da instrução com e sem
   a chave; teste de conversa inteira com a IA falsa (quatro respostas → `leads` completa, ficha, cartão,
   fala final); teste da pressa (ficha incompleta com `faltou`). — reversão: revert.

5. **As duas travas** — `backend/olivia.py`: (a) `aviso_sem_ficha(con, conversa, texto)`: fala que afirma
   que o consultor foi avisado ou está recebendo, numa conversa sem `leads.enviada_em`, é trocada pela
   apresentação simples, com registro próprio (molde: `promessa_sem_candidatura`); (b) apresentação
   garantida: `passar_contato` ou `fechar_lead` chamados sem texto na mesma resposta → o código manda
   "<nome>, na sua região quem atende é o nosso consultor <primeiro nome>. Segue o contato dele." antes
   do cartão (sem nome da pessoa, a frase começa em "Na sua região"). Vale para toda a venda. —
   verificação: um teste para cada (a frase trocada e registrada; o cartão sem fala ganha a
   apresentação; com fala, não duplica). — reversão: revert.

6. **A conversa de qualificação não é travada** — `olivia.travou`: com linha em `leads` para a conversa
   e sem `enviada_em`, só valem o "não é isso" e a repetição de mensagem com mais de três palavras. —
   verificação: teste com quatro respostas curtas seguidas, nenhuma fala marcada `travou`. — reversão:
   revert.

7. **O entorno** — `olivia.fechar_dia` conta os leads do dia (completos, incompletos, com erro de envio)
   no resumo do vigia; `vaga.limpar` (ou rotina ao lado) apaga `leads` com mais de 12 meses;
   `recepcionista./saude` ganha `olivia_qualifica`; `scripts/olivia.py` ganha `ligar-qualifica` e
   `desligar-qualifica` (recusam quando o ajuste não existe ou a venda está desligada). — verificação:
   testes de cada um. — reversão: revert.

8. **A bateria inteira** — `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=<único>`,
   uma por vez (conferir antes se não há outra do AxiaAtende). — verificação: tudo verde, e o número
   de testes dito no commit. — reversão: nada a reverter.

9. **A governança (R7)** — `C:\AxiaSecurity\design\agentes.json` (a linha `olivia-anonima`: o modo de
   qualificação, as duas ferramentas, a mensagem ao interno e a chave),
   `docs\governanca\politica-uso-ia.md` (a regra do #1589 ganha a do #1660), e o inventário regravado
   por `scripts\gerar_tabela_agentes.py`. Editar a FONTE json, nunca a tabela md. — verificação:
   `scripts\conferir_inventario_agentes.py --politica` e `scripts\conferir_agentes.py --sem-banco`
   passam; o documento diz o que o sistema passou a fazer. — reversão: revert no AxiaSecurity.

10. **O manual** — `docs/manuais/olivia.md`: a seção da conversa de quem quer comprar ganha o piloto (o
    texto é o `## Manual de uso` da spec), a tabela do `/saude` ganha `olivia_qualifica`, e saem as duas
    frases que ficam falsas ("não guarda ficha de quem quer comprar e não avisa o representante"; "não
    avisa o representante: quem chama é a pessoa, pelo cartão") para o produtor de SC e RS com a chave
    ligada. O manual já está no `INDICE.md`; conferir a linha. — verificação: quem não participou do
    desenho segue o caminho comum sem perguntar. — reversão: revert.

11. **Subir** — commits citando `#1660`, push; reinício de `axiaatende-backend` (aplica a migração) e de
    `axiaatende-recepcionista` pela Porta-Ação, conferindo o id ecoado e a hora de subida no `/saude`.
    — verificação: `/saude` de pé com `olivia_qualifica: desligada`; a tabela existe (papel de leitura).
    — reversão: ROLLBACK_PLAN da spec, passos 3 e 4.

12. **[SÓ O DONO] A tela e a chave** — ver "O que só você pode fazer". — verificação: pela leitura, a
    folha `comercial.produtor.sc` com destino Maicon Gregory e o `/saude` com `olivia_qualifica: ligada`.
    — reversão: a mesma tela e `desligar-qualifica`.

13. **A prova real** — de um número de fora, como produtor de SC: (a) respondendo as quatro perguntas;
    (b) dizendo "só quero o contato" na segunda. Ler as duas conversas e o que chegou ao dono. —
    verificação: nos dois casos a ficha chegou ao WhatsApp do dono (em (b), marcada incompleta), o
    cartão saiu com apresentação, e a frase "está recebendo agora" só aparece porque a ficha saiu. —
    reversão: `desligar-qualifica`.

14. **Devolver o chamado** — `entregar 1660 --devolucao @arquivo.txt`, com o manual e o pré-requisito (a
    janela de 24 h de quem recebe). — verificação: o dono usa lendo só a devolução. — reversão: reabrir.

## O que só você pode fazer

1. Na tela Destinos (no servidor, `127.0.0.1:8009`): opção *Comercial › Produtor rural › SC* → destino
   **Maicon Gregory**. O RS já está em seu nome.
2. Ligar o piloto, em PowerShell administrador:
   ```
   cd C:\AxiaAtende; $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'; .\.venv\Scripts\python.exe scripts\olivia.py ligar-qualifica
   ```
3. A prova do passo 13, de um número de fora.

```pos-entrega
dono=trocar o destino de Comercial › Produtor rural › SC para Maicon Gregory na tela Destinos
dono=rodar scripts\olivia.py ligar-qualifica em PowerShell administrador
dono=prova real de um numero de fora como produtor de SC, completa e com pressa
```

## Riscos de execução identificados

- Passos 1 a 10: interrompidos em qualquer ponto, nada muda em produção (nada subiu).
- Passo 11: backend reiniciado e recepcionista não → a tabela existe e ninguém a usa; seguro. O inverso
  (recepcionista com o código novo e a migração não aplicada) → a chave não existe, `qualifica()` lê
  false e o comportamento é o de hoje; seguro, mas reiniciar o backend primeiro.
- Passo 12 feito pela metade (chave ligada, SC ainda no Djeison): a ficha e o cartão do produtor de SC
  vão ao Djeison, que não sabe do piloto. Fazer a tela ANTES da chave.
- Entre o 12 e o 13 o piloto já vale para produtor real: se a prova mostrar defeito, `desligar-qualifica`
  na hora.
- O número da migração pode ter sido tomado por outra sessão (aconteceu com a 071): conferir a pasta no
  passo 1 e de novo antes do passo 11.
- A Porta-Ação é de slot único: pedido feito enquanto outra sessão usa é perdido. Conferir a hora de
  subida no `/saude`, não só o `.out`.

## Linha de abertura da sessão de execução

Leia `C:\AxiaAtende\CLAUDE.md` e `C:\SuporteAxia\docs\PADRAO-TRABALHO.md` (o que vai para a tela durante a execução está no §1). Execute o plano `C:\AxiaAtende\docs\specs\2026-11-19-olivia-qualifica-o-produtor-rural-plano.md` (spec ao lado, D1 a D10): é aplicação de plano aprovado. Chamado #1660; todo commit cita `#1660`, e o primeiro ato é `tratar 1660 --status em_andamento` pela skill `/demanda`. Não se reabrem: perguntas ANTES do cartão; ficha e cartão para o destino da folha (no piloto, o dono); piloto só produtor rural de SC e RS; sem resposta, cartão na hora e ficha incompleta; fora da janela o modelo `olivia_resumo`; sem classificação de lead nem tela; ela só diz que o consultor está recebendo o resumo quando a ficha saiu. Pare no passo 12 ("O que só você pode fazer"): a tela Destinos e a chave são do dono, a tela antes da chave.
