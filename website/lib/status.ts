import type { Status } from './types'

/**
 * Mapeamento visual do contrato. O frontend nunca calcula status:
 * apenas traduz o código vindo da API em rótulo e token de cor.
 */

export const STATUS_ORDER: Status[] = ['empty', 'normal', 'high', 'over_limit', 'no_data']

export const STATUS_LABEL: Record<Status, string> = {
  empty: 'Vazio',
  normal: 'Normal',
  high: 'Alta ocupação',
  over_limit: 'Acima do limite',
  no_data: 'Sem dados',
}

/** Referência ao token CSS, nunca ao hex. */
export const STATUS_COLOR: Record<Status, string> = {
  empty: 'var(--status-empty)',
  normal: 'var(--status-normal)',
  high: 'var(--status-high)',
  over_limit: 'var(--status-over)',
  no_data: 'var(--status-nodata)',
}

export function statusLabel(status: Status): string {
  return STATUS_LABEL[status] ?? STATUS_LABEL.no_data
}

export function statusColor(status: Status): string {
  return STATUS_COLOR[status] ?? STATUS_COLOR.no_data
}
