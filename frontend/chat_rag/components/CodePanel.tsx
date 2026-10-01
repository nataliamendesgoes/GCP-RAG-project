'use client'

import { useEffect, useMemo, useState } from 'react'
import { CodeView } from './CodeView'
import { agentColor, analyze, parseConsole } from '@/lib/maspy'
import { executar, type ExecResult } from '@/lib/api'

const FILE_NAME = 'maspy_system.py'
type Tab = 'console' | 'beliefs' | 'messages'

// Execução guardada junto com o código que foi rodado: se o código mudar, o resultado antigo some
type Run =
  | { code: string; state: 'running' }
  | { code: string; state: 'done'; result: ExecResult }
  | { code: string; state: 'failed'; message: string }

function timeAgo(date: Date | null, now: number): string {
  if (!date) return ''
  const s = Math.floor((now - date.getTime()) / 1000)
  if (s < 10) return 'atualizado agora'
  if (s < 60) return `atualizado há ${s}s`
  return `atualizado há ${Math.floor(s / 60)} min`
}

function statusText(r: ExecResult): { text: string; cls: string } {
  if (r.status === 'concluido') return { text: `✓ Concluído em ${r.duracao_s}s`, cls: 'ok' }
  if (r.status === 'erro') return { text: `✗ Terminou com erro em ${r.duracao_s}s`, cls: 'bad' }
  return {
    text: `⏱ Parado após ${Math.round(r.duracao_s)}s: o sistema não terminou sozinho. Chame self.stop_cycle() quando cada agente acabar o trabalho.`,
    cls: 'warn',
  }
}

export function CodePanel({ code, updatedAt }: { code: string; updatedAt: Date | null }) {
  const [tab, setTab] = useState<Tab>('console')
  const [copied, setCopied] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const [run, setRun] = useState<Run | null>(null)
  const info = useMemo(() => analyze(code), [code])

  const current = run && run.code === code ? run : null
  const running = current?.state === 'running'
  const lines = useMemo(
    () => (current?.state === 'done' ? parseConsole(current.result.saida, current.result.erro) : []),
    [current]
  )
  // Cores que o MASPY deu a cada agente na última execução (iguais às do terminal)
  const runColors = useMemo(() => {
    const m = new Map<string, string>()
    for (const l of lines) if (l.who && l.color && l.kind !== 'Admin') m.set(l.who, l.color)
    return m
  }, [lines])
  const colorOf = (name: string) => runColors.get(name) ?? agentColor(name)

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 10_000)
    return () => clearInterval(t)
  }, [])

  const copy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const download = () => {
    const url = URL.createObjectURL(new Blob([code + '\n'], { type: 'text/x-python' }))
    const a = document.createElement('a')
    a.href = url
    a.download = FILE_NAME
    a.click()
    URL.revokeObjectURL(url)
  }

  const execute = async () => {
    if (!code || running) return
    const ran = code
    setTab('console')
    setRun({ code: ran, state: 'running' })
    try {
      const result = await executar(ran)
      setRun({ code: ran, state: 'done', result })
    } catch (err) {
      setRun({ code: ran, state: 'failed', message: err instanceof Error ? err.message : 'Erro desconhecido' })
    }
  }

  const agents = info.classes.filter(c => c.kind === 'Agent').length
  const meta = running
    ? '● executando…'
    : code
      ? `● ${agents} agente${agents === 1 ? '' : 's'} definido${agents === 1 ? '' : 's'}`
      : ''

  return (
    <section className="workspace">
      <header className="code-header">
        <span className="file-title"><span className="file-dot" aria-hidden="true" />{FILE_NAME}</span>
        {updatedAt && <span className="updated">· {timeAgo(updatedAt, now)}</span>}
        <div className="code-actions">
          <button type="button" className="link-btn" onClick={copy} disabled={!code}>
            {copied ? 'Copiado' : 'Copiar'}
          </button>
          <button type="button" className="link-btn" onClick={download} disabled={!code}>
            Baixar .py
          </button>
          <button
            type="button"
            className="run-btn"
            onClick={execute}
            disabled={!code || running}
            aria-label={running ? 'Executando' : 'Executar'}
            title="Roda o programa em um servidor isolado (até 15 segundos)"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 4l14 8-14 8z" /></svg>
            {running ? 'Executando…' : 'Executar'}
          </button>
        </div>
      </header>

      <div className="code-scroll">
        {code ? (
          <CodeView code={code} />
        ) : (
          <div className="code-empty">O código gerado aparece aqui.</div>
        )}
      </div>

      <div className="console">
        <div className="console-tabs" role="tablist">
          {([
            ['console', 'Console'],
            ['beliefs', 'Crenças'],
            ['messages', 'Mensagens'],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              className={tab === id ? 'active' : ''}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
          <span className={`console-meta ${running ? 'running' : ''}`}>{meta}</span>
        </div>

        <div className="console-body" aria-live="polite">
          {!code && <p className="console-note">Nenhum código ainda.</p>}

          {code && tab === 'console' && (
            <>
              {!current && (
                <>
                  {info.classes.map(c => (
                    <div key={c.name} className="console-row">
                      <span className={`who kind-${c.kind}`} style={c.kind === 'Agent' ? { color: colorOf(c.name) } : undefined}>[{c.name}]</span>
                      <span>{c.kind === 'Agent' ? 'agente' : c.kind === 'Environment' ? 'ambiente' : 'canal'}</span>
                    </div>
                  ))}
                  <p className="console-note">Clique em Executar para rodar os agentes (até 15 segundos).</p>
                </>
              )}

              {running && (
                <p className="console-note"><span className="status-dot inline" /> Rodando os agentes…</p>
              )}

              {current?.state === 'failed' && <p className="console-status bad">{current.message}</p>}

              {current?.state === 'done' && (
                <>
                  {lines.length === 0 && <p className="console-note">O programa não imprimiu nada.</p>}
                  {lines.map((l, i) => {
                    // Igual ao terminal: a linha como o MASPY imprime, na cor que o próprio framework definiu
                    const style = l.color ? { color: l.color } : undefined
                    return (
                      <div key={i} className={`console-row line-${l.kind}`}>
                        <span className="line-text" style={style}>{l.text}</span>
                      </div>
                    )
                  })}
                  <p className={`console-status ${statusText(current.result).cls}`}>{statusText(current.result).text}</p>
                </>
              )}
            </>
          )}

          {code && tab === 'beliefs' && (
            info.beliefs.length ? info.beliefs.map((b, i) => (
              <div key={i} className="console-row">
                <span className="who" style={{ color: colorOf(b.owner) }}>[{b.owner}]</span><span>{b.text}</span>
              </div>
            )) : <p className="console-note">Nenhuma crença, objetivo ou percepção encontrada.</p>
          )}

          {code && tab === 'messages' && (
            info.messages.length ? info.messages.map((m, i) => (
              <div key={i} className="console-row">
                <span className="who" style={{ color: colorOf(m.owner) }}>[{m.owner}]</span><span>send {m.text}</span>
              </div>
            )) : <p className="console-note">Nenhum self.send() encontrado.</p>
          )}
        </div>
      </div>
    </section>
  )
}
