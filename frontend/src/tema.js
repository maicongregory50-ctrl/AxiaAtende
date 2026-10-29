// #1200: claro ou escuro. Abre seguindo o tema do computador; o botao do rodape do menu troca e a
// escolha fica guardada NESTE navegador. Sem localStorage (janela privada, bloqueio), segue o
// sistema e o botao continua trocando ate a pagina recarregar.
const CHAVE = 'axiaatende-tema'

function guardado() {
  try { return localStorage.getItem(CHAVE) } catch { return null }
}

export function temaAtual() {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

export function aplicarTema() {
  const escolha = guardado()
  const sistema = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  document.documentElement.dataset.theme = escolha === 'dark' || escolha === 'light' ? escolha : sistema
}

export function alternarTema() {
  const novo = temaAtual() === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = novo
  try { localStorage.setItem(CHAVE, novo) } catch { /* fica so nesta visita */ }
  return novo
}
