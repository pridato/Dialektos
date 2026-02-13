'use client'

/**
 * ActiveSessionHUD: flujo completo de sesión de estudio (Setup → HUD Zen → Debrief).
 * Diseño Dark Mode minimalista (slate-950 / slate-200), sin distracciones.
 * - Timer híbrido: cuenta atrás hasta meta, luego "tiempo extra" en otro color.
 * - Anillo de progreso alrededor del timer.
 * - Botón discreto "Registrar distracción" y "Finalizar sesión" con modal de valoración.
 */

import * as React from 'react'
import {
  AlertCircle,
  Square,
  Target,
  BookOpen,
  Cpu,
  Code,
  Atom,
  type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Slider } from '@/components/ui/slider'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import type {
  SessionIntent,
  SessionDebrief,
  StudySessionRecord,
  SessionSubject,
  TaskTypeId,
} from '@/lib/session-types'
import {
  SESSION_SUBJECTS,
  TASK_TYPES,
} from '@/lib/session-types'

// ----- Constantes y helpers -----

const SUBJECT_ICONS: Record<SessionSubject, LucideIcon> = {
  Cálculo: BookOpen,
  IA: Cpu,
  Programación: Code,
  Física: Atom,
}

function formatTime(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function buildSessionRecord(
  intent: SessionIntent,
  startTime: Date,
  endTime: Date,
  distractionCount: number,
  debrief: SessionDebrief,
  userId: string,
  preSessionEnergy?: number,
  zone?: string
): StudySessionRecord {
  const durationMinutes = Math.round((endTime.getTime() - startTime.getTime()) / 60000)
  const dateRef = endTime.toISOString().slice(0, 10)
  return {
    session_id: crypto.randomUUID(),
    user_id: userId,
    start_time: startTime.toISOString(),
    end_time: endTime.toISOString(),
    duration_minutes: durationMinutes,
    subject: intent.subject,
    task_type: intent.task_type,
    goal_description: intent.goal_description,
    distraction_count: distractionCount,
    perceived_focus_score: debrief.perceived_focus_score,
    perceived_difficulty: debrief.perceived_difficulty,
    date_ref: dateRef,
    pre_session_energy: preSessionEnergy,
    zone,
    comments: debrief.comments?.trim() || undefined,
  }
}

// ----- SessionSetup: Contrato de Intención -----

interface SessionSetupProps {
  onStart: (intent: SessionIntent) => void
  defaultGoalMinutes?: number
}

function SessionSetup({ onStart, defaultGoalMinutes = 50 }: SessionSetupProps) {
  const [subject, setSubject] = React.useState<SessionSubject | ''>('')
  const [taskType, setTaskType] = React.useState<TaskTypeId | ''>('')
  const [goalDescription, setGoalDescription] = React.useState('')
  const [goalMinutes, setGoalMinutes] = React.useState(defaultGoalMinutes)

  const canStart =
    subject !== '' &&
    taskType !== '' &&
    goalDescription.trim().length > 0 &&
    goalMinutes >= 1

  const handleStart = () => {
    if (!canStart) return
    onStart({
      subject: subject as SessionSubject,
      task_type: taskType as TaskTypeId,
      goal_description: goalDescription.trim(),
      goal_minutes: goalMinutes,
    })
  }

  return (
    <div className="flex flex-col gap-6 max-w-md mx-auto text-slate-200">
      <p className="text-slate-400 text-sm">
        Define el objetivo antes de empezar. Reduce la carga cognitiva errante.
      </p>

      <div className="space-y-2">
        <Label className="text-slate-300">Asignatura</Label>
        <Select value={subject} onValueChange={(v) => setSubject(v as SessionSubject)}>
          <SelectTrigger className="bg-slate-900/80 border-slate-700 text-slate-200">
            <SelectValue placeholder="Elige asignatura" />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-slate-700">
            {SESSION_SUBJECTS.map((s) => {
              const Icon = SUBJECT_ICONS[s]
              return (
                <SelectItem key={s} value={s} className="text-slate-200 focus:bg-slate-800">
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4 opacity-70" />
                    {s}
                  </span>
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label className="text-slate-300">Tipo de tarea</Label>
        <Select value={taskType} onValueChange={(v) => setTaskType(v as TaskTypeId)}>
          <SelectTrigger className="bg-slate-900/80 border-slate-700 text-slate-200">
            <SelectValue placeholder="Categoría" />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-slate-700">
            {TASK_TYPES.map((t) => (
              <SelectItem key={t.id} value={t.id} className="text-slate-200 focus:bg-slate-800">
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label className="text-slate-300">Objetivo micro</Label>
        <Input
          placeholder="Ej: Entender Backpropagation / Resolver 3 límites"
          value={goalDescription}
          onChange={(e) => setGoalDescription(e.target.value)}
          className="bg-slate-900/80 border-slate-700 text-slate-200 placeholder:text-slate-500"
        />
      </div>

      <div className="space-y-2">
        <Label className="text-slate-300">Meta de tiempo (min)</Label>
        <Input
          type="number"
          min={1}
          max={120}
          value={goalMinutes}
          onChange={(e) => setGoalMinutes(Number(e.target.value) || 25)}
          className="bg-slate-900/80 border-slate-700 text-slate-200 w-24"
        />
      </div>

      <Button
        onClick={handleStart}
        disabled={!canStart}
        className="bg-slate-700 hover:bg-slate-600 text-slate-100 border-0"
      >
        Iniciar sesión
      </Button>
    </div>
  )
}

// ----- EndSessionModal: Debrief (Foco, Dificultad, Comentarios) -----

interface EndSessionModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (debrief: SessionDebrief) => void
}

function EndSessionModal({ open, onClose, onSubmit }: EndSessionModalProps) {
  const [focus, setFocus] = React.useState(7)
  const [difficulty, setDifficulty] = React.useState(3)
  const [comments, setComments] = React.useState('')

  const handleSubmit = () => {
    onSubmit({
      perceived_focus_score: focus,
      perceived_difficulty: difficulty,
      comments: comments.trim() || undefined,
    })
    setFocus(7)
    setDifficulty(3)
    setComments('')
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="bg-slate-900 border-slate-700 text-slate-200 max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-slate-100">Etiqueta de sesión</DialogTitle>
          <DialogDescription className="text-slate-400">
            Valoración rápida (máx. unos segundos). Ayuda al análisis posterior.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <div className="space-y-2">
            <Label className="text-slate-300">Foco percibido (1-10)</Label>
            <div className="flex items-center gap-3">
              <Slider
                value={[focus]}
                onValueChange={([v]) => setFocus(v ?? 7)}
                min={1}
                max={10}
                step={1}
                className="flex-1"
              />
              <span className="font-mono tabular-nums text-slate-200 w-6">{focus}</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Dificultad (1-5)</Label>
            <div className="flex items-center gap-3">
              <Slider
                value={[difficulty]}
                onValueChange={([v]) => setDifficulty(v ?? 3)}
                min={1}
                max={5}
                step={1}
                className="flex-1"
              />
              <span className="font-mono tabular-nums text-slate-200 w-6">{difficulty}</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Comentarios (opcional)</Label>
            <Textarea
              placeholder="Ej: Me dio sueño a los 20 min"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              className="bg-slate-800/80 border-slate-700 text-slate-200 placeholder:text-slate-500 min-h-[72px] resize-none"
              rows={2}
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="ghost" onClick={onClose} className="text-slate-400 hover:text-slate-200">
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            className="bg-slate-700 hover:bg-slate-600 text-slate-100"
          >
            Guardar y finalizar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ----- HUD: Timer + anillo + objetivo + botones -----

const TIMER_SIZE = 220
const STROKE_WIDTH = 6
const RADIUS = (TIMER_SIZE - STROKE_WIDTH) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

interface HUDViewProps {
  intent: SessionIntent
  startTime: Date
  distractionCount: number
  onDistraction: () => void
  onEndSession: () => void
}

function HUDView({
  intent,
  startTime,
  distractionCount,
  onDistraction,
  onEndSession,
}: HUDViewProps) {
  const goalSeconds = intent.goal_minutes * 60
  const [now, setNow] = React.useState(() => Date.now())

  React.useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])

  const elapsedSeconds = Math.floor((now - startTime.getTime()) / 1000)

  const inExtraTime = elapsedSeconds >= goalSeconds
  const countdownRemaining = Math.max(0, goalSeconds - elapsedSeconds)
  const extraSeconds = inExtraTime ? elapsedSeconds - goalSeconds : 0

  // Progreso del anillo: 0..1 durante countdown, 1 en extra
  const progress = Math.min(1, elapsedSeconds / goalSeconds)
  const strokeDashoffset = CIRCUMFERENCE * (1 - progress)

  const displaySeconds = inExtraTime ? extraSeconds : countdownRemaining
  const displayLabel = inExtraTime ? 'Extra' : 'Restante'

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-8 px-4">
      {/* Anillo + Timer */}
      <div className="relative" style={{ width: TIMER_SIZE, height: TIMER_SIZE }}>
        <svg
          className="rotate-[-90deg]"
          width={TIMER_SIZE}
          height={TIMER_SIZE}
          aria-hidden
        >
          <circle
            cx={TIMER_SIZE / 2}
            cy={TIMER_SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="currentColor"
            strokeWidth={STROKE_WIDTH}
            className="text-slate-800"
          />
          <circle
            cx={TIMER_SIZE / 2}
            cy={TIMER_SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="currentColor"
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={strokeDashoffset}
            className={cn(
              'transition-[stroke-dashoffset] duration-1000 ease-linear',
              inExtraTime ? 'text-amber-500/70' : 'text-slate-400'
            )}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-0">
          <span
            className={cn(
              'font-mono tabular-nums text-5xl tracking-tight',
              inExtraTime ? 'text-amber-400/90' : 'text-slate-200'
            )}
          >
            {formatTime(displaySeconds)}
          </span>
          <span className="text-xs text-slate-500 font-medium uppercase tracking-wider mt-1">
            {displayLabel}
          </span>
        </div>
      </div>

      {/* Objetivo actual */}
      <p className="text-slate-400 text-sm text-center max-w-xs">
        Estudiando: <span className="text-slate-300">{intent.subject}</span>
        <span className="text-slate-500"> · </span>
        <span className="text-slate-400 truncate block mt-0.5">{intent.goal_description}</span>
      </p>

      {/* Acciones: Distracción + Finalizar */}
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onDistraction}
          className={cn(
            'flex items-center justify-center w-12 h-12 rounded-full border border-slate-700/80',
            'text-slate-500 hover:text-slate-300 hover:border-slate-600',
            'transition-colors duration-200',
            'animate-pulse'
          )}
          aria-label="Registrar distracción"
        >
          <AlertCircle className="h-5 w-5" strokeWidth={1.5} />
        </button>
        {distractionCount > 0 && (
          <span className="font-mono text-xs text-slate-500 tabular-nums">
            {distractionCount}
          </span>
        )}

        <Button
          variant="outline"
          onClick={onEndSession}
          className="border-slate-600 text-slate-300 hover:bg-slate-800 hover:text-slate-100"
        >
          <Square className="h-4 w-4 mr-2" />
          Finalizar sesión
        </Button>
      </div>
    </div>
  )
}

// ----- Contenedor principal: ActiveSessionHUD -----

export interface ActiveSessionHUDProps {
  /** Tras guardar el debrief se entrega el registro listo para persistir */
  onSessionComplete?: (record: StudySessionRecord) => void
  /** Energía pre-sesión (ej. de "Batería Corporal") para el snapshot */
  preSessionEnergy?: number
  /** Zona calculada (ej. Flow) para el snapshot */
  zone?: string
  /** ID de usuario para el registro */
  userId?: string
}

export function ActiveSessionHUD({
  onSessionComplete,
  preSessionEnergy,
  zone,
  userId = 'local',
}: ActiveSessionHUDProps) {
  const [intent, setIntent] = React.useState<SessionIntent | null>(null)
  const [startTime, setStartTime] = React.useState<Date | null>(null)
  const [distractionCount, setDistractionCount] = React.useState(0)
  const [debriefOpen, setDebriefOpen] = React.useState(false)

  const handleStart = React.useCallback((newIntent: SessionIntent) => {
    setIntent(newIntent)
    setStartTime(new Date())
    setDistractionCount(0)
  }, [])

  const handleEndSession = React.useCallback(() => {
    setDebriefOpen(true)
  }, [])

  const handleDebriefSubmit = React.useCallback(
    (debrief: SessionDebrief) => {
      if (!intent || !startTime) return
      const endTime = new Date()
      const record = buildSessionRecord(
        intent,
        startTime,
        endTime,
        distractionCount,
        debrief,
        userId,
        preSessionEnergy,
        zone
      )
      onSessionComplete?.(record)
      setIntent(null)
      setStartTime(null)
      setDistractionCount(0)
      setDebriefOpen(false)
    },
    [intent, startTime, distractionCount, userId, preSessionEnergy, zone, onSessionComplete]
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col items-center justify-center p-6">
      {!intent ? (
        <SessionSetup onStart={handleStart} defaultGoalMinutes={50} />
      ) : (
        <>
          <HUDView
            intent={intent}
            startTime={startTime!}
            distractionCount={distractionCount}
            onDistraction={() => setDistractionCount((c) => c + 1)}
            onEndSession={handleEndSession}
          />
          <EndSessionModal
            open={debriefOpen}
            onClose={() => setDebriefOpen(false)}
            onSubmit={handleDebriefSubmit}
          />
        </>
      )}
    </div>
  )
}

export default ActiveSessionHUD
