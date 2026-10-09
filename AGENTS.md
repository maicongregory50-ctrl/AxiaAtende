# Antes de qualquer ação nesta pasta

Este arquivo existe porque o Cursor não lê `CLAUDE.md` sozinho — o Claude Code lê. O conteúdo é o mesmo
para os dois: **a porta é a instrução de leitura, não a pasta.**

1. Leia `CLAUDE.md` desta pasta **inteiro** — é o mapa estrutural do projeto (o recepcionista do WhatsApp, o envio à carteira,
   o que é exposto à internet e o que não tocar na Meta).
2. Leia `C:\SuporteAxia\docs\PADRAO-TRABALHO.md` — o padrão comum aos projetos (sessão, as três faixas, spec →
   plano → código, três provas, pontas soltas, segurança, glossário) e **o canal**: a fila é uma só, em `axia.demandas`.
3. Liste a fila deste projeto: `python C:\SuporteAxia\skills\demanda\demanda.py listar --sistema axiaatende`.
   Se for tocar outro projeto também, leia o `CLAUDE.md` dele antes.
4. `git status` antes de editar. Arquivo modificado que você não tocou é de outra sessão: não comite, não reverta, avise.

Ao encerrar: ponta solta que atravessa sessão ou projeto vai para a fila (`demanda.py abrir` / `comentar`); estado em
curso vai para a fila também — **este projeto não tem diário** (PADRAO-TRABALHO.md §1); commit com prefixo `[axiaatende]`, listando os arquivos — nunca `git add -A`.
