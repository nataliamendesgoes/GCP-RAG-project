// Utilidades para separar a resposta do LLM em texto do chat + programa MASPy,
// e extrair informações estáticas do código (agentes, crenças, mensagens).

import { lineColor, stripAnsi } from './ansi'

const CODE_BLOCK =/```(?:python|py)?\s*\n([\s\S]*?)```/g

/** Um bloco é um "programa" (vai para o painel de código) se inicia o sistema. */
function isProgram(code: string): boolean {
  return /Admin\(\)|start_system\(/.test(code) && /class\s+\w+\s*\(/.test(code)
}

export interface ParsedAnswer {
  text: string            // markdown para o chat (sem o programa)
  program: string | null  // código completo para o painel, se houver
}

export function parseAnswer(answer: string): ParsedAnswer {
  const blocks = [...answer.matchAll(CODE_BLOCK)]
  const programs = blocks.filter(b => isProgram(b[1]))
  if (programs.length === 0) return { text: answer.trim(), program: null }

  // O maior bloco que inicia o sistema vira o arquivo; os demais trechos ficam no chat
  const main = programs.reduce((a, b) => (b[1].length > a[1].length ? b : a))
  const text = answer.replace(main[0], '').replace(/\n{3,}/g, '\n\n').trim()
  return { text, program: main[1].trimEnd() }
}

/** Contagem simples de linhas adicionadas/removidas (multiconjunto de linhas). */
export function diffStats(before: string, after: string): { added: number; removed: number } {
  const count = (s: string) => {
    const m = new Map<string, number>()
    for (const l of s.split('\n')) if (l.trim()) m.set(l, (m.get(l) ?? 0) + 1)
    return m
  }
  const a = count(before)
  const b = count(after)
  let added = 0
  let removed = 0
  for (const [l, n] of b) added += Math.max(0, n - (a.get(l) ?? 0))
  for (const [l, n] of a) removed += Math.max(0, n - (b.get(l) ?? 0))
  return { added, removed }
}

export interface ClassInfo {
  name: string
  kind: 'Agent' | 'Environment' | 'Channel'
}

export interface StaticInfo {
  classes: ClassInfo[]
  beliefs: { owner: string; text: string }[]
  messages: { owner: string; text: string }[]
}

// Cores dos agentes no console escuro: cada nome sempre recebe a mesma cor
const AGENT_COLORS = ['#f2c200', '#5ec4b6', '#ff8a65', '#b39ddb', '#81c784', '#64b5f6', '#f48fb1']

export function agentColor(name: string): string {
  let h = 0
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return AGENT_COLORS[h % AGENT_COLORS.length]
}

export interface ConsoleLine {
  who: string | null  // nome do agente/ambiente/Admin, quando a linha vem de um print do MASPY
  kind: 'Agent' | 'Environment' | 'Channel' | 'Admin' | 'stdout' | 'stderr'
  text: string        // a linha exatamente como o MASPY imprime (sem os códigos de cor)
  color?: string      // cor que o próprio MASPY deu à linha (código ANSI convertido)
}

/**
 * Separa a saída do MASPY em linhas por autor. Formatos (maspy-ml):
 *   "Agent:Nome> msg", "Environment:Nome> msg", "# Admin #> msg"; o resto é print comum.
 * O console mostra a linha como o framework imprime, na cor que o próprio MASPY definiu.
 */
export function parseConsole(saida: string, erro: string): ConsoleLine[] {
  const lines: ConsoleLine[] = []
  for (const colored of saida.split('\n')) {
    const raw = stripAnsi(colored)
    if (!raw.trim()) continue
    const color = lineColor(colored)
    const admin = raw.match(/^#\s*Admin\s*#>\s?(.*)$/)
    const ent = raw.match(/^(Agent|Environment|Channel):([^>]+)>\s?(.*)$/)
    if (admin) lines.push({ who: 'Admin', kind: 'Admin', text: raw, color })
    else if (ent) lines.push({ who: ent[2], kind: ent[1] as ConsoleLine['kind'], text: raw, color })
    else lines.push({ who: null, kind: 'stdout', text: raw, color })
  }
  for (const raw of erro.split('\n')) {
    if (raw.trim()) lines.push({ who: null, kind: 'stderr', text: raw })
  }
  return lines
}

/** Análise estática (sem executar): classes, crenças e envios de mensagem por classe. */
export function analyze(code: string): StaticInfo {
  const info: StaticInfo = { classes: [], beliefs: [], messages: [] }
  let owner = '__main__'

  for (const line of code.split('\n')) {
    const cls = line.match(/^class\s+(\w+)\s*\(\s*(Agent|Environment|Channel)\s*\)/)
    if (cls) {
      owner = cls[1]
      info.classes.push({ name: cls[1], kind: cls[2] as ClassInfo['kind'] })
      continue
    }
    if (/^\S/.test(line)) owner = '__main__'

    for (const m of line.matchAll(/\b(?:Belief|Percept|Goal)\([^()]*(?:\([^()]*\)[^()]*)*\)/g)) {
      if (!/self\.send/.test(line)) info.beliefs.push({ owner, text: m[0] })
    }
    const send = line.match(/self\.send\((.*)\)\s*$/)
    if (send) info.messages.push({ owner, text: send[1] })
  }
  return info
}
