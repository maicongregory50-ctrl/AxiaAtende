// Custos (#1223): quanto cada funcao paga por uso custa por mes -- a Meta (WhatsApp), o Claude (a OlivIA)
// e o Gemini (o AxiaMarketing). So para quem o servidor libera (AXIAATENDE_CUSTOS_LOGINS).
// Manual: docs/manuais/custos.md.
import React, { useEffect, useState } from 'react'
import { mandar, pegar } from './api.js'

const SERVICO = { meta: 'Meta (WhatsApp)', claude: 'Claude (OlivIA)', gemini: 'Gemini (Marketing)' }
const FUNCAO = {
  convite: 'Convite da carteira', direta: 'Comunicação direta', reabertura: 'Reabertura dos avisos',
  curriculo: 'Currículo para a Fran', sem_funcao: 'sem função',
  aviso_recusa: 'Aviso: cliente pediu para parar', aviso_sem_atendimento: 'Aviso: cliente sem atendimento',
  aviso_avaliacao_ruim: 'Aviso: avaliação ruim', aviso_endereco_fora: 'Aviso: endereço fora do ar',
  aviso_endereco_voltou: 'Aviso: endereço voltou', aviso_plano_sem_registro: 'Aviso: plano sem registro',
  aviso_lote_do_representante: 'Aviso: resumo do lote', aviso_status_do_dia: 'Aviso: status do dia',
  aviso_auditoria_estoque: 'Aviso: auditoria de estoque',
  triagem: 'OlivIA · triagem do motivo', campo: 'OlivIA · material de campo', visita: 'OlivIA · registro de visita',
  pendencia: 'OlivIA · de qual chamado é a resposta',
  edicao: 'Edição de imagem', olhar_foto: 'Olhar sobre a foto',
}
const FONTE = { resumo: 'pelo resumo', nenhum: '', registro: '', axiaatende: '', axiamarketing: '' }
const CONFERENCIA = {
  ok: ['conferido', 'estado-aprovada'], sem_acesso: ['sem acesso', 'estado-falhou'], erro: ['erro na leitura', 'estado-falhou'],
  sem_conferencia: ['sem conferência', 'estado-cancelada'],
}

function dinheiro(v, moedas) {
  const m = moedas && moedas.length === 1 ? moedas[0] : 'US$'
  return `${m === 'USD' ? 'US$' : m} ${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
}
function mesAo(mes, passo) {
  const [a, m] = mes.split('-').map(Number)
  const d = new Date(a, m - 1 + passo, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
function hojeMes() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}` }

// O valor de uma linha: com parte sem preco, diz quantas -- nunca mostra 0 no lugar de "nao sei".
function Valor({ l }) {
  if (l.sem_preco === l.quantidade) return <span className="selo estado-enviando">sem preço</span>
  return (
    <>
      {dinheiro(l.valor, l.moedas)}
      {l.sem_preco > 0 && <span className="selo estado-enviando">+ {l.sem_preco} sem preço</span>}
    </>
  )
}

