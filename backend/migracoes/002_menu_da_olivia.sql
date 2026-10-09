-- #950 -- a semente: o menu da OlivIA de hoje (fluxo exportado do Opa, lido em 09/10/2026), com
-- todo destino virando link (dono, 09/10/2026), e os destinos dados pelo dono no mesmo dia.
-- Depois de aplicada, quem muda nome e numero e a tela Destinos; esta mudanca nao se edita.
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

INSERT INTO atendimento.destinos (nome, whatsapp) VALUES
    ('Maicon Gregory',      '5549991505565'),
    ('Djeison de Oliveira', '5549999567572'),
    ('Willian Souza',       '5546999784298'),
    ('Benedito',            '5549999190249'),
    ('Fran',                '5549991938910'),
    ('Alisson',             '5549999410889');

-- A arvore. `d(nome)` acha o destino pelo nome, so dentro desta semente.
CREATE TEMP TABLE _d ON COMMIT DROP AS SELECT id, nome FROM atendimento.destinos;

INSERT INTO atendimento.menu (pai_id, chave, rotulo, descricao, pergunta, acao, ordem) VALUES
    (NULL, 'raiz', 'Menu principal', '', 'Escolha a sua opção de atendimento.', 'menu', 0);

-- primeiro nivel: as 7 opcoes de hoje, na ordem de hoje
INSERT INTO atendimento.menu (pai_id, chave, rotulo, descricao, pergunta, acao, destino_id, texto_antes, ordem)
SELECT (SELECT id FROM atendimento.menu WHERE chave = 'raiz'), v.chave, v.rotulo, v.descricao, v.pergunta, v.acao,
       (SELECT id FROM _d WHERE nome = v.destino), v.texto_antes, v.ordem
  FROM (VALUES
    ('comercial',    '🛒 Comercial',        'Cotar sementes',             'Qual a sua área de atuação?',                       'menu',     NULL, '', 1),
    ('fretes',       '🚚 Fretes',           'Cotações de frete',          '',                                                  'destino',  'Benedito',
         'Consulte os fretes disponíveis em https://www.fretebras.com.br/fretes/grupo-empresa-22206 e, para agilizar, informe o destino do frete que lhe interessa.', 2),
    ('financeiro',   '🧾 Financeiro',       'Boletos, nota fiscal, etc.', 'Selecione uma opção do nosso atendimento financeiro.', 'menu', NULL, '', 3),
    ('fornecedores', '📦 Fornecedores',     'Atendimento a fornecedores', 'Você já é nosso fornecedor?',                       'menu',     NULL, '', 4),
    ('trabalhe',     '🤝 Trabalhe conosco', 'Faça parte do nosso time',   '',                                                  'destino',  'Fran', '', 5),
    ('qualidade',    '🏆 Qualidade',        'Doc. de sementes',           '',                                                  'destino',  'Alisson', '', 6),
    ('encerrar',     '🔚 Encerrar',         '',                           '',                                                  'encerrar', NULL, '', 7)
  ) AS v(chave, rotulo, descricao, pergunta, acao, destino, texto_antes, ordem);

-- Comercial: a area
INSERT INTO atendimento.menu (pai_id, chave, rotulo, pergunta, acao, destino_id, ordem)
SELECT (SELECT id FROM atendimento.menu WHERE chave = 'comercial'), v.chave, v.rotulo, v.pergunta, v.acao,
       (SELECT id FROM _d WHERE nome = v.destino), v.ordem
  FROM (VALUES
    ('comercial.produtor', 'Produtor rural', 'Em qual estado você atua?', 'menu',    NULL,             1),
    ('comercial.revenda',  'Revendedor',     'Em qual estado você atua?', 'menu',    NULL,             2),
    ('comercial.corretor', 'Corretor',       '',                          'destino', 'Maicon Gregory', 3)
  ) AS v(chave, rotulo, pergunta, acao, destino, ordem);

