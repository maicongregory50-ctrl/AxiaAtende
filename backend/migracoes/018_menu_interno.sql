-- #1031 (dono, 15/10/2026): QUEM E DA CASA TEM MENU PROPRIO. Hoje as 13:52 o Benedito escreveu
-- "Boa Tarde" e recebeu o menu de CLIENTE, embora a conversa 36 tenha sido gravada com
-- erp_codigo 7687 e papeis {equipe,cliente} -- o furo era o PEDE_MENU lendo saudacao como pedido
-- de menu (15 das 20 conversas de interno abriram assim).
--
-- Uma SEGUNDA RAIZ em atendimento.menu, com duas opcoes. O menu interno e CADASTRO, nao codigo,
-- como o do cliente -- so que de duas opcoes fixas: a tela Destinos le a arvore a partir de
-- chave = 'raiz' e nao administra esta (lacuna conhecida, escrita na spec).
--
-- Dois verbos novos de `acao`, que o motor passa a conhecer nesta mesma etapa:
--   texto        -- o no diz a sua `pergunta` e PARA, sem avancar no nenhum
--   menu_cliente -- mostra a raiz do cliente (a saida para quem quer ver o que o cliente ve,
--                   e por onde falar com um colega continua acontecendo)
--
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

-- O CHECK `menu_acao` e a lista fechada de verbos, e e uma TRAVA e nao um estorvo: verbo que nao
-- esta nela nao pode ser cadastrado, e um `acao` escrito errado a mao e recusado pelo BANCO em vez
-- de cair no `else` do motor (que hoje e "encerrar"). Os dois novos entram nela.
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_acao;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_acao
    CHECK (acao IN ('menu', 'destino', 'encerrar', 'texto', 'menu_cliente'));

-- `menu_pergunta_so_no_menu` dizia "pergunta so em no de menu", porque `pergunta` e o que se diz ao
-- ABRIR o no. Num no `texto` e exatamente isso tambem -- so que a frase nao termina em "?". O CHECK
-- e ampliado para os dois, e continua barrando `pergunta` em `destino` e em `encerrar`, que e o que
-- ele existe para impedir. A alternativa seria guardar a linha em `texto_antes`, cuja definicao e
-- "vai antes do link": num no sem link, seria a coluna errada carregando o sentido.
ALTER TABLE atendimento.menu DROP CONSTRAINT menu_pergunta_so_no_menu;
ALTER TABLE atendimento.menu ADD CONSTRAINT menu_pergunta_so_no_menu
    CHECK (acao IN ('menu', 'texto') OR pergunta = '');

-- `chave` so aceita [a-z0-9_.] (menu_chave_formato), por isso `raiz_interna` e nao `raiz-interna`.
-- `rotulo` tem CHECK de 1..20 caracteres: e o limite do titulo de BOTAO no WhatsApp, e com duas
-- opcoes este menu sai como botoes (MAX_BOTOES = 3), nao como lista. A descricao, que a lista
-- mostraria, fica guardada mesmo assim -- e o que a IA le, e serve se um dia houver uma 4a opcao.
INSERT INTO atendimento.menu (pai_id, chave, rotulo, descricao, pergunta, acao, ordem) VALUES
    (NULL, 'raiz_interna', 'Menu da casa', '',
     'Você é da equipe. O que precisa?', 'menu', 0);

INSERT INTO atendimento.menu (pai_id, chave, rotulo, descricao, pergunta, acao, texto_antes, ordem)
SELECT (SELECT id FROM atendimento.menu WHERE chave = 'raiz_interna'),
       v.chave, v.rotulo, v.descricao, v.pergunta, v.acao, '', v.ordem
  FROM (VALUES
    ('interna.campo',   '📸 Foto do campo',   'Mandar foto ou vídeo para o catálogo do marketing',
     'É só mandar a foto ou o vídeo aqui mesmo. Eu pergunto o que faltar para catalogar — o que mostra, o produto, a fase e a data. Se quiser, escreva antes uma frase sobre a próxima foto e ela vai junto.',
     'texto', 1),
    ('interna.cliente', '👤 Menu do cliente', 'Ver o mesmo atendimento que o cliente recebe',
     '', 'menu_cliente', 2)
  ) AS v(chave, rotulo, descricao, pergunta, acao, ordem);

-- A chave do reconhecimento. NASCE LIGADA: e o comportamento que o dono pediu, e a chave existe
-- como alavanca de ROLLBACK, nao como porta de entrada -- virar para 'false' aqui devolve todo
-- mundo ao tratamento de hoje, sem restart e sem deploy.
INSERT INTO atendimento.ajustes (chave, valor) VALUES ('interno.ligado', 'true'::jsonb);
