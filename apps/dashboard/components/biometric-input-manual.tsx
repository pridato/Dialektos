'use client'

/**
 * Formulario gamificado de entrada manual de biométricos.
 * Dividido en 3 pasos semánticos: Sueño, Corazón, Recursos.
 * Valores por defecto: media móvil últimos 3 días cuando hay historial.
 */

import * as React from 'react'
import { Moon, Heart, Battery, ChevronRight, ChevronLeft, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Input } from '@/components/ui/input'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { cn } from '@/lib/utils'
import type { RecentBiometric } from '@/lib/api'

const STEPS = [
  { id: 1, title: 'El Descanso', subtitle: '¿Cómo has dormido?', icon: Moon },
  { id: 2, title: 'La Fisiología', subtitle: '¿Qué dice tu corazón?', icon: Heart },
  { id: 3, title: 'El Estado', subtitle: 'Recursos y carga', icon: Battery },
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
  })

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
        <h2 className="text-xl font-semibold text-foreground">Sincronización Matutina</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Paso {step} de 3 — {STEPS[step - 1].title}
        </p>
      </div>

      {/* Indicador de pasos */}
      <div className="flex gap-2">
        {STEPS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setStep(s.id)}
            className={cn(
              'flex-1 rounded-xl py-2 px-3 text-center transition-all',
              step === s.id
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'bg-muted/50 text-muted-foreground hover:bg-muted'
            )}
          >
            <s.icon className="h-4 w-4 mx-auto mb-0.5 block" />
            <span className="text-xs font-medium">{s.title}</span>
          </button>
        ))}
      </div>

      {/* Paso 1: Sueño */}
      {step === 1 && (
        <div className="space-y-6">
          <div className="bg-card rounded-2xl border border-border p-4 lg:p-5 shadow-sm">
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

          <div className="bg-card rounded-2xl border border-border p-4 lg:p-5 shadow-sm">
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

          <Accordion type="single" collapsible className="border border-border rounded-2xl overflow-hidden bg-card">
            <AccordionItem value="advanced" className="border-0">
              <AccordionTrigger className="px-4 py-3 text-sm text-muted-foreground hover:text-foreground">
                Datos avanzados (opcional): profundo / REM / ligero
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4 pt-0">
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label className="text-xs text-muted-foreground">Profundo (min)</Label>
                    <Input
                      type="number"
                      min={0}
                      placeholder="—"
                      value={form.deep_sleep_min ?? ''}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          deep_sleep_min: e.target.value === '' ? null : parseInt(e.target.value, 10) || null,
                        }))
                      }
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">REM (min)</Label>
                    <Input
                      type="number"
                      min={0}
                      placeholder="—"
                      value={form.rem_sleep_min ?? ''}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          rem_sleep_min: e.target.value === '' ? null : parseInt(e.target.value, 10) || null,
                        }))
                      }
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Ligero (min)</Label>
                    <Input
                      type="number"
                      min={0}
                      placeholder="—"
                      value={form.light_sleep_min ?? ''}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          light_sleep_min: e.target.value === '' ? null : parseInt(e.target.value, 10) || null,
                        }))
                      }
                      className="mt-1"
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
          <div className="bg-card rounded-2xl border border-border p-5 shadow-sm">
            <Stepper
              label="HRV (RMSSD)"
              unit="ms"
              value={form.hrv_rmssd}
              onChange={(v) => setForm((f) => ({ ...f, hrv_rmssd: v }))}
              min={20}
              max={120}
              step={1}
            />
          </div>
          <div className="bg-card rounded-2xl border border-border p-5 shadow-sm">
            <Stepper
              label="Frecuencia en reposo"
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
          <div className="bg-card rounded-2xl border border-border p-5 shadow-sm">
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

          <div className="bg-card rounded-2xl border border-border p-5 shadow-sm">
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

      {/* Navegación */}
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
        {step < 3 ? (
          <Button type="button" onClick={() => setStep((s) => s + 1)} className="gap-1">
            Siguiente
            <ChevronRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleSubmit} disabled={saving} className="gap-1">
            {saving ? 'Guardando…' : 'Calcular ICD y guardar'}
          </Button>
        )}
      </div>
    </div>
  )
}
