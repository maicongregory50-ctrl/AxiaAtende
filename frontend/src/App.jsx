// As tres telas do AxiaAtende (#950): Recepcao, Envios e Destinos. Menu lateral no modelo do
// AxiaMarketing e do AxiaGestao.
import React, { useEffect, useState } from 'react'
import { LogOut, MessagesSquare, Send, Signpost } from 'lucide-react'
import { aoPerderSessao, mandar, pegar } from './api.js'
import Entrar from './Entrar.jsx'
import Recepcao from './Recepcao.jsx'
import Envios from './Envios.jsx'
import Destinos from './Destinos.jsx'

const MENU = [
  { aba: 'recepcao', rotulo: 'Recepção', Icone: MessagesSquare },
  { aba: 'envios', rotulo: 'Envios', Icone: Send },
  { aba: 'destinos', rotulo: 'Destinos', Icone: Signpost },
]

export default function App() {
  const [eu, setEu] = useState(undefined) // undefined = ainda perguntando
  const [aba, setAba] = useState('recepcao')

  useEffect(() => { pegar('/eu').then(setEu).catch(() => setEu(null)) }, [])
  useEffect(() => {
    aoPerderSessao(() => setEu(null))
    return () => aoPerderSessao(null)
  }, [])

  async function sair() {
    try { await mandar('POST', '/sair') } finally { setEu(null) }
  }

  if (eu === undefined) return <div className="carregando">Abrindo…</div>
  if (!eu) return <Entrar aoEntrar={setEu} />

  return (
    <div className="casa">
      <aside className="lateral">
        <div className="marca">Atendimento <span>Renascer</span></div>
        <nav>
          {MENU.map(({ aba: a, rotulo, Icone }) => (
            <button key={a} className={aba === a ? 'ativa' : ''} onClick={() => setAba(a)}>
              <Icone size={17} strokeWidth={2} />
              <span>{rotulo}</span>
            </button>
          ))}
        </nav>
        <div className="quem">
          <span>{eu.nome}</span>
          <button className="link" onClick={sair} title="Sair"><LogOut size={16} /></button>
        </div>
      </aside>
      <main>
        {aba === 'recepcao' && <Recepcao />}
        {aba === 'envios' && <Envios />}
        {aba === 'destinos' && <Destinos />}
      </main>
    </div>
  )
}
