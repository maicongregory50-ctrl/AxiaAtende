import React, { useState } from 'react'
import { mandar } from './api.js'

export default function Entrar({ aoEntrar }) {
  const [login, setLogin] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [indo, setIndo] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setIndo(true)
    try {
      aoEntrar(await mandar('POST', '/entrar', { login, senha }))
    } catch (err) {
      setErro(err.message)
      setSenha('')
    } finally {
      setIndo(false)
    }
  }

  return (
    <div className="entrar">
      <form onSubmit={enviar}>
        <div className="marca grande">Atendimento <span>Renascer</span></div>
        <label>
          Usuário
          <input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" autoFocus required />
        </label>
        <label>
          Senha
          <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)}
                 autoComplete="current-password" required />
        </label>
        {erro && <p className="aviso erro">{erro}</p>}
        <button className="primario" disabled={indo}>{indo ? 'Entrando…' : 'Entrar'}</button>
      </form>
    </div>
  )
}
