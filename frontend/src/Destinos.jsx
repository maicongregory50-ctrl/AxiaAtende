// Destinos (#950): para quem a OlivIA manda cada motivo. Trocar aqui vale para a proxima pessoa que
// chamar. Manual: docs/manuais/destinos.md.
import React, { useEffect, useState } from 'react'
import { mandar, pegar } from './api.js'

const DIAS = ['', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
const telefone = (w) => (w && w.length >= 12 ? `${w.slice(2, 4)} ${w.slice(4, w.length - 4)}-${w.slice(-4)}` : w)

export default function Destinos() {
  const [d, setD] = useState(null)
  const [erro, setErro] = useState('')
  const [editando, setEditando] = useState(null)   // {id, nome, whatsapp} ou {novo: true}
  const [horario, setHorario] = useState(null)

  function carregar() { pegar('/destinos').then((x) => { setD(x); setHorario(x.horario) }).catch((e) => setErro(e.message)) }
  useEffect(carregar, [])

  async function fazer(metodo, caminho, corpo) {
    setErro('')
    try { await mandar(metodo, caminho, corpo); setEditando(null); carregar() } catch (e) { setErro(e.message) }
  }
  const nomeDe = (id) => (d.destinos.find((x) => x.id === id) || {}).nome

  return (
    <section className="atende">
      <h1>Destinos</h1>
      <p className="sub">Para quem a OlivIA manda cada motivo. Trocar aqui vale para a próxima pessoa que chamar, sem precisar de ninguém.</p>
      {erro && <p className="aviso erro">{erro}</p>}
      {d && (
        <>
          <table className="tabela">
            <thead><tr><th>Motivo</th><th>Perguntas no caminho</th><th>Resposta</th><th>Mandado para</th><th>WhatsApp</th></tr></thead>
            <tbody>
              {d.opcoes.map((o) => (
                <tr key={o.id}>
                  <td>{o.caminho[0]}</td>
                  <td className="leve">{o.perguntas.slice(1).join(' › ') || '—'}</td>
                  <td>{o.caminho.slice(1).join(' › ') || '—'}{o.texto_antes && <span className="leve"> (antes vai um texto)</span>}</td>
                  <td><select value={o.destino_id} onChange={(e) => fazer('PUT', `/opcoes/${o.id}`, { destino_id: Number(e.target.value) })}>
                    {d.destinos.map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
                  </select></td>
                  <td className="num">{telefone((d.destinos.find((x) => x.id === o.destino_id) || {}).whatsapp)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2>As pessoas</h2>
          <table className="tabela estreita">
            <thead><tr><th>Nome</th><th>WhatsApp</th><th /></tr></thead>
            <tbody>
              {d.destinos.map((x) => (editando && editando.id === x.id ? (
                <tr key={x.id}>
                  <td><input value={editando.nome} onChange={(e) => setEditando({ ...editando, nome: e.target.value })} /></td>
                  <td><input value={editando.whatsapp} onChange={(e) => setEditando({ ...editando, whatsapp: e.target.value })} /></td>
                  <td><button className="primario" onClick={() => fazer('PUT', `/destinos/${x.id}`, editando)}>Salvar</button>
                    <button className="link" onClick={() => setEditando(null)}>Voltar</button></td>
                </tr>
              ) : (
                <tr key={x.id}><td>{x.nome}</td><td className="num">{telefone(x.whatsapp)}</td>
                  <td><button className="link" onClick={() => setEditando({ id: x.id, nome: x.nome, whatsapp: telefone(x.whatsapp) })}>editar</button></td></tr>
              )))}
              {editando && editando.novo ? (
                <tr>
                  <td><input placeholder="Nome" value={editando.nome} onChange={(e) => setEditando({ ...editando, nome: e.target.value })} /></td>
                  <td><input placeholder="49 99999-0000" value={editando.whatsapp} onChange={(e) => setEditando({ ...editando, whatsapp: e.target.value })} /></td>
                  <td><button className="primario" onClick={() => fazer('POST', '/destinos', editando)}>Salvar</button>
                    <button className="link" onClick={() => setEditando(null)}>Voltar</button></td>
                </tr>
              ) : (
                <tr><td colSpan={3}><button className="link" onClick={() => setEditando({ novo: true, nome: '', whatsapp: '' })}>+ Pessoa</button></td></tr>
              )}
            </tbody>
          </table>

          <h2>Horário de atendimento</h2>
          {horario && (
            <div className="filtros">
              {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                <label key={n} className="caixa"><input type="checkbox" checked={horario.dias.includes(n)}
                  onChange={(e) => setHorario({ ...horario, dias: e.target.checked ? [...horario.dias, n].sort() : horario.dias.filter((x) => x !== n) })} />{DIAS[n]}</label>
              ))}
              {horario.faixas.map((f, i) => (
                <span key={i}><input type="time" value={f[0]} onChange={(e) => setHorario({ ...horario, faixas: horario.faixas.map((g, j) => (j === i ? [e.target.value, g[1]] : g)) })} />
                  {' às '}<input type="time" value={f[1]} onChange={(e) => setHorario({ ...horario, faixas: horario.faixas.map((g, j) => (j === i ? [g[0], e.target.value] : g)) })} /></span>
              ))}
              <button className="secundario" onClick={() => fazer('PUT', '/ajustes/horario', horario)}>Salvar horário</button>
            </div>
          )}
          <p className="leve">Fora do horário, o link vai do mesmo jeito, com o aviso de que o retorno vem no próximo horário.</p>

          <h2>Canal de campo</h2>
          <div className="filtros">
            <label className="caixa"><input type="checkbox" checked={!!d.campo_ligado}
              onChange={(e) => fazer('PUT', '/ajustes/campo', { ligado: e.target.checked })} /> ligado</label>
            <span className="leve">{d.campo_ligado
              ? 'A foto ou o vídeo de colaborador e representante do cadastro vai para a Caixa do marketing; a OlivIA pergunta o que é e se é de hoje.'
              : 'Desligado: a foto da equipe é só guardada, como sempre; o marketing não busca.'}</span>
          </div>

          <h2>Quem é avisado quando alguém diz que não foi atendido</h2>
          <div className="filtros">
            <select value={d.avisado_no_nao || ''} onChange={(e) => fazer('PUT', '/ajustes/avisado', { destino_id: Number(e.target.value) })}>
              {d.destinos.map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
            </select>
            <span className="leve">atual: {nomeDe(d.avisado_no_nao)}</span>
          </div>
        </>
      )}
    </section>
  )
}
