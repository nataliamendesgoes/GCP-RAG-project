'use client'

import { Fragment } from 'react'

// Realce de sintaxe Python mínimo, com as cores do painel (ver .tok-* em globals.css)
const KEYWORDS = new Set([
  'from', 'import', 'class', 'def', 'return', 'if', 'elif', 'else', 'for', 'while',
  'in', 'not', 'and', 'or', 'is', 'None', 'True', 'False', 'pass', 'break',
  'continue', 'with', 'as', 'try', 'except', 'finally', 'raise', 'lambda', 'yield',
  'global', 'self',
])
const MASPY = new Set([
  'Agent', 'Environment', 'Channel', 'Admin', 'Belief', 'Goal', 'Percept', 'Plan',
  'Any', 'gain', 'lose', 'test', 'tell', 'untell', 'achieve', 'unachieve', 'askOne',
  'askOneReply', 'askAll', 'tellHow', 'untellHow', 'askHow', 'pl',
])

const TOKEN =
  /(#.*$)|("""[\s\S]*?"""|'''[\s\S]*?'''|f?"(?:\\.|[^"\\])*"|f?'(?:\\.|[^'\\])*')|(@\w+)|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_]\w*\b)/gm

type Tok = { text: string; cls?: string }

function tokenizeLine(line: string): Tok[] {
  const out: Tok[] = []
  let last = 0
  let prevWord = ''
  for (const m of line.matchAll(TOKEN)) {
    const i = m.index ?? 0
    if (i > last) out.push({ text: line.slice(last, i) })
    const [text, comment, str, deco, num, word] = m
    let cls: string | undefined
    if (comment) cls = 'tok-comment'
    else if (str) cls = 'tok-string'
    else if (deco) cls = 'tok-deco'
    else if (num) cls = 'tok-number'
    else if (word) {
      if (prevWord === 'class' || prevWord === 'def') cls = 'tok-def'
      else if (KEYWORDS.has(word)) cls = 'tok-keyword'
      else if (MASPY.has(word)) cls = 'tok-maspy'
      prevWord = word
    }
    out.push({ text, cls })
    last = i + text.length
  }
  if (last < line.length) out.push({ text: line.slice(last) })
  return out
}

export function CodeView({ code }: { code: string }) {
  const lines = code.split('\n')
  return (
    <pre className="code-view" aria-label="Código MASPy gerado">
      {lines.map((line, n) => (
        <div className="code-line" key={n}>
          <span className="code-ln" aria-hidden="true">{n + 1}</span>
          <code>
            {line === '' ? '\u00a0' : tokenizeLine(line).map((t, i) => (
              <Fragment key={i}>{t.cls ? <span className={t.cls}>{t.text}</span> : t.text}</Fragment>
            ))}
          </code>
        </div>
      ))}
    </pre>
  )
}
