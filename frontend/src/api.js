// Toda chamada ao servico passa por aqui (molde: AxiaMarketing). O cabecalho X-Axiaatende e
// exigido pelo servico em todo pedido que muda alguma coisa (backend/main.py).

export class ErroDaApi extends Error {
  constructor(status, mensagem) {
    super(mensagem)
    this.status = status
  }
}

// A sessao vence em 12 h; quem ouve (o App) volta para a tela de entrar.
let quemOuve = null
export function aoPerderSessao(fn) { quemOuve = fn }

async function ler(resposta) {
  let corpo = null
  try { corpo = await resposta.json() } catch { /* sem corpo */ }
  if (!resposta.ok) {
    if (resposta.status === 401 && quemOuve) quemOuve()
    const d = corpo && corpo.detail
    throw new ErroDaApi(resposta.status, typeof d === 'string' ? d : 'o servidor respondeu ' + resposta.status)
  }
  return corpo
}

export async function pegar(caminho) {
  return ler(await fetch('/api' + caminho, { credentials: 'same-origin' }))
}

export async function mandar(metodo, caminho, dados) {
  return ler(await fetch('/api' + caminho, {
    method: metodo,
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Axiaatende': '1' },
    body: dados === undefined ? undefined : JSON.stringify(dados),
  }))
}

// Datas no relogio de quem olha: 09/10 14:04
export function quando(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const dois = (n) => String(n).padStart(2, '0')
  return `${dois(d.getDate())}/${dois(d.getMonth() + 1)} ${dois(d.getHours())}:${dois(d.getMinutes())}`
}

export function hora(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
