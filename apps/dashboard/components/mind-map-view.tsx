'use client'

/**
 * Vista de mapa mental (grafo de conocimiento) con ReactFlow y layout dagre.
 * Permite generar un grafo desde texto y, al hacer clic en un nodo, disparar
 * un callback para "chatear" con ese concepto.
 */

import { forwardRef, useCallback, useImperativeHandle, useState, useMemo } from 'react'
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

import { api, type MindMapNode as ApiNode, type MindMapEdge as ApiEdge, type StudyPathNode } from '@/lib/api'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'

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
  /** Genera la ruta de estudio estructurada desde el texto. */
  generateStudyPath: (text: string) => Promise<void>
}

export const MindMapView = forwardRef<MindMapViewHandle, MindMapViewProps>(
  function MindMapView({ onConceptSelect, className }, ref) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  
  // Estado para la ruta de estudio
  const [studyPathNodes, setStudyPathNodes] = useState<StudyPathNode[] | null>(null)
  const [studyPathLoading, setStudyPathLoading] = useState(false)
  const [studyPathError, setStudyPathError] = useState<Error | null>(null)

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

  const generateStudyPath = useCallback(async (text: string) => {
    if (!text.trim()) return
    setStudyPathLoading(true)
    setStudyPathError(null)
    try {
      const response = await api.generateStudyPath(text.trim())
      setStudyPathNodes(response.nodes)
    } catch (err) {
      setStudyPathError(err instanceof Error ? err : new Error(String(err)))
      setStudyPathNodes(null)
    } finally {
      setStudyPathLoading(false)
    }
  }, [])

  useImperativeHandle(ref, () => ({
    generateMindmap,
    generateStudyPath,
  }), [generateMindmap, generateStudyPath])

  const onNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      const label = typeof node.data?.label === 'string' ? node.data.label : node.id
      onConceptSelect?.(node.id, label)
    },
    [onConceptSelect]
  )

  // Calcular niveles de los nodos para el árbol jerárquico
  const studyPathLevels = useMemo(() => {
    if (!studyPathNodes || studyPathNodes.length === 0) return []
    
    const nodeMap = new Map(studyPathNodes.map(n => [n.id, n]))
    const levels: StudyPathNode[][] = []
    const visited = new Set<string>()
    const inDegree = new Map<string, number>()
    
    // Inicializar inDegree
    studyPathNodes.forEach(node => {
      inDegree.set(node.id, node.prerequisites.length)
    })
    
    // BFS: empezar con nodos sin prerequisitos (nivel 0)
    let currentLevel: StudyPathNode[] = studyPathNodes.filter(n => n.prerequisites.length === 0)
    let level = 0
    
    while (currentLevel.length > 0) {
      levels.push([...currentLevel])
      currentLevel.forEach(node => visited.add(node.id))
      
      // Encontrar nodos del siguiente nivel (cuyos prerequisitos ya están visitados)
      const nextLevel: StudyPathNode[] = []
      studyPathNodes.forEach(node => {
        if (!visited.has(node.id)) {
          const allPrereqsMet = node.prerequisites.every(prereq => visited.has(prereq))
          if (allPrereqsMet) {
            nextLevel.push(node)
          }
        }
      })
      
      currentLevel = nextLevel
      level++
    }
    
    // Añadir nodos restantes (por si hay ciclos o nodos desconectados)
    studyPathNodes.forEach(node => {
      if (!visited.has(node.id)) {
        if (levels.length === 0) levels.push([])
        levels[levels.length - 1].push(node)
      }
    })
    
    return levels
  }, [studyPathNodes])

  return (
    <div className={`relative ${className ?? 'h-[500px] w-full rounded-lg border bg-card'}`} style={{ minHeight: 320 }}>
      <Tabs defaultValue="exploration" className="h-full flex flex-col">
        <TabsList className="mx-2 mt-2">
          <TabsTrigger value="exploration">Exploración libre</TabsTrigger>
          <TabsTrigger value="study-path">Ruta de estudio</TabsTrigger>
        </TabsList>
        
        <TabsContent value="exploration" className="flex-1 mt-0">
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
        </TabsContent>
        
        <TabsContent value="study-path" className="flex-1 mt-0 overflow-auto p-4">
          {studyPathLoading && (
            <div className="flex items-center justify-center h-full">
              <p className="text-sm text-muted-foreground">Generando ruta de estudio...</p>
            </div>
          )}
          {studyPathError && (
            <div className="rounded bg-destructive/90 px-3 py-2 text-sm text-destructive-foreground mb-4">
              {studyPathError.message}
            </div>
          )}
          {!studyPathLoading && !studyPathError && studyPathNodes && studyPathNodes.length > 0 && (
            <div className="space-y-6">
              {studyPathLevels.map((levelNodes, levelIndex) => (
                <div key={levelIndex} className="space-y-4">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    Nivel {levelIndex + 1}
                  </div>
                  {levelNodes.map((node) => {
                    const difficultyStars = '★'.repeat(node.difficulty) + '☆'.repeat(5 - node.difficulty)
                    return (
                      <div
                        key={node.id}
                        className="relative pl-6 border-l-2 border-border ml-2 pb-4 last:pb-0"
                      >
                        <div className="bg-card rounded-lg border p-4 shadow-sm">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <h3 className="font-semibold text-foreground mb-1">{node.label}</h3>
                              <p className="text-sm text-muted-foreground mb-2">{node.description}</p>
                              <div className="flex items-center gap-3 text-xs">
                                <span className="text-muted-foreground">Dificultad:</span>
                                <span className="text-yellow-500">{difficultyStars}</span>
                                <span className="text-muted-foreground">({node.difficulty}/5)</span>
                              </div>
                              {node.prerequisites.length > 0 && (
                                <div className="mt-2 text-xs text-muted-foreground">
                                  <span className="font-medium">Prerequisitos: </span>
                                  {node.prerequisites.map((prereqId, idx) => {
                                    const prereqNode = studyPathNodes.find(n => n.id === prereqId)
                                    return (
                                      <span key={prereqId}>
                                        {prereqNode?.label || prereqId}
                                        {idx < node.prerequisites.length - 1 && ', '}
                                      </span>
                                    )
                                  })}
                                </div>
                              )}
                            </div>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                console.log("Llamar a retriever.py para el nodo:", node.id)
                              }}
                              className="shrink-0"
                            >
                              Generar Reto Práctico
                            </Button>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
          {!studyPathLoading && !studyPathError && (!studyPathNodes || studyPathNodes.length === 0) && (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              Genera una ruta de estudio desde el texto para ver los conceptos organizados por niveles.
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
})
