import { executarMock, perguntarMock } from './mock'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'
// NEXT_PUBLIC_API_MOCK: "1" simula chat e execução; "chat" simula só o chat (sem gastar Gemini) e executa de verdade
const MOCK_MODE = process.env.NEXT_PUBLIC_API_MOCK
export const MOCK = MOCK_MODE === '1' || MOCK_MODE === 'chat'
const MOCK_EXEC = MOCK_MODE === '1'

interface ChatResponse {
  resposta: string
}

export interface ExecResult {
  status: 'concluido' | 'erro' | 'tempo_esgotado'
  saida: string
  erro: string
  duracao_s: number
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `Erro ${res.status}`)
  }
  return (await res.json()) as T
}

export async function perguntar(pergunta: string): Promise<string> {
  if (MOCK) return perguntarMock(pergunta)
  const data = await postJson<ChatResponse>('/chat', { pergunta })
  return data.resposta
}

/** Executa o programa no runner isolado (via /api/executar). */
export async function executar(codigo: string): Promise<ExecResult> {
  if (MOCK_EXEC) return executarMock(codigo)
  return postJson<ExecResult>('/executar', { codigo })
}

export async function checkHealth(): Promise<boolean> {
  if (MOCK_EXEC) return true
  try {
    const res = await fetch(`${API_BASE}/`, { cache: 'no-store' })
    return res.ok
  } catch {
    return false
  }
}
