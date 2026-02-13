/**
 * Hook para manejar el chat
 */

import { useState } from 'react'
import { api, ChatMessage, ChatRequest } from '@/lib/api'

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const sendMessage = async (prompt: string, adversaryMode: boolean = true) => {
    // Agregar mensaje del usuario
    const userMessage: ChatMessage = {
      role: 'user',
      text: prompt,
    }
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)
    setError(null)

    try {
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
