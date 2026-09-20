/** Formatações de exibição. Dado ausente vira travessão, nunca zero. */

export const EMPTY_VALUE = '—'

/** ISO 8601 UTC -> horário local HH:MM. */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return EMPTY_VALUE
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return EMPTY_VALUE
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

/** ISO 8601 UTC -> horário local HH:MM:SS. */
export function formatTimeWithSeconds(iso: string | null | undefined): string {
  if (!iso) return EMPTY_VALUE
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return EMPTY_VALUE
  return date.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/** occupancy_rate (0 a 1) -> "90%". */
export function formatRate(rate: number | null | undefined): string {
  if (rate === null || rate === undefined) return EMPTY_VALUE
  return `${Math.round(rate * 100)}%`
}

export function formatCount(count: number | null | undefined): string {
  if (count === null || count === undefined) return EMPTY_VALUE
  return String(count)
}

/** effective_limit = operational_limit se não for nulo; senão, capacity. */
export function effectiveLimit(capacity: number, operationalLimit: number | null): number {
  return operationalLimit ?? capacity
}
