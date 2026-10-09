# AxiaAtende — O atendimento da Renascer no WhatsApp
## Documento de referência — v0.1 — 09/10/2026

> Leia este documento integralmente antes de qualquer ação. Ele é o mapa **estrutural** — o que o
> projeto é hoje, não o que aconteceu ontem.

> **Nasceu em 09/10/2026, pelo chamado #950** (spec e plano em
> `C:\AxiaMarketing\docs\specs\2026-10-09-axiaatende-recepcionista-e-envio*.md`). O chamado é do
> AxiaMarketing porque nasceu lá; o código é daqui, e todo commit da etapa cita `#950`.

## O que é

O atendimento da Renascer no WhatsApp, pelo número **49 3664 0121**, no lugar do Opa Suite (a OlivIA).
Duas funções, e só elas:

1. **O recepcionista.** Quem chama recebe o menu de motivos, **tudo por botão**, e termina no link do
   WhatsApp de quem atende (tela Destinos). Quem escreve em vez de tocar recebe a proposta da IA e
   confirma com um botão. Não há atendimento humano dentro do sistema: a conversa continua no WhatsApp
   de quem recebeu o link.
2. **O envio à carteira.** O AxiaMarketing pede, o dono aprova lá, e daqui sai um **convite pago** por
   cliente. Quem toca "Quero receber" recebe as imagens na janela de 24h, sem custo; quem toca "Não
   quero receber" sai da lista e o responsável dele é avisado.

Três telas, no computador: **Recepção**, **Envios** e **Destinos**.

**É o único projeto da casa que qualquer pessoa da internet alcança com lógica.** A vitrine do
AxiaMarketing só entrega imagem; o recepcionista daqui recebe e responde mensagem de qualquer um. Por
isso ele roda num processo próprio, sem nada além do necessário.

## Leia antes de agir

- `C:\AxiaMarketing\docs\specs\2026-10-09-axiaatende-recepcionista-e-envio.md`: a spec, com as decisões
  do dono e a seção **Cuidado com a Meta**.
- `C:\AxiaMarketing\docs\specs\2026-10-09-axiaatende-recepcionista-e-envio-plano.md`: o plano, as fases
  e o que só o dono pode fazer.
- O AxiaMarketing é o molde deste projeto (config, migrações, login, serviços). Na dúvida de "como a
  casa faz", leia lá antes de inventar.

## Protocolo de sessão

> **Padrão transversal:** o que é comum aos projetos está em
> `C:\SuporteAxia\docs\PADRAO-TRABALHO.md`. **A fila deste projeto é
> `axia.demandas WHERE sistema='axiaatende'`.**

Ao iniciar:
1. Leia este `CLAUDE.md` inteiro.
2. Liste a fila: `python C:\SuporteAxia\skills\demanda\demanda.py listar --sistema axiaatende`.

Ao encerrar ou fazer pausa longa:
1. **Ponta solta vai para a fila**, não para arquivo local (`demanda.py abrir` / `comentar`) —
   inclusive o estado em curso.
2. Acrescente uma linha em `C:\AxiaAtende\logs\sessions.log`: `[DATA][ATENDE-END] resumo de 1 linha`.
3. Commit com prefixo `[axiaatende]`, listando os arquivos — nunca `git add -A`.

> **Este projeto não tem `CONTEXT.md`.** Documento de estado só se justifica se alguém o lê ao abrir
> a sessão; se ninguém lê, não é estado — é ruído com data (decisão 2 de
> `C:\SuporteAxia\docs\2026-09-04-arquitetura-das-portas-e-do-canal.md`). O que precisa atravessar
> sessão vai para a fila, que é onde outra sessão vai olhar.

## Regras permanentes

1. **Nada que arrisque o número na Meta.** Nunca registrar ou desregistrar o número, trocar o PIN,
   pedir troca do nome exibido ou migrar de conta. A troca de atendimento é só o redirecionamento de
   avisos por número, e desfazer é apagá-lo.
2. **O recepcionista nasce em escuta** (`ATENDE_RESPONDE=false`): grava e não responde. Só o ensaio e a
   troca do dia ligam a chave. Com o Opa ainda ativo, a chave ligada faz o cliente receber duas
   respostas.
3. **A IA não tem ferramenta.** Ela devolve só uma chave da lista de motivos; o link sai sempre da tela
   Destinos. Erro, demora ou resposta fora da lista vão para o menu, nunca para "tente de novo".
4. **Consentimento não se apaga.** Aceite e recusa ficam gravados com data e id da Meta, inclusive num
   rollback. Quem recusou não recebe mais convite.
5. **Envio em degraus:** lotes de até 20 por dia, por faturamento; o próximo só sai com a nota do
   número em verde, e na amarela para sozinho.
6. **Categoria declarada é a verdadeira.** Convite é Marketing. Aviso interno é Utilidade; se a Meta
   recusar a Utilidade, refaz como Marketing uma vez e nunca insiste.
7. **A conversa é chaveada pelo BSUID** (`user_id` da Meta); o número de telefone é opcional.

## Segurança e Backup (Axia Security)

- Segredos só em `C:\AxiaAtende\.env.secrets`, fechado a administrador: o token da Meta **só de
  WhatsApp** (app `axiaatende`, não o do AxiaMarketing), o segredo do app (assinatura dos avisos) e a
  chave da Anthropic **própria, com teto de gasto**. Nunca em código, commit, log ou tela.
- O único processo exposto é o recepcionista (`127.0.0.1:8008`, LocalService), publicado pelo Funnel do
  Tailscale em `:443`. Ele confere a assinatura `X-Hub-Signature-256` de todo aviso. As telas ficam em
  `127.0.0.1:8009`, sem saída externa.
- Logs em `C:\Logs\AxiaAtende`, backup do banco e do código pelo `/security` (passo G6 do plano).
