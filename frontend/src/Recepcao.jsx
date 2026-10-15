// A Recepcao (#950): quem chamou no 49 3664 0121, o que escolheu e para quem foi mandado.
// #969: quem ja esta no cadastro do ERP aparece com o nome, o papel e o contato (so registro).
// #1025: a coluna QUEM linka para o WhatsApp de quem chamou -- um clique e a conversa abre no
//        WhatsApp Web de quem esta na tela. O endereco vem PRONTO do servidor, no campo `conversar`:
//        esta tela nao sabe formar endereco de WhatsApp, e e de proposito -- sem o campo nao ha link
//        (nunca um link morto), e tirar o campo do backend apaga o recurso inteiro daqui.
// Manual: docs/manuais/recepcao.md.
import React, { useEffect, useState } from 'react'
import { pegar, quando, hora } from './api.js'

// os papeis da casa em azul, os de fora em verde (maquete aprovada do #969)
const PAPEL = {
  equipe: ['Equipe', 'int'], representante: ['Representante', 'int'], cliente: ['Cliente', ''],
  produtor: ['Produtor', ''], fornecedor: ['Fornecedor', ''],
}

// o convite a conversar, so quando o servidor mandou endereco (#1025)
function Conversar({ para, className, children }) {
  if (!para) return null
  return <a className={className} href={para} target="_blank" rel="noopener noreferrer"
    title="Abrir a conversa no seu WhatsApp Web">{children}</a>
}

function Quem({ l }) {
  if (l.cadastro) {
    const c = l.cadastro
    const contato = c.contato_setor && `contato ${c.contato_setor}${c.contato_nome ? ': ' + c.contato_nome : ''}`
    return <>
      {c.nome} <span className="cod">· {c.codigo}</span>{' '}
      <Conversar para={l.conversar} className="zap">Conversar no WhatsApp</Conversar><br />
      {c.papeis.map((p) => <span key={p} className={'chip ' + (PAPEL[p] || [p, ''])[1]}>{(PAPEL[p] || [p])[0]}</span>)}
      {contato && <span className="chip">{contato}</span>}
    </>
  }
  return <>
    {/* o numero continua mascarado; quem carrega o numero inteiro e o endereco do link (#1025) */}
    {l.conversar
      ? <Conversar para={l.conversar} className="zap-num">{l.numero}</Conversar>
      : l.numero} <span className="leve">{l.perfil ? `(${l.perfil})` : ''}</span>
    {l.cadastros === 0 && <><br /><span className="chip fora">fora do cadastro</span></>}
    {l.cadastros > 1 && <><br /><span className="chip duvida">número em {l.cadastros} cadastros</span></>}
  </>
}

function Leitura({ leitura }) {
  if (!leitura) return <p className="leve">A leitura do cadastro não está ligada: ninguém é reconhecido ainda.</p>
  return <p className="leve">
    {leitura.lida_em ? <>Cadastro lido em {quando(leitura.lida_em)} ({leitura.linhas} números).</> : 'O cadastro ainda não foi lido.'}
    {leitura.erro && <span className="erro-leve"> A última leitura falhou: {leitura.erro}.</span>}
  </p>
}

const ESTADO = {
  sim: ['Sim', 'v'], nao: ['Não · você foi avisado', 'r'], perguntado: ['perguntado, sem resposta', ''],
  pergunta_marcada: ['pergunta às', ''], parou: ['parou no meio', 'a'], encerrou: ['encerrou', ''],
  em_curso: ['escolhendo agora', ''], coberta: ['já perguntado hoje, em outra conversa', ''],
  sem_pergunta: ['não perguntado (mais de 24h sem mensagem)', ''],
}

// a nota da pesquisa, em tres botoes (#969, 11/10/2026): o Ruim tambem avisa o gestor
const NOTA = { 3: ['Bom', 'v'], 2: ['Normal', ''], 1: ['Ruim · você foi avisado', 'r'] }

export default function Recepcao() {
  const [dias, setDias] = useState(7)
  const [motivo, setMotivo] = useState('')
  const [situacao, setSituacao] = useState('')
  const [quem, setQuem] = useState('')
  const [d, setD] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    const q = new URLSearchParams({ dias, motivo, situacao, quem })
    pegar('/recepcao?' + q).then(setD).catch((e) => setErro(e.message))
  }, [dias, motivo, situacao, quem])

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
        <select value={quem} onChange={(e) => setQuem(e.target.value)}>
          <option value="">Todos (cadastro e fora dele)</option><option value="cadastro">Só quem está no cadastro</option>
          <option value="fora">Só quem não está</option>
        </select>
      </div>
      {erro && <p className="aviso erro">{erro}</p>}
      {d && (
        <>
          <div className="grupo">No período escolhido</div>
          <div className="cartoes">
            <div className="cartao"><span>Chegaram</span><b>{d.cartoes.chegaram}</b></div>
            <div className="cartao"><span>Do nosso cadastro</span><b>{d.cartoes.do_cadastro}</b></div>
            <div className="cartao"><span>Receberam o link</span><b>{d.cartoes.receberam_link}</b></div>
            <div className="cartao alerta"><span>Pararam no meio</span><b>{d.cartoes.pararam_no_meio}</b></div>
            <div className="cartao"><span>Disseram que foram atendidos</span><b>{d.cartoes.disseram_sim}</b></div>
            <div className="cartao alerta"><span>Disseram que não</span><b>{d.cartoes.disseram_nao}</b></div>
            <div className="cartao"><span>IA acertou / errou</span><b>{d.cartoes.ia_acertou} / {d.cartoes.ia_errou}</b></div>
            {d.cartoes.campo > 0 && <div className="cartao"><span>Fotos do campo (equipe)</span><b>{d.cartoes.campo}{d.cartoes.campo_catalogadas ? ` · ${d.cartoes.campo_catalogadas} no catálogo` : ''}</b></div>}
          </div>
          <Leitura leitura={d.leitura} />
          <table className="tabela">
            <thead><tr><th>Quando</th><th>Quem</th><th>Caminho</th><th>Mandado para</th><th>Recebeu o atendimento?</th></tr></thead>
            <tbody>
              {d.linhas.length === 0 && <tr><td colSpan={5} className="vazio">Ninguém chamou neste período.</td></tr>}
              {d.linhas.map((l, i) => (
                <tr key={i}>
                  <td>{quando(l.quando)}</td>
                  <td><Quem l={l} /></td>
                  <td>{l.caminho.join(' › ') || <span className="leve">— só chegou</span>}{l.ia === true && <span className="leve"> · IA acertou</span>}</td>
                  <td>{l.destino || <span className="leve">—</span>}</td>
                  <td><span className={'selo ' + ESTADO[l.estado][1]}>
                    {ESTADO[l.estado][0]}{l.estado === 'pergunta_marcada' ? ' ' + hora(l.pergunta_em) : ''}
                    {l.estado === 'nao' && l.aviso_nao_em ? ' ' + hora(l.aviso_nao_em) : ''}</span>
                    {NOTA[l.satisfacao] && <> <span className={'selo ' + NOTA[l.satisfacao][1]}>{NOTA[l.satisfacao][0]}</span></>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
