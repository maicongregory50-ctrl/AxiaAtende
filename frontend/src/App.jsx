// As tres telas do AxiaAtende (#950): Recepcao, Envios e Destinos. Menu lateral no modelo do
// AxiaMarketing e do AxiaGestao.
import React, { useEffect, useState } from 'react'
import { LogOut, MessagesSquare, Moon, Send, Signpost, Sun } from 'lucide-react'
import { aoPerderSessao, mandar, pegar } from './api.js'
import { alternarTema, temaAtual } from './tema.js'
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
  const [tema, setTema] = useState(temaAtual)   // #1200: so para o icone do botao sol/lua

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
        <div className="marca">
          <img src="/marca/atende-balao.svg" alt="" width="30" height="30" />
          <span>AxiaAtende</span>
        </div>
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
          <button className="link" onClick={() => setTema(alternarTema())}
                  title={tema === 'dark' ? 'Tema claro' : 'Tema escuro'}>
            {tema === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
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
