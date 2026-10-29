# AxiaAtende — Identidade Visual

> Fonte da verdade. Qualquer artefato do AxiaAtende (telas, favicon, app icon,
> documentos) usa **somente** os valores abaixo.
> Tokens prontos em `design-atende/tokens.css` (prefixo `--at-*`).
> Fontes locais em `design-atende/fonts.css` — **nada de CDN** (o sistema roda em HTTP na rede interna).

## 1. Paleta

### Marca (estrutura e acento)
| Token | Hex | Uso |
|---|---|---|
| Violeta | `#5B3FB5` | Cor primária: botões de ação, links, foco, seleção, contorno do balão. **Não usar como status.** |
| Violeta Profunda | `#1E1440` | Wordmark, fundo escuro, app icon, losango do núcleo. |
| Lilás | `#A792F2` | Acento: brilho do núcleo, terminais. **Nunca como status nem em texto.** |
| Traço | `#6E55C2` | Só os traços do eixo na versão `primary`. |
| Tinta | `#EDE8FF` | Centro do gradiente do núcleo. |

A casa: Security = ciano (protege) · Gestão = verde (organiza) · Suporte = cobre (responde) · Marketing = framboesa (cria) · **Atende = violeta (encaminha)**.

### Superfícies (tema claro — padrão)
As superfícies e o texto são **os da casa** (AxiaGestão), sob o prefixo `--at-*`: as telas do AxiaAtende são internas e convivem com o ERP. Muda só a marca.

| Token | Hex | Uso |
|---|---|---|
| Fundo | `#F5F7F5` | Fundo da página. |
| Superfície | `#FFFFFF` | Cards, tabelas, painéis. |
| Superfície hover | `#EFF4EF` | Hover de linhas e itens de menu. |
| Borda | `#DCE3DD` | Bordas de cards e inputs. |
| Borda suave | `#E9EEE9` | Divisórias internas, linhas de tabela. |

### Texto
| Token | Hex | Uso |
|---|---|---|
| Texto forte | `#1A2420` | Títulos, números fortes. |
| Texto | `#3D4A44` | Corpo de texto, dados. |
| Texto brando | `#6B7A72` | Labels, metadados, timestamps. |
| Rótulo | `#52705F` | "Eyebrow" / títulos de seção em caixa alta. |

### Status (significado fixo — NÃO trocar)
| Estado | Texto | Fundo | Uso |
|---|---|---|---|
| `erro` | `#B3271D` | `#FBEDEB` | Erro fatal, cancelado. **Só aqui entra vermelho.** |
| `urgente` | `#A04E00` | `#FBF1E4` | Vencido, ação imediata. |
| `aviso` | `#8A6D03` | `#FAF5E1` | Prazo próximo, atenção não bloqueante. |
| `ok` | `#1F7A48` | `#EAF5EE` | Publicado, entregue, resolvido. |
| `info` | `#2D6CA8` | `#EBF2F9` | Neutro / informativo. |

**Regras invioláveis**
- Violeta (marca) nunca vira status; Lilás nunca vira texto.
- Vermelho aparece **somente** em `erro`.
- Todo par texto/fundo acima passa de 4.5:1 de contraste; não clarear. Exceção herdada da casa: Texto brando sobre Fundo dá 4.2:1 — usar só em metadados, nunca em texto corrido.
- Nenhuma tela referencia hex direto — só `var(--at-*)`.

### Tema escuro (documentado em `tokens.css`)
Ative com `data-theme="dark"` no `<html>`. Os mesmos tokens mudam de valor; a primária sobe para `#9784E6` para manter 4.5:1 sobre as superfícies escuras.

## 2. Tipografia

| Família | Pesos | Uso |
|---|---|---|
| **Archivo** | 400, 500, 600, 700, 800 | Wordmark, títulos, UI, rótulos, botões. |
| **IBM Plex Mono** | 400, 500, 600 | Dados: datas, contadores, IDs, números de envio, timestamps. |

- Wordmark "AxiaAtende" = Archivo 800, `letter-spacing:-0.5px`, Violeta Profunda (branco no escuro). No lockup a 60px o letter-spacing escala para -1.2px.
- Rótulos de seção = Archivo 600 caixa alta, `letter-spacing` 0.06–0.08em, cor Rótulo.
- Tamanho mínimo em tela: **11px (mono) / 12px (corpo)**. Densidade vem de espaçamento, nunca de fonte menor.
- Números em tabelas: sempre Plex Mono, alinhados à direita.
- Arquivos woff2 locais em `assets/fonts/` + `fonts.css`. **Proibido carregar fonte de CDN.**

