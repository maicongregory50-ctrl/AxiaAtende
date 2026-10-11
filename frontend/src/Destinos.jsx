// Destinos (#950): para quem a OlivIA manda cada motivo. Trocar aqui vale para a proxima pessoa que
// chamar. Manual: docs/manuais/destinos.md.
// Passada de design em 11/10/2026 (#970, pedido do dono): cada ajuste num cartao, como as telas de
// configuracao do ERP (RegraComissaoPage: h2 + texto de ajuda em cinza + cartao), e o que liga e
// desliga vira BOTAO com o estado escrito (Ativar / Desativar), nunca uma caixinha.
import React, { useEffect, useState } from 'react'
import { mandar, pegar } from './api.js'

const DIAS = ['', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
const telefone = (w) => (w && w.length >= 12 ? `${w.slice(2, 4)} ${w.slice(4, w.length - 4)}-${w.slice(-4)}` : w)

function Secao({ titulo, ajuda, children }) {
  return (
    <>
      <h2>{titulo}</h2>
      {ajuda && <p className="ajuda">{ajuda}</p>}
      <div className="cartao-ajuste">{children}</div>
    </>
  )
}

export default function Destinos() {
  const [d, setD] = useState(null)
  const [erro, setErro] = useState('')
  const [feito, setFeito] = useState('')
  const [editando, setEditando] = useState(null)   // {id, nome, whatsapp} ou {novo: true}
  const [horario, setHorario] = useState(null)

  function carregar() { pegar('/destinos').then((x) => { setD(x); setHorario(x.horario) }).catch((e) => setErro(e.message)) }
  useEffect(carregar, [])

  async function fazer(metodo, caminho, corpo, aviso) {
    setErro(''); setFeito('')
    try {
      await mandar(metodo, caminho, corpo)
      setEditando(null); carregar()
      if (aviso) { setFeito(aviso); setTimeout(() => setFeito(''), 4000) }
    } catch (e) { setErro(e.message) }
  }
  const nomeDe = (id) => (d.destinos.find((x) => x.id === id) || {}).nome
  const diaLigado = (n) => horario && horario.dias.includes(n)
  const alternarDia = (n) => setHorario({ ...horario, dias: diaLigado(n) ? horario.dias.filter((x) => x !== n) : [...horario.dias, n].sort() })
  const horarioMudou = d && horario && JSON.stringify(horario) !== JSON.stringify(d.horario)

  return (
    <section className="atende destinos">
      <h1>Destinos</h1>
      <p className="sub">Para quem a OlivIA manda cada motivo. Trocar aqui vale para a próxima pessoa que chamar, sem precisar de ninguém.</p>
      {erro && <p className="aviso erro">{erro}</p>}
      {feito && <p className="aviso ok">{feito}</p>}
      {d && (
        <>
          <Secao titulo="Os motivos e para quem vão" ajuda="O caminho que a pessoa percorre no menu e quem recebe o cartão de contato no fim.">
            <table className="tabela">
              <thead><tr><th>Motivo</th><th>Perguntas no caminho</th><th>Resposta</th><th>Mandado para</th><th>WhatsApp</th></tr></thead>
              <tbody>
                {d.opcoes.map((o) => (
                  <tr key={o.id}>
                    <td>{o.caminho[0]}</td>
                    <td className="leve">{o.perguntas.slice(1).join(' › ') || '—'}</td>
                    <td>{o.caminho.slice(1).join(' › ') || '—'}{o.texto_antes && <span className="leve"> (antes vai um texto)</span>}</td>
                    <td><select value={o.destino_id} onChange={(e) => fazer('PUT', `/opcoes/${o.id}`, { destino_id: Number(e.target.value) }, 'Destino trocado.')}>
                      {d.destinos.map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
                    </select></td>
                    <td className="num">{telefone((d.destinos.find((x) => x.id === o.destino_id) || {}).whatsapp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Secao>

          <Secao titulo="As pessoas" ajuda="Quem pode receber alguém pelo link: nome e WhatsApp com DDD.">
            <table className="tabela estreita">
              <thead><tr><th>Nome</th><th>WhatsApp</th><th className="acoes" /></tr></thead>
              <tbody>
                {d.destinos.map((x) => (editando && editando.id === x.id ? (
                  <tr key={x.id} className="editando">
                    <td><input value={editando.nome} onChange={(e) => setEditando({ ...editando, nome: e.target.value })} /></td>
                    <td><input value={editando.whatsapp} onChange={(e) => setEditando({ ...editando, whatsapp: e.target.value })} /></td>
                    <td className="acoes"><button className="primario pequeno" onClick={() => fazer('PUT', `/destinos/${x.id}`, editando, 'Pessoa salva.')}>Salvar</button>
                      <button className="fantasma pequeno" onClick={() => setEditando(null)}>Cancelar</button></td>
                  </tr>
                ) : (
                  <tr key={x.id}><td>{x.nome}</td><td className="num">{telefone(x.whatsapp)}</td>
                    <td className="acoes"><button className="fantasma pequeno" onClick={() => setEditando({ id: x.id, nome: x.nome, whatsapp: telefone(x.whatsapp) })}>Editar</button></td></tr>
                )))}
                {editando && editando.novo ? (
                  <tr className="editando">
                    <td><input placeholder="Nome" value={editando.nome} onChange={(e) => setEditando({ ...editando, nome: e.target.value })} /></td>
                    <td><input placeholder="49 99999-0000" value={editando.whatsapp} onChange={(e) => setEditando({ ...editando, whatsapp: e.target.value })} /></td>
                    <td className="acoes"><button className="primario pequeno" onClick={() => fazer('POST', '/destinos', editando, 'Pessoa cadastrada.')}>Salvar</button>
                      <button className="fantasma pequeno" onClick={() => setEditando(null)}>Cancelar</button></td>
                  </tr>
                ) : (
                  <tr><td colSpan={3}><button className="fantasma pequeno" onClick={() => setEditando({ novo: true, nome: '', whatsapp: '' })}>+ Pessoa</button></td></tr>
                )}
              </tbody>
            </table>
          </Secao>

          <Secao titulo="Horário de atendimento" ajuda="Fora do horário, o link vai do mesmo jeito, com o aviso de que o retorno vem no próximo horário.">
            {horario && (
              <div className="linha-ajuste">
                <div className="dias">
                  {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                    <button key={n} type="button" className={'dia' + (diaLigado(n) ? ' ligado' : '')}
                            aria-pressed={diaLigado(n)} onClick={() => alternarDia(n)}>{DIAS[n]}</button>
                  ))}
                </div>
                <div className="faixas">
                  {horario.faixas.map((f, i) => (
                    <span key={i} className="faixa"><input type="time" value={f[0]} onChange={(e) => setHorario({ ...horario, faixas: horario.faixas.map((g, j) => (j === i ? [e.target.value, g[1]] : g)) })} />
                      <span className="leve">às</span><input type="time" value={f[1]} onChange={(e) => setHorario({ ...horario, faixas: horario.faixas.map((g, j) => (j === i ? [g[0], e.target.value] : g)) })} /></span>
                  ))}
                </div>
                <button className="primario pequeno" disabled={!horarioMudou} onClick={() => fazer('PUT', '/ajustes/horario', horario, 'Horário salvo.')}>Salvar horário</button>
              </div>
            )}
          </Secao>

          <Secao titulo="Canal de campo" ajuda="A foto ou o vídeo que um colaborador ou representante do cadastro manda ao WhatsApp da Renascer vai sozinho ao catálogo do marketing; a OlivIA responde, diz o que a foto parece e pergunta se é de hoje.">
            <div className="linha-ajuste">
              <span className={'estado ' + (d.campo_ligado ? 'ok' : 'off')}>{d.campo_ligado ? 'Ativo' : 'Inativo'}</span>
              <span className="leve">{d.campo_ligado
                ? 'Ligado: a equipe manda e o marketing busca a cada minuto.'
                : 'Desligado: a foto da equipe é só guardada, como sempre; o marketing não busca.'}</span>
              <button className={(d.campo_ligado ? 'perigo' : 'primario') + ' pequeno'}
                      onClick={() => fazer('PUT', '/ajustes/campo', { ligado: !d.campo_ligado }, d.campo_ligado ? 'Canal de campo desativado.' : 'Canal de campo ativado.')}>
                {d.campo_ligado ? 'Desativar' : 'Ativar'}
              </button>
            </div>
          </Secao>

          <Secao titulo="Quem é avisado quando alguém diz que não foi atendido" ajuda="Recebe um aviso no WhatsApp quando a pessoa responde que não foi atendida, ou dá a nota Ruim.">
            <div className="linha-ajuste">
              <select value={d.avisado_no_nao || ''} onChange={(e) => fazer('PUT', '/ajustes/avisado', { destino_id: Number(e.target.value) }, 'Avisado trocado.')}>
                {d.destinos.map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
              </select>
              <span className="leve">atual: {nomeDe(d.avisado_no_nao) || '—'}</span>
            </div>
          </Secao>
        </>
      )}
    </section>
  )
}
