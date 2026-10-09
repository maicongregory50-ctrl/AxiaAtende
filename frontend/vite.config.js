import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// #950. A tela e entregue pelo proprio servico das telas (8009); nao ha servico de tela.
// `npm run dev` so para desenvolver: 3009 com proxy para o servico.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 3009,
    proxy: { '/api': { target: 'http://127.0.0.1:8009' } },
  },
})
