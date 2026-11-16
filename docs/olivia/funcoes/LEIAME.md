# O que cada função faz — o lugar (#1525, D9)

Esta pasta guarda, **um arquivo por vaga**, o que a pessoa faz no dia daquela função, para a OlivIA tirar
dúvida do candidato e apresentar a vaga. Nasceu vazia em 16/11/2026: as descrições de função vêm da Fran
(o pedido saiu pelo chamado no WhatsApp; a volta com arquivo é o #1528), e o resumo é escrito a partir
delas e **corrigido pelo dono** antes de valer.

## O que entra

- Um arquivo `<vaga_id>.md` por vaga (o número da vaga na tela Destinos; `2.md` é a Auxiliar de produção,
  `3.md` o Operador de empilhadeira).
- Curto: o que se faz no dia, em linguagem de quem vai fazer. Dez linhas bastam.
- **Cada afirmação com fonte e data entre colchetes**, como a base da empresa
  (`docs/olivia/base-da-empresa.md`): `[descrição de função da Fran, 20/11/2026]`. A OlivIA lê a fonte e
  não a repete ao candidato.

## O que NÃO entra

- Número e valor: salário, horas extras, prêmio. O filtro de saída recusa, e não é ela quem fala disso.
- Promessa: efetivação, prazo, carreira.
- O que não estiver numa fonte.

## Como vale

`backend/olivia.py: funcao_da_vaga` lê o arquivo da vaga **quando ele existe** e o relê quando muda, sem
restart. Sem arquivo, nada entra, e a OlivIA diz só o que o cadastro da vaga diz (título, região,
requisitos, benefícios). Só vale com a chave `olivia.conduz_vaga` ligada. Este `LEIAME.md` nunca entra.
