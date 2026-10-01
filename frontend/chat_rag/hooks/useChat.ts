'use client'

import { useState, useCallback, useEffect } from 'react'
import { perguntar } from '@/lib/api'
import { parseAnswer, diffStats } from '@/lib/maspy'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  // Presente quando a resposta atualizou o arquivo do painel
  fileChange?: { added: number; removed: number }
}

const newId = () => `${Date.now()}_${Math.random()}`

/** A API é stateless: para pedidos de alteração, o código atual vai junto na pergunta. */
function buildQuestion(text: string, code: string): string {
  if (!code) return text
  return `${text}\n\nCódigo MASPy atual (altere-o conforme o pedido e devolva o arquivo completo):\n\`\`\`python\n${code}\n\`\`\``
}

// ---------- Conversa salva no navegador (só para este visitante; some ao limpar os dados do site) ----------

const STORAGE_KEY = 'maspy-chat-v1'

interface Saved {
  messages: Message[]
  code: string
  updatedAt: string | null
}

function load(): Saved | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as Saved
    return Array.isArray(data.messages) && typeof data.code === 'string' ? data : null
  } catch {
    return null  // navegador sem localStorage (aba anônima, dados bloqueados) ou dado corrompido
  }
}

function save(data: Saved | null): void {
  try {
    if (data) localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // sem localStorage: a conversa só não sobrevive ao recarregar
  }
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [code, setCode] = useState('')
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Só salva depois de restaurar, para não sobrescrever a conversa guardada com o estado vazio inicial
  const [restored, setRestored] = useState(false)

  // Restaura depois de montar (o HTML estático é gerado sem conversa, então não dá para ler antes)
  useEffect(() => {
    const saved = load()
    if (saved) {
      setMessages(saved.messages)
      setCode(saved.code)
      setUpdatedAt(saved.updatedAt ? new Date(saved.updatedAt) : null)
    }
    setRestored(true)
  }, [])

  useEffect(() => {
    if (!restored) return
    save(messages.length || code ? { messages, code, updatedAt: updatedAt?.toISOString() ?? null } : null)
  }, [restored, messages, code, updatedAt])

  const submit = useCallback(
    async (text: string) => {
      if (!text.trim() || loading) return

      setError(null)
      setMessages(prev => [...prev, { id: newId(), role: 'user', content: text }])
      setLoading(true)

      try {
        const answer = await perguntar(buildQuestion(text, code))
        const { text: prose, program } = parseAnswer(answer)

        let fileChange: Message['fileChange']
        if (program) {
          fileChange = diffStats(code, program)
          setCode(program)
          setUpdatedAt(new Date())
        }
        setMessages(prev => [
          ...prev,
          { id: newId(), role: 'assistant', content: prose, fileChange },
        ])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro desconhecido')
      } finally {
        setLoading(false)
      }
    },
    [loading, code]
  )

  /** Nova conversa: apaga mensagens e código (também do navegador). */
  const reset = useCallback(() => {
    setMessages([])
    setCode('')
    setUpdatedAt(null)
    setError(null)
    save(null)
  }, [])

  return { messages, code, updatedAt, loading, error, submit, reset }
}
