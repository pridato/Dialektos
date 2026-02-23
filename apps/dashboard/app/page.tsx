'use client'

import { useState, useEffect, useRef } from 'react'
import { Menu, MessageSquare, Activity, User, Settings, TrendingUp, TrendingDown, Brain, Battery, Moon, Heart, Zap, Target, Send, Sparkles, Network } from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import * as VisuallyHiddenPrimitive from '@radix-ui/react-visually-hidden'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useICD } from '@/hooks/use-icd'
import { useTodayBiometrics, useRecentBiometrics } from '@/hooks/use-biometrics'
import { BiometricInputManual } from '@/components/biometric-input-manual'
import { ActiveSessionHUD } from '@/components/active-session-hud'
import { useChat } from '@/hooks/use-chat'
import { api } from '@/lib/api'
import MarkdownRenderer from '@/components/markdown-renderer'
import type { StudySessionRecord } from '@/lib/session-types'
import { MindMapView, type MindMapViewHandle } from '@/components/mind-map-view'
import { toast } from 'sonner'

type View = 'chat' | 'biotracker' | 'session' | 'mindmap'

export default function Page() {
  const [currentView, setCurrentView] = useState<View>('mindmap')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [socraticMode, setSocraticMode] = useState(true)
  const [chatInput, setChatInput] = useState('')
  const [studyStreak, setStudyStreak] = useState<string[]>([])
  
  // Hooks para datos reales
  const { icd, loading: icdLoading } = useICD()
  const { biometrics: todayBiometrics, loading: bioLoading } = useTodayBiometrics()
  const { biometrics: recentBiometrics } = useRecentBiometrics(7)
  const { messages, loading: chatLoading, sendMessage, clearMessages } = useChat(true)
  
  // Datos calculados
  const icdScore = icd?.icd_score ?? null
  const zoneColor = icd?.zone_color ?? 'hsl(var(--muted))'
  const zoneLabel = icd?.zone_label ?? 'Sin datos'
  
  // Cargar racha de estudio (fallback silencioso si el backend no está disponible)
  useEffect(() => {
    api.getStudyStreak()
      .then((data) => setStudyStreak(data.days ?? []))
      .catch(() => setStudyStreak([]))
  }, [])

  // Precalentar backend del chat al abrir la vista para que la primera pregunta sea rápida
  useEffect(() => {
    if (currentView === 'chat') api.warmupChat()
  }, [currentView])

  // Scroll al final del chat cuando llegan mensajes (streaming paso a paso)
  useEffect(() => {
    chatMessagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [messages])
  
  // Sin datos de hoy: no confundir con "valores en cero"
  const hasTodayData = todayBiometrics != null && !bioLoading

  // Si no hay datos de hoy, abrir automáticamente Bio-Tracker (solo una vez por carga)
  const hasAutoOpenedBiotracker = useRef(false)
  const chatMessagesEndRef = useRef<HTMLDivElement>(null)
  const mindMapRef = useRef<MindMapViewHandle>(null)
  const [mindMapText, setMindMapText] = useState('')
  const [userLevel, setUserLevel] = useState<string>('auto')
  const [inputAreaCollapsed, setInputAreaCollapsed] = useState(false)
  useEffect(() => {
    if (bioLoading || hasAutoOpenedBiotracker.current) return
    if (!hasTodayData) {
      hasAutoOpenedBiotracker.current = true
      setCurrentView('biotracker')
    }
  }, [bioLoading, hasTodayData])

  // Biometrics con valores por defecto (solo significativos si hasTodayData)
  const biometrics = {
    hrv: {
      value: todayBiometrics?.hrv_rmssd ?? 0,
      ln: todayBiometrics?.ln_rmssd ?? 0,
      trend: 'up' as const
    },
    sleep: todayBiometrics?.sleep_quality ?? 0,
    battery: todayBiometrics?.body_resources ?? 0,
    recovery: (todayBiometrics?.body_resources ?? 0) > 70 ? 'Óptima' :
              (todayBiometrics?.body_resources ?? 0) > 50 ? 'Normal' : 'Baja'
  }

  /** Formatea minutos a "X h Y min" para el desglose de sueño en el dashboard */
  const formatMinToHoursMin = (min: number): string => {
    const h = Math.floor(min / 60)
    const m = min % 60
    if (h === 0) return `${m} min`
    if (m === 0) return `${h} h`
    return `${h} h ${m} min`
  }

  const hasSleepBreakdown =
    hasTodayData &&
    (todayBiometrics?.sleep_total_min != null ||
      todayBiometrics?.deep_sleep_min != null ||
      todayBiometrics?.rem_sleep_min != null ||
      todayBiometrics?.light_sleep_min != null)

  const [bioData, setBioData] = useState({
    energia: todayBiometrics?.energy_level ?? 5,
    claridad: todayBiometrics?.mental_clarity ?? 5,
    motivacion: 5,
    dolor: 3,
    animo: 'neutral',
    notas: ''
  })
  const [saving, setSaving] = useState(false)

  const suggestionChips = [
    '¿Cuáles son los supuestos de la regresión lineal?',
    'Explícame el teorema de Gauss-Markov',
    'Diferencia entre correlación y causalidad',
  ]

  const streakData = Array.from({ length: 28 }, (_, i) => ({
    day: i,
    studied: Math.random() > 0.3
  }))

  const navItemClass = (view: View) =>
    `w-full justify-start items-center transition-all duration-300 rounded-xl pl-3 pr-3 py-2 ${
      currentView === view
        ? 'bg-primary/10 text-foreground font-semibold border-l-4 border-l-accent border border-slate-800 dark:border-white/10'
        : 'text-muted-foreground dark:text-slate-400 hover:text-foreground hover:bg-muted/50 dark:hover:bg-white/5'
    }`

  const NavLinks = ({ mobile = false }: { mobile?: boolean }) => (
    <nav className="flex flex-col gap-1">
      <Button
        variant="ghost"
        className={navItemClass('chat')}
        onClick={() => {
          setCurrentView('chat')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <MessageSquare className="mr-2 h-4 w-4 flex-shrink-0" />
        <span className="flex-1 text-left">Chat Socrático</span>
      </Button>
      <Button
        variant="ghost"
        className={navItemClass('biotracker')}
        onClick={() => {
          setCurrentView('biotracker')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <Activity className="mr-2 h-4 w-4 flex-shrink-0" />
        <span className="flex-1 text-left">Bio-Tracker</span>
      </Button>
      <Button
        variant="ghost"
        className={navItemClass('mindmap')}
        onClick={() => {
          setCurrentView('mindmap')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <Network className="mr-2 h-4 w-4 flex-shrink-0" />
        <span className="flex-1 text-left">Mapa mental</span>
      </Button>
      <Button
        variant="ghost"
        className={navItemClass('session')}
        onClick={() => {
          setCurrentView('session')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <Target className="mr-2 h-4 w-4 flex-shrink-0" />
        <span className="flex-1 text-left">Sesión Focus</span>
      </Button>
    </nav>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-background app-bg">
      {/* Desktop Sidebar — Glassmorphism + indicador activo */}
      <aside className="hidden lg:flex w-64 flex-col border-r border-slate-800 dark:border-white/10 bg-card/80 dark:bg-slate-900/50 backdrop-blur-xl shadow-lg dark:shadow-black/20 transition-all duration-300">
        <div className="p-6 border-b border-slate-800 dark:border-white/10">
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Dialektos</h1>
          <p className="text-sm text-muted-foreground mt-1 leading-relaxed">Sistema RAG Adaptativo</p>
        </div>
        <div className="p-4 border-b border-slate-800 dark:border-white/10">
          {icdLoading ? (
            <div className="text-sm text-muted-foreground">Cargando ICD...</div>
          ) : icdScore !== null ? (
            <div className="rounded-xl p-4" style={{ 
              background: `linear-gradient(135deg, ${zoneColor}22, ${zoneColor}08)`,
              border: `1px solid ${zoneColor}44`
            }}>
              <div className="text-xs text-muted-foreground mb-1">ICD Hoy</div>
              <div className="text-3xl font-bold" style={{ color: zoneColor }}>
                {Math.round(icdScore)}
              </div>
              <div className="mt-2">
                <Badge style={{ backgroundColor: zoneColor, color: 'white' }} className="text-xs">
                  {icd?.strategy?.emoji} {zoneLabel}
                </Badge>
              </div>
            </div>
          ) : (
            <div className="rounded-xl p-4 bg-muted">
              <div className="text-xs text-muted-foreground mb-1">ICD Hoy</div>
              <div className="text-3xl font-bold text-muted-foreground">—</div>
              <div className="text-xs text-muted-foreground mt-2">Sin datos</div>
            </div>
          )}
        </div>
        <div className="flex-1 p-4">
          <NavLinks />
        </div>
        <div className="p-4 border-t border-slate-800 dark:border-white/10 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">Tema</span>
            <ThemeToggle />
          </div>
          <Button variant="ghost" className="w-full justify-start">
            <User className="mr-2 h-4 w-4" />
            Perfil
          </Button>
          <Button variant="ghost" className="w-full justify-start">
            <Settings className="mr-2 h-4 w-4" />
            Ajustes
          </Button>
        </div>
      </aside>

      {/* Mobile Header — Glassmorphism */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-background/80 dark:bg-slate-900/50 backdrop-blur-xl border-b border-slate-800 dark:border-white/10 p-4 flex items-center justify-between shadow-lg dark:shadow-black/20">
        <h1 className="text-xl font-bold">Dialektos</h1>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <Menu className="h-6 w-6" />
              </Button>
            </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0">
            <VisuallyHiddenPrimitive.Root asChild>
              <SheetTitle>Menú de navegación</SheetTitle>
            </VisuallyHiddenPrimitive.Root>
            <div className="p-6 border-b border-border">
              <h1 className="text-2xl font-bold">Dialektos</h1>
              <p className="text-sm text-muted-foreground mt-1">Sistema RAG Adaptativo</p>
            </div>
            <div className="p-4">
              <NavLinks mobile />
            </div>
            <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-muted-foreground">Tema</span>
                <ThemeToggle />
              </div>
              <Button variant="ghost" className="w-full justify-start">
                <User className="mr-2 h-4 w-4" />
                Perfil
              </Button>
              <Button variant="ghost" className="w-full justify-start">
                <Settings className="mr-2 h-4 w-4" />
                Ajustes
              </Button>
            </div>
          </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden pt-16 lg:pt-0">
        <div className="flex-1 flex flex-col min-h-0 p-4 lg:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
          {/* Dashboard View */}
          {currentView === 'session' && (
            <ActiveSessionHUD
              userId="local"
              preSessionEnergy={biometrics.battery}
              zone={zoneLabel}
              onSessionComplete={async (record: StudySessionRecord) => {
                try {
                  await api.saveStudySession({
                    start_time: record.start_time,
                    end_time: record.end_time,
                    duration_minutes: record.duration_minutes,
                    subject: record.subject,
                    task_type: record.task_type,
                    goal_description: record.goal_description,
                    distraction_count: record.distraction_count,
                    perceived_focus_score: record.perceived_focus_score,
                    perceived_difficulty: record.perceived_difficulty,
                    date_ref: record.date_ref,
                    pre_session_energy: record.pre_session_energy,
                    zone: record.zone,
                    comments: record.comments,
                  })
                } catch (e) {
                  console.error('Error guardando sesión:', e)
                }
              }}
            />
          )}
          {/* Mapa mental — texto → grafo de conceptos */}
          {currentView === 'mindmap' && (
            <div className="flex flex-col flex-1 min-h-0 h-full">
              <div className="flex-shrink-0 mb-4">
                <h2 className="text-3xl font-bold text-balance text-foreground tracking-tight">Mapa mental</h2>
                <p className="text-muted-foreground mt-1">Pega un texto (apuntes, tema) y genera un grafo de conceptos. Haz clic en un nodo para preguntar sobre ese concepto en el chat.</p>
              </div>
              
              {/* Área de entrada colapsable */}
              <Collapsible open={!inputAreaCollapsed} onOpenChange={(open) => setInputAreaCollapsed(!open)} className="flex-shrink-0 mb-4">
                <Card>
                  <CollapsibleTrigger asChild>
                    <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors rounded-t-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <CardTitle className="text-lg">Texto para analizar</CardTitle>
                          {inputAreaCollapsed && mindMapText.trim() && (
                            <CardDescription className="mt-1">
                              Texto analizado: <span className="font-medium text-foreground">{mindMapText.substring(0, 50)}{mindMapText.length > 50 ? '...' : ''}</span>
                            </CardDescription>
                          )}
                          {!inputAreaCollapsed && (
                            <CardDescription>Introduce o pega el contenido del que quieres extraer conceptos y relaciones.</CardDescription>
                          )}
                        </div>
                        {inputAreaCollapsed && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              setInputAreaCollapsed(false)
                            }}
                            className="ml-2"
                          >
                            Editar
                          </Button>
                        )}
                      </div>
                    </CardHeader>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <CardContent className="space-y-4">
                      <Textarea
                        placeholder="Pega aquí un fragmento de apuntes, un tema o un capítulo... Ej: 'redes neuronales', 'cálculo diferencial'"
                        value={mindMapText}
                        onChange={(e) => setMindMapText(e.target.value)}
                        className="min-h-[120px] resize-y"
                      />
                      <div className="flex items-end gap-2">
                        <div className="flex-1">
                          <Label htmlFor="user-level" className="text-xs text-muted-foreground mb-1 block">
                            Nivel de conocimiento (opcional)
                          </Label>
                          <Select value={userLevel} onValueChange={setUserLevel}>
                            <SelectTrigger id="user-level" className="w-full">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="auto">Auto (inferir del texto)</SelectItem>
                              <SelectItem value="principiante">Principiante</SelectItem>
                              <SelectItem value="intermedio">Intermedio</SelectItem>
                              <SelectItem value="avanzado">Avanzado</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <Button
                          onClick={async () => {
                            const level = userLevel === 'auto' ? undefined : userLevel
                            setCurrentView('mindmap')
                            await mindMapRef.current?.generateStudyPlan(mindMapText, level)
                            // Colapsar automáticamente después de generar el plan
                            setInputAreaCollapsed(true)
                          }}
                          disabled={!mindMapText.trim()}
                          className="gap-2"
                        >
                          <Target className="h-4 w-4" />
                          Generar plan de estudio
                        </Button>
                      </div>
                    </CardContent>
                  </CollapsibleContent>
                </Card>
              </Collapsible>
              
              {/* Área de resultados que se expande */}
              <div className="flex-1 min-h-0 flex flex-col">
                <MindMapView
                  ref={mindMapRef}
                  className="flex-1 min-h-[400px]"
                  onConceptSelect={(_, label) => {
                    setCurrentView('chat')
                    setChatInput(`Explica este concepto: ${label}`)
                  }}
                />
              </div>
            </div>
          )}

          {/* Chat View — estilo ChatGPT + UI Uber */}
          {currentView === 'chat' && (
            <div
              className="chat-uber flex flex-col flex-1 min-h-0 rounded-2xl overflow-hidden border border-slate-800 dark:border-white/10 backdrop-blur-xl shadow-lg dark:shadow-black/20 transition-all duration-300"
              style={{
                backgroundColor: 'hsl(var(--chat-bg))',
                borderColor: 'hsl(var(--chat-border))',
              }}
            >
              {/* Barra superior mínima tipo Uber */}
              <header className="flex-shrink-0 flex items-center justify-between px-4 lg:px-6 py-3 border-b border-[hsl(var(--chat-border))] bg-[hsl(var(--chat-bg))]/80 backdrop-blur-xl">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-[hsl(var(--chat-accent))] flex items-center justify-center shadow-lg ring-1 ring-white/10">
                    <Sparkles className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-foreground tracking-tight">Chat Socrático</h2>
                    <p className="text-xs text-muted-foreground">Aprende con preguntas guiadas</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor="socratic-mode" className="text-xs text-muted-foreground">Modo Socrático</Label>
                  <Switch
                    id="socratic-mode"
                    checked={socraticMode}
                    onCheckedChange={setSocraticMode}
                    className="data-[state=checked]:bg-[hsl(var(--chat-accent))] transition-colors duration-300"
                  />
                </div>
              </header>

              {/* Área de mensajes — scroll central tipo ChatGPT */}
              <ScrollArea className="flex-1 min-h-0">
                <div className="max-w-3xl mx-auto px-4 py-6 lg:px-6 space-y-8">
                  {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-16 lg:py-24 text-center">
                      <div className="w-14 h-14 rounded-2xl bg-[hsl(var(--chat-surface))] border border-[hsl(var(--chat-border))] flex items-center justify-center mb-5">
                        <MessageSquare className="h-7 w-7 text-muted-foreground" />
                      </div>
                      <h3 className="text-lg font-medium text-foreground mb-1">¿En qué puedo ayudarte?</h3>
                      <p className="text-sm text-muted-foreground mb-8 max-w-sm">
                        Escribe una pregunta o elige una sugerencia para empezar.
                      </p>
                      <div className="flex flex-wrap justify-center gap-2">
                        {suggestionChips.map((label, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => setChatInput(label)}
                            className="px-4 py-2.5 rounded-xl text-sm text-muted-foreground bg-[hsl(var(--chat-surface))] border border-[hsl(var(--chat-border))] hover:bg-[hsl(var(--chat-input-bg))] hover:border-[hsl(var(--chat-accent))]/40 hover:text-foreground transition-all duration-300 hover:shadow-md"
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {messages.map((msg, idx) => {
                    const isStreamingBubble = msg.role === 'ai' && idx === messages.length - 1 && chatLoading
                    return (
                    <div
                      key={idx}
                      className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} transition-opacity duration-300`}
                    >
                      {msg.role === 'ai' && (
                        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-[hsl(var(--chat-accent))] flex items-center justify-center shadow-lg ring-1 ring-white/10">
                          <Brain className="h-4 w-4 text-white" />
                        </div>
                      )}
                      <div
                        className={`max-w-[85%] rounded-2xl px-5 py-3.5 transition-all duration-300 ${isStreamingBubble ? 'min-h-[2.5rem]' : ''} ${
                          msg.role === 'user'
                            ? 'bg-[hsl(var(--chat-bubble-user))] text-white rounded-br-md shadow-lg shadow-black/15'
                            : 'bg-[hsl(var(--chat-bubble-ai))] text-foreground border border-[hsl(var(--chat-border))] rounded-bl-md backdrop-blur-sm'
                        }`}
                      >
                        <div className="w-full min-w-0">
                          <MarkdownRenderer content={msg.text} />
                        </div>
                        {msg.sources && msg.sources.length > 0 && (
                          <Accordion type="single" collapsible className="mt-3">
                            <AccordionItem value="sources" className="border-0">
                              <AccordionTrigger className="text-xs py-2 text-muted-foreground hover:text-foreground [&[data-state=open]]:text-foreground">
                                📚 Fuentes ({msg.sources.length})
                              </AccordionTrigger>
                              <AccordionContent>
                                <ul className="text-xs space-y-1 text-muted-foreground">
                                  {msg.sources.map((source, i) => (
                                    <li key={i} className="flex items-center gap-2">
                                      <Target className="h-3 w-3 flex-shrink-0" />
                                      {source}
                                    </li>
                                  ))}
                                </ul>
                              </AccordionContent>
                            </AccordionItem>
                          </Accordion>
                        )}
                        {msg.adversary_info?.active && (
                          <div className="mt-2 text-xs text-muted-foreground">🔍 Modo Socrático</div>
                        )}
                      </div>
                      {msg.role === 'user' && <div className="w-8 flex-shrink-0" />}
                    </div>
                    )
                  })}
                  <div ref={chatMessagesEndRef} />
                  {chatLoading && messages[messages.length - 1]?.role !== 'ai' && (
                    <div className="flex gap-3 justify-start">
                      <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-[hsl(var(--chat-accent))] flex items-center justify-center shadow-lg ring-1 ring-white/10 animate-pulse">
                        <Brain className="h-4 w-4 text-white" />
                      </div>
                      <div className="rounded-2xl rounded-bl-md px-5 py-3.5 bg-[hsl(var(--chat-bubble-ai))] border border-[hsl(var(--chat-border))] backdrop-blur-sm">
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span className="inline-flex gap-1">
                            <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
                            <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                            <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
                          </span>
                          Pensando...
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>

              {/* Input fijo abajo — cápsula con glassmorphism */}
              <div className="flex-shrink-0 p-4 border-t border-[hsl(var(--chat-border))] bg-[hsl(var(--chat-bg))]/80 backdrop-blur-xl">
                <div className="max-w-3xl mx-auto">
                  <div
                    className="flex items-end gap-2 rounded-2xl border border-[hsl(var(--chat-border))] bg-[hsl(var(--chat-input-bg))]/90 dark:bg-slate-900/60 backdrop-blur-xl p-2.5 focus-within:border-[hsl(var(--chat-accent))] focus-within:ring-1 focus-within:ring-[hsl(var(--chat-accent))]/30 transition-all duration-300 shadow-lg dark:shadow-black/20"
                  >
                    <Textarea
                      placeholder="Escribe tu pregunta..."
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey && chatInput.trim()) {
                          e.preventDefault()
                          sendMessage(chatInput, socraticMode)
                          setChatInput('')
                        }
                      }}
                      disabled={chatLoading}
                      rows={1}
                      className="min-h-[44px] max-h-32 resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground text-foreground"
                    />
                    <Button
                      size="icon"
                      className="flex-shrink-0 w-10 h-10 rounded-xl bg-[hsl(var(--chat-accent))] hover:bg-[hsl(var(--chat-accent))]/90 text-white transition-all duration-300"
                      onClick={() => {
                        if (chatInput.trim()) {
                          sendMessage(chatInput, socraticMode)
                          setChatInput('')
                        }
                      }}
                      disabled={chatLoading || !chatInput.trim()}
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex items-center justify-between mt-2 px-1">
                    <p className="text-xs text-muted-foreground">LaTeX y código soportados. Enter para enviar.</p>
                    <button
                      type="button"
                      onClick={() => clearMessages()}
                      disabled={chatLoading}
                      className="text-xs text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
                    >
                      Limpiar chat
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Bio-Tracker View */}
          {currentView === 'biotracker' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold text-balance text-foreground tracking-tight">Bio-Tracker</h2>
                <p className="text-muted-foreground mt-1 leading-relaxed">Registra tus datos diarios: sueño, corazón y recursos</p>
              </div>

              <Tabs defaultValue="manual" className="w-full">
                <TabsList className="grid w-full grid-cols-2 rounded-xl bg-muted/50 p-1">
                  <TabsTrigger value="manual" className="rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm">
                    Sincronización matutina
                  </TabsTrigger>
                  <TabsTrigger value="subjective" className="rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm">
                    Datos subjetivos
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="manual" className="mt-4">
                  <Card>
                    <CardContent className="pt-6">
                      <BiometricInputManual
                        recentBiometrics={recentBiometrics}
                        saving={saving}
                        onSave={async (payload) => {
                          setSaving(true)
                          try {
                            await api.saveBiometrics(payload)
                            await api.saveConfounders({ date: payload.date as string, notes: (payload.notes as string) ?? '' })
                            window.location.reload()
                          } catch (error) {
                            console.error('Error guardando datos:', error)
                            alert('Error al guardar. Ver consola.')
                          } finally {
                            setSaving(false)
                          }
                        }}
                      />
                    </CardContent>
                  </Card>
                </TabsContent>
                <TabsContent value="subjective" className="mt-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="font-semibold">Datos Biométricos Subjetivos</CardTitle>
                      <CardDescription className="text-slate-400 leading-relaxed">Ajusta los valores según tu estado actual</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="energia" className="text-sm font-medium text-foreground mb-2 block">
                            Nivel de Energía: {bioData.energia}/10
                          </Label>
                          <Slider
                            id="energia"
                            min={1}
                            max={10}
                            step={1}
                            value={[bioData.energia]}
                            onValueChange={(v) => setBioData({ ...bioData, energia: v[0] })}
                          />
                        </div>

                        <div>
                          <Label htmlFor="claridad" className="text-sm font-medium mb-2 block">
                            Claridad Mental: {bioData.claridad}/10
                          </Label>
                          <Slider
                            id="claridad"
                            min={1}
                            max={10}
                            step={1}
                            value={[bioData.claridad]}
                            onValueChange={(v) => setBioData({ ...bioData, claridad: v[0] })}
                          />
                        </div>

                        <div>
                          <Label htmlFor="motivacion" className="text-sm font-medium mb-2 block">
                            Motivación: {bioData.motivacion}/10
                          </Label>
                          <Slider
                            id="motivacion"
                            min={1}
                            max={10}
                            step={1}
                            value={[bioData.motivacion]}
                            onValueChange={(v) => setBioData({ ...bioData, motivacion: v[0] })}
                          />
                        </div>

                        <div>
                          <Label htmlFor="dolor" className="text-sm font-medium mb-2 block">
                            Dolor Muscular: {bioData.dolor}/10
                          </Label>
                          <Slider
                            id="dolor"
                            min={1}
                            max={10}
                            step={1}
                            value={[bioData.dolor]}
                            onValueChange={(v) => setBioData({ ...bioData, dolor: v[0] })}
                          />
                        </div>
                      </div>

                      <div>
                        <Label htmlFor="animo" className="text-sm font-medium mb-2 block">
                          Estado de Ánimo
                        </Label>
                        <Select value={bioData.animo} onValueChange={(v) => setBioData({ ...bioData, animo: v })}>
                          <SelectTrigger id="animo">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="enfocado">Enfocado</SelectItem>
                            <SelectItem value="ansioso">Ansioso</SelectItem>
                            <SelectItem value="cansado">Cansado</SelectItem>
                            <SelectItem value="neutral">Neutral</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label htmlFor="notas" className="text-sm font-medium mb-2 block">
                          Notas del día
                        </Label>
                        <Textarea
                          id="notas"
                          placeholder="Escribe cualquier contexto adicional sobre tu estado actual..."
                          value={bioData.notas}
                          onChange={(e) => setBioData({ ...bioData, notas: e.target.value })}
                          rows={4}
                        />
                      </div>

                      <Button
                        className="w-full"
                        size="lg"
                        onClick={async () => {
                          setSaving(true)
                          try {
                            const today = new Date().toISOString().split('T')[0]
                            await api.saveBiometrics({
                              date: today,
                              energy_level: bioData.energia,
                              mental_clarity: bioData.claridad,
                              motivation: bioData.motivacion,
                              muscle_soreness: bioData.dolor,
                              mood: bioData.animo,
                            })
                            await api.saveConfounders({
                              date: today,
                              notes: bioData.notas,
                            })
                            window.location.reload()
                          } catch (error) {
                            console.error('Error guardando datos:', error)
                            alert('Error al guardar datos. Ver consola para más detalles.')
                          } finally {
                            setSaving(false)
                          }
                        }}
                        disabled={saving}
                      >
                        {saving ? 'Guardando...' : '💾 Guardar subjetivos y calcular ICD'}
                      </Button>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          )}

        </div>
      </main>
    </div>
  )
}
