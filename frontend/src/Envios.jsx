// Envios (#950): cada envio a clientes, cliente por cliente -- convite, entregue, lido, o que
// respondeu, as imagens. O envio nasce no AxiaMarketing (Publicacoes) e e aprovado la.
// Manual: docs/manuais/envios.md.
import React, { useEffect, useState } from 'react'
import { mandar, pegar, quando, hora } from './api.js'

const SITUACAO = {
  aguardando: ['na fila', ''], convidado: ['enviado', ''], sem_responsavel: ['sem responsável no cadastro', 'a'],
  sem_whatsapp: ['sem WhatsApp', ''], sem_aceite: ['sem aceite', 'a'], recusou_antes: ['recusou antes', 'r'],
  ja_recebeu: ['já recebeu esta peça', ''], falhou: ['não entregue', 'r'], nao_e_whatsapp: ['número não é WhatsApp', 'a'],
  // #1163: o comprador que ja recebeu duas mensagens nossas no mes; volta a receber no mes seguinte
  teto_do_mes: ['fora: teto do mês (já recebeu duas)', 'a'],
}
const TIPO = { material: 'Material para cliente', direta: 'Comunicação direta' }
const ESTADO = { ativo: 'enviando', parado_nota: 'PARADO pela nota do número', concluido: 'concluído', suspenso: 'suspenso' }
const NOTA = { GREEN: 'verde', YELLOW: 'amarela', RED: 'vermelha', UNKNOWN: 'sem leitura' }
// #1188: os avisos a equipe. Dentro das 24 h da pessoa saem como texto (de graca); fora, esperam o
// toque em Ver da reabertura; 7 dias sem o toque, "nao visto" -- e nao somem.
const ESTADO_AVISO = {
  texto: ['Enviado (texto)', 'v'], modelo: ['Enviado (modelo)', 'v'], guardado: ['Guardado', 'a'],
  nao_visto: ['Não visto', 'r'], erro: ['Erro', 'r'], na_fila: ['na fila', ''],
}
const TIPO_AVISO = {
  recusa: 'Cliente pediu para parar', sem_atendimento: 'Cliente sem atendimento', avaliacao_ruim: 'Avaliação ruim',
  endereco_fora: 'Endereço fora do ar', endereco_voltou: 'Endereço voltou', plano_sem_registro: 'Plano sem registro',
  lote_do_representante: 'Resumo do lote',
}

