# Plano — A OlivIA atende o cliente da carteira na conversa do boletim
**Data:** 2026-11-24
**Chamado:** #1754
**Spec de origem:** `C:\AxiaAtende\docs\specs\2026-11-24-olivia-atende-a-carteira-no-boletim.md`
**Status:** APROVADO
**Executável pelo agente:** não -- chamado do axiaatende (o EXECUTOR não tem raiz lá, #976), com modelo a propor à Meta, texto a aprovar e prova no WhatsApp do dono.

## Contexto

O Boletim nº 1 foi lido e não virou conversa (84 viram, 4 escreveram, 1 tocou). A spec decidiu que o
boletim seguinte convida, e que a OlivIA atende quem aceitar: pelo toque em "Quero saber mais" ou pelo
texto em até 7 dias. O código manda a saudação, a versão maior e o texto da parceria; ela conversa,
anota o interesse em lista fechada, e o código manda a ficha ao representante. Tudo atrás da chave
`olivia.atende_carteira`, que nasce desligada.

Conformidade: a spec diz R7 **muda** (a política de uso de IA e o inventário de agentes), e isso é o
passo 15, antes de a chave ligar. Manual legal: não se aplica.

## Passos

1. **Pegar o chamado.** `tratar 1754 --status em_andamento`; `C:\AxiaAtende\CLAUDE.md`; `git status`;
   `pg_isready -p 5437`. — verificação: chamado em andamento. — reversão: nenhuma.

2. **Medir o que a spec deixou em aberto** (só leitura):
   - no código do AxiaGestão, o que a rota que recebe os eventos de envio faz com um valor de
     `resposta` que não conhece (recusa a linha, o lote, ou guarda);
   - se `envio_destinatarios.resposta` tem CHECK (ler as migrações);
   - se o modelo `olivia_resumo` está aprovado na Meta (o leitor de modelos da casa).
   — verificação: as três respostas no chamado; a primeira decide a tradução do passo 11.

3. **O texto da parceria.** `docs/olivia/parceria-da-carteira.md`, curto o bastante para uma mensagem
   de WhatsApp, a partir das palavras do dono de 23/11. Rascunho da sessão:
   > *A safra de sementes de cobertura deste ano veio curta: menos campo inscrito e colheita difícil.
   > Por isso a nossa prioridade é quem já compra com a gente. Estamos nos esforçando para segurar
   > estoque para a nossa carteira, dentro do nosso limite, antes de oferecer ao mercado. O preço
   > acompanha o mercado no dia do fechamento, e quem consegue antecipar pega condição melhor. Me diga
   > quais culturas te interessam que eu aviso quem cuida de você aqui.*

   **[SÓ O DONO]** aprova ou corrige; vale o texto dele, literal.
   — verificação: o arquivo com a data e "aprovado pelo dono". — reversão: `git revert`.

4. **O modelo novo.** A sessão entrega o texto do modelo de direta (saudação com o primeiro nome, uma
   linha do boletim, cabeçalho de imagem) e os dois botões de resposta rápida, "Quero saber mais" e
   "Não quero receber", categoria Marketing. **[SÓ O DONO]** propõe à Meta.
   — verificação: o modelo aparece como proposto no leitor de modelos. O plano segue enquanto a Meta
   analisa; só o passo 17 espera a aprovação.

5. **A migração**, com o próximo número **lido da pasta na hora** (a última hoje é a 075) e `_VOLTA`:
   tabela de interesses (destinatário do envio, conversa, culturas, papel, o texto do cliente, e os
   campos da ficha: enviada em, como, wamid, erro); coluna de culturas em `envios`; a linha do modelo
   novo e o CHECK `modelos_botao` com o valor novo (repetindo a lista inteira de hoje); o valor novo em
   `resposta`, se houver CHECK; a chave `olivia.atende_carteira = false`; o `GRANT` de leitura ao
   `axiaatende_ro`. Afirmação de saída: a chave nasceu desligada.
   — verificação: aplica e desfaz no 5437; `tests/test_migracoes.py`. — reversão: apagar os arquivos.

6. **O pedido.** `backend/rotas_pedido.py`: `Pedido` ganha o campo opcional das culturas (lista curta
   de rótulos); `Envio.receber_pedido` grava. Pedido sem o campo continua valendo.
   — verificação: teste com e sem o campo. — reversão: `git revert`.

7. **O toque.** `backend/envio.py`: `_mensagem` monta os botões do modelo novo
   (`envio:<id>:saber` e a recusa); `tratar_toque` ganha a ação `saber`:
   - chave desligada → `_falar_pelo_toque`, como o "falar" de hoje;
   - chave ligada → grava a resposta, manda a saudação pelo primeiro nome (`primeiro_nome`), as
     imagens (`_mandar_imagens`) e o texto da parceria, e abre a conversa do modo carteira.
   Os resumos em `enviadas` não começam por `portao do cliente`.
   — verificação: testes novos ao lado de `tests/test_informativo_ao_comprador.py`: chave desligada,
   chave ligada, segundo toque, toque de quem recusou. — reversão: `git revert`.

8. **O texto em 7 dias.** `backend/motor.py`, antes de `portao_do_cliente`: texto de quem recebeu um
   envio com o botão novo nos últimos 7 dias, com a chave ligada, vai à OlivIA no modo carteira.
   `olivia.e_de_fora` e `olivia.atender` passam a aceitar esse modo; a retomada da conversa também.
   — verificação: testes: dentro dos 7 dias → ela; fora → o portão; chave desligada → o portão;
   interno e cooperante continuam nos degraus deles. **Os testes de hoje do portão e da OlivIA passam
   sem mudança.** — reversão: `git revert`.

9. **A OlivIA no modo carteira.** `backend/olivia.py`: regras próprias (não fala de quantidade, preço
   nem prazo; não promete estoque; perguntada se é IA, não nega; quem pede uma pessoa recebe o
   representante), no molde de `REGRAS_DA_VENDA`; o que ela sabe do cliente entra no `extra`, fora do
   cache (primeiro nome, cadastro, papel, quem atende, culturas, o texto da parceria); a lista de
   ferramentas do modo em `ferramentas`: mandar a versão maior, anotar interesse (enum das culturas do
   envio; sem culturas, não é oferecida), passar o representante, oferecer as opções da
   `raiz_carteira`, encerrar. As de vaga, venda e lead não são oferecidas neste modo.
   — verificação: testes no molde de `tests/test_olivia_venda.py`: a lista de ferramentas por estado;
   ferramenta fora da lista é recusada; fala com valor em R$ é trocada pelo filtro.
   — reversão: `git revert`.

10. **O interesse e a ficha.** Módulo novo no molde de `backend/lead.py`: gravar o interesse; montar a
    ficha (cliente, papel, culturas, o texto do cliente literal); `mandar` ao responsável da linha do
    envio, texto dentro da janela e `olivia_resumo` fora, **sem nunca levantar**. A trava de fala
    (`aviso_sem_ficha`) cobre "avisei o representante" sem ficha enviada. A linha do representante sai
    depois da fala final, como `_cartao_pendente`.
    — verificação: testes no molde de `tests/test_olivia_lead.py`: ficha na janela, ficha fora dela,
    ficha que falha (a fala é trocada e o erro fica gravado), responsável igual a quem escreve.
    — reversão: `git revert`.

11. **O registro no ERP.** `backend/eventos_erp.py`, `montar`: a resposta nova sai traduzida para um
    valor que o ERP aceita (conforme o passo 2), com o texto "Quis saber mais. Interesse: ..." em até
    500 caracteres. — verificação: teste de `montar`; nenhum valor novo sai cru. — reversão: `git revert`.

12. **Vigia, saúde, chave e tela.** `fechar_dia` conta conversas da carteira, interesses e fichas com
    erro; `/saude` publica a chave; `scripts/olivia.py` ganha ligar e desligar a carteira; a tela
    Envios mostra "quis saber mais" e as culturas.
    — verificação: testes do vigia; `vite build`. — reversão: `git revert`.

13. **Bateria inteira.** `pytest -p no:cacheprovider --basetemp=C:/Temp/1754-<único>`.
    — verificação: verde, com o número no commit.

14. **Manual e contrato.** `docs/manuais/olivia.md` (o texto da spec; caçar "não atende cliente da
    carteira"); `PROJETO.md` (*Exijo*: o campo opcional das culturas no pedido; *Ofereço*: a ficha de
    interesse); conferir a linha no `INDICE.md`.
    — verificação: quem lê só o manual sabe o que é "quis saber mais" sem culturas.

15. **A política de IA** (AxiaSecurity; ler o `CLAUDE.md` de lá antes; commit próprio citando #1754):
    `docs\governanca\politica-uso-ia.md` ganha a linha deste fluxo em "Pode sozinho" (o que vai ao
    modelo, a finalidade, a chave, e que ela não nega ser IA) e a linha do #1520 deixa de dizer que
    ela não atende cliente da carteira; a ficha da OlivIA no inventário é atualizada; `agentes.json`
    conferido. — verificação: `python scripts/conferir_inventario_agentes.py --politica` e
    `scripts/conferir_agentes.py` verdes. — reversão: `git revert`.

16. **Pôr no ar, com a chave desligada.** Commit e push; reiniciar `axiaatende-recepcionista` e
    `axiaatende-backend`. — verificação: `/saude` mostra a chave desligada; log sem erro; um toque
    "falar" de envio antigo responde como antes.

17. **Prova real**, com o modelo aprovado na Meta. Um envio de teste só para o WhatsApp do dono, com
    um responsável que **não** seja o próprio número dele (a ficha a si mesmo é recusada por desenho),
    e a chave ligada durante a prova. **[SÓ O DONO]**: toca "Quero saber mais"; confere a saudação, as
    imagens e o texto; pergunta preço (ela manda ao representante); pergunta se é um robô (ela não
    nega); indica duas culturas. A sessão confere pelo `ler_conversa.py`: a ficha chegou ao
    responsável, o interesse está gravado, e o Relacionamento do ERP mostra a linha. Depois, a prova do
    texto sem toque. A chave volta a desligada ao fim.
    — reversão: ROLLBACK_PLAN 1 da spec.

18. **Devolver.** `entregar 1754` com o manual e os pré-requisitos ditos (modelo aprovado, texto
    aprovado, a chave liga quando o Boletim nº 2 for sair); abrir o chamado do estado "interessado" no
    ERP, ligado ao #1753; linha em `logs/sessions.log`.
    — verificação: o chamado fecha. — reversão: reabrir.

## O que só você pode fazer

- **Passo 3:** aprovar ou corrigir o texto da parceria.
- **Passo 4:** propor o modelo novo à Meta (a sessão entrega o texto e os botões prontos).
- **Passo 16:** se a Porta-Ação não tiver os serviços do AxiaAtende no catálogo, o restart em janela
  elevada: `Restart-Service axiaatende-recepcionista, axiaatende-backend`.
- **Passo 17:** a prova com o seu WhatsApp.
- **Depois:** ligar a chave quando o Boletim nº 2 for sair:
  `.\.venv\Scripts\python.exe scripts\olivia.py` com o verbo novo de ligar a carteira.

Sem bloco `pos-entrega`: execução em sessão com você.

## Riscos de execução identificados

- **Código no ar com a chave desligada (entre o passo 16 e o 17):** estado seguro; o cliente da
  carteira é atendido como hoje. Pode ficar parado ali.
- **Modelo recusado pela Meta:** o plano não insiste (regra 6 do projeto). A sessão refaz o texto com
  você uma vez; sem modelo, a entrada por toque não existe e sobra a entrada por texto.
- **Chave ligada na prova é global:** durante o passo 17, um cliente que escreva em resposta a um
  boletim com o botão novo seria atendido por ela. Só existe esse risco se algum boletim real já
  tiver saído com o modelo novo; a prova é feita antes disso.
- **Migração aplicada e código revertido:** a tabela e a coluna ficam vazias e ninguém as lê. Seguro.
- **Número de migração tomado por outra sessão:** lido na hora; se colidir, renumera antes de aplicar.
- **Fio não coberto por passo:** o `O_Que_Rendeu.csv` do AxiaMarketing soma respostas por tipo; a
  resposta nova chega lá como o valor traduzido do passo 11. A leitura fina fica para o #1755.
- **O contato técnico:** nenhum recebeu direta até hoje; o código trata o papel, e a primeira prova
  real com técnico é do #1755.

## Linha de abertura da sessão de execução

```
AxiaAtende: aplicação de plano aprovado. Leia C:\AxiaAtende\CLAUDE.md e C:\SuporteAxia\docs\PADRAO-TRABALHO.md, e execute o plano C:\AxiaAtende\docs\specs\2026-11-24-olivia-atende-a-carteira-no-boletim-plano.md (a spec está ao lado, sem o "-plano"). Chamado #1754; todo commit cita #1754, e o primeiro ato é `tratar 1754 --status em_andamento` pela skill /demanda. Decisões que NÃO se reabrem: a OlivIA entra pelo toque "Quero saber mais" e pelo texto em até 7 dias do boletim; dois botões, sem "Falar com meu atendimento"; o primeiro bloco (saudação, imagens, texto da parceria) é do código, sem fala de IA; ela sabe só nome, cadastro, papel, quem atende e as culturas do boletim; não fala de quantidade, preço nem prazo; não avisa que é IA e não nega se perguntada; interesse em lista fechada; a ficha é do código e vai ao responsável da linha do envio; o ERP não muda (a resposta nova sai traduzida); tudo atrás da chave olivia.atende_carteira, que nasce desligada e só eu ligo. Pare e me entregue pronto nos passos [SÓ O DONO]: o texto da parceria para eu aprovar (passo 3), o modelo para eu propor à Meta (passo 4) e a prova com o meu WhatsApp (passo 17). A política de uso de IA do AxiaSecurity é atualizada antes de qualquer prova com a chave ligada (passo 15). O que vai para a tela durante a execução está no PADRAO-TRABALHO.md §1.
```