## 3. Logotipo (direção Balão de recepção)

### Marca institucional — o eixo em violeta (`axia-atende-*`)
A geometria exata do eixo da casa, na quinta cor. Usar em: `favicon-16`, usos
abaixo de 28px, documentos P&B, marca d'água.
- `primary` (fundo claro) · `mono` (P&B) · `line` (contorno) · `reverse` (branco sobre escuro).

### Símbolo do produto — o balão de recepção (`atende-balao.svg`)
Balão quadrado (72×64 no viewBox 100, cantos 12, traço 5 em Violeta) com a
**cauda no alto à direita** — de onde a mensagem chega — e o eixo inteiro
dentro, a 43%. É visivelmente diferente do balão do SuporteAxia (largo, cauda
embaixo à esquerda: lá o assistente fala; aqui a casa recebe). Usar em: login
das três telas (Recepção, Envios, Destinos), cabeçalho, app icon, lockup,
documentos internos.
- `atende-balao.svg` (fundo claro) · `atende-balao-reverse.svg` (branco sobre Violeta Profunda).
- **Tamanho mínimo do balão+eixo: 28px**, como no Suporte. Abaixo, a marca institucional (`favicon-16` leva o eixo livre).
- **O cliente do WhatsApp nunca vê esta marca.** O perfil do número continua sendo o da Sementes Renascer. Nunca aproximar o balão do verde `#25D366`, nunca pôr telefone dentro dele.

**Regras (valem para os dois símbolos)**
- Área de respiro mínima = ¼ da largura do símbolo, nos 4 lados.
- Tamanho mínimo do eixo livre: **20px**. Abaixo disso, só o núcleo (losango sobre o disco).
- A geometria do eixo é a de `axia-gestao-primary.svg` (viewBox 100×100), sem alteração. Muda a cor; o contêiner só aparece onde o canal pede.
- Nunca distorcer, rotacionar, recolorir fora da paleta ou aplicar sombra colorida. Nunca envolver em escudo (Security), círculo, hexágono, losango, semente, órbita ou malha.
- App icon = quadrado arredondado (raio 22%) em Violeta Profunda + símbolo do produto em `reverse`, como nos outros produtos.
- Favicons: `favicon-48`, `favicon-32` = balão · `favicon-16` = eixo livre.

## 4. Caminhos dos assets

```
design-atende/
├─ 01-identidade-visual.md      este documento
├─ tokens.css                   variáveis --at-* (claro + escuro)
├─ fonts.css                    @font-face locais
└─ assets/
   ├─ axia-atende-{primary|mono|line|reverse}.svg   marca institucional (eixo livre)
   ├─ atende-balao{|-reverse}.svg   símbolo do produto
   ├─ alt/                      axia-atende-a-entrada-* e axia-atende-b-fora-* (direções A e B, não escolhidas)
   ├─ fonts/                    archivo-{400..800}.woff2 · ibm-plex-mono-{400..600}.woff2
   ├─ icons/                    mark-{primary|mono|white}-{512|256|128}.png (eixo livre) · balao-{primary|white}-{512|256|128}.png
   ├─ app-icon/                 appicon-{1024|512|192|180}.png · favicon-{48|32|16}.png
   └─ lockup/                   lockup-horizontal-{light|dark}.svg e .png (símbolo + wordmark)
```

Use sempre o **SVG** quando o meio aceitar. PNG apenas onde SVG não é suportado.
O `<text>` dos lockups SVG pede a Archivo instalada; onde ela não estiver, use o PNG (3×).

## 5. Voz

Curto, cordial, sem tom de chatbot — quem chama quer chegar na pessoa certa.
Frases-âncora:
- "O eixo que encaminha."
- "Uma entrada, o destino certo."
Evitar: emoji decorativo, "Oi! Como posso te ajudar hoje? 😊", diminutivos, jargão.
Nas telas internas o tom é o da casa (técnico, direto). Nas mensagens que saem
para o cliente, a voz é a da Sementes Renascer, não a do AxiaAtende.
