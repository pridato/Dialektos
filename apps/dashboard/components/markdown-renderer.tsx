import React, { memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import 'katex/dist/katex.min.css'

interface MarkdownRendererProps {
  content: string
}

const MarkdownRenderer = memo(({ content }: MarkdownRendererProps) => {
  const processedContent = content
    .replace(/\\\[/g, '$$$')
    .replace(/\\\]/g, '$$$')
    .replace(/\\\(/g, '$')
    .replace(/\\\)/g, '$')

  return (
    <div className="markdown-prose text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[rehypeKatex]}
        components={{
        code({ node, inline, className, children, ...props }: any) {
          const match = /language-(\w+)/.exec(className || '')
          return !inline && match ? (
            <div className="rounded-md overflow-hidden my-4 shadow-sm border border-border/50">
              <div className="bg-slate-900 px-3 py-1 text-xs text-slate-400 border-b border-slate-700 flex justify-between">
                <span>{match[1]}</span>
              </div>
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
                customStyle={{ margin: 0, borderRadius: 0 }}
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            </div>
          ) : (
            <code className="bg-muted/50 text-red-500 dark:text-red-400 px-1.5 py-0.5 rounded-md font-mono text-[0.9em]" {...props}>
              {children}
            </code>
          )
        },
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto my-4 rounded-md border border-border">
            <table className="w-full text-sm" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => <thead className="bg-muted/50" {...props} />,
        th: ({ node, ...props }) => <th className="px-4 py-2 text-left font-medium border-b border-border" {...props} />,
        td: ({ node, ...props }) => <td className="px-4 py-2 border-b border-border last:border-0" {...props} />,
        a: ({ node, ...props }) => (
          <a className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
        ),
        ul: ({ node, ...props }) => <ul className="list-disc pl-4 space-y-1 my-2" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal pl-4 space-y-1 my-2" {...props} />,
      }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  )
})

MarkdownRenderer.displayName = 'MarkdownRenderer'
export default MarkdownRenderer
