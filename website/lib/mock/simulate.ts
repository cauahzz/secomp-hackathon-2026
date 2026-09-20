import type { Status } from '../types'

/**
 * Este arquivo emula o servidor, não o frontend.
 *
 * No modo mock não existe API: o cálculo de status abaixo é a mesma regra da
 * tabela do contrato, executada aqui só porque este módulo faz o papel do
 * backend. Nenhum componente da interface deriva status por conta própria.
 */

/** Intervalo entre snapshots simulados, igual ao da visão (5 s). */
export const SNAPSHOT_INTERVAL_MS = 5000

function seedOf(id: string): number {
  let seed = 0
  for (let i = 0; i < id.length; i++) {
    seed = (seed * 31 + id.charCodeAt(i)) % 1000
  }
  return seed
}

/**
 * Passeio suave em torno do valor base, determinístico no par (space, tempo).
 * Permite que histórico e leitura atual contem a mesma história.
 */
export function simulateCount(
  spaceId: string,
  baseCount: number,
  capacity: number,
  atMs: number,
): number {
  const seed = seedOf(spaceId)
  const tick = Math.floor(atMs / SNAPSHOT_INTERVAL_MS)
  const amplitude = Math.max(2, Math.round(capacity * 0.14))
  const wave =
    Math.sin(tick / 23 + seed) * 0.6 +
    Math.sin(tick / 7 + seed * 0.7) * 0.3 +
    Math.sin(tick / 3 + seed * 1.9) * 0.1
  const count = Math.round(baseCount + wave * amplitude)
  return Math.min(capacity, Math.max(0, count))
}

/** Regra do contrato, avaliada exatamente nesta ordem. */
export function computeStatus(
  personCount: number,
  capacity: number,
  operationalLimit: number | null,
  cameraOnline: boolean,
): Status {
  if (!cameraOnline) return 'no_data'
  if (personCount === 0) return 'empty'
  const limit = operationalLimit ?? capacity
  if (personCount < 0.7 * limit) return 'normal'
  if (personCount <= limit) return 'high'
  return 'over_limit'
}

/** Instante do último snapshot: o relógio "bate" a cada 5 s, como no ingest. */
export function lastSnapshotAt(atMs: number): string {
  const aligned = Math.floor(atMs / SNAPSHOT_INTERVAL_MS) * SNAPSHOT_INTERVAL_MS
  return new Date(aligned).toISOString().replace(/\.\d{3}Z$/, 'Z')
}
