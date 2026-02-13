/**
 * Hook para manejar el chat
 * Streaming con "drip": los tokens se acumulan y se muestran a ritmo de lectura (tipo Gemini).
 */

import { useState, useRef } from 'react'
import { flushSync } from 'react-dom'
import { api, ChatMessage, ChatRequest } from '@/lib/api'

/** Cada cuántos ms actualizamos la UI con un trozo de texto */
const DRIP_INTERVAL_MS = 55
/** Máximo de caracteres a mostrar por tick (ritmo ~70 chars/s, cómodo para leer) */
const DRIP_CHARS = 4

export function useChat(stream: boolean = true) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const streamBufferRef = useRef('')
  const streamIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const streamDoneRef = useRef(false)
  const streamPendingMetaRef = useRef<{ sources?: ChatMessage['sources']; adversary_info?: ChatMessage['adversary_info'] } | null>(null)

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
        streamBufferRef.current = ''
        streamDoneRef.current = false
        streamPendingMetaRef.current = null
        if (streamIntervalRef.current) {
          clearInterval(streamIntervalRef.current)
          streamIntervalRef.current = null
        }
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
              streamBufferRef.current += ev.content
              if (streamIntervalRef.current === null) {
                streamIntervalRef.current = setInterval(() => {
                  const buf = streamBufferRef.current
                  if (!buf) {
                    if (streamDoneRef.current) {
                      if (streamIntervalRef.current) {
                        clearInterval(streamIntervalRef.current)
                        streamIntervalRef.current = null
                      }
                      const pending = streamPendingMetaRef.current
                      streamDoneRef.current = false
                      streamPendingMetaRef.current = null
                      if (pending) {
                        flushSync(() => {
                          setMessages((prev) => {
                            const next = [...prev]
                            const last = next[next.length - 1]
                            if (last?.role === 'ai') {
                              next[next.length - 1] = {
                                ...last,
                                sources: pending.sources,
                                adversary_info: pending.adversary_info,
                              }
                            }
                            return next
                          })
                        })
                      }
                    }
                    return
                  }
                  const chunk = buf.length <= DRIP_CHARS ? buf : buf.slice(0, DRIP_CHARS)
                  streamBufferRef.current = buf.slice(chunk.length)
                  flushSync(() => {
                    setMessages((prev) => {
                      const next = [...prev]
                      const last = next[next.length - 1]
                      if (last?.role === 'ai') {
                        next[next.length - 1] = { ...last, text: last.text + chunk }
                      }
                      return next
                    })
                  })
                }, DRIP_INTERVAL_MS)
              }
            } else if (ev.event === 'done') {
              const pendingMeta = {
                sources: ev.sources?.map((s) =>
                  s.type === 'notes'
                    ? `${s.filename} (p.${s.page})`
                    : s.title || s.url || ''
                ),
                adversary_info: ev.adversary_info,
              }
              const buf = streamBufferRef.current
              if (!buf) {
                // No quedaba nada por mostrar: aplicar meta (y respuesta completa solo si no hubo stream)
                if (streamIntervalRef.current) {
                  clearInterval(streamIntervalRef.current)
                  streamIntervalRef.current = null
                }
                streamDoneRef.current = false
                streamPendingMetaRef.current = null
                setMessages((prev) => {
                  const next = [...prev]
                  const last = next[next.length - 1]
                  if (last?.role === 'ai') {
                    const text = last.text.trim() ? last.text : (ev.answer ?? '')
                    next[next.length - 1] = { ...last, text, ...pendingMeta }
                  }
                  return next
                })
              } else {
                streamDoneRef.current = true
                streamPendingMetaRef.current = pendingMeta
                // El resto del buffer se sigue mostrando paso a paso; luego el interval aplicará meta.
              }
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
