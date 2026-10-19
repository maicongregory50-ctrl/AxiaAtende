-- #1048 (dono, 19/10/2026): A LISTA DE BASTIDORES VIRA CADASTRO, e ganha quatro categorias.
--
-- Hoje as 08:29 o dono mandou OITO fotos com a legenda "Estoque.". A OlivIA propos "Parece
-- beneficiamento. E isso?", ele respondeu "Estoque.", e ela passou para a proxima pergunta: as oito
-- foram ao catalogo SEM CLASSE (ATV-0737 a ATV-0744). Ele disse a palavra duas vezes e o sistema nao
-- tem onde po-la -- e nao disse isso a ninguem.
--
-- POR QUE CADASTRO, E NAO MAIS UMA CONSTANTE: a lista vivia em SEIS lugares, em dois repositorios
-- (campo.BASTIDORES, o enum de ia.py, a prosa de INSTRUCOES_CAMPO, e no AxiaMarketing
-- visao.BASTIDORES, ETIQUETA_DO_BASTIDOR e a regra de institucional) -- e faltar em um deles NAO DA
-- ERRO, DA SILENCIO. Nesta mesma casa os PRODUTOS ja sao cadastro (ajuste `campo.produtos`): duas
-- listas do mesmo fluxo tratadas de modos opostos. Agora e uma linha com seis consumidores.
--
-- OBJETOS, nao slugs, porque os seis lugares querem coisas diferentes da mesma linha:
--   chave         -> o enum do modelo e o valor em material_de_campo.classe_bastidor
--   rotulo        -> o botao, a linha da lista e a etiqueta do catalogo
--   descricao     -> a prosa que o modelo le (era o texto inline de INSTRUCOES_CAMPO)
--   institucional -> a regra de produto do marketing (hoje: beneficiamento, controle-de-qualidade e
--                    entrega nao levam produto). AS CINCO DE HOJE MANTEM O QUE JA ERA.
--
-- As quatro novas foram escolhidas pelo dono a partir das legendas sem classe medidas em 19/10:
-- "Estoque." (8 pecas), "Manejo, rolo faca" (2), "Parte externa da empresa, estacionamento" (4) e
-- "Primeira versao do AVR Lanco, formula" (1). `institucional` nas duas primeiras e proposta minha,
-- registrada na spec como corrigivel pelo dono.
--
-- Sem BEGIN nem COMMIT: a transacao e de backend/migracoes.py.

INSERT INTO atendimento.ajustes (chave, valor) VALUES ('campo.bastidores', '[
  {"chave": "campo-de-sementes",     "rotulo": "Campo de sementes",
   "descricao": "lavoura em pé, vistoria, plantio, floração",            "institucional": false},
  {"chave": "colheita",              "rotulo": "Colheita",
   "descricao": "colheitadeira, grãos saindo",                           "institucional": false},
  {"chave": "beneficiamento",        "rotulo": "Beneficiamento",
   "descricao": "UBS, limpeza, ensaque",                                 "institucional": true},
  {"chave": "controle-de-qualidade", "rotulo": "Controle de qualidade",
   "descricao": "laboratório, amostra, germinação",                      "institucional": true},
  {"chave": "entrega",               "rotulo": "Entrega / carregamento",
   "descricao": "carregamento, caminhão, revenda, cliente",              "institucional": true},
  {"chave": "estoque",               "rotulo": "Estoque / armazém",
   "descricao": "semente guardada, armazém, pálete, sacaria em estoque", "institucional": true},
  {"chave": "estrutura",             "rotulo": "Estrutura da empresa",
   "descricao": "sede, pátio, fachada, estacionamento, parte externa",   "institucional": true},
  {"chave": "produto-embalagem",     "rotulo": "Produto / embalagem",
   "descricao": "o saco, o rótulo, a embalagem, a fórmula do produto",   "institucional": false},
  {"chave": "manejo",                "rotulo": "Manejo / implemento",
   "descricao": "rolo-faca, implemento, máquina, operação no campo que não é colheita",
   "institucional": false}
]'::jsonb)
ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor, atualizado_em = now();
