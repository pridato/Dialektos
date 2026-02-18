'use client'

/**
 * Formulario gamificado de entrada manual de biométricos.
 * Dividido en 4 pasos: Sueño, Corazón, Recursos, Percepción (subjetivo).
 * Valores por defecto: media móvil últimos 3 días cuando hay historial.
 */

import * as React from 'react'
import { Moon, Heart, Battery, Brain, ChevronRight, ChevronLeft, Zap, Frown, Meh, Smile, Laugh } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { cn } from '@/lib/utils'
import type { RecentBiometric } from '@/lib/api'

const STEPS = [
  { id: 1, title: 'El Descanso', subtitle: '¿Cómo has dormido?', icon: Moon },
  { id: 2, title: 'La Fisiología', subtitle: '¿Qué dice tu corazón?', icon: Heart },
  { id: 3, title: 'El Estado', subtitle: 'Recursos y carga', icon: Battery },
  { id: 4, title: 'La Percepción', subtitle: 'Datos subjetivos', icon: Brain },
] as const

/** Valores de ánimo en UI; al enviar se mapean al enum del backend (focused, anxious, tired, neutral). */
const MOOD_OPTIONS = [
  { value: 'pésimo', label: 'Pésimo', icon: Frown, apiValue: 'tired' as const },
  { value: 'malo', label: 'Malo', icon: Frown, apiValue: 'anxious' as const },
  { value: 'neutral', label: 'Neutral', icon: Meh, apiValue: 'neutral' as const },
  { value: 'bueno', label: 'Bueno', icon: Smile, apiValue: 'focused' as const },
  { value: 'excelente', label: 'Excelente', icon: Laugh, apiValue: 'focused' as const },
] as const

export interface ManualBiometricFormValues {
  sleep_quality: number
  sleep_bed_time: string
  sleep_wake_time: string
  deep_sleep_min: number | null
  rem_sleep_min: number | null
  light_sleep_min: number | null
  hrv_rmssd: number
  resting_hr: number
  body_resources: number
  training_load: number
  energy_level: number
  mental_clarity: number
  motivation: number
  muscle_soreness: number
  mood: typeof MOOD_OPTIONS[number]['value']
  notes: string
}

function averageLast3<T extends number | null>(
  items: Array<Record<string, T>>,
  key: string
): number | null {
  const values = items
    .slice(-3)
    .map((r) => r[key])
    .filter((v): v is number => v != null && typeof v === 'number')
  if (values.length === 0) return null
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length)
}

