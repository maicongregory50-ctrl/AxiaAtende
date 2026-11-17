# Plano — A OlivIA na conversa de quem quer comprar
**Data:** 2026-11-17
**Chamado:** #1589
**Spec de origem:** docs/specs/2026-11-17-olivia-conversa-de-venda.md
**Status:** APROVADO
**Executável pelo agente:** não -- ligar a chave e a prova real são da mão do dono

> A chave `olivia.conduz_venda` nasce `false`; até ser ligada, a conversa de quem quer comprar é a de
> hoje. Manual legal: não se aplica. Todos os fios da spec são do `motor.escolher`, que a ferramenta
> reusa: nenhum escritor novo em `conversas`.

## Passos

1. **Migração 070** — `backend/migracoes/070_olivia_conduz_venda.sql` + `_VOLTA.sql`: o ajuste
   `olivia.conduz_venda = false` (`ON CONFLICT DO NOTHING`). — verificação: a bateria aplica no 5437; o
   ajuste existe e é `false`. — reversão: a `_VOLTA`.
2. **A chave** — `backend/olivia.py: conduz_venda(con)`; `scripts/olivia.py`: `ligar-venda`,
   `desligar-venda`, e o `mostrar` diz as duas chaves; o `/saude` do recepcionista ganha `olivia_venda`.
   — verificação: teste do script e do `/saude`. — reversão: revert.
3. **As regras da venda** — `backend/olivia.py: REGRAS_DA_VENDA`, na instrução só com a chave ligada (as
   sete regras da spec, item 1 da Decisão). O nome do perfil chega como nota **fora** da instrução em
   cache e fora do texto da pessoa (`nota_do_perfil`), sem mexer na marca de "travou". — verificação:
   passo 5 (a), (e). — reversão: revert.
4. **A ferramenta `passar_contato`** — `ferramentas()`: oferecida com a chave ligada e a conversa fora
   da vaga; `chave` em `enum` das folhas de destino do Comercial (`_opcoes_do_menu`, `chave` começando
   por `comercial` e `acao = 'destino'`). `_executar`: chama `motor.escolher` com o nó; registra
   `olivia: ferramenta passar_contato: <chave>`; devolve quem atende, e o lembrete de que ninguém foi
   avisado. Não é ferramenta muda (ela manda o cartão). — verificação: passo 5 (b), (c), (d). —
   reversão: revert.
5. **Testes** — `tests/test_olivia_venda.py`:
   (a) chave ligada: a instrução traz as regras da venda; desligada, não;
   (b) "sou produtor de SC, tem aveia?" → `passar_contato(comercial.produtor.sc)` → o texto e o cartão
   do destino daquela folha, conversa `com_link`, `pergunta_em` marcada, `link: comercial.produtor.sc`
   em `enviadas`, sem botão "Sim";
   (c) chave desligada: `passar_contato` não está na lista, e a conversa de hoje (os botões) não muda;
   (d) chave fora do `enum` (um nó que não é destino do Comercial) → "não existe", nada enviado;
   (e) a nota do perfil chega à IA e não entra em `enviadas`;
   (f) na conversa de vaga a ferramenta não é oferecida;
   (g) o vigia: conversa de venda com cartão entregue é `bem`.
   — verificação: `pytest tests/test_olivia_venda.py tests/test_olivia.py tests/test_olivia_vaga.py` e a
   bateria inteira, sozinha no 5437. — reversão: apagar.
6. **Inventário e política (R7)** — `C:\AxiaSecurity\docs\governanca\inventario-agentes.md` (a linha da
   OlivIA: a ferramenta e a chave) e `politica-uso-ia.md`, em *Pode sozinho*, a regra da spec com a
   fonte. — verificação: `python scripts/conferir_inventario_agentes.py --politica` passa. — reversão:
   revert.
7. **Manual** — `docs/manuais/olivia.md`: o item da conversa de compra, os sinais e o que não faz
   (texto da spec). `INDICE.md`: a linha já existe. — verificação: quem lê sabe por que o cartão saiu
   sem o botão. — reversão: revert.
8. **Commit** citando `#1589`, nomeando os arquivos, e **push**; o AxiaSecurity em commit próprio.
9. **No ar, desligado** — restart do `axiaatende-backend` (aplica a 070) e do
   `axiaatende-recepcionista` pela Porta-Ação. — verificação: `/saude` diz `olivia_venda: desligada`.
10. **Ligar** (dono, janela elevada): `python scripts\olivia.py ligar-venda`. — verificação: `/saude` diz
    `olivia_venda: ligada`.
11. **Prova real**: um número de fora escreve "vocês têm semente de aveia?" e segue a conversa até o
    cartão. — verificação: a conversa lida com `ler_conversa.py`, colada no chamado.
12. **Devolver**: o que mudou, o manual e a escada dos próximos degraus; `entregar 1589 --devolucao` e
    `fechar 1589`.

## O que só você pode fazer

- **Ligar a chave**, em PowerShell como administrador:
  ```
  cd C:\AxiaAtende
  $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
  .\.venv\Scripts\python.exe scripts\olivia.py ligar-venda
  ```
- **A prova real** de um número de fora (passo 11).
- **Corrigir a base da empresa** (`docs/olivia/base-da-empresa.md`), que continua sendo o rascunho de
  16/11: é o que ela afirma sobre os produtos.

```pos-entrega
dono=python scripts\olivia.py ligar-venda em janela elevada; prova real de um numero de fora; corrigir a base da empresa
```

## Riscos de execução identificados

- **Passos 1 a 9 interrompidos:** nada muda para quem escreve; a chave está `false`.
- **Cartão do representante errado:** a chave da ferramenta vem de lista fechada, mas quem escolhe a folha
  é o modelo, pela conversa. A instrução manda usar os botões em dúvida; a análise horária lê as
  primeiras conversas; `desligar-venda` volta aos botões na hora.
- **"Já avisei o representante":** nesta etapa ninguém é avisado, e a regra está só na instrução. Se
  aparecer numa conversa, vira trava de código, como a da promessa na vaga.
- **A base em uso é rascunho:** o "temos" dela vem de uma lista que o dono ainda não corrigiu (AVR Versa
  Multi, AVR Cerrado Rede e outros pontos do `FONTES.md`, seção 6).

## Linha de abertura da sessão de execução

Executado na sessão que escreveu o plano, com o dono (17/11/2026). Chamado **#1589**; todo commit cita
`#1589`.
