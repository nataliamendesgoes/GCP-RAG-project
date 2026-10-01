'use client'

import { useState, useCallback } from 'react'
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

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [code, setCode] = useState('')
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  const reset = useCallback(() => {
    setMessages([])
    setCode('')
    setUpdatedAt(null)
    setError(null)
  }, [])

  return { messages, code, updatedAt, loading, error, submit, reset }
}
