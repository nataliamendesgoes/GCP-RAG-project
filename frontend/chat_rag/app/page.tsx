'use client'

import { useEffect, useState } from 'react'
import { ChatPanel } from '@/components/ChatPanel'
import { CodePanel } from '@/components/CodePanel'
import { useChat } from '@/hooks/useChat'
import { checkHealth } from '@/lib/api'

export default function Home() {
  const { messages, code, updatedAt, loading, error, submit } = useChat()
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    checkHealth().then(setOnline)
  }, [])

  return (
    <main className="layout">
      <ChatPanel messages={messages} loading={loading} error={error} online={online} onSubmit={submit} />
      <CodePanel code={code} updatedAt={updatedAt} />
    </main>
  )
}
