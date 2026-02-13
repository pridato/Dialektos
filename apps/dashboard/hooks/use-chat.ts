/**
 * Hook para manejar el chat
 */

import { useState } from 'react'
import { api, ChatMessage, ChatRequest } from '@/lib/api'

export function useChat(stream: boolean = true) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

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

        const response = await api.chatStream(
          { prompt, adversary_mode: adversaryMode },
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
              setMessages((prev) => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.role === 'ai') {
                  next[next.length - 1] = { ...last, text: last.text + ev.content }
                }
                return next
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
      } else {
        const response = await api.chat({ prompt, adversary_mode: adversaryMode })
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
  }

  return { messages, loading, error, sendMessage, clearMessages }
}
