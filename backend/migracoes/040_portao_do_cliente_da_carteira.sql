-- #1189 (dono, 28/10/2026): O CLIENTE DA CARTEIRA NAO CAI NO FLUXO GERAL. Quem recebeu um envio da
-- carteira nos ultimos 30 dias e escreve ao numero da empresa recebe o contato do representante dele
-- e, para outro assunto, ESTE menu: uma terceira raiz, com quatro destinos que ja existem.
--
-- Nas palavras do dono: "se quiser o boleto, ou saber como esta a carga dele, ele e direcionado ao
-- contato correto, como ja temos essa parte. Ou cliente quer reclamar, estiver zangado, ai fala
-- comigo." O "Falar com a empresa" e o comercial de quem nao quer o representante, e a reclamacao.
--
-- OS DESTINOS SAO OS DO MENU DE HOJE, lidos dos nos que ja os levam -- nenhum numero novo entra
-- aqui. A empresa e o destino do "Corretor" (o dono, semente 002). Folha cujo destino nao se acha
-- simplesmente nao nasce: o CHECK menu_destino_so_na_folha recusaria, e uma recusa aqui impediria o
-- servico de subir.
--
-- A tela Destinos le a arvore a partir de chave = 'raiz' e nao administra esta (a mesma lacuna da
-- raiz_interna, 018). Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

INSERT INTO atendimento.menu (pai_id, chave, rotulo, descricao, pergunta, acao, ordem) VALUES
    (NULL, 'raiz_carteira', 'Cliente da carteira', '',
     'Se for outro assunto, escolha abaixo.', 'menu', 0);

INSERT INTO atendimento.menu (pai_id, chave, rotulo, descricao, acao, destino_id, ordem)
SELECT (SELECT id FROM atendimento.menu WHERE chave = 'raiz_carteira'), v.chave, v.rotulo, v.descricao, 'destino',
       (SELECT destino_id FROM atendimento.menu WHERE chave = v.de), v.ordem
  FROM (VALUES
    ('carteira.financeiro', '🧾 Boleto e nota',     'Boleto, nota fiscal ou pagamento',                    'financeiro.boleto',  1),
    ('carteira.carga',      '🚚 Carga e entrega',   'Onde está a carga, entrega ou frete do pedido',       'fretes',             2),
    ('carteira.qualidade',  '🏆 Qualidade',         'Documento ou qualidade da semente',                   'qualidade',          3),
    ('carteira.empresa',    '💬 Falar c/ a empresa', 'Comercial com a empresa, reclamação ou insatisfação', 'comercial.corretor', 4)
  ) AS v(chave, rotulo, descricao, de, ordem)
 WHERE (SELECT destino_id FROM atendimento.menu WHERE chave = v.de) IS NOT NULL;

INSERT INTO atendimento.ajustes (chave, valor) VALUES ('portao.ligado', 'true'::jsonb)
    ON CONFLICT (chave) DO NOTHING;
