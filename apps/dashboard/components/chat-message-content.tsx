'use client'

/**
 * Renderizado enriquecido del contenido del chat:
 * - Markdown (párrafos, listas, negritas, enlaces)
 * - Matemáticas LaTeX (inline $...$ y bloque $$...$$) vía KaTeX
 * - Bloques de código con syntax highlighting (Prism)
 *
 * Pipeline: parsing (remark) → transform (remark-math, rehype-katex) → render (components).
 * Durante streaming, el contenedor usa fuente monoespaciada para reducir parpadeo
 * cuando el markdown llega incompleto.
 * El estilo del código (oneLight / oneDark) sigue el tema claro/oscuro de next-themes.
 */

import React, { useMemo } from 'react'
import { useTheme } from 'next-themes'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { Components } from 'react-markdown'
import 'katex/dist/katex.min.css'

export interface ChatMessageContentProps {
  /** Texto en Markdown (puede incluir LaTeX y bloques de código). */
  content: string
  /** Si true, aplica estilos que reducen parpadeo mientras llega el stream. */
  isStreaming?: boolean
  /** Clases CSS adicionales para el contenedor. */
  className?: string
}

/** Lenguajes soportados por Prism; si no se especifica o no está, usamos 'text'. */
const DEFAULT_LANG = 'text'

/** Estilo Prism según tema: claro → oneLight, oscuro → oneDark. */
function getPrismStyleForTheme(resolvedTheme: string | undefined): typeof oneDark {
  return resolvedTheme === 'dark' ? oneDark : oneLight
}

/** True si el contenido entre ( ) debe tratarse como math inline (LaTeX o variable(s)). */
function isInlineMathContent(content: string): boolean {
  if (/\\/.test(content)) return true
  const t = content.trim()
  return /^[a-zA-Z](_[a-zA-Z0-9]+)?(\s*,\s*[a-zA-Z](_[a-zA-Z0-9]+)?)*\s*(\.\.\.\s*[a-zA-Z](_[a-zA-Z0-9]+)?)?\s*$/.test(t)
}

/**
 * Normaliza delimitadores de matemáticas que envían algunos LLMs:
 * - [ ecuación ] → \[ ecuación \] (bloque, si contiene \ o =)
 * - ( expresión ) → \( expresión \) (inline, con paréntesis balanceados si hay anidación)
 * Así KaTeX puede renderizar aunque el modelo no use $...$ ni $$...$$.
 */
function normalizeMathDelimiters(text: string): string {
  // 1) Bloques: [ ... ] → \[ ... \] cuando el contenido parece ecuación (tiene \ o =). No tocar si ya es \[
  let out = text.replace(/(^|[^\\])\[([^\]]*)\]/g, (_, before, inner) =>
    /\\|=/.test(inner) ? `${before}\\[${inner}\\]` : `${before}[${inner}]`
  )
  // 2) Inline: ( ... ) → \( ... \) con paréntesis balanceados (para ( c \cdot (u + v) = ... ) etc.)
  const parts: string[] = []
  let i = 0
  while (i < out.length) {
    const nextOpen = out.indexOf('(', i)
    if (nextOpen === -1) {
      parts.push(out.slice(i))
      break
    }
    const beforeParen = nextOpen > 0 ? out[nextOpen - 1] : ' '
    const isMathOpen = (nextOpen === 0 || /[\s\n]/.test(beforeParen)) && beforeParen !== '\\'
    if (!isMathOpen) {
      parts.push(out.slice(i, nextOpen + 1))
      i = nextOpen + 1
      continue
    }
    let depth = 1
    let j = nextOpen + 1
    while (j < out.length && depth > 0) {
      if (out[j] === '(') depth++
      else if (out[j] === ')') depth--
      j++
    }
    if (depth !== 0) {
      parts.push(out.slice(i, nextOpen + 1))
      i = nextOpen + 1
      continue
    }
    const contentEnd = j - 1
    const content = out.slice(nextOpen + 1, contentEnd)
    parts.push(out.slice(i, nextOpen))
    if (isInlineMathContent(content)) {
      parts.push('\\(', content, '\\)')
    } else {
      parts.push('(', content, ')')
    }
    i = contentEnd + 1
  }
  return parts.join('')
}

export function ChatMessageContent({
  content,
  isStreaming = false,
  className = '',
}: ChatMessageContentProps): React.ReactElement {
  const { resolvedTheme } = useTheme()
  const prismStyle = getPrismStyleForTheme(resolvedTheme)

  const components: Components = useMemo(() => ({
    code({ inline, className: codeClassName, children }) {
      const match = /language-(\w+)/.exec(codeClassName ?? '')
      const lang = match ? match[1] : DEFAULT_LANG
      const codeString = String(children).replace(/\n$/, '')

      if (!inline && (match || codeString.includes('\n'))) {
        return (
          <SyntaxHighlighter
            style={prismStyle}
            language={lang}
            PreTag="div"
            customStyle={{
              margin: '0.5rem 0',
              borderRadius: '0.5rem',
              fontSize: '0.8125rem',
            }}
            codeTagProps={{ style: { fontFamily: 'inherit' } }}
            showLineNumbers={false}
          >
            {codeString}
          </SyntaxHighlighter>
        )
      }

      return (
        <code
          className={codeClassName}
          style={{
            backgroundColor: 'hsl(var(--muted))',
            padding: '0.15em 0.4em',
            borderRadius: '0.25rem',
            fontSize: '0.9em',
          }}
        >
          {children}
        </code>
      )
    },
    // Evitar doble wrapper <pre><div> cuando usamos SyntaxHighlighter
    pre({ children }) {
      return <>{children}</>
    },
  }), [prismStyle])

  if (!content.trim()) {
    return (
      <span className={`block text-sm leading-relaxed ${className}`}>
        <span className="inline-block w-2 h-4 bg-muted-foreground/60 animate-pulse rounded-sm" aria-hidden />
      </span>
    )
  }

  return (
    <div
      className={`
        chat-message-content text-sm leading-relaxed break-words
        ${isStreaming ? 'font-mono' : ''}
        [&_.katex]:text-inherit
        [&_.katex-display]:overflow-x-auto [&_.katex-display]:overflow-y-hidden
        ${className}
      `}
      data-streaming={isStreaming ? 'true' : undefined}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {normalizeMathDelimiters(content)}
      </ReactMarkdown>
    </div>
  )
}
