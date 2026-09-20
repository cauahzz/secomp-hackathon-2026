import type { Space, Status } from './types'

/**
 * Agregações para os níveis acima do ambiente (prédio, andar).
 * A API é a fonte do status de cada space; aqui só se escolhe qual deles
 * representa o conjunto — nunca se recalcula um status a partir de números.
 */

/** Do mais crítico ao menos crítico. */
const SEVERITY: Status[] = ['over_limit', 'high', 'normal', 'empty', 'no_data']

export function worstStatus(spaces: Space[]): Status | null {
  if (spaces.length === 0) return null
  for (const status of SEVERITY) {
    if (spaces.some((space) => space.status === status)) return status
  }
  return null
}

/** Soma apenas os ambientes que não estão em no_data, como faz /summary. */
export function totalPeople(spaces: Space[]): number {
  return spaces.reduce((total, space) => total + (space.person_count ?? 0), 0)
}