-- Comercial: o estado, igual para produtor e revenda
INSERT INTO atendimento.menu (pai_id, chave, rotulo, pergunta, acao, destino_id, ordem)
SELECT p.id, p.chave || '.' || v.sufixo, v.rotulo, v.pergunta, v.acao, (SELECT id FROM _d WHERE nome = v.destino), v.ordem
  FROM atendimento.menu p
 CROSS JOIN (VALUES
    ('sc',    'SC',    '',                                     'destino', 'Maicon Gregory',      1),
    ('pr',    'PR',    'Qual cidade está mais perto de você?', 'menu',    NULL,                  2),
    ('sp',    'SP',    '',                                     'destino', 'Djeison de Oliveira', 3),
    ('rs',    'RS',    '',                                     'destino', 'Maicon Gregory',      4),
    ('outro', 'Outro', '',                                     'destino', 'Maicon Gregory',      5)
  ) AS v(sufixo, rotulo, pergunta, acao, destino, ordem)
 WHERE p.chave IN ('comercial.produtor', 'comercial.revenda');

-- Comercial: a cidade no PR
INSERT INTO atendimento.menu (pai_id, chave, rotulo, acao, destino_id, ordem)
SELECT p.id, p.chave || '.' || v.sufixo, v.rotulo, 'destino', (SELECT id FROM _d WHERE nome = v.destino), v.ordem
  FROM atendimento.menu p
 CROSS JOIN (VALUES
    ('cascavel',     'Cascavel',     'Willian Souza',       1),
    ('ponta_grossa', 'Ponta Grossa', 'Djeison de Oliveira', 2)
  ) AS v(sufixo, rotulo, destino, ordem)
 WHERE p.chave IN ('comercial.produtor.pr', 'comercial.revenda.pr');

-- Financeiro
INSERT INTO atendimento.menu (pai_id, chave, rotulo, descricao, acao, destino_id, ordem)
SELECT (SELECT id FROM atendimento.menu WHERE chave = 'financeiro'), v.chave, v.rotulo, v.descricao, 'destino',
       (SELECT id FROM _d WHERE nome = 'Fran'), v.ordem
  FROM (VALUES
    ('financeiro.boleto',     '🧾 2ª via do Boleto', '',                          1),
    ('financeiro.nota',       '📑 Nota Fiscal',      '',                          2),
    ('financeiro.pagamentos', '📥 Financeiro',       'Pagamentos e recebimentos', 3)
  ) AS v(chave, rotulo, descricao, ordem);

-- Fornecedores
INSERT INTO atendimento.menu (pai_id, chave, rotulo, acao, destino_id, texto_antes, ordem)
SELECT (SELECT id FROM atendimento.menu WHERE chave = 'fornecedores'), v.chave, v.rotulo, 'destino',
       (SELECT id FROM _d WHERE nome = 'Benedito'), v.texto_antes, v.ordem
  FROM (VALUES
    ('fornecedores.ja',    'Já sou fornecedor',  '', 1),
    ('fornecedores.ainda', 'Ainda não sou',      'Agradecemos seu contato. Fique à vontade para apresentar seus produtos ou serviços para uma avaliação prévia.', 2)
  ) AS v(chave, rotulo, texto_antes, ordem);

-- Os textos e as regras que o dono ajusta (os textos de hoje da OlivIA, corrigidos na grafia)
INSERT INTO atendimento.ajustes (chave, valor) VALUES
    ('boas_vindas', to_jsonb('Seja bem-vindo à Sementes Renascer. Sou a OlivIA, sua atendente virtual.'::text)),
    ('link',        to_jsonb('Seu atendimento é feito por {nome}. Toque no link para falar direto: {link}'::text)),
    ('fora_do_horario', to_jsonb('Agora estamos fora do horário de atendimento (segunda a sexta, das 08:00 às 11:30 e das 13:30 às 17:30). O retorno vem no próximo horário.'::text)),
    ('horario',     '{"dias": [1, 2, 3, 4, 5], "faixas": [["08:00", "11:30"], ["13:30", "17:30"]]}'::jsonb),
    ('encerrar',    to_jsonb('Obrigado por nos contatar, estamos sempre à disposição. Tenha um excelente dia!'::text)),
    ('pergunta_recebeu', to_jsonb('Seu feedback é importante: você recebeu o atendimento que precisava?'::text)),
    ('pergunta_horas', '4.5'::jsonb),
    ('nao_recebeu', to_jsonb('Estamos trabalhando para lhe atender o mais breve possível; muitas vezes nosso profissional está em atendimento de campo. O gestor do departamento acaba de ser avisado.'::text)),
    ('avisado_no_nao', to_jsonb((SELECT id FROM _d WHERE nome = 'Maicon Gregory')));
