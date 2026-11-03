# #1242 — Pôr o 49 3664-0121 de volta na conta da Meta
**Data:** 03/11/2026 · **Quem faz:** o dono, no Meta Business Manager · **O sistema não toca** (regra 1)

O que a leitura das 17:43 mostrou (`tmp\numero_meta_2026-11-03_1743.txt`): a conta de WhatsApp Business
(WABA 1442233593867052) é sua, verificada e aprovada, mas está **sem número nenhum**; o número antigo
(id 725888737278277) não existe mais; o app "Direct Opa! Suite" continua inscrito no webhook da conta.

## Os links diretos (montados com os ids lidos da sua conta)

Portfólio (Business ID) **571906881636731** · conta do WhatsApp (WABA) **1442233593867052** · app
**AxiaAtende** 1136509615470343. Se um link abrir outra tela, siga o caminho de menu escrito ao lado.

| Para quê | Link |
|---|---|
| A conta do WhatsApp nas Configurações do negócio (abas Parceiros, Usuários, Apps; renomear) | https://business.facebook.com/settings/whatsapp-business-accounts/1442233593867052?business_id=571906881636731 |
| Parceiros do portfólio (o Opa/IXC, se estiver como parceiro) | https://business.facebook.com/settings/partners?business_id=571906881636731 |
| Usuários do sistema | https://business.facebook.com/settings/system-users?business_id=571906881636731 |
| Apps conectados ao portfólio (o "Direct Opa! Suite") | https://business.facebook.com/settings/apps?business_id=571906881636731 |
| WhatsApp Manager → Números de telefone (adicionar o número, verificação, PIN) | https://business.facebook.com/wa/manage/phone-numbers/?business_id=571906881636731&waba_id=1442233593867052 |
| WhatsApp Manager → visão geral da conta (qualidade, limites, nome) | https://business.facebook.com/wa/manage/home/?business_id=571906881636731&waba_id=1442233593867052 |
| WhatsApp Manager → Modelos de mensagem (conferir que continuam aprovados) | https://business.facebook.com/wa/manage/message-templates/?business_id=571906881636731&waba_id=1442233593867052 |
| App AxiaAtende → WhatsApp → Configuração da API (registrar o número, se ficar Desconectado) | https://developers.facebook.com/apps/1136509615470343/whatsapp-business/wa-dev-console/ |
| App AxiaAtende → WhatsApp → Configuração (webhook e campos inscritos) | https://developers.facebook.com/apps/1136509615470343/whatsapp-business/wa-settings/ |
| Verificação do negócio / Central de segurança | https://business.facebook.com/settings/security?business_id=571906881636731 |

## 0. Antes de começar (10 min)

- Entrar em `business.facebook.com` com uma conta que seja **administradora do portfólio** Sementes
  Renascer (id 571906881636731). Sem isso os menus abaixo não aparecem.
- Alguém **no escritório, perto do telefone fixo** 49 3664-0121: a verificação de número fixo é por
  **ligação de voz** com um código de 6 dígitos.
- O **PIN de dois passos** do número (6 dígitos). Se o Opa o criou e você não tem, a Meta oferece
  "esqueci o PIN": ela manda um e-mail de redefinição para o e-mail cadastrado no número, ou abre um
  prazo de 7 dias para desativar. Peça ao Opa o PIN antes, se ainda falar com eles; é o que mais atrasa.

## 1. Tirar o Opa da conta (faça ANTES de pôr o número de volta)

1. Configurações do negócio → **Contas** → **Contas do WhatsApp** → selecione "49 3664-0121 - Sementes
   Renascer - Opa Suite".
2. Aba **Parceiros**: se o Opa Suite / IXC aparecer, **Remover**.
3. **Usuários** → **Usuários do sistema**: qualquer usuário de sistema do Opa/IXC com acesso a esta
   conta → remover o ativo ou excluir o usuário.
4. **Integrações** → **Apps conectados** (ou, na conta do WhatsApp, "Apps"): "Direct Opa! Suite"
   (1182653405705606) → **remover**. É ele que ainda recebe os seus webhooks.
5. Renomear a conta (lápis ao lado do nome): "Sementes Renascer - 49 3664-0121".
6. Conferir: rode `numero_meta.py` de novo; em "APPS INSCRITOS NO WEBHOOK" só o AxiaAtende pode
   aparecer.

Por que antes: se o Opa ainda tiver acesso, pode remover o número de novo, e você refaz tudo.

