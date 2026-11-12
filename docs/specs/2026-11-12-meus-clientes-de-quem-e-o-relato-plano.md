# Plano — Meus clientes: de quem é o relato, parar sem perder texto, sem meio
**Data:** 2026-11-12
**Chamado:** #1439
**Spec de origem:** docs/specs/2026-11-12-meus-clientes-de-quem-e-o-relato.md
**Status:** APROVADO
**Executável pelo agente:** não -- depende do chamado irmão do ERP entrar antes, e os restarts são de janela elevada; executado nesta sessão com o dono no teclado

## Passos

1. **IA: de quem é** — `backend/ia.py`: `ler_visita(texto, ficha, motivos, hoje, candidatos=())`;
   `instrucoes_visita` ganha o parágrafo do cliente (aberto a menos que o texto nomeie outro da lista;
   na dúvida, desconhecido) e perde o do MEIO; o schema ganha `cliente` (string: "aberto",
   "desconhecido" ou o código) e perde `meio`; a mensagem do usuário lista os candidatos
   (`codigo · nome · contato`). O retorno traz `cliente` (int, "aberto" ou "desconhecido") e não traz
   `meio`. — verificação: testes do passo 5 (dublê). — reversão: `git revert`.
2. **Mover o relato** — `backend/clientes_do_dia.py`: `candidatos(con, c)` (a fila do consultor);
   `_mover_relato(con, saida, reg, codigo, agora)` (acha o registro vivo/`depois`/`descartado` de
   hoje ou ontem daquele código ou cria um com a ficha da fila; passa `textos` para lá, zera no
   origem, marca o destino `aberto, lido=false`; manda *"Entendi: isso é sobre X."*; devolve o
   destino); em `rodar`, depois da leitura: `cliente` código ≠ aberto → mover e `seguir` no destino;
   `desconhecido` → `_perguntar_de_quem` (botões aberto + até 2 nomes casados no texto; 3+ lista; sem
   casamento: aberto / "Outro cliente" → lista dos 10 primeiros); toque `cli:dequem:<id>:<codigo>` em
   `_toque` → mover e `seguir`; `cli:dequem:<id>:aberto` → `seguir` no próprio. `_falta` sem `meio`;
   `cartao` sem a linha do meio. — verificação: passo 5.
3. **Parar sem perder** — `_toque`, ramo `parar`: com `textos` e `NOT lido` → mantém `aberto`,
   responde a frase "Guardei…"; senão `descartado` como hoje. — verificação: passo 5.
4. **Sem meio ao ERP** — `backend/clientes_erp.py`: `corpo_do_registro` manda `meio: None`. A
   `texto_da_ficha` mostra o último contato sem o parêntese quando `ultimo_meio` vier vazio. —
   verificação: passo 5.
5. **Testes** — `tests/test_clientes_do_dia.py` + dublê `tests/saida_falsa.py` (`ler_visita` aceita
   `candidatos`, devolve `self.visita` com `cliente`): (a) relato que nomeia outro cliente da fila move
   o registro, diz "Entendi", pergunta o que falta nele, e o aberto volta como corrente depois; (b)
   `desconhecido` pergunta com botões e o toque move; (c) Parar com texto não lido guarda e `rodar` lê
   depois; Parar sem texto descarta; (d) nenhum teste pergunta meio e o corpo ao ERP leva `meio None`;
   os testes antigos que esperavam a pergunta do meio são ajustados. — verificação: pytest do arquivo,
   com o banco de teste 5437.
6. **Manual** — `docs/manuais/meus-clientes.md` com o texto da spec. — verificação: alguém de fora lê.
7. **Commit e bateria** do AxiaAtende.
8. **Devolver** depois dos restarts e de uma prova real sua: um relato de outro cliente da fila e um
   Parar com texto pendente.

## O que só você pode fazer

- **Primeiro o ERP** (chamado irmão): fase do `meio` opcional aplicada e backend reiniciado.
- Depois, restart de `axiaatende-recepcionista` e `axiaatende-backend` (janela elevada).
- A prova real no seu WhatsApp (passo 8).

```pos-entrega
dono=aplicar a fase do ERP (chamado irmão) e reiniciar axiagestao-backend ANTES; depois reiniciar axiaatende-recepcionista e axiaatende-backend; provar com um relato de outro cliente da fila
```

## Riscos de execução identificados

- Atende no ar antes do ERP aceitar meio nulo: o ERP recusa ("Diga como foi o contato") e a frase
  volta ao consultor; nada se perde, o registro volta a `aberto`. Ordem: ERP primeiro.
- Leitura que nomeia o cliente errado: o consultor vê "Entendi: isso é sobre X" e o cartão com o nome;
  o Corrigir continua existindo; e a correção escrita passa pela mesma leitura.
- Dois registros `aberto` ao mesmo tempo (o movido e o que estava): `_aberto` pega o mais novo; o
  antigo volta quando o novo fechar. Testado em (a).

## Linha de abertura da sessão de execução

Executado nesta sessão (dono, 12/11/2026). Se outra retomar: `C:\AxiaAtende\CLAUDE.md` e
`PADRAO-TRABALHO.md` §1; este plano; o chamado irmão do ERP antes; decisões fechadas: registra direto
quando o nome casa um cliente da fila, pergunta só na dúvida; Parar guarda texto; meio sai; pare em "O
que só você pode fazer".