export default function Envios() {
  const [lista, setLista] = useState(null)
  const [escolhido, setEscolhido] = useState(null)
  const [d, setD] = useState(null)
  const [responsavel, setResponsavel] = useState('')
  const [resposta, setResposta] = useState('')
  const [erro, setErro] = useState('')

  function carregar() {
    pegar('/envios').then((l) => {
      setLista(l)
      if (!escolhido && l.envios.length) setEscolhido(l.envios[0].id)
    }).catch((e) => setErro(e.message))
  }
  useEffect(carregar, [])
  useEffect(() => {
    if (!escolhido) return
    const q = new URLSearchParams({ responsavel, resposta })
    pegar(`/envios/${escolhido}?` + q).then(setD).catch((e) => setErro(e.message))
  }, [escolhido, responsavel, resposta])

  async function religar() {
    try { await mandar('POST', `/envios/${escolhido}/religar`); carregar(); setD(null); setEscolhido(escolhido) }
    catch (e) { setErro(e.message) }
  }

  const c = d && d.cartoes
  return (
    <section className="atende">
      <h1>Envios</h1>
      <p className="sub">O Marketing pede o envio e você aprova lá, em Publicações. Aqui o envio é acompanhado: quem
        recebeu, quem leu, quem quis e quem não quis. Sai em lotes de até 20 por dia, só com a nota do número em verde.</p>
      {erro && <p className="aviso erro">{erro}</p>}
      {lista && lista.envios.length === 0 && <p className="vazio">Nenhum envio ainda. Ele nasce em Publicações, no AxiaMarketing.</p>}
      {lista && lista.envios.length > 0 && (
        <div className="filtros">
          <select value={escolhido || ''} onChange={(e) => { setEscolhido(Number(e.target.value)); setD(null) }}>
            {lista.envios.map((e) => (
              <option key={e.id} value={e.id}>{TIPO[e.tipo]} · {e.campanha || e.peca} · {quando(e.aprovado_em)}</option>))}
          </select>
          <select value={responsavel} onChange={(e) => setResponsavel(e.target.value)}>
            <option value="">Todos os responsáveis</option>
            {d && d.responsaveis.map((r) => <option key={r}>{r}</option>)}
          </select>
          <select value={resposta} onChange={(e) => setResposta(e.target.value)}>
            <option value="">Toda resposta</option><option value="quero">Quero receber</option>
            <option value="nao_quero">Não quero</option><option value="texto">Escreveu</option><option value="falar">Tocou em falar</option>
            <option value="sem_responsavel">Sem responsável</option><option value="sem_aceite">Sem aceite</option>
          </select>
          {lista.nota && <span className="leve">Nota do número: <b>{NOTA[lista.nota.nota]}</b></span>}
        </div>
      )}
      {d && (
        <>
          <div className="grupo">{TIPO[d.envio.tipo]} · {d.envio.peca} · aprovado por {d.envio.aprovado_por} em {quando(d.envio.aprovado_em)}
            {' · '}<b>{ESTADO[d.envio.situacao]}</b>
            {d.envio.situacao === 'parado_nota' && <button className="secundario religar" onClick={religar}>Religar o envio</button>}</div>
          <div className="cartoes">
            <div className="cartao"><span>{d.envio.tipo === 'direta' ? 'Enviados' : 'Convidados'}</span><b>{c.convidados}</b></div>
            <div className="cartao"><span>Entregues</span><b>{c.entregues}</b></div>
            <div className="cartao"><span>Lidos</span><b>{c.lidos}</b></div>
            {d.envio.tipo === 'material' && <div className="cartao"><span>Quero receber</span><b>{c.quero}</b></div>}
            {d.envio.tipo === 'material' && <div className="cartao"><span>Não quero</span><b>{c.nao_quero}</b></div>}
            <div className="cartao alerta"><span>Não entregues</span><b>{c.nao_entregues}</b></div>
            <div className="cartao alerta"><span>Sem responsável</span><b>{c.sem_responsavel}</b></div>
            <div className="cartao"><span>Na fila</span><b>{c.aguardando}</b></div>
            <div className="cartao"><span>Custo US$</span><b>{String(c.custo_usd).replace('.', ',')}</b></div>
          </div>
          <table className="tabela">
            <thead><tr><th>Cliente</th><th>Cidade</th><th>Responsável</th><th>Situação</th><th>Enviado</th>
              <th>Entregue</th><th>Lido</th><th>Resposta</th><th>Imagens</th></tr></thead>
            <tbody>
              {d.linhas.map((l) => (
                <tr key={l.codigo}>
                  <td>{l.codigo} · {l.nome}</td><td>{l.cidade} {l.uf}</td>
                  <td>{l.responsavel || <span className="leve">— {l.sugestao && `sugestão: ${l.sugestao}`}</span>}</td>
                  <td><span className={'selo ' + SITUACAO[l.situacao][1]}>{SITUACAO[l.situacao][0]}</span></td>
                  <td>{quando(l.convite_em)}</td>
                  <td className={l.entregue_em ? 'ok' : ''}>{hora(l.entregue_em)}</td>
                  <td className={l.lido_em ? 'ok' : ''}>{hora(l.lido_em)}</td>
                  <td>{l.resposta === 'quero' && <span className="selo v">Quero receber · {hora(l.resposta_em)}</span>}
                    {l.resposta === 'nao_quero' && <span className="selo r">Não quero · {hora(l.resposta_em)}
                      {l.aviso_recusa_em ? ' · responsável avisado' : ''}</span>}
                    {l.resposta === 'falar' && <span className="selo v">tocou em falar · {hora(l.resposta_em)}</span>}
                    {l.resposta === 'texto' && <><span className="selo v">escreveu · {hora(l.resposta_em)}</span> “{l.resposta_texto}”</>}
                    {!l.resposta && <span className="leve">—</span>}</td>
                  <td>{l.resposta === 'quero' ? l.imagens : <span className="leve">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {lista && lista.avisos && lista.avisos.length > 0 && (
        <>
          <h2>Avisos à equipe · últimos 30 dias</h2>
          <table className="tabela">
            <thead><tr><th>Para</th><th>Aviso</th><th>Situação</th><th>Quando</th><th>Criado</th></tr></thead>
            <tbody>
              {lista.avisos.map((a) => (
                <tr key={a.id}>
                  <td>{a.para} <span className="leve">{a.numero}</span></td>
                  <td>{TIPO_AVISO[a.tipo] || a.tipo}</td>
                  <td><span className={'selo ' + ESTADO_AVISO[a.estado][1]}>{ESTADO_AVISO[a.estado][0]}</span>
                    {a.estado === 'erro' && <span className="leve"> {a.erro}</span>}</td>
                  <td>{a.em ? quando(a.em) : <span className="leve">—</span>}</td>
                  <td>{quando(a.criado_em)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
