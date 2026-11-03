"""#1238, passo 12: a MAQUETE ESCRITA POR NOS -- 30 mensagens do jeito que a equipe escreve no WhatsApp da
empresa, cada uma com o estado que a pessoa tinha aberto naquela hora e o destino que a mensagem deveria ter.

De onde vieram: dos padroes medidos nos 82 textos reais de internos (30 dias ate 03/11/2026) e das tres
cenas da prova de 03/11 (o "Ok, recebi" e o "blz, legal." com chamado esperando, a legenda 26 s depois do
video, a logo da DJ AGRO), reescritas sem nome de pessoa nem numero real. Os clientes sao os do banco de
teste (PLANTAGRO, COOPERPASSO).

Duas maneiras de rodar:
- `tests/test_maquete_roteador.py` (pytest): monta cada cena no banco de teste, passa a mensagem pelo motor
  com a IA FALSA respondendo o esperado, e confere que o texto chegou ao fio certo -- a tubulacao, 30/30.
  Com `AXIAATENDE_GRAVAR_MAQUETE=1` grava tambem os retratos em `tests/maquete_roteador.json`.
- `scripts/ensaiar_roteador.py`: manda os mesmos retratos a OlivIA REAL e imprime, ao lado do esperado, o
  que ela respondeu. E a rodada que o dono le antes de ligar.

Cada cena: `abertos` (o que a pessoa tem aberto: chamado, foto, foto_agora, logo, cliente, curriculo),
`texto`, `esperado` (o fio, "nenhum", ou "corrente" quando nem chega ao roteador) e, na correcao, `antes`
(o texto anterior e o fio errado para onde ele foi) e `certo` (o fio para onde devia ir).
"""

CENAS = [
    # -- a prova de 03/11: resposta solta a uma pergunta de chamado, com cliente aberto
    {"abertos": ["chamado", "cliente"], "texto": "Ok, recebi", "esperado": "chamado"},
    {"abertos": ["chamado", "cliente"], "texto": "blz, legal.", "esperado": "chamado"},
    {"abertos": ["chamado"], "texto": "sim, ficou claro, pode seguir", "esperado": "chamado"},
    {"abertos": ["chamado", "foto"], "texto": "o 1222 pode fechar", "esperado": "chamado"},
    {"abertos": ["chamado"], "texto": "não entendi a pergunta, qual passo?", "esperado": "chamado"},
    {"abertos": ["chamado", "cliente"], "texto": "a resposta é sim, pode publicar", "esperado": "chamado"},
    {"abertos": ["chamado", "cliente", "curriculo"], "texto": "ok", "esperado": "chamado"},
    # -- a foto: legenda solta, a pergunta do canal respondida sem deslizar
    {"abertos": ["chamado", "foto_agora"], "texto": "colheita do centeio na área 2", "esperado": "foto"},
    {"abertos": ["chamado", "foto"], "texto": "centeio florindo, lavoura do Arno", "esperado": "foto"},
    {"abertos": ["chamado", "foto"], "texto": "isso é aveia preta, já em semente", "esperado": "foto"},
    {"abertos": ["chamado", "foto"], "texto": "a foto é da UBS, ensaque do centeio", "esperado": "foto"},
    {"abertos": ["foto", "chamado"], "texto": "tá verde ainda, perfilhando", "esperado": "foto"},
    {"abertos": ["foto"], "texto": "colheitadeira na área do Ivo", "esperado": "foto"},
    # -- o cliente do dia, pelo nome ou pelo conteudo
    {"abertos": ["chamado", "cliente", "foto"], "texto": "a Plantagro quer preço do +Palha", "esperado": "cliente"},
    {"abertos": ["foto", "cliente"], "texto": "liguei pra ele, vai pensar até sexta", "esperado": "cliente"},
    {"abertos": ["cliente"], "texto": "não atendeu, tento amanhã", "esperado": "cliente"},
    {"abertos": ["cliente", "chamado"], "texto": "ele comprou 20 sacos de aveia, pedido 5512", "esperado": "cliente"},
    {"abertos": ["chamado", "logo", "cliente"], "texto": "(áudio) o pessoal da Plantagro pediu a proposta por email",
     "esperado": "cliente"},
    # -- a logo: o nome do cliente sem deslizar
    {"abertos": ["chamado", "logo"], "texto": "é da Cooperpasso", "esperado": "logo"},
    {"abertos": ["logo", "cliente"], "texto": "Cooperpasso", "esperado": "logo"},
    {"abertos": ["logo"], "texto": "4655", "esperado": "logo"},
    {"abertos": ["logo", "foto"], "texto": "Agro Real Insumos", "esperado": "logo"},
    {"abertos": ["logo", "chamado"], "texto": "não sei o código, é a Copermap", "esperado": "logo"},
    # -- o curriculo: o comentario da Fran depois do "errada"
    {"abertos": ["curriculo", "chamado"], "texto": "ela não viu que a moça mora em Maravilha", "esperado": "curriculo"},
    # -- nada a ver com o que esta aberto
    {"abertos": ["chamado", "foto"], "texto": "vou almoçar e depois vejo", "esperado": "nenhum"},
    {"abertos": ["chamado", "cliente"], "texto": "preciso falar com o Benedito sobre o frete de amanhã", "esperado": "nenhum"},
    {"abertos": ["chamado", "foto"], "texto": "pode ser às 14h a reunião", "esperado": "nenhum"},
    {"abertos": ["chamado", "cliente"], "texto": "bom dia", "esperado": "corrente"},
    # -- a correcao escrita
    {"abertos": ["chamado", "foto"], "antes": ("trigo na Linha Bonita", "chamado"),
     "texto": "não, era sobre a foto", "esperado": "correcao", "certo": "foto"},
    {"abertos": ["foto", "cliente"], "antes": ("Plantagro", "foto"),
     "texto": "era do cliente, não da foto", "esperado": "correcao", "certo": "cliente"},
]

assert len(CENAS) == 30, len(CENAS)

# o rotulo com que cada fio aparece no retrato (o comeco basta para achar o numero)
ROTULO = {"chamado": "Chamado 1222", "foto": "Foto", "foto_agora": "Foto", "logo": "Logo",
          "cliente": "Cliente PLANTAGRO", "curriculo": "Currículo"}
