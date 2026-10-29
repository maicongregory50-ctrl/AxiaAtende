import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './fontes.css'
import './tokens.css'
import './estilo.css'
import './atende.css'
import { aplicarTema } from './tema.js'

aplicarTema()

createRoot(document.getElementById('raiz')).render(<App />)
