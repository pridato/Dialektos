'use client'

/**
 * Vista de mapa mental (grafo de conocimiento) con ReactFlow y layout dagre.
 * Permite generar un grafo desde texto y, al hacer clic en un nodo, disparar
 * un callback para "chatear" con ese concepto.
 */

import { forwardRef, useCallback, useImperativeHandle, useState } from 'react'
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from 'reactflow'
import dagre from 'dagre'
import 'reactflow/dist/style.css'

import { api, type MindMapNode as ApiNode, type MindMapEdge as ApiEdge } from '@/lib/api'

// Dimensiones aproximadas del nodo por defecto para el layout
const NODE_WIDTH = 180
const NODE_HEIGHT = 44

function getLayoutedElements(
  apiNodes: ApiNode[],
  apiEdges: ApiEdge[],
  direction: 'TB' | 'LR' = 'TB'
): { nodes: Node[]; edges: Edge[] } {
  const isHorizontal = direction === 'LR'
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: direction })

  apiNodes.forEach((n) => {
    dagreGraph.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  })
  apiEdges.forEach((e) => {
    dagreGraph.setEdge(e.source, e.target)
  })

  dagre.layout(dagreGraph)

  const nodes: Node[] = apiNodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      id: node.id,
      type: 'default',
      data: { label: node.label },
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
      sourcePosition: isHorizontal ? 'right' : 'bottom',
      targetPosition: isHorizontal ? 'left' : 'top',
    }
  })

  const edges: Edge[] = apiEdges.map((e, i) => ({
    id: `e-${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
  }))

  return { nodes, edges }
}

export interface MindMapViewProps {
  /** Callback al hacer clic en un nodo: permite abrir/contextualizar el chat con ese concepto. */
  onConceptSelect?: (nodeId: string, label: string) => void
  /** Clase CSS para el contenedor del grafo. */
  className?: string
}

export interface MindMapViewHandle {
  /** Genera el mapa mental desde el texto y actualiza el grafo. */
  generateMindmap: (text: string) => Promise<void>
}

export const MindMapView = forwardRef<MindMapViewHandle, MindMapViewProps>(
  function MindMapView({ onConceptSelect, className }, ref) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const generateMindmap = useCallback(async (text: string) => {
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    try {
      const response = await api.generateMindmap(text.trim())
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        response.nodes,
        response.edges,
        'TB'
      )
      setNodes(layoutedNodes)
      setEdges(layoutedEdges)
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
      setNodes([])
      setEdges([])
    } finally {
      setLoading(false)
    }
  }, [setNodes, setEdges])

  useImperativeHandle(ref, () => ({
    generateMindmap,
  }), [generateMindmap])

  const onNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      const label = typeof node.data?.label === 'string' ? node.data.label : node.id
      onConceptSelect?.(node.id, label)
    },
    [onConceptSelect]
  )

  return (
    <div className={`relative ${className ?? 'h-[500px] w-full rounded-lg border bg-card'}`} style={{ minHeight: 320 }}>
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-background/80">
          <p className="text-sm text-muted-foreground">Generando mapa mental...</p>
        </div>
      )}
      {error && (
        <div className="absolute left-2 top-2 z-10 rounded bg-destructive/90 px-2 py-1 text-xs text-destructive-foreground">
          {error.message}
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
})
