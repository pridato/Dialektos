'use client'

/**
 * Vista de mapa mental (grafo de conocimiento) con ReactFlow y layout dagre.
 * Permite generar un grafo desde texto y, al hacer clic en un nodo, disparar
 * un callback para "chatear" con ese concepto.
 */

import { forwardRef, useCallback, useImperativeHandle, useState, useMemo, useEffect } from 'react'
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  useReactFlow,
  type Node,
  type Edge,
  type NodeMouseHandler,
  Handle,
  Position,
} from 'reactflow'
import dagre from 'dagre'
import 'reactflow/dist/style.css'

import { api, type MindMapNode as ApiNode, type MindMapEdge as ApiEdge, type StudyPathNode, type StudyPlanResponse, type StudyPhase } from '@/lib/api'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Book, PlayCircle, Code, CheckCircle2, Target, Clock, ChevronDown, ChevronRight, Lock, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'
import { toast } from 'sonner'

// Dimensiones aproximadas del nodo por defecto para el layout
const NODE_WIDTH = 180
const NODE_HEIGHT = 44

// Componente de controles de zoom personalizados (debe estar dentro del contexto de ReactFlow)
function ZoomControls() {
  const { zoomIn, zoomOut, fitView } = useReactFlow()
  
  return (
    <div className="absolute top-4 right-4 z-10 flex flex-col gap-2 bg-card/90 backdrop-blur-sm border rounded-lg p-1 shadow-lg">
      <Button
        variant="outline"
        size="icon"
        onClick={() => zoomIn()}
        className="h-8 w-8"
        title="Acercar"
      >
        <ZoomIn className="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="icon"
        onClick={() => zoomOut()}
        className="h-8 w-8"
        title="Alejar"
      >
        <ZoomOut className="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="icon"
        onClick={() => fitView({ padding: 0.2, duration: 300 })}
        className="h-8 w-8"
        title="Centrar a la vista"
      >
        <Maximize2 className="h-4 w-4" />
      </Button>
    </div>
  )
}

// Componente de nodo personalizado para mostrar fases bloqueadas/desbloqueadas
function CustomPhaseNode({ data, selected }: { data: any; selected: boolean }) {
  const isLocked = data.locked === true
  const isGoal = data.goal === true
  
  return (
    <div
      className={`px-4 py-2 rounded-lg border-2 transition-all ${
        isLocked
          ? 'bg-muted/50 border-dashed border-muted-foreground/50 opacity-50 cursor-not-allowed'
          : selected
          ? 'bg-primary/10 border-primary shadow-lg'
          : 'bg-card border-border hover:border-primary/50 hover:shadow-md'
      }`}
      style={{ minWidth: NODE_WIDTH, minHeight: NODE_HEIGHT }}
    >
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div className="flex items-center gap-2">
        {isLocked && <Lock className="h-4 w-4 text-muted-foreground shrink-0" />}
        {isGoal && <Target className="h-4 w-4 text-primary shrink-0" />}
        <span className={`text-sm font-medium ${isLocked ? 'text-muted-foreground' : 'text-foreground'}`}>
          {data.label}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </div>
  )
}

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
  /** Genera un plan de estudio progresivo completo desde las bases hasta el objetivo. */
  generateStudyPlan: (text: string, userLevel?: string) => Promise<void>
}

