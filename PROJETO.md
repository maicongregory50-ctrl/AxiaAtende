# AxiaAtende — manifesto

**v1.0 — 09/10/2026.** Duas listas, e é só isso. Serve para outro projeto saber com o que pode contar
aqui, e para se descobrir a ordem de instalação sem ninguém narrar. Criado pelo passo B1 do plano do chamado **#950**
(`C:\AxiaMarketing\docs\specs\2026-10-09-axiaatende-recepcionista-e-envio-plano.md`).

**Atendimento, não marketing.** Este projeto fala com quem chama a Renascer no WhatsApp e entrega o
envio que o AxiaMarketing pede. Ele não decide campanha, peça nem lista: isso é do AxiaMarketing.

## Ofereço

| O quê | Onde |
|---|---|
| **O recepcionista do WhatsApp** do número 49 3664 0121: menu por botão, link de quem atende, a IA que propõe o motivo | serviço `axiaatende-recepcionista` (`127.0.0.1:8008`, publicado pelo Funnel em `:443`) — **a partir da Fase H do plano** |
| **O envio à carteira**: o convite, as imagens na janela, o aceite e a recusa, o aviso ao responsável | API local `127.0.0.1:8009/envios`, só no próprio servidor — **a partir da Fase E do plano** |
| O resumo para o KR2 (quem aceitou e quem respondeu, por período) | API local `127.0.0.1:8009` — **a partir da Fase E do plano** |

## Exijo

| O quê | De quem | Se faltar |
|---|---|---|
| `C:\SuporteAxia\skills\demanda` para listar a fila | SuporteAxia / `C:\Dados` | sem fila; o resto continua |
| `axia.demandas` no banco `renascer` | AxiaGestão | sem fila; o resto continua |
| `porta 8001` (a API do ERP, por onde a fila é escrita) | AxiaGestão | sem fila; o resto continua |
| O código `axiaatende` em `axia.sistemas` | AxiaGestão | `demanda abrir --sistema axiaatende` toma HTTP 400 |
| `C:\Python314\python.exe` | a máquina | os serviços não sobem |
| PostgreSQL 17 instalado (os binários de `initdb`, `pg_ctl`, `pg_dump`) | a máquina | o banco do atendimento não nasce |
| `C:\SuporteAxia\servicos\suporteaxia-backend.exe` (o WinSW da casa, copiado ao instalar) | SuporteAxia | instalar o serviço pede outro WinSW |
| O **Funnel do Tailscale** liberado para este nó (conferir com `tailscale funnel status`) | Tailscale (política da tailnet) | a Meta não alcança o recepcionista: ninguém recebe resposta |
| A Cloud API do WhatsApp (`graph.facebook.com`) e a conta 1442233593867052 | Meta | nada entra e nada sai |
| A API da Anthropic | Anthropic | quem escreve em vez de tocar recebe o menu; o resto continua |
| O pedido de envio e a lista com o responsável de cada cliente | AxiaMarketing | não há envio à carteira; o recepcionista continua |
| Assinatura Claude Code no perfil | perfil do usuário | sem sessão de agente; os serviços continuam |

## Se eu cair

**Depois da troca do dia (Fase H), quem chama a Renascer no WhatsApp fica sem resposta.** É o efeito
mais visível da casa inteira, e é por isso que o alerta "serviço parado" do AxiaSecurity existe. A Meta
guarda e repete os avisos por até 7 dias, então nenhuma mensagem se perde, só atrasa.

**A volta é imediata:** apagar o redirecionamento de avisos do número devolve o atendimento ao Opa,
que fica contratado e parado por um mês depois da troca. O envio à carteira para junto, e nada sai
fora do que foi aprovado: o convite que não saiu não sai depois sozinho.

Antes da troca, cair não afeta ninguém: o recepcionista está em escuta e o Opa atende.
