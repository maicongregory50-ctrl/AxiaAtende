// A Recepcao (#950): quem chamou no 49 3664 0121, o que escolheu e para quem foi mandado.
// Manual: docs/manuais/recepcao.md.
import React, { useEffect, useState } from 'react'
import { pegar, quando, hora } from './api.js'

const ESTADO = {
  sim: ['Sim', 'v'], nao: ['Não · você foi avisado', 'r'], perguntado: ['perguntado, sem resposta', ''],
  pergunta_marcada: ['pergunta às', ''], parou: ['parou no meio', 'a'], encerrou: ['encerrou', ''],
  em_curso: ['escolhendo agora', ''],
}

export default function Recepcao() {
  const [dias, setDias] = useState(7)
  const [motivo, setMotivo] = useState('')
  const [situacao, setSituacao] = useState('')
  const [d, setD] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    const q = new URLSearchParams({ dias, motivo, situacao })
    pegar('/recepcao?' + q).then(setD).catch((e) => setErro(e.message))
  }, [dias, motivo, situacao])

  return (
    <section className="atende">
      <h1>Recepção</h1>
      <p className="sub">Quem chamou no 49 3664 0121, o que escolheu e para quem foi mandado. A OlivIA atende e manda o
        link; a conversa continua no WhatsApp de quem recebeu o link.</p>
      <div className="filtros">
        <select value={dias} onChange={(e) => setDias(Number(e.target.value))}>
          <option value={1}>Hoje e ontem</option><option value={7}>Últimos 7 dias</option>
          <option value={30}>Últimos 30 dias</option>
        </select>
        <select value={motivo} onChange={(e) => setMotivo(e.target.value)}>
          <option value="">Todos os motivos</option>
          {d && d.motivos.map((m) => <option key={m.chave} value={m.chave}>{m.rotulo}</option>)}
        </select>
        <select value={situacao} onChange={(e) => setSituacao(e.target.value)}>
          <option value="">Toda situação</option><option value="parou">Parou no meio</option>
          <option value="nao">Disse que não foi atendido</option><option value="sim">Disse que foi atendido</option>
        </select>
      </div>
      {erro && <p className="aviso erro">{erro}</p>}
      {d && (
        <>
          <div className="grupo">No período escolhido</div>
          <div className="cartoes">
            <div className="cartao"><span>Chegaram</span><b>{d.cartoes.chegaram}</b></div>
            <div className="cartao"><span>Receberam o link</span><b>{d.cartoes.receberam_link}</b></div>
            <div className="cartao alerta"><span>Pararam no meio</span><b>{d.cartoes.pararam_no_meio}</b></div>
            <div className="cartao"><span>Disseram que foram atendidos</span><b>{d.cartoes.disseram_sim}</b></div>
            <div className="cartao alerta"><span>Disseram que não</span><b>{d.cartoes.disseram_nao}</b></div>
            <div className="cartao"><span>IA acertou / errou</span><b>{d.cartoes.ia_acertou} / {d.cartoes.ia_errou}</b></div>
          </div>
          <table className="tabela">
            <thead><tr><th>Quando</th><th>Quem</th><th>Caminho</th><th>Mandado para</th><th>Recebeu o atendimento?</th></tr></thead>
            <tbody>
              {d.linhas.length === 0 && <tr><td colSpan={5} className="vazio">Ninguém chamou neste período.</td></tr>}
              {d.linhas.map((l, i) => (
                <tr key={i}>
                  <td>{quando(l.quando)}</td>
                  <td>{l.cliente || <>{l.numero} <span className="leve">{l.perfil ? `(${l.perfil})` : '(não é cliente)'}</span></>}</td>
                  <td>{l.caminho.join(' › ') || <span className="leve">— só chegou</span>}{l.ia === true && <span className="leve"> · IA acertou</span>}</td>
                  <td>{l.destino || <span className="leve">—</span>}</td>
                  <td><span className={'selo ' + ESTADO[l.estado][1]}>
                    {ESTADO[l.estado][0]}{l.estado === 'pergunta_marcada' ? ' ' + hora(l.pergunta_em) : ''}
                    {l.estado === 'nao' && l.aviso_nao_em ? ' ' + hora(l.aviso_nao_em) : ''}</span>
                    {l.satisfacao && <span className="leve"> nota {l.satisfacao}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
