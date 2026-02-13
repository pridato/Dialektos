/**
 * Hook para manejar el chat
 */

import { useState, useRef } from 'react'
import { flushSync } from 'react-dom'
import { api, ChatMessage, ChatRequest } from '@/lib/api'

export function useChat(stream: boolean = true) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const sessionIdRef = useRef<string | null>(null)

  const sendMessage = async (prompt: string, adversaryMode: boolean = true) => {
    const userMessage: ChatMessage = {
      role: 'user',
      text: prompt,
    }
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)
    setError(null)

    try {
      if (stream) {
        const placeholder: ChatMessage = {
          role: 'ai',
          text: '',
          adversary_info: undefined,
        }
        setMessages((prev) => [...prev, placeholder])

        if (!sessionIdRef.current) {
          sessionIdRef.current = typeof crypto !== 'undefined' && crypto.randomUUID
            ? crypto.randomUUID()
            : `session-${Date.now()}-${Math.random().toString(36).slice(2)}`
        }
        const sessionId = sessionIdRef.current

        const response = await api.chatStream(
          { prompt, adversary_mode: adversaryMode, session_id: sessionId },
          (ev) => {
            if (ev.event === 'meta') {
              setMessages((prev) => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.role === 'ai') {
                  next[next.length - 1] = {
                    ...last,
                    sources: ev.sources?.map((s) =>
                      s.type === 'notes'
                        ? `${s.filename} (p.${s.page})`
                        : s.title || s.url || ''
                    ),
                    adversary_info: ev.adversary_info,
                  }
                }
                return next
              })
            } else if (ev.event === 'token') {
              // flushSync para que cada token pinte al instante y se vea el streaming paso a paso
              flushSync(() => {
                setMessages((prev) => {
                  const next = [...prev]
                  const last = next[next.length - 1]
                  if (last?.role === 'ai') {
                    next[next.length - 1] = { ...last, text: last.text + ev.content }
                  }
                  return next
                })
              })
            } else if (ev.event === 'done') {
              setMessages((prev) => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.role === 'ai') {
                  next[next.length - 1] = {
                    ...last,
                    text: ev.answer,
                    sources: ev.sources?.map((s) =>
                      s.type === 'notes'
                        ? `${s.filename} (p.${s.page})`
                        : s.title || s.url || ''
                    ),
                    adversary_info: ev.adversary_info,
                  }
                }
                return next
              })
            }
          }
        )

        if (response?.answer) {
          setMessages((prev) => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last?.role === 'ai' && !last.text) {
              next[next.length - 1] = { ...last, text: response.answer }
            }
            return next
          })
        }
      } else {
        if (!sessionIdRef.current) {
          sessionIdRef.current = typeof crypto !== 'undefined' && crypto.randomUUID
            ? crypto.randomUUID()
            : `session-${Date.now()}-${Math.random().toString(36).slice(2)}`
        }
        const response = await api.chat({
          prompt,
          adversary_mode: adversaryMode,
          session_id: sessionIdRef.current,
        })
        const aiMessage: ChatMessage = {
          role: 'ai',
          text: response.answer,
          sources: response.sources?.map((s) =>
            s.type === 'notes'
              ? `${s.filename} (p.${s.page})`
              : s.title || s.url || ''
          ),
          adversary_info: response.adversary_info,
        }
        setMessages((prev) => [...prev, aiMessage])
      }
    } catch (err) {
      setError(err as Error)
      const errorMessage: ChatMessage = {
        role: 'ai',
        text: `Error: ${(err as Error).message}`,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const clearMessages = () => {
    setMessages([])
    setError(null)
    sessionIdRef.current = null
  }

  return { messages, loading, error, sendMessage, clearMessages }
}
