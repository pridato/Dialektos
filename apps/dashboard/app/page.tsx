'use client'

import { useState, useEffect, useRef } from 'react'
import { Menu, Home, MessageSquare, Activity, BarChart3, User, Settings, TrendingUp, TrendingDown, Brain, Battery, Moon, Heart, Zap, Target, Send, Sparkles } from 'lucide-react'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LineChart, Line, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useICD } from '@/hooks/use-icd'
import { useTodayBiometrics, useRecentBiometrics } from '@/hooks/use-biometrics'
import { BiometricInputManual } from '@/components/biometric-input-manual'
import { ActiveSessionHUD } from '@/components/active-session-hud'
import { useChat } from '@/hooks/use-chat'
import { api } from '@/lib/api'
import type { StudySessionRecord } from '@/lib/session-types'

type View = 'dashboard' | 'chat' | 'biotracker' | 'analytics' | 'session'

export default function Page() {
  const [currentView, setCurrentView] = useState<View>('dashboard')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [socraticMode, setSocraticMode] = useState(true)
  const [chatInput, setChatInput] = useState('')
  const [studyStreak, setStudyStreak] = useState<string[]>([])
  
  // Hooks para datos reales
  const { icd, loading: icdLoading } = useICD()
  const { biometrics: todayBiometrics, loading: bioLoading } = useTodayBiometrics()
  const { biometrics: recentBiometrics } = useRecentBiometrics(7)
  const { messages, loading: chatLoading, sendMessage, clearMessages } = useChat()
  
  // Datos calculados
  const icdScore = icd?.icd_score ?? null
  const zoneColor = icd?.zone_color ?? 'hsl(var(--muted))'
  const zoneLabel = icd?.zone_label ?? 'Sin datos'
  
  // Cargar racha de estudio
  useEffect(() => {
    api.getStudyStreak().then((data) => {
      setStudyStreak(data.days)
    }).catch(console.error)
  }, [])

  // Precalentar backend del chat al abrir la vista para que la primera pregunta sea rápida
  useEffect(() => {
    if (currentView === 'chat') api.warmupChat()
  }, [currentView])
  
  // Sin datos de hoy: no confundir con "valores en cero"
  const hasTodayData = todayBiometrics != null && !bioLoading

  // Si no hay datos de hoy, abrir automáticamente Bio-Tracker (solo una vez por carga)
  const hasAutoOpenedBiotracker = useRef(false)
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

  const scatterData = Array.from({ length: 30 }, (_, i) => ({
    vfc: 30 + Math.random() * 40,
    foco: 3 + Math.random() * 7,
    zone: Math.random() > 0.5 ? 'flow' : Math.random() > 0.5 ? 'deep-work' : 'survival'
  }))

  const correlationData = [
    { metric: 'VFC', vfc: 1, sleep: 0.65, energy: 0.72, focus: 0.58 },
    { metric: 'Sueño', vfc: 0.65, sleep: 1, energy: 0.81, focus: 0.69 },
    { metric: 'Energía', vfc: 0.72, sleep: 0.81, energy: 1, focus: 0.88 },
    { metric: 'Foco', vfc: 0.58, sleep: 0.69, energy: 0.88, focus: 1 }
  ]

  const streakData = Array.from({ length: 28 }, (_, i) => ({
    day: i,
    studied: Math.random() > 0.3
  }))

  const navItemClass = (view: View) =>
    `justify-start transition-all duration-300 rounded-xl pl-3 ${
      currentView === view
        ? 'bg-primary/10 text-foreground font-semibold border-l-4 border-l-accent border border-border dark:border-white/10'
        : 'text-muted-foreground dark:text-slate-400 hover:text-foreground hover:bg-muted/50 dark:hover:bg-white/5'
    }`

  const NavLinks = ({ mobile = false }: { mobile?: boolean }) => (
    <nav className="flex flex-col gap-1">
      <Button
        variant="ghost"
        className={navItemClass('dashboard')}
        onClick={() => {
          setCurrentView('dashboard')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <Home className="mr-2 h-4 w-4" />
        Inicio
      </Button>
      <Button
        variant="ghost"
        className={navItemClass('chat')}
        onClick={() => {
          setCurrentView('chat')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <MessageSquare className="mr-2 h-4 w-4" />
        Chat Socrático
      </Button>
      <Button
        variant="ghost"
        className={navItemClass('biotracker')}
        onClick={() => {
          setCurrentView('biotracker')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <Activity className="mr-2 h-4 w-4" />
        Bio-Tracker
      </Button>
      <Button
        variant="ghost"
        className={navItemClass('analytics')}
        onClick={() => {
          setCurrentView('analytics')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <BarChart3 className="mr-2 h-4 w-4" />
        Analíticas
      </Button>
      <Button
        variant="ghost"
        className={navItemClass('session')}
        onClick={() => {
          setCurrentView('session')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <Target className="mr-2 h-4 w-4" />
        Sesión Focus
      </Button>
    </nav>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-background app-bg">
      {/* Desktop Sidebar — Glassmorphism + indicador activo */}
      <aside className="hidden lg:flex w-64 flex-col border-r border-border dark:border-white/10 bg-card/80 dark:bg-slate-900/50 backdrop-blur-md shadow-lg dark:shadow-blue-900/10">
        <div className="p-6 border-b border-border dark:border-white/10">
          <h1 className="text-2xl font-bold text-foreground">Dialektos</h1>
          <p className="text-sm text-muted-foreground dark:text-slate-400 mt-1 leading-relaxed">Sistema RAG Adaptativo</p>
        </div>
        <div className="p-4 border-b border-border dark:border-white/10">
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
        <div className="p-4 border-t border-border dark:border-white/10 space-y-2">
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
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-background/80 dark:bg-slate-900/50 backdrop-blur-md border-b border-border dark:border-white/10 p-4 flex items-center justify-between shadow-lg shadow-blue-900/10">
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
          {currentView === 'dashboard' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold text-balance text-foreground">Panel de Control</h2>
                <p className="text-slate-400 mt-1 leading-relaxed">Tu cockpit cognitivo personalizado</p>
              </div>

              {/* ICD Hero Section */}
              {icdLoading ? (
                <Card>
                  <CardContent className="p-6 lg:p-8">
                    <div className="text-center py-8">Cargando datos del ICD...</div>
                  </CardContent>
                </Card>
              ) : icdScore !== null ? (
                <Card className="border-2 rounded-3xl shadow-glow transition-all duration-300" style={{ borderColor: zoneColor }}>
                  <CardContent className="p-6 lg:p-8">
                    <div className="flex flex-col lg:flex-row items-center gap-8">
                      <div className="relative drop-shadow-[0_0_24px_rgba(34,197,94,0.25)]">
                        <svg className="w-40 h-40 lg:w-48 lg:h-48" viewBox="0 0 200 200">
                          <defs>
                            <linearGradient id="icdRingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                              <stop offset="0%" stopColor="hsl(142, 76%, 36%)" />
                              <stop offset="100%" stopColor="hsl(217, 91%, 60%)" />
                            </linearGradient>
                          </defs>
                          <circle
                            cx="100"
                            cy="100"
                            r="80"
                            fill="none"
                            stroke="hsl(var(--muted))"
                            strokeWidth="14"
                            className="opacity-40"
                          />
                          <circle
                            cx="100"
                            cy="100"
                            r="80"
                            fill="none"
                            stroke="url(#icdRingGradient)"
                            strokeWidth="14"
                            strokeDasharray={`${(icdScore / 100) * 502.4} 502.4`}
                            strokeLinecap="round"
                            transform="rotate(-90 100 100)"
                            className="transition-all duration-700 ease-out"
                          />
                          <text
                            x="100"
                            y="100"
                            textAnchor="middle"
                            dy="0.3em"
                            className="text-5xl font-bold fill-foreground tabular-nums"
                          >
                            {Math.round(icdScore)}
                          </text>
                        </svg>
                      </div>
                      <div className="flex-1 text-center lg:text-left">
                        <h3 className="text-2xl font-bold mb-2 leading-tight">Índice Cognitivo Diario (ICD)</h3>
                        <div className="flex items-center justify-center lg:justify-start gap-2 mb-4">
                          <Badge 
                            className="text-lg px-4 py-1"
                            style={{ backgroundColor: zoneColor, color: 'white' }}
                          >
                            {icd?.strategy?.emoji} Zona: {zoneLabel}
                          </Badge>
                        </div>
                        {icd?.strategy && (
                          <Card className="bg-secondary/50 rounded-2xl">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-lg font-semibold">Estrategia Actual</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <p className="text-xl font-semibold text-balance leading-relaxed">{icd.strategy.name}</p>
                              <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                                {icd.strategy.description}
                              </p>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="p-6 lg:p-8">
                    <div className="text-center py-8">
                      <p className="text-muted-foreground mb-4">Sin datos de ICD para hoy</p>
                      <p className="text-sm text-muted-foreground">Completa el formulario de datos fisiológicos en Bio-Tracker</p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Biometrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {!hasTodayData ? (
                  <Card className="md:col-span-2 lg:col-span-4">
                    <CardContent className="p-6 flex flex-col items-center justify-center gap-4">
                      <p className="text-muted-foreground text-center mb-0">
                        Sin datos biométricos para hoy
                      </p>
                      <Button
                        onClick={() => setCurrentView('biotracker')}
                        variant="default"
                        size="lg"
                        className="shrink-0"
                      >
                        Añadir día en Bio-Tracker
                      </Button>
                    </CardContent>
                  </Card>
                ) : (
                  <>
                    <Card className="transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/20">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm font-semibold text-foreground">VFC (lnRMSSD)</CardTitle>
                          <Heart className="h-4 w-4 text-slate-400" />
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-2xl font-bold tabular-nums">{biometrics.hrv.value} ms</p>
                            <p className="text-xs text-slate-400">ln: {biometrics.hrv.ln}</p>
                          </div>
                          {biometrics.hrv.trend === 'up' ? (
                            <TrendingUp className="h-6 w-6 text-green-500" />
                          ) : (
                            <TrendingDown className="h-6 w-6 text-red-500" />
                          )}
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/20">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm font-semibold text-foreground">Calidad de Sueño</CardTitle>
                          <Moon className="h-4 w-4 text-slate-400" />
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-2xl font-bold mb-2 tabular-nums">{biometrics.sleep}%</p>
                        <Progress value={biometrics.sleep} className="h-2" />
                      </CardContent>
                    </Card>

                    <Card className="transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/20">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm font-semibold text-foreground">Batería Corporal</CardTitle>
                          <Battery className="h-4 w-4 text-slate-400" />
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-2xl font-bold mb-2 tabular-nums">{biometrics.battery}/100</p>
                        <Progress value={biometrics.battery} className="h-2" />
                      </CardContent>
                    </Card>

                    <Card className="transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/20">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm font-semibold text-foreground">Estado Recuperación</CardTitle>
                          <Zap className="h-4 w-4 text-slate-400" />
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-2xl font-bold">{biometrics.recovery}</p>
                      </CardContent>
                    </Card>
                  </>
                )}
              </div>

              {/* Desglose de sueño (total, profundo, REM, ligero) en horas-min */}
              {hasSleepBreakdown && (
                <Card className="transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/20">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-semibold text-foreground">Desglose de sueño</CardTitle>
                      <Moon className="h-4 w-4 text-slate-400" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                      {todayBiometrics?.sleep_total_min != null && (
                        <div>
                          <p className="text-muted-foreground text-xs uppercase">Total</p>
                          <p className="font-semibold tabular-nums">{formatMinToHoursMin(todayBiometrics.sleep_total_min)}</p>
                        </div>
                      )}
                      {todayBiometrics?.deep_sleep_min != null && (
                        <div>
                          <p className="text-muted-foreground text-xs uppercase">Profundo</p>
                          <p className="font-semibold tabular-nums">{formatMinToHoursMin(todayBiometrics.deep_sleep_min)}</p>
                        </div>
                      )}
                      {todayBiometrics?.rem_sleep_min != null && (
                        <div>
                          <p className="text-muted-foreground text-xs uppercase">REM</p>
                          <p className="font-semibold tabular-nums">{formatMinToHoursMin(todayBiometrics.rem_sleep_min)}</p>
                        </div>
                      )}
                      {todayBiometrics?.light_sleep_min != null && (
                        <div>
                          <p className="text-muted-foreground text-xs uppercase">Ligero</p>
                          <p className="font-semibold tabular-nums">{formatMinToHoursMin(todayBiometrics.light_sleep_min)}</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Study Streak */}
              <Card>
                <CardHeader>
                  <CardTitle className="font-semibold">Racha de Estudio</CardTitle>
                  <CardDescription className="text-slate-400">Últimos 28 días</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-7 gap-2">
                    {Array.from({ length: 28 }, (_, i) => {
                      const dayDate = new Date()
                      dayDate.setDate(dayDate.getDate() - (27 - i))
                      const dayStr = dayDate.toISOString().split('T')[0]
                      const hasStudy = studyStreak.includes(dayStr)
                      return (
                        <div
                          key={i}
                          className="aspect-square rounded"
                          style={{
                            backgroundColor: hasStudy ? zoneColor : 'hsl(var(--muted))',
                            opacity: hasStudy ? 1 : 0.3
                          }}
                          title={dayStr}
                        />
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Chat View — estilo ChatGPT + UI Uber */}
          {currentView === 'chat' && (
            <div
              className="chat-uber flex flex-col flex-1 min-h-0 rounded-2xl overflow-hidden border border-border dark:border-white/10 backdrop-blur-md shadow-lg dark:shadow-blue-900/20 transition-all duration-300"
              style={{
                backgroundColor: 'hsl(var(--chat-bg))',
                borderColor: 'hsl(var(--chat-border))',
              }}
            >
              {/* Barra superior mínima tipo Uber */}
              <header className="flex-shrink-0 flex items-center justify-between px-4 lg:px-6 py-3 border-b border-[hsl(var(--chat-border))]">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-[hsl(var(--chat-uber-green))] flex items-center justify-center">
                    <Sparkles className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-foreground">Chat Socrático</h2>
                    <p className="text-xs text-muted-foreground">Aprende con preguntas guiadas</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor="socratic-mode" className="text-xs text-muted-foreground">Modo Socrático</Label>
                  <Switch
                    id="socratic-mode"
                    checked={socraticMode}
                    onCheckedChange={setSocraticMode}
                    className="data-[state=checked]:bg-[hsl(var(--chat-uber-green))]"
                  />
                </div>
              </header>

              {/* Área de mensajes — scroll central tipo ChatGPT */}
              <ScrollArea className="flex-1 min-h-0">
                <div className="max-w-3xl mx-auto px-4 py-6 lg:px-6 space-y-6">
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
                            className="px-4 py-2.5 rounded-full text-sm text-muted-foreground bg-[hsl(var(--chat-surface))] border border-[hsl(var(--chat-border))] hover:bg-[hsl(var(--chat-input-bg))] hover:border-border hover:text-foreground transition-all duration-300 hover:shadow-md"
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} transition-opacity duration-300`}
                    >
                      {msg.role === 'ai' && (
                        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-[hsl(var(--chat-uber-green))] flex items-center justify-center shadow-lg ring-2 ring-border dark:ring-white/10">
                          <Brain className="h-4 w-4 text-white" />
                        </div>
                      )}
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-3 transition-all duration-300 ${
                          msg.role === 'user'
                            ? 'bg-[hsl(var(--chat-uber-green))] text-white rounded-br-md shadow-lg shadow-black/20'
                            : 'bg-[hsl(var(--chat-bubble-ai))] text-foreground border border-[hsl(var(--chat-border))] rounded-bl-md backdrop-blur-sm'
                        }`}
                      >
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
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
                  ))}
                  {chatLoading && (
                    <div className="flex gap-3 justify-start">
                      <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-[hsl(var(--chat-uber-green))] flex items-center justify-center shadow-lg ring-2 ring-border dark:ring-white/10 animate-pulse">
                        <Brain className="h-4 w-4 text-white" />
                      </div>
                      <div className="rounded-2xl rounded-bl-md px-4 py-3 bg-[hsl(var(--chat-bubble-ai))] border border-[hsl(var(--chat-border))] backdrop-blur-sm">
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

              {/* Input fijo abajo tipo ChatGPT/Uber */}
              <div className="flex-shrink-0 p-4 border-t border-[hsl(var(--chat-border))] bg-[hsl(var(--chat-bg))]">
                <div className="max-w-3xl mx-auto">
                  <div
                    className="flex items-end gap-2 rounded-2xl border border-[hsl(var(--chat-border))] bg-[hsl(var(--chat-input-bg))] p-2 focus-within:border-[hsl(var(--chat-uber-green))] focus-within:ring-1 focus-within:ring-[hsl(var(--chat-uber-green))]/30 transition-all duration-300"
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
                      className="flex-shrink-0 w-10 h-10 rounded-xl bg-[hsl(var(--chat-uber-green))] hover:opacity-90 text-white"
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
                <h2 className="text-3xl font-bold text-balance text-foreground">Bio-Tracker</h2>
                <p className="text-slate-400 mt-1 leading-relaxed">Registra tus datos diarios: sueño, corazón y recursos</p>
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

          {/* Analytics View */}
          {currentView === 'analytics' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold text-balance text-foreground">Analíticas</h2>
                <p className="text-slate-400 mt-1 leading-relaxed">Correlaciones y patrones de rendimiento</p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>VFC vs. Nivel de Foco</CardTitle>
                  <CardDescription>Relación entre variabilidad de frecuencia cardíaca y capacidad de concentración</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis
                        type="number"
                        dataKey="vfc"
                        name="VFC"
                        unit=" ms"
                        stroke="hsl(var(--muted-foreground))"
                      />
                      <YAxis
                        type="number"
                        dataKey="foco"
                        name="Foco"
                        unit="/10"
                        stroke="hsl(var(--muted-foreground))"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '0.5rem'
                        }}
                      />
                      <Scatter data={scatterData}>
                        {scatterData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={
                              entry.zone === 'flow'
                                ? 'hsl(var(--flow))'
                                : entry.zone === 'deep-work'
                                ? 'hsl(var(--deep-work))'
                                : 'hsl(var(--survival))'
                            }
                          />
                        ))}
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Matriz de Correlación</CardTitle>
                  <CardDescription>Relaciones entre métricas biométricas y cognitivas</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr>
                          <th className="p-2 text-left text-sm font-medium"></th>
                          <th className="p-2 text-center text-sm font-medium">VFC</th>
                          <th className="p-2 text-center text-sm font-medium">Sueño</th>
                          <th className="p-2 text-center text-sm font-medium">Energía</th>
                          <th className="p-2 text-center text-sm font-medium">Foco</th>
                        </tr>
                      </thead>
                      <tbody>
                        {correlationData.map((row, i) => (
                          <tr key={i}>
                            <td className="p-2 text-sm font-medium">{row.metric}</td>
                            <td className="p-2">
                              <div
                                className="h-12 flex items-center justify-center text-sm font-semibold rounded"
                                style={{
                                  backgroundColor: `rgba(${row.vfc > 0.5 ? '34, 197, 94' : '239, 68, 68'}, ${Math.abs(row.vfc)})`
                                }}
                              >
                                {row.vfc.toFixed(2)}
                              </div>
                            </td>
                            <td className="p-2">
                              <div
                                className="h-12 flex items-center justify-center text-sm font-semibold rounded"
                                style={{
                                  backgroundColor: `rgba(${row.sleep > 0.5 ? '34, 197, 94' : '239, 68, 68'}, ${Math.abs(row.sleep)})`
                                }}
                              >
                                {row.sleep.toFixed(2)}
                              </div>
                            </td>
                            <td className="p-2">
                              <div
                                className="h-12 flex items-center justify-center text-sm font-semibold rounded"
                                style={{
                                  backgroundColor: `rgba(${row.energy > 0.5 ? '34, 197, 94' : '239, 68, 68'}, ${Math.abs(row.energy)})`
                                }}
                              >
                                {row.energy.toFixed(2)}
                              </div>
                            </td>
                            <td className="p-2">
                              <div
                                className="h-12 flex items-center justify-center text-sm font-semibold rounded"
                                style={{
                                  backgroundColor: `rgba(${row.focus > 0.5 ? '34, 197, 94' : '239, 68, 68'}, ${Math.abs(row.focus)})`
                                }}
                              >
                                {row.focus.toFixed(2)}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
