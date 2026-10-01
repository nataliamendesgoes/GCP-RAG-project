'use client'

import { useEffect, useRef, useState, KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '@/hooks/useChat'
import { MOCK } from '@/lib/api'

const SUGESTOES = [
  'Crie um vendedor e um comprador que negociam um preço. O comprador aceita qualquer valor abaixo de 50.',
  'Crie dois agentes que trocam mensagens entre si.',
  'Agente com um plano que reage a um objetivo.',
  'Como envio uma mensagem para outro agente?',
]

interface Props {
  messages: Message[]
  loading: boolean
  error: string | null
  online: boolean | null
  onSubmit: (text: string) => void
  onNewChat: () => void
}

export function ChatPanel({ messages, loading, error, online, onSubmit, onNewChat }: Props) {
  const [text, setText] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading, error])

  // Auto-resize do campo de texto
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }, [text])

  const send = (value = text) => {
    if (!value.trim() || loading) return
    onSubmit(value.trim())
    setText('')
  }

  const newChat = () => {
    if (window.confirm('Começar uma nova conversa? As mensagens e o código atual serão apagados.')) {
      onNewChat()
      setText('')
      inputRef.current?.focus()
    }
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <section className="chat">
      <header className="chat-header">
        <h1 className="logo">
          {/* Site estático: <img> simples, sem otimização do next/image */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/maspy-logo.png" alt="MASPY — Multi-Agent System for Python" width={257} height={88} />
        </h1>
        {messages.length > 0 && (
          <button type="button" className="new-chat" onClick={newChat} disabled={loading} title="Apaga a conversa e o código atual">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            Nova conversa
          </button>
        )}
        {MOCK && <span className="mock-badge" title="Respostas simuladas (lib/mock.ts), sem chamar a API">simulado</span>}
        <span
          className={`api-status ${online ? 'on' : online === false ? 'off' : ''}`}
          title={online ? 'API online' : online === false ? 'API offline' : 'Verificando API…'}
        />
      </header>

      <div className="chat-scroll">
        {messages.length === 0 && !loading && (
          <div className="empty">
            <p>Descreva o sistema multiagente que você quer criar. O código aparece no painel ao lado.</p>
            <div className="suggestions">
              {SUGESTOES.map(s => (
                <button key={s} type="button" onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map(m =>
          m.role === 'user' ? (
            <div key={m.id} className="msg-user">{m.content}</div>
          ) : (
            <div key={m.id} className="msg-assistant">
              {m.content && (
                <div className="md">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                </div>
              )}
              {m.fileChange && (
                <div className="file-card">
                  <span className="file-name">~ maspy_system.py</span>
                  <span className="file-diff">
                    <span className="add">+{m.fileChange.added}</span>{' '}
                    <span className="del">-{m.fileChange.removed}</span>
                  </span>
                </div>
              )}
            </div>
          )
        )}

        {loading && (
          <div className="status-line">
            <span className="status-dot" /> Gerando agentes…
          </div>
        )}
        {error && <div className="error-line">{error}</div>}
        <div ref={endRef} />
      </div>

      <form
        className="composer"
        onSubmit={e => {
          e.preventDefault()
          send()
        }}
      >
        <textarea
          ref={inputRef}
          rows={1}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Peça ao MASPY para criar ou alterar agentes…"
          aria-label="Mensagem"
        />
        <button type="submit" className="send" disabled={!text.trim() || loading} aria-label="Enviar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </button>
      </form>
    </section>
  )
}