## 2. Adicionar o número de volta

1. **WhatsApp Manager** (`business.facebook.com/wa/manage/`) → conta 1442233593867052 → **Números de
   telefone** → **Adicionar número de telefone**.
2. Perfil: nome exibido **Sementes Renascer** (o mesmo de antes, para a aprovação ser rápida),
   categoria, descrição. O nome exibido passa por nova análise da Meta; até aprovar, o número funciona
   com o nome pendente.
3. Número: Brasil, **49 3664 0121**. Método de verificação: **Ligação** (fixo não recebe SMS). Atenda no
   escritório e digite o código de 6 dígitos.
4. Se pedir o **PIN de dois passos**, digite o PIN (item 0). Se não tiver, "Esqueci o PIN" e siga o
   e-mail.
5. Se a Meta disser que o número **foi excluído recentemente** (erro 133015 ou aviso na tela): espere
   **5 minutos** e tente **uma** vez; se continuar, espere 30 a 60 minutos. Não tente em sequência:
   são no máximo 10 tentativas de registro em 72 horas (erro 133016 trava tudo).
6. Quando aparecer na lista com status **Conectado** (ou "Pendente" só pelo nome exibido), o número
   está de volta na Cloud API. Se ficar em **Desconectado**, falta o registro (item 3).

## 3. Registrar na Cloud API (só se ficou "Desconectado")

Na tela do desenvolvedor (`developers.facebook.com` → app **AxiaAtende** → WhatsApp → **Configuração
da API**), selecione o número novo na lista "De" e, se houver o botão, **Registrar**. Alternativa,
uma única vez, na sua mão (nunca no sistema), com o token temporário dessa mesma tela:

```
POST https://graph.facebook.com/v23.0/<NOVO_PHONE_NUMBER_ID>/register
{"messaging_product": "whatsapp", "pin": "<SEU_PIN_DE_6_DIGITOS>"}
```

## 4. Me passar o id novo, e eu fecho o lado do sistema

1. Rode de novo, elevado:
   ```powershell
   cd C:\AxiaAtende
   $env:AXIAATENDE_AMBIENTE = 'producao'; $env:AXIAATENDE_PROCESSO = 'recepcionista'
   .\.venv\Scripts\python.exe scripts\numero_meta.py
   ```
   O bloco "NUMEROS DA CONTA" traz o `id` novo e o `status`. Me diga o arquivo.
2. Eu troco `META_PHONE_ID` em `backend/config.py` (é constante no código, não `.env`), commito e peço o
   restart do recepcionista pela Porta-Ação. A inscrição do webhook é por conta: o AxiaAtende volta a
   receber assim que o número estiver "Conectado".
3. Prova: você manda "oi" do seu celular ao 49 3664-0121; eu confiro o evento chegando e a resposta
   saindo (`/saude` → `chegadas.aceitas`).

## 5. O que muda depois de voltar (para não estranhar)

- **Limite de envio** e **qualidade** recomeçam do nível inicial (250 conversas iniciadas por dia, subindo
  com o uso). Os envios à carteira em degraus (20 por dia) cabem nisso.
- Os **modelos** (reabertura, lote do representante, convites) são da conta, não do número: continuam
  aprovados.
- Quem mandou mensagem **entre 15:18 e a volta** não chegou a lugar nenhum e não recebeu resposta: a
  Meta não guarda o que foi mandado a um número que não existia.
- O histórico do sistema (conversas, pendências, fotos) está intacto: é do banco, não do número.

## Fontes (terceiros; a tela da Meta vale mais que elas)

- Registro, PIN e limite de 10 tentativas/72 h; erros 133015/133016:
  [theautomate.ai](https://theautomate.ai/blog/whatsapp-cloud-api-phone-number/),
  [conferbot](https://www.conferbot.com/blog/whatsapp-number-registration-failed)
- Remover parceiro na WABA (Business Settings → Accounts → WhatsApp Accounts → Partners):
  [getdarwin.ai](https://help.getdarwin.ai/en/articles/15136946-how-to-resolve-the-ghost-partner-error-on-whatsapp-business),
  [chakrahq](https://chakrahq.com/help/chat/faqs/coexistence-faqs/troubleshooting-issue-business-sharing-account-partner)
- Prazo curto depois de excluir e tentar de novo: [bitbybit](https://bitbybit.tawk.help/article/registering-a-new-phone-number-to-whatsapp-cloud-api)