export const MindMapView = forwardRef<MindMapViewHandle, MindMapViewProps>(
  function MindMapView({ onConceptSelect, className }, ref) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  
  // Estado para la ruta de estudio (legacy)
  const [studyPathNodes, setStudyPathNodes] = useState<StudyPathNode[] | null>(null)
  const [studyPathLoading, setStudyPathLoading] = useState(false)
  const [studyPathError, setStudyPathError] = useState<Error | null>(null)
  
  // Estado para el plan de estudio progresivo
  const [studyPlan, setStudyPlan] = useState<StudyPlanResponse | null>(null)
  const [studyPlanLoading, setStudyPlanLoading] = useState(false)
  const [studyPlanError, setStudyPlanError] = useState<Error | null>(null)
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set())
  const [completedMilestones, setCompletedMilestones] = useState<Set<string>>(new Set())

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

  // Función para determinar si una fase está bloqueada
  const isPhaseLocked = useCallback((phase: StudyPhase, completedMilestonesSet: Set<string>, plan: StudyPlanResponse): boolean => {
    if (phase.prerequisites.length === 0) return false
    return !phase.prerequisites.every(prereqId => {
      const prereqPhase = plan.phases.find(p => p.id === prereqId)
      if (!prereqPhase) return false
      // Una fase prerequisito está completa si todos sus milestones están completados
      return prereqPhase.milestones.every(m => completedMilestonesSet.has(m.id))
    })
  }, [])
  
  // Función para generar el grafo del plan de estudio con fases bloqueadas
  const generateStudyPlanGraph = useCallback(async (plan: StudyPlanResponse, completedSet?: Set<string>) => {
    const completed = completedSet || completedMilestones
    const phaseNodes: ApiNode[] = plan.phases.map(phase => ({
      id: phase.id,
      label: phase.title,
      type: isPhaseLocked(phase, completed, plan) ? 'locked' : 'unlocked'
    }))
    
    // Agregar nodo objetivo
    const goalNode: ApiNode = {
      id: 'goal',
      label: plan.goal,
      type: 'goal'
    }
    
    // Crear edges basados en prerequisitos
    const phaseEdges: ApiEdge[] = []
    plan.phases.forEach(phase => {
      if (phase.prerequisites.length === 0) {
        // Conectar fases sin prerequisitos al objetivo
        phaseEdges.push({
          source: 'goal',
          target: phase.id,
          relation: 'leads_to'
        })
      } else {
        // Conectar prerequisitos a la fase
        phase.prerequisites.forEach(prereqId => {
          phaseEdges.push({
            source: prereqId,
            target: phase.id,
            relation: 'prerequisite'
          })
        })
      }
    })
    
    // Crear nodos con estilos según estado bloqueado/desbloqueado
    const dagreGraph = new dagre.graphlib.Graph()
    dagreGraph.setDefaultEdgeLabel(() => ({}))
    dagreGraph.setGraph({ rankdir: 'TB' })
    
    const allNodes = [goalNode, ...phaseNodes]
    allNodes.forEach((n) => {
      dagreGraph.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
    })
    phaseEdges.forEach((e) => {
      dagreGraph.setEdge(e.source, e.target)
    })
    
    dagre.layout(dagreGraph)
    
    const layoutedNodes: Node[] = allNodes.map((node) => {
      const nodeWithPosition = dagreGraph.node(node.id)
      const isLocked = node.type === 'locked'
      const isGoal = node.type === 'goal'
      
      return {
        id: node.id,
        type: 'phaseNode',
        data: { 
          label: node.label,
          locked: isLocked,
          goal: isGoal
        },
        position: {
          x: nodeWithPosition.x - NODE_WIDTH / 2,
          y: nodeWithPosition.y - NODE_HEIGHT / 2,
        },
      }
    })
    
    const layoutedEdges: Edge[] = phaseEdges.map((e, i) => ({
      id: `e-${e.source}-${e.target}-${i}`,
      source: e.source,
      target: e.target,
      style: {
        stroke: 'hsl(var(--muted-foreground))',
        strokeWidth: 2,
        strokeDasharray: isPhaseLocked(
          plan.phases.find(p => p.id === e.target) || plan.phases[0],
          completed,
          plan
        ) ? '5,5' : undefined,
      },
      animated: !isPhaseLocked(
        plan.phases.find(p => p.id === e.target) || plan.phases[0],
        completed,
        plan
      ),
    }))
    
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }, [completedMilestones, isPhaseLocked, setNodes, setEdges])

  const generateStudyPlan = useCallback(async (text: string, userLevel?: string) => {
    if (!text.trim()) return
    setStudyPlanLoading(true)
    setStudyPlanError(null)
    const loadingToast = toast.loading('Generando plan de estudio...')
    try {
      const response = await api.generateStudyPlan(text.trim(), userLevel)
      setStudyPlan(response)
      // Expandir todas las fases por defecto
      setExpandedPhases(new Set(response.phases.map(p => p.id)))
      
      // Generar mapa mental dinámico con fases bloqueadas basado en prerequisitos
      await generateStudyPlanGraph(response)
      
      toast.dismiss(loadingToast)
      toast.success('Plan de estudio generado correctamente')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido'
      setStudyPlanError(err instanceof Error ? err : new Error(String(err)))
      setStudyPlan(null)
      toast.dismiss(loadingToast)
      toast.error(`Error al generar plan de estudio: ${errorMessage}`)
    } finally {
      setStudyPlanLoading(false)
    }
  }, [generateStudyPlanGraph])

  const togglePhase = useCallback((phaseId: string) => {
    setExpandedPhases(prev => {
      const next = new Set(prev)
      if (next.has(phaseId)) {
        next.delete(phaseId)
      } else {
        next.add(phaseId)
      }
      return next
    })
  }, [])

  const toggleMilestone = useCallback((milestoneId: string) => {
    setCompletedMilestones(prev => {
      const next = new Set(prev)
      if (next.has(milestoneId)) {
        next.delete(milestoneId)
      } else {
        next.add(milestoneId)
      }
      return next
    })
  }, [])
  
  // Efecto para actualizar el grafo cuando cambian los milestones completados
  useEffect(() => {
    if (studyPlan && nodes.length > 0) {
      // Solo regenerar si ya hay un grafo generado (evitar regenerar en la carga inicial)
      generateStudyPlanGraph(studyPlan, completedMilestones)
    }
  }, [completedMilestones, studyPlan, generateStudyPlanGraph, nodes.length])

  useImperativeHandle(ref, () => ({
    generateMindmap,
    generateStudyPath,
    generateStudyPlan,
  }), [generateMindmap, generateStudyPath, generateStudyPlan, generateStudyPlanGraph])

  const onNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      const isLocked = node.data?.locked === true
      if (isLocked) {
        toast.info('Esta fase está bloqueada. Completa los prerequisitos para desbloquearla.')
        return
      }
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
      <Tabs defaultValue="exploration" className="h-full flex flex-col min-h-0">
        <TabsList className="mx-2 mt-2">
          <TabsTrigger value="exploration">Exploración libre</TabsTrigger>
          <TabsTrigger value="study-path">Ruta de estudio</TabsTrigger>
        </TabsList>
        
        <TabsContent value="exploration" className="flex-1 mt-0 relative">
          {loading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-lg bg-background/80 backdrop-blur-sm">
              <div className="relative w-16 h-16 mb-4">
                <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-transparent border-t-primary rounded-full animate-spin"></div>
              </div>
              <p className="text-sm text-muted-foreground font-medium">Generando mapa mental...</p>
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
            nodeTypes={{
              phaseNode: CustomPhaseNode,
            }}
          >
            <Background />
            <Controls />
            {/* Controles de zoom personalizados dentro del contexto de ReactFlow */}
            <ZoomControls />
          </ReactFlow>
        </TabsContent>
        
        <TabsContent value="study-path" className="flex-1 mt-0 overflow-y-auto p-4 min-h-0">
          {(studyPathLoading || studyPlanLoading) && (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="relative w-16 h-16 mb-4">
                <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-transparent border-t-primary rounded-full animate-spin"></div>
              </div>
              <p className="text-sm text-muted-foreground font-medium">
                {studyPlanLoading ? 'Generando plan de estudio...' : 'Generando ruta de estudio...'}
              </p>
            </div>
          )}
          {(studyPathError || studyPlanError) && (
            <div className="rounded bg-destructive/90 px-3 py-2 text-sm text-destructive-foreground mb-4">
              {(studyPlanError || studyPathError)?.message}
            </div>
          )}
          
          {/* Vista del Plan de Estudio Progresivo */}
          {!studyPlanLoading && !studyPlanError && studyPlan && (
            <div className="space-y-6">
              {/* Header del Plan */}
              <div className="bg-gradient-to-r from-primary/10 to-primary/5 rounded-lg border p-6">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex-1">
                    <h2 className="text-2xl font-bold text-foreground mb-2">
                      Plan de Estudio: {studyPlan.goal}
                    </h2>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Target className="h-4 w-4" />
                        Nivel inferido: <span className="font-medium text-foreground capitalize">{studyPlan.inferred_level}</span>
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        {studyPlan.total_estimated_weeks.toFixed(1)} semanas ({studyPlan.total_estimated_hours.toFixed(0)} horas)
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Fases del Plan */}
              <div className="space-y-6">
                {studyPlan.phases.map((phase, phaseIndex) => {
                  const isExpanded = expandedPhases.has(phase.id)
                  const cumulativeWeeks = studyPlan.phases
                    .slice(0, phaseIndex + 1)
                    .reduce((sum, p) => sum + p.estimated_weeks, 0)
                  const cumulativeHours = studyPlan.phases
                    .slice(0, phaseIndex + 1)
                    .reduce((sum, p) => sum + p.estimated_hours, 0)
                  
                  return (
                    <div
                      key={phase.id}
                      className="relative pl-8 border-l-2 border-primary/30 ml-2"
                    >
                      {/* Línea vertical de conexión */}
                      {phaseIndex < studyPlan.phases.length - 1 && (
                        <div className="absolute left-[-2px] top-0 bottom-[-24px] w-0.5 bg-primary/20" />
                      )}
                      
                      {/* Contenido de la Fase */}
                      <div className="bg-card rounded-lg border shadow-sm">
                        {/* Header de la Fase */}
                        <button
                          onClick={() => togglePhase(phase.id)}
                          className="w-full p-4 text-left hover:bg-muted/50 transition-colors rounded-t-lg"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                {isExpanded ? (
                                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                ) : (
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                )}
                                <span className="text-xs font-semibold text-primary uppercase tracking-wide">
                                  Fase {phase.level + 1}
                                </span>
                              </div>
                              <h3 className="text-lg font-semibold text-foreground mb-1">{phase.title}</h3>
                              <p className="text-sm text-muted-foreground mb-2">{phase.description}</p>
                              <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                                <span>{phase.estimated_weeks.toFixed(1)} semanas</span>
                                <span>{phase.estimated_hours.toFixed(0)} horas</span>
                                <span>Progreso acumulado: {cumulativeWeeks.toFixed(1)} semanas ({cumulativeHours.toFixed(0)} horas)</span>
                              </div>
                            </div>
                          </div>
                        </button>

                        {/* Contenido Expandible */}
                        {isExpanded && (
                          <div className="px-4 pb-4 space-y-4 border-t">
                            {/* Conceptos */}
                            {phase.concepts.length > 0 && (
                              <div>
                                <h4 className="text-sm font-semibold text-foreground mb-2">Conceptos cubiertos:</h4>
                                <div className="flex flex-wrap gap-2">
                                  {phase.concepts.map((concept, idx) => (
                                    <span
                                      key={idx}
                                      className="px-2 py-1 text-xs bg-muted rounded-md text-muted-foreground"
                                    >
                                      {concept}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Prerequisitos */}
                            {phase.prerequisites.length > 0 && (
                              <div>
                                <h4 className="text-sm font-semibold text-foreground mb-2">Prerequisitos:</h4>
                                <div className="flex flex-wrap gap-2">
                                  {phase.prerequisites.map((prereqId) => {
                                    const prereqPhase = studyPlan.phases.find(p => p.id === prereqId)
                                    return (
                                      <span
                                        key={prereqId}
                                        className="px-2 py-1 text-xs bg-primary/10 text-primary rounded-md"
                                      >
                                        {prereqPhase?.title || prereqId}
                                      </span>
                                    )
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Acciones */}
                            {phase.actions.length > 0 && (
                              <div>
                                <h4 className="text-sm font-semibold text-foreground mb-2">Acciones a realizar:</h4>
                                <div className="space-y-2">
                                  {phase.actions.map((action) => {
                                    const actionIcons = {
                                      read: Book,
                                      practice: Code,
                                      watch: PlayCircle,
                                      project: Target,
                                      review: CheckCircle2,
                                    }
                                    const Icon = actionIcons[action.type] || Book
                                    return (
                                      <div
                                        key={action.id}
                                        className="flex items-start gap-3 p-3 bg-muted/30 rounded-md"
                                      >
                                        <Icon className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                                        <div className="flex-1 min-w-0">
                                          <p className="text-sm text-foreground">{action.description}</p>
                                          {action.resource && (
                                            <p className="text-xs text-muted-foreground mt-1">{action.resource}</p>
                                          )}
                                        </div>
                                        {action.estimated_hours && (
                                          <span className="text-xs text-muted-foreground shrink-0">
                                            {action.estimated_hours.toFixed(1)}h
                                          </span>
                                        )}
                                      </div>
                                    )
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Hitos */}
                            {phase.milestones.length > 0 && (
                              <div>
                                <h4 className="text-sm font-semibold text-foreground mb-2">Criterios de superación:</h4>
                                <div className="space-y-2">
                                  {phase.milestones.map((milestone) => {
                                    const isCompleted = completedMilestones.has(milestone.id)
                                    return (
                                      <div
                                        key={milestone.id}
                                        className="flex items-start gap-3 p-3 bg-muted/30 rounded-md"
                                      >
                                        <button
                                          onClick={() => toggleMilestone(milestone.id)}
                                          className={`mt-0.5 h-4 w-4 rounded border-2 shrink-0 transition-colors ${
                                            isCompleted
                                              ? 'bg-primary border-primary'
                                              : 'border-muted-foreground/30 hover:border-primary/50'
                                          }`}
                                        >
                                          {isCompleted && (
                                            <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                                          )}
                                        </button>
                                        <div className="flex-1 min-w-0">
                                          <p className={`text-sm ${isCompleted ? 'line-through text-muted-foreground' : 'text-foreground'}`}>
                                            {milestone.description}
                                          </p>
                                          {milestone.validation_hint && (
                                            <p className="text-xs text-muted-foreground mt-1">
                                              💡 {milestone.validation_hint}
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Botón Generar Reto Práctico */}
                            <div className="pt-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  console.log("Llamar a retriever.py para la fase:", phase.id)
                                }}
                                className="w-full"
                              >
                                <Target className="h-4 w-4 mr-2" />
                                Generar Reto Práctico para esta Fase
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Vista Legacy de Ruta de Estudio (si no hay plan) */}
          {!studyPlanLoading && !studyPlanError && !studyPlan && !studyPathLoading && !studyPathError && studyPathNodes && studyPathNodes.length > 0 && (
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

          {/* Estado vacío */}
          {!studyPlanLoading && !studyPlanError && !studyPlan && !studyPathLoading && !studyPathError && (!studyPathNodes || studyPathNodes.length === 0) && (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              Genera un plan de estudio desde el texto para ver el camino progresivo desde las bases hasta tu objetivo.
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
})
