'use client'

import { useState, useEffect } from 'react'
import { Menu, Home, MessageSquare, Activity, BarChart3, User, Settings, TrendingUp, TrendingDown, Brain, Battery, Moon, Heart, Zap, Target } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { LineChart, Line, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useICD } from '@/hooks/use-icd'
import { useTodayBiometrics, useRecentBiometrics } from '@/hooks/use-biometrics'
import { useChat } from '@/hooks/use-chat'
import { api } from '@/lib/api'

type View = 'dashboard' | 'chat' | 'biotracker' | 'analytics'

export default function Page() {
  const [currentView, setCurrentView] = useState<View>('dashboard')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [socraticMode, setSocraticMode] = useState(true)
  const [chatInput, setChatInput] = useState('')
  const [studyStreak, setStudyStreak] = useState<string[]>([])
  
  // Hooks para datos reales
  const { icd, loading: icdLoading } = useICD()
  const { biometrics: todayBiometrics, loading: bioLoading } = useTodayBiometrics()
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
  
  // Biometrics con valores por defecto
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

  const [bioData, setBioData] = useState({
    energia: todayBiometrics?.energy_level ?? 5,
    claridad: todayBiometrics?.mental_clarity ?? 5,
    motivacion: 5,
    dolor: 3,
    animo: 'neutral',
    notas: ''
  })
  const [saving, setSaving] = useState(false)

  const chatMessages = [
    { role: 'user', text: '¿Cuáles son los supuestos de la regresión lineal?' },
    { role: 'ai', text: 'Los supuestos fundamentales de la regresión lineal son: 1) Linealidad, 2) Independencia de errores, 3) Homocedasticidad, 4) Normalidad de residuos. Te recomiendo revisar el teorema de Gauss-Markov para entender por qué estos supuestos son importantes.', sources: ['Introducción a la Regresión Lineal (p. 45)', 'Estadística Aplicada (p. 112)'] }
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

  const NavLinks = ({ mobile = false }: { mobile?: boolean }) => (
    <nav className={`flex ${mobile ? 'flex-col' : 'flex-col'} gap-1`}>
      <Button
        variant={currentView === 'dashboard' ? 'secondary' : 'ghost'}
        className="justify-start"
        onClick={() => {
          setCurrentView('dashboard')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <Home className="mr-2 h-4 w-4" />
        Inicio
      </Button>
      <Button
        variant={currentView === 'chat' ? 'secondary' : 'ghost'}
        className="justify-start"
        onClick={() => {
          setCurrentView('chat')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <MessageSquare className="mr-2 h-4 w-4" />
        Chat Socrático
      </Button>
      <Button
        variant={currentView === 'biotracker' ? 'secondary' : 'ghost'}
        className="justify-start"
        onClick={() => {
          setCurrentView('biotracker')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <Activity className="mr-2 h-4 w-4" />
        Bio-Tracker
      </Button>
      <Button
        variant={currentView === 'analytics' ? 'secondary' : 'ghost'}
        className="justify-start"
        onClick={() => {
          setCurrentView('analytics')
          if (mobile) setMobileMenuOpen(false)
        }}
      >
        <BarChart3 className="mr-2 h-4 w-4" />
        Analíticas
      </Button>
    </nav>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex w-64 flex-col border-r border-border bg-card">
        <div className="p-6 border-b border-border">
          <h1 className="text-2xl font-bold text-foreground">Dialektos</h1>
          <p className="text-sm text-muted-foreground mt-1">Sistema RAG Adaptativo</p>
        </div>
        <div className="p-4 border-b border-border">
          {icdLoading ? (
            <div className="text-sm text-muted-foreground">Cargando ICD...</div>
          ) : icdScore !== null ? (
            <div className="rounded-lg p-4" style={{ 
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
            <div className="rounded-lg p-4 bg-muted">
              <div className="text-xs text-muted-foreground mb-1">ICD Hoy</div>
              <div className="text-3xl font-bold text-muted-foreground">—</div>
              <div className="text-xs text-muted-foreground mt-2">Sin datos</div>
            </div>
          )}
        </div>
        <div className="flex-1 p-4">
          <NavLinks />
        </div>
        <div className="p-4 border-t border-border space-y-2">
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

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-card border-b border-border p-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">Dialektos</h1>
        <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0">
            <div className="p-6 border-b border-border">
              <h1 className="text-2xl font-bold">Dialektos</h1>
              <p className="text-sm text-muted-foreground mt-1">Sistema RAG Adaptativo</p>
            </div>
            <div className="p-4">
              <NavLinks mobile />
            </div>
            <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border space-y-2">
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

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto pt-16 lg:pt-0">
        <div className="p-4 lg:p-8 max-w-7xl mx-auto">
          {/* Dashboard View */}
          {currentView === 'dashboard' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold text-balance">Panel de Control</h2>
                <p className="text-muted-foreground mt-1">Tu cockpit cognitivo personalizado</p>
              </div>

              {/* ICD Hero Section */}
              {icdLoading ? (
                <Card>
                  <CardContent className="p-6 lg:p-8">
                    <div className="text-center py-8">Cargando datos del ICD...</div>
                  </CardContent>
                </Card>
              ) : icdScore !== null ? (
                <Card className="border-2" style={{ borderColor: zoneColor }}>
                  <CardContent className="p-6 lg:p-8">
                    <div className="flex flex-col lg:flex-row items-center gap-8">
                      <div className="relative">
                        <svg className="w-40 h-40 lg:w-48 lg:h-48" viewBox="0 0 200 200">
                          <circle
                            cx="100"
                            cy="100"
                            r="80"
                            fill="none"
                            stroke="hsl(var(--muted))"
                            strokeWidth="16"
                          />
                          <circle
                            cx="100"
                            cy="100"
                            r="80"
                            fill="none"
                            stroke={zoneColor}
                            strokeWidth="16"
                            strokeDasharray={`${(icdScore / 100) * 502.4} 502.4`}
                            strokeLinecap="round"
                            transform="rotate(-90 100 100)"
                          />
                          <text
                            x="100"
                            y="100"
                            textAnchor="middle"
                            dy="0.3em"
                            className="text-5xl font-bold fill-foreground"
                          >
                            {Math.round(icdScore)}
                          </text>
                        </svg>
                      </div>
                      <div className="flex-1 text-center lg:text-left">
                        <h3 className="text-2xl font-bold mb-2">Índice Cognitivo Diario (ICD)</h3>
                        <div className="flex items-center justify-center lg:justify-start gap-2 mb-4">
                          <Badge 
                            className="text-lg px-4 py-1"
                            style={{ backgroundColor: zoneColor, color: 'white' }}
                          >
                            {icd?.strategy?.emoji} Zona: {zoneLabel}
                          </Badge>
                        </div>
                        {icd?.strategy && (
                          <Card className="bg-secondary/50">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-lg">Estrategia Actual</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <p className="text-xl font-semibold text-balance">{icd.strategy.name}</p>
                              <p className="text-sm text-muted-foreground mt-2">
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
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium">VFC (lnRMSSD)</CardTitle>
                      <Heart className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold">{biometrics.hrv.value} ms</p>
                        <p className="text-xs text-muted-foreground">ln: {biometrics.hrv.ln}</p>
                      </div>
                      {biometrics.hrv.trend === 'up' ? (
                        <TrendingUp className="h-6 w-6 text-green-500" />
                      ) : (
                        <TrendingDown className="h-6 w-6 text-red-500" />
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium">Calidad de Sueño</CardTitle>
                      <Moon className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold mb-2">{biometrics.sleep}%</p>
                    <Progress value={biometrics.sleep} className="h-2" />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium">Batería Corporal</CardTitle>
                      <Battery className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold mb-2">{biometrics.battery}/100</p>
                    <Progress value={biometrics.battery} className="h-2" />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium">Estado Recuperación</CardTitle>
                      <Zap className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold">{biometrics.recovery}</p>
                  </CardContent>
                </Card>
              </div>

              {/* Study Streak */}
              <Card>
                <CardHeader>
                  <CardTitle>Racha de Estudio</CardTitle>
                  <CardDescription>Últimos 28 días</CardDescription>
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

          {/* Chat View */}
          {currentView === 'chat' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-3xl font-bold text-balance">Chat Socrático</h2>
                  <p className="text-muted-foreground mt-1">Aprende mediante preguntas guiadas</p>
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor="socratic-mode" className="text-sm">Modo Socrático</Label>
                  <Switch
                    id="socratic-mode"
                    checked={socraticMode}
                    onCheckedChange={setSocraticMode}
                  />
                </div>
              </div>

              <Card className="h-[calc(100vh-16rem)] flex flex-col">
                <ScrollArea className="flex-1 p-6">
                  <div className="space-y-4">
                    {messages.length === 0 && (
                      <div className="text-center py-12 text-muted-foreground">
                        <div className="text-4xl mb-4">💬</div>
                        <div className="text-lg mb-2">Comienza una conversación</div>
                        <div className="text-sm">Escribe tu pregunta en el campo de abajo</div>
                      </div>
                    )}
                    {messages.map((msg, idx) => (
                      <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary'} rounded-lg p-4`}>
                          <div className="flex items-start gap-2 mb-2">
                            {msg.role === 'ai' && <Brain className="h-5 w-5 mt-0.5" />}
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                          </div>
                          {msg.sources && msg.sources.length > 0 && (
                            <Accordion type="single" collapsible className="mt-3">
                              <AccordionItem value="sources" className="border-0">
                                <AccordionTrigger className="text-xs py-2">
                                  📚 Fuentes / Referencias ({msg.sources.length})
                                </AccordionTrigger>
                                <AccordionContent>
                                  <ul className="text-xs space-y-1">
                                    {msg.sources.map((source, i) => (
                                      <li key={i} className="flex items-center gap-2">
                                        <Target className="h-3 w-3" />
                                        {source}
                                      </li>
                                    ))}
                                  </ul>
                                </AccordionContent>
                              </AccordionItem>
                            </Accordion>
                          )}
                          {msg.adversary_info?.active && (
                            <div className="mt-2 text-xs text-muted-foreground">
                              🔍 Modo Socrático Activo
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="flex justify-start">
                        <div className="bg-secondary rounded-lg p-4">
                          <div className="flex items-center gap-2">
                            <Brain className="h-5 w-5 animate-pulse" />
                            <span className="text-sm text-muted-foreground">Pensando...</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </ScrollArea>
                <div className="p-4 border-t border-border">
                  <div className="flex gap-2">
                    <Input
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
                      className="flex-1"
                      disabled={chatLoading}
                    />
                    <Button 
                      onClick={() => {
                        if (chatInput.trim()) {
                          sendMessage(chatInput, socraticMode)
                          setChatInput('')
                        }
                      }}
                      disabled={chatLoading || !chatInput.trim()}
                    >
                      Enviar
                    </Button>
                    <Button variant="outline" onClick={clearMessages} disabled={chatLoading}>
                      Limpiar
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Soporta LaTeX ($$x^2$$) y bloques de código
                  </p>
                </div>
              </Card>
            </div>
          )}

          {/* Bio-Tracker View */}
          {currentView === 'biotracker' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold text-balance">Bio-Tracker</h2>
                <p className="text-muted-foreground mt-1">Registra tus datos subjetivos diarios</p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Datos Biométricos Subjetivos</CardTitle>
                  <CardDescription>Ajusta los valores según tu estado actual</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="energia" className="text-sm font-medium mb-2 block">
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
                        // Refrescar datos
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
                    {saving ? 'Guardando...' : '💾 Calcular ICD y Sincronizar Suunto'}
                  </Button>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Analytics View */}
          {currentView === 'analytics' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold text-balance">Analíticas</h2>
                <p className="text-muted-foreground mt-1">Correlaciones y patrones de rendimiento</p>
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
