-- #1027 (dono, 15/10/2026): A DIRECAO DO PEDIDO. A Yasmin, da World Rafia, escreveu "Eu poderia te
-- fazer uma COTACAO para apresentar nossos precos e condicoes de fornecimento?" -- e a IA propos
-- `comercial`, que e o caminho de quem quer COMPRAR da Renascer. Ela queria VENDER.
--
-- A causa nao era o modelo: era ESTE CADASTRO. A IA recebe cada opcao como `chave: caminho
-- (descricao)` (ia._lista), 23 das 29 opcoes nao tinham descricao, e a UNICA cujo texto continha
-- "cotar" era `comercial` ("Cotar sementes"). A IA fez a coisa razoavel com o dado que tinha.
--
-- A COLUNA TEM DOIS PUBLICOS, e e o que decide como cada linha abaixo e escrita: `perguntar` manda
-- BOTOES com 3 opcoes ou menos e LISTA acima disso, e no WhatsApp a linha de lista mostra a
-- descricao -- o botao, nao. Entao:
--   - `comercial` e `fornecedores` sao filhos da raiz (7 filhos => lista): o CLIENTE LE. Escritas
--     para gente, e tambem boas para a IA.
--   - os filhos de `comercial` (3) e de `fornecedores` (2) saem em BOTAO: invisiveis ao cliente,
--     lidos so pela IA. Escritas para a maquina, com o vocabulario de cada lado.
--
-- As outras 16 continuam vazias de proposito: sao nomes de estado (SC, PR, RS, SP, Cascavel, Ponta
-- Grossa, Outro) e o `encerrar`. Nome de estado nao precisa de explicacao, e enche-los poria texto
-- na tela do cliente sem ninguem ganhar nada.
--
-- Limite da coluna: 72 caracteres (menu_descricao). Sem BEGIN nem COMMIT.

-- ── as duas que o CLIENTE le, no menu principal ─────────────────────────────
UPDATE atendimento.menu SET descricao = 'Comprar sementes: cotação, preço e pedido'
 WHERE chave = 'comercial';
UPDATE atendimento.menu SET descricao = 'Vender para a Renascer, ou já ser nosso fornecedor'
 WHERE chave = 'fornecedores';

-- ── as cinco que SO A IA le (saem em botao) ─────────────────────────────────
-- Do lado de quem COMPRA, a palavra e sempre "comprar":
UPDATE atendimento.menu SET descricao = 'Produtor que quer COMPRAR semente para a lavoura dele'
 WHERE chave = 'comercial.produtor';
UPDATE atendimento.menu SET descricao = 'Revenda que quer COMPRAR semente para revender'
 WHERE chave = 'comercial.revenda';
UPDATE atendimento.menu SET descricao = 'Corretor que intermedeia a compra de semente'
 WHERE chave = 'comercial.corretor';

-- Do lado de quem VENDE para nos. "cotação de venda" existe aqui de proposito: e o que tira de
-- `comercial` o monopolio da palavra que a Yasmin usou.
UPDATE atendimento.menu SET descricao = 'Já fornece à Renascer: pedido de compra, entrega, pagamento'
 WHERE chave = 'fornecedores.ja';
UPDATE atendimento.menu SET descricao = 'Quer VENDER à Renascer: oferecer produto, serviço ou cotação de venda'
 WHERE chave = 'fornecedores.ainda';