function Precos({ voltar }) {
  const [d, setD] = useState(null)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')
  const [f, setF] = useState({ servico: 'meta', item: '', vale_desde: new Date().toISOString().slice(0, 10),
                               por_mensagem: '', por_milhao_entrada: '', por_milhao_saida: '', moeda: 'USD' })
  function carregar() { pegar('/custos/precos').then(setD).catch((e) => setErro(e.message)) }
  useEffect(carregar, [])
  const num = (s) => (s === '' ? null : Number(String(s).replace(',', '.')))
  async function lancar(e) {
    e.preventDefault(); setErro(''); setOk('')
    try {
      await mandar('POST', '/custos/precos', { ...f, item: f.item.trim(), por_mensagem: num(f.por_mensagem),
        por_milhao_entrada: num(f.por_milhao_entrada), por_milhao_saida: num(f.por_milhao_saida) })
      setOk('Preço lançado. Ele vale a partir da data informada; os dias de antes continuam com o preço anterior.')
      carregar()
    } catch (e2) { setErro(e2.message) }
  }
  const muda = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <>
      <div className="filtros"><button className="secundario" onClick={voltar}>← Voltar aos custos</button></div>
      <p className="sub">Preço novo é linha nova: o antigo continua valendo para os dias de antes. Meta: valor por
        mensagem, na categoria que a Meta cobra. Claude e Gemini: valor por milhão de tokens.</p>
      {erro && <p className="aviso erro">{erro}</p>}
      {ok && <p className="aviso ok">{ok}</p>}
      <form className="filtros" onSubmit={lancar}>
        <select value={f.servico} onChange={muda('servico')}>
          {Object.entries(SERVICO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input list="itens-custo" placeholder={f.servico === 'meta' ? 'categoria (marketing…)' : 'modelo'}
               value={f.item} onChange={muda('item')} required />
        <datalist id="itens-custo">{d && (d.itens[f.servico] || []).map((i) => <option key={i} value={i} />)}</datalist>
        <label className="leve">vale desde <input type="date" value={f.vale_desde} onChange={muda('vale_desde')} required /></label>
        {f.servico === 'meta'
          ? <input placeholder="por mensagem" inputMode="decimal" value={f.por_mensagem} onChange={muda('por_mensagem')} required />
          : <>
              <input placeholder="por milhão (entrada)" inputMode="decimal" value={f.por_milhao_entrada} onChange={muda('por_milhao_entrada')} required />
              <input placeholder="por milhão (saída)" inputMode="decimal" value={f.por_milhao_saida} onChange={muda('por_milhao_saida')} required />
            </>}
        <input style={{ width: 70 }} value={f.moeda} onChange={muda('moeda')} maxLength={3} />
        <button type="submit">Lançar preço</button>
      </form>
      {d && (
        <table className="tabela">
          <thead><tr><th>Serviço</th><th>Item</th><th>Vale desde</th><th>Valor</th><th>Lançado por</th></tr></thead>
          <tbody>
            {d.precos.map((p) => (
              <tr key={p.id}>
                <td>{SERVICO[p.servico]}</td><td>{p.item}</td><td>{p.vale_desde.split('-').reverse().join('/')}</td>
                <td>{p.servico === 'meta'
                  ? `${dinheiro(p.por_mensagem, [p.moeda])} por mensagem`
                  : `${dinheiro(p.por_milhao_entrada, [p.moeda])} / ${dinheiro(p.por_milhao_saida, [p.moeda])} por milhão`}</td>
                <td>{p.criado_por || '(semente)'}</td>
              </tr>))}
          </tbody>
        </table>
      )}
    </>
  )
}

export default function Custos() {
  const [mes, setMes] = useState(hojeMes)
  const [d, setD] = useState(null)
  const [erro, setErro] = useState('')
  const [precos, setPrecos] = useState(false)

  useEffect(() => {
    if (precos) return
    setD(null); setErro('')
    pegar(`/custos?mes=${mes}`).then(setD).catch((e) => setErro(e.message))
  }, [mes, precos])

  const total = (s) => d ? d.linhas.filter((l) => l.servico === s).reduce((t, l) => t + l.valor, 0) : 0
  const semPreco = (s) => d ? d.linhas.filter((l) => l.servico === s).reduce((t, l) => t + l.sem_preco, 0) : 0
  return (
    <section className="atende">
      <h1>Custos</h1>
      <p className="sub">Quanto cada função paga por uso custa no mês: as mensagens pagas do WhatsApp, a OlivIA (Claude) e o
        Gemini do Marketing. A quantidade é real; o valor é a quantidade vezes o preço que você lançou. O que roda na
        assinatura do Claude não aparece aqui, porque não é cobrado por uso.</p>
      {erro && <p className="aviso erro">{erro}</p>}
      {precos ? <Precos voltar={() => setPrecos(false)} /> : (
        <>
          <div className="filtros">
            <button className="secundario" onClick={() => setMes(mesAo(mes, -1))}>←</button>
            <b>{mes.split('-').reverse().join('/')}</b>
            <button className="secundario" onClick={() => setMes(mesAo(mes, 1))} disabled={mes >= hojeMes()}>→</button>
            <button className="secundario" onClick={() => setPrecos(true)} style={{ marginLeft: 'auto' }}>Preços</button>
          </div>
          {d && (
            <>
              <div className="cartoes">
                {Object.keys(SERVICO).map((s) => (
                  <div key={s} className={'cartao' + (semPreco(s) ? ' alerta' : '')}>
                    <span>{SERVICO[s]}</span><b>{dinheiro(total(s))}</b>
                    {semPreco(s) > 0 && <span>{semPreco(s)} sem preço</span>}
                  </div>))}
              </div>
              {d.linhas.length === 0 && <p className="vazio">Nada pago por uso neste mês.</p>}
              {d.linhas.length > 0 && (
                <table className="tabela">
                  <thead><tr><th>Serviço</th><th>Função</th><th>Item</th><th>Quantidade</th><th>Valor</th></tr></thead>
                  <tbody>
                    {d.linhas.map((l, i) => (
                      <tr key={i}>
                        <td>{SERVICO[l.servico]}</td>
                        <td>{l.funcao === 'sem_funcao'
                          ? <span className="selo estado-falhou">sem função</span>
                          : FUNCAO[l.funcao] || l.funcao}
                          {FONTE[l.fonte] && <span className="selo estado-cancelada">{FONTE[l.fonte]}</span>}</td>
                        <td>{l.item}</td>
                        <td>{l.quantidade} {l.unidade}{l.unidade === 'chamadas' &&
                          <span className="leve"> · {l.entrada.toLocaleString('pt-BR')} / {l.saida.toLocaleString('pt-BR')} tokens</span>}</td>
                        <td><Valor l={l} /></td>
                      </tr>))}
                  </tbody>
                </table>
              )}
              {d.meta_dias.length > 0 && (
                <>
                  <div className="grupo">Meta: calculado × cobrado, por dia</div>
                  <table className="tabela">
                    <thead><tr><th>Dia</th><th>Mensagens pagas</th><th>Calculado</th><th>Cobrado pela Meta</th><th>Conferência</th></tr></thead>
                    <tbody>
                      {d.meta_dias.map((x) => {
                        const [rot, cls] = CONFERENCIA[x.situacao] || [x.situacao, '']
                        return (
                          <tr key={x.dia}>
                            <td>{x.dia.split('-').reverse().join('/')}</td>
                            <td>{x.quantidade}</td>
                            <td>{x.sem_preco === x.quantidade && x.quantidade > 0
                              ? <span className="selo estado-enviando">sem preço</span>
                              : <>{dinheiro(x.calculado)}{x.sem_preco > 0 && <span className="selo estado-enviando">+ {x.sem_preco} sem preço</span>}</>}</td>
                            <td>{x.cobrado === null ? '—' : dinheiro(x.cobrado, x.moeda ? [x.moeda] : null)}
                              {x.cobrado_volume !== null && <span className="leve"> · {x.cobrado_volume} msg</span>}</td>
                            <td><span className={'selo ' + cls} title={x.detalhe || ''}>{rot}</span></td>
                          </tr>)
                      })}
                    </tbody>
                  </table>
                </>
              )}
            </>
          )}
        </>
      )}
    </section>
  )
}