function parseTimeToMinutes(t: string): number {
  if (!t || !/^\d{1,2}:\d{2}$/.test(t)) return 0
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

/** Convierte minutos a string "H:MM" para mostrar en inputs de duración (profundo/REM/ligero). */
function minToTimeStr(min: number | null): string {
  if (min == null) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  return `${h}:${String(m).padStart(2, '0')}`
}

/** Parsea "H:MM" o "HH:MM" a minutos; devuelve null si vacío o inválido. */
function parseDurationToMinutes(t: string): number | null {
  const trimmed = t.trim()
  if (!trimmed) return null
  if (!/^\d{1,2}:\d{2}$/.test(trimmed)) return null
  const [h, m] = trimmed.split(':').map(Number)
  if (Number.isNaN(h) || Number.isNaN(m) || m < 0 || m > 59) return null
  return h * 60 + m
}

/** Calcula minutos totales de sueño entre hora acostarse y hora levantarse (permite cruzar medianoche). */
function computeSleepTotalMinutes(bedTime: string, wakeTime: string): number {
  const bed = parseTimeToMinutes(bedTime)
  let wake = parseTimeToMinutes(wakeTime)
  if (wake <= bed) wake += 24 * 60
  return wake - bed
}

interface BiometricInputManualProps {
  recentBiometrics: RecentBiometric[]
  onSave: (payload: Record<string, unknown>) => Promise<void>
  saving?: boolean
}

export function BiometricInputManual({
  recentBiometrics,
  onSave,
  saving = false,
}: BiometricInputManualProps) {
  const [step, setStep] = React.useState(1)
  const last3 = recentBiometrics.slice(-3)

  const defaults = React.useMemo(() => ({
    sleep_quality: averageLast3(last3, 'sleep_quality') ?? 75,
    hrv_rmssd: averageLast3(last3, 'hrv_rmssd') ?? 45,
    resting_hr: averageLast3(last3, 'resting_hr') ?? 58,
    body_resources: averageLast3(last3, 'body_resources') ?? 65,
    training_load: averageLast3(last3, 'training_load') ?? 0,
  }), [last3])

  const [form, setForm] = React.useState<ManualBiometricFormValues>({
    sleep_quality: 75,
    sleep_bed_time: '23:00',
    sleep_wake_time: '07:00',
    deep_sleep_min: null,
    rem_sleep_min: null,
    light_sleep_min: null,
    hrv_rmssd: 45,
    resting_hr: 58,
    body_resources: 65,
    training_load: 0,
    energy_level: 5,
    mental_clarity: 5,
    motivation: 5,
    muscle_soreness: 3,
    mood: 'neutral',
    notes: '',
  })

  // Drafts para inputs h:min (profundo/REM/ligero) para no borrar mientras se escribe
  const [draftDeep, setDraftDeep] = React.useState('')
  const [draftRem, setDraftRem] = React.useState('')
  const [draftLight, setDraftLight] = React.useState('')

  // Prellenar con media móvil de últimos 3 días cuando llega historial
  const hasPrefilled = React.useRef(false)
  React.useEffect(() => {
    if (last3.length > 0 && !hasPrefilled.current) {
      hasPrefilled.current = true
      setForm((prev) => ({
        ...prev,
        sleep_quality: defaults.sleep_quality,
        hrv_rmssd: defaults.hrv_rmssd,
        resting_hr: defaults.resting_hr,
        body_resources: defaults.body_resources,
        training_load: defaults.training_load,
      }))
    }
  }, [last3.length, defaults.sleep_quality, defaults.hrv_rmssd, defaults.resting_hr, defaults.body_resources, defaults.training_load])

  const sleepTotalMin = computeSleepTotalMinutes(form.sleep_bed_time, form.sleep_wake_time)

  const handleSubmit = async () => {
    const today = new Date().toISOString().split('T')[0]
    const moodApi = MOOD_OPTIONS.find((o) => o.value === form.mood)?.apiValue ?? 'neutral'
    const payload = {
      date: today,
      sleep_quality: form.sleep_quality,
      sleep_total_min: sleepTotalMin > 0 ? sleepTotalMin : null,
      deep_sleep_min: form.deep_sleep_min ?? undefined,
      rem_sleep_min: form.rem_sleep_min ?? undefined,
      light_sleep_min: form.light_sleep_min ?? undefined,
      hrv_rmssd: form.hrv_rmssd,
      resting_hr: form.resting_hr,
      body_resources: form.body_resources,
      training_load: form.training_load,
      energy_level: form.energy_level,
      mental_clarity: form.mental_clarity,
      motivation: form.motivation,
      muscle_soreness: form.muscle_soreness,
      mood: moodApi,
      notes: form.notes,
    }
    await onSave(payload)
  }

  const Stepper = ({
    value,
    onChange,
    min,
    max,
    step = 1,
    label,
    unit,
    className,
  }: {
    value: number
    onChange: (n: number) => void
    min: number
    max: number
    step?: number
    label: string
    unit: string
    className?: string
  }) => (
    <div className={cn('flex flex-col gap-2', className)}>
      <Label className="text-xs text-muted-foreground uppercase">{label}</Label>
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-10 w-10 rounded-xl shrink-0"
          onClick={() => onChange(Math.max(min, value - step))}
          disabled={value <= min}
        >
          −
        </Button>
        <span className="text-2xl lg:text-3xl font-display font-bold tabular-nums min-w-[3rem] text-center">
          {value}
          <span className="text-sm font-normal text-muted-foreground ml-0.5">{unit}</span>
        </span>
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-10 w-10 rounded-xl shrink-0"
          onClick={() => onChange(Math.min(max, value + step))}
          disabled={value >= max}
        >
          +
        </Button>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground tracking-tight">Sincronización Matutina</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Paso {step} de 4 — {STEPS[step - 1].title}
        </p>
      </div>

      {/* Indicador de pasos — tarjetas con profundidad y acento */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {STEPS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setStep(s.id)}
            className={cn(
              'flex flex-col items-center gap-1.5 rounded-2xl py-4 px-3 text-center transition-all duration-300 border',
              step === s.id
                ? 'bg-slate-800/80 dark:bg-slate-800/80 border-accent/50 dark:border-white/20 shadow-lg shadow-accent/10 text-foreground'
                : 'bg-slate-900/50 dark:bg-slate-900/50 border-slate-800 dark:border-white/10 text-muted-foreground hover:border-slate-700 hover:bg-slate-800/50 dark:hover:border-white/15 dark:hover:bg-slate-800/40'
            )}
          >
            <s.icon className="h-6 w-6 shrink-0" />
            <span className="text-sm font-semibold leading-tight">{s.title}</span>
            <span className="text-xs opacity-80 hidden sm:block">{s.subtitle}</span>
          </button>
        ))}
      </div>

      {/* Paso 1: Sueño */}
      {step === 1 && (
        <div className="space-y-6">
          <div className="bg-slate-900/50 dark:bg-slate-900/50 rounded-2xl border border-slate-800 dark:border-white/10 p-4 lg:p-5 shadow-sm backdrop-blur-sm transition-all duration-300">
            <Label className="text-sm text-muted-foreground">Calidad del sueño</Label>
            <div className="flex items-center gap-4 mt-2">
              <span
                className={cn(
                  'text-2xl font-bold tabular-nums min-w-[4rem]',
                  form.sleep_quality < 40 && 'text-red-500',
                  form.sleep_quality >= 40 && form.sleep_quality < 70 && 'text-amber-500',
                  form.sleep_quality >= 70 && 'text-emerald-500'
                )}
              >
                {form.sleep_quality}%
              </span>
              <div className="flex-1">
                <Slider
                  min={0}
                  max={100}
                  step={1}
                  value={[form.sleep_quality]}
                  onValueChange={([v]) => setForm((f) => ({ ...f, sleep_quality: v }))}
                />
              </div>
            </div>
          </div>

          <div className="bg-slate-900/50 dark:bg-slate-900/50 rounded-2xl border border-slate-800 dark:border-white/10 p-4 lg:p-5 shadow-sm backdrop-blur-sm transition-all duration-300">
            <Label className="text-sm text-muted-foreground">Horas de sueño</Label>
            <p className="text-xs text-muted-foreground mt-0.5">Me acosté a las… / Me levanté a las…</p>
            <div className="grid grid-cols-2 gap-4 mt-3">
              <div>
                <Label htmlFor="bed-time" className="text-xs uppercase text-muted-foreground">Acosté</Label>
                <Input
                  id="bed-time"
                  type="time"
                  value={form.sleep_bed_time}
                  onChange={(e) => setForm((f) => ({ ...f, sleep_bed_time: e.target.value }))}
                  className="text-lg font-semibold mt-1"
                />
              </div>
              <div>
                <Label htmlFor="wake-time" className="text-xs uppercase text-muted-foreground">Levánté</Label>
                <Input
                  id="wake-time"
                  type="time"
                  value={form.sleep_wake_time}
                  onChange={(e) => setForm((f) => ({ ...f, sleep_wake_time: e.target.value }))}
                  className="text-lg font-semibold mt-1"
                />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Total: <strong className="text-foreground tabular-nums">{Math.floor(sleepTotalMin / 60)} h {sleepTotalMin % 60} min</strong>
            </p>
          </div>

          <Accordion type="single" collapsible className="border border-slate-800 dark:border-white/10 rounded-2xl overflow-hidden bg-slate-900/50 dark:bg-slate-900/50 backdrop-blur-sm">
            <AccordionItem value="advanced" className="border-0">
              <AccordionTrigger className="px-4 py-3 text-sm text-muted-foreground hover:text-foreground">
                Datos avanzados (opcional): profundo / REM / ligero
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4 pt-0">
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label className="text-xs text-muted-foreground">Profundo (h:min)</Label>
                    <Input
                      type="text"
                      inputMode="numeric"
                      placeholder="0:00"
                      value={draftDeep !== '' ? draftDeep : minToTimeStr(form.deep_sleep_min)}
                      onChange={(e) => {
                        const v = e.target.value
                        setDraftDeep(v)
                        const parsed = parseDurationToMinutes(v)
                        if (parsed !== null) setForm((f) => ({ ...f, deep_sleep_min: parsed }))
                      }}
                      onBlur={() => {
                        if (parseDurationToMinutes(draftDeep) !== null || draftDeep.trim() === '') setDraftDeep('')
                      }}
                      className="mt-1 font-mono"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">REM (h:min)</Label>
                    <Input
                      type="text"
                      inputMode="numeric"
                      placeholder="0:00"
                      value={draftRem !== '' ? draftRem : minToTimeStr(form.rem_sleep_min)}
                      onChange={(e) => {
                        const v = e.target.value
                        setDraftRem(v)
                        const parsed = parseDurationToMinutes(v)
                        if (parsed !== null) setForm((f) => ({ ...f, rem_sleep_min: parsed }))
                      }}
                      onBlur={() => {
                        if (parseDurationToMinutes(draftRem) !== null || draftRem.trim() === '') setDraftRem('')
                      }}
                      className="mt-1 font-mono"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Ligero (h:min)</Label>
                    <Input
                      type="text"
                      inputMode="numeric"
                      placeholder="0:00"
                      value={draftLight !== '' ? draftLight : minToTimeStr(form.light_sleep_min)}
                      onChange={(e) => {
                        const v = e.target.value
                        setDraftLight(v)
                        const parsed = parseDurationToMinutes(v)
                        if (parsed !== null) setForm((f) => ({ ...f, light_sleep_min: parsed }))
                      }}
                      onBlur={() => {
                        if (parseDurationToMinutes(draftLight) !== null || draftLight.trim() === '') setDraftLight('')
                      }}
                      className="mt-1 font-mono"
                    />
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      )}

      {/* Paso 2: Corazón */}
      {step === 2 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="bg-slate-900/50 dark:bg-slate-900/50 rounded-2xl border border-slate-800 dark:border-white/10 p-5 shadow-sm backdrop-blur-sm">
            <Stepper
              label="VFC (RMSSD)"
              unit="ms"
              value={form.hrv_rmssd}
              onChange={(v) => setForm((f) => ({ ...f, hrv_rmssd: v }))}
              min={20}
              max={120}
              step={1}
            />
          </div>
          <div className="bg-slate-900/50 dark:bg-slate-900/50 rounded-2xl border border-slate-800 dark:border-white/10 p-5 shadow-sm backdrop-blur-sm">
            <Stepper
              label="FC mínima diurna"
              unit="bpm"
              value={form.resting_hr}
              onChange={(v) => setForm((f) => ({ ...f, resting_hr: v }))}
              min={35}
              max={100}
              step={1}
            />
          </div>
        </div>
      )}

      {/* Paso 3: Recursos */}
      {step === 3 && (
        <div className="space-y-6">
          <div className="bg-slate-900/50 dark:bg-slate-900/50 rounded-2xl border border-slate-800 dark:border-white/10 p-5 shadow-sm backdrop-blur-sm">
            <Label className="text-sm text-muted-foreground">Batería corporal (recursos)</Label>
            <div className="flex items-center gap-4 mt-3">
              <Zap className="h-8 w-8 text-amber-500 shrink-0" />
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-2xl font-bold tabular-nums text-foreground">{form.body_resources}</span>
                  <span className="text-muted-foreground">/ 100</span>
                </div>
                <Slider
                  min={0}
                  max={100}
                  step={5}
                  value={[form.body_resources]}
                  onValueChange={([v]) => setForm((f) => ({ ...f, body_resources: v }))}
                  className="accent-emerald-500"
                />
              </div>
            </div>
          </div>

          <div className="bg-slate-900/50 dark:bg-slate-900/50 rounded-2xl border border-slate-800 dark:border-white/10 p-5 shadow-sm backdrop-blur-sm">
            <Label className="text-sm text-muted-foreground">Carga de entrenamiento</Label>
            <p className="text-xs text-muted-foreground mt-0.5">Puede ser negativa (recuperación)</p>
            <div className="flex items-center gap-3 mt-3">
              <Stepper
                label="Carga"
                unit="pts"
                value={form.training_load}
                onChange={(v) => setForm((f) => ({ ...f, training_load: v }))}
                min={-50}
                max={50}
                step={1}
                className="flex-1"
              />
            </div>
          </div>
        </div>
      )}

      {/* Paso 4: La Percepción (subjetivo) */}
      {step === 4 && (
        <div className="space-y-6">
          {/* Grid 2x2: sliders compactos */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-white dark:bg-slate-900/50 rounded-3xl shadow-sm border border-slate-200 dark:border-white/10 p-4 backdrop-blur-sm">
              <Label className="text-sm font-medium text-foreground">Nivel de Energía</Label>
              <div className="flex items-center gap-3 mt-2">
                <Slider
                  min={1}
                  max={10}
                  step={1}
                  value={[form.energy_level]}
                  onValueChange={([v]) => setForm((f) => ({ ...f, energy_level: v }))}
                  className="flex-1 [&_.bg-primary]:bg-indigo-500 dark:[&_.bg-primary]:bg-indigo-500"
                />
                <span className="text-sm font-semibold tabular-nums min-w-[3rem] text-right">{form.energy_level}/10</span>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-900/50 rounded-3xl shadow-sm border border-slate-200 dark:border-white/10 p-4 backdrop-blur-sm">
              <Label className="text-sm font-medium text-foreground">Claridad Mental</Label>
              <div className="flex items-center gap-3 mt-2">
                <Slider
                  min={1}
                  max={10}
                  step={1}
                  value={[form.mental_clarity]}
                  onValueChange={([v]) => setForm((f) => ({ ...f, mental_clarity: v }))}
                  className="flex-1 [&_.bg-primary]:bg-indigo-500 dark:[&_.bg-primary]:bg-indigo-500"
                />
                <span className="text-sm font-semibold tabular-nums min-w-[3rem] text-right">{form.mental_clarity}/10</span>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-900/50 rounded-3xl shadow-sm border border-slate-200 dark:border-white/10 p-4 backdrop-blur-sm">
              <Label className="text-sm font-medium text-foreground">Motivación</Label>
              <div className="flex items-center gap-3 mt-2">
                <Slider
                  min={1}
                  max={10}
                  step={1}
                  value={[form.motivation]}
                  onValueChange={([v]) => setForm((f) => ({ ...f, motivation: v }))}
                  className="flex-1 [&_.bg-primary]:bg-indigo-500 dark:[&_.bg-primary]:bg-indigo-500"
                />
                <span className="text-sm font-semibold tabular-nums min-w-[3rem] text-right">{form.motivation}/10</span>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-900/50 rounded-3xl shadow-sm border border-slate-200 dark:border-white/10 p-4 backdrop-blur-sm">
              <Label className="text-sm font-medium text-foreground">Dolor Muscular</Label>
              <div className="flex items-center gap-3 mt-2">
                <Slider
                  min={1}
                  max={10}
                  step={1}
                  value={[form.muscle_soreness]}
                  onValueChange={([v]) => setForm((f) => ({ ...f, muscle_soreness: v }))}
                  className="flex-1 [&_.bg-primary]:bg-rose-500 dark:[&_.bg-primary]:bg-rose-500"
                />
                <span className="text-sm font-semibold tabular-nums min-w-[3rem] text-right">{form.muscle_soreness}/10</span>
              </div>
            </div>
          </div>

          {/* Estado de ánimo: 5 botones con iconos */}
          <div className="bg-white dark:bg-slate-900/50 rounded-3xl shadow-sm border border-slate-200 dark:border-white/10 p-4 backdrop-blur-sm">
            <Label className="text-sm font-medium text-foreground block mb-3">Estado de ánimo</Label>
            <div className="flex flex-wrap gap-2">
              {MOOD_OPTIONS.map((opt) => {
                const Icon = opt.icon
                const isSelected = form.mood === opt.value
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, mood: opt.value }))}
                    className={cn(
                      'flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all border',
                      isSelected
                        ? 'bg-indigo-50 dark:bg-indigo-950/50 border-indigo-200 dark:border-indigo-800 ring-2 ring-indigo-200 dark:ring-indigo-700 ring-offset-2 dark:ring-offset-background text-indigo-700 dark:text-indigo-300'
                        : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-white/10 text-muted-foreground hover:border-slate-300 dark:hover:border-white/15 hover:text-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {opt.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Notas */}
          <div className="bg-white dark:bg-slate-900/50 rounded-3xl shadow-sm border border-slate-200 dark:border-white/10 p-4 backdrop-blur-sm">
            <Label htmlFor="notes-perception" className="text-sm font-medium text-foreground block mb-2">
              Notas
            </Label>
            <Textarea
              id="notes-perception"
              placeholder="¿Algún factor externo? (Ej: Ayuno, Estrés por examen...)"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              rows={3}
              className="resize-none rounded-xl border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900/50 focus-visible:ring-accent"
            />
          </div>

          {/* Botón principal: solo en paso 4 */}
          <Button
            onClick={handleSubmit}
            disabled={saving}
            variant="default"
            size="lg"
            className="w-full rounded-xl h-12 text-base font-medium shadow-sm hover:shadow-md transition-shadow"
          >
            {saving ? 'Guardando…' : '💾 Guardar y Calcular ICD'}
          </Button>
        </div>
      )}

      {/* Navegación (Atrás / Siguiente; en paso 4 el CTA está dentro del paso) */}
      <div className="flex justify-between gap-3 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => setStep((s) => Math.max(1, s - 1))}
          disabled={step === 1}
          className="gap-1"
        >
          <ChevronLeft className="h-4 w-4" />
          Atrás
        </Button>
        {step < 4 ? (
          <Button type="button" onClick={() => setStep((s) => s + 1)} className="gap-1">
            Siguiente
            <ChevronRight className="h-4 w-4" />
          </Button>
        ) : null}
      </div>
    </div>
  )
}
