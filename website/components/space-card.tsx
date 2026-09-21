'use client'

import { EMPTY_VALUE, formatRate } from '@/lib/format'
import { statusColor } from '@/lib/status'
import type { Space } from '@/lib/types'
import { StatusBadge } from './status-badge'

/** Cartão de ambiente: usado como fallback do mapa e nas listas. */
export function SpaceCard({ space, onSelect }: { space: Space; onSelect: () => void }) {
  const hasData = space.status !== 'no_data'
  const fill = hasData ? Math.min(100, Math.round((space.occupancy_rate ?? 0) * 100)) : 0

  // A marca só existe quando o limite operacional aperta mais que a capacidade
  // — é ela que explica por que o status virou antes de lotar.
  const limitMark =
    space.operational_limit !== null && space.operational_limit < space.capacity
      ? (space.operational_limit / space.capacity) * 100
      : null

  return (
    <button
      type="button"
      onClick={onSelect}
      className="press flex h-full w-full flex-col rounded-xl border border-border bg-surface p-3 text-left hover:border-brand hover:bg-surface-2 sm:p-4"
      style={{ borderLeft: `3px solid ${statusColor(space.status)}` }}
    >
      {/* Em dois cartões por linha no celular sobram ~150 px: "Restaurante
          Universitário" cortado informa menos que o mesmo nome em duas linhas. */}
      <span className="line-clamp-2 w-full font-medium text-text">{space.name}</span>
      <span className="mt-0.5 block w-full truncate text-xs text-muted">
        {space.building.name} · {space.floor.name}
      </span>

      <span className="mt-3 flex w-full items-baseline justify-between gap-2">
        <span className="flex items-baseline gap-1">
          <span className="tabular text-3xl leading-none font-bold text-text">
            {hasData ? space.person_count : EMPTY_VALUE}
          </span>
          <span className="tabular text-sm text-muted">/ {space.capacity}</span>
        </span>
        <span className="tabular shrink-0 text-xs text-muted">
          {hasData ? formatRate(space.occupancy_rate) : EMPTY_VALUE}
        </span>
      </span>

      {/* A barra dá a proporção que o número sozinho não dá de relance. */}
      <span className="relative mt-2.5 block h-1.5 w-full overflow-hidden rounded-full bg-bg">
        <span
          className="bar-fill block h-full rounded-full"
          style={{ width: `${fill}%`, backgroundColor: statusColor(space.status) }}
        />
        {limitMark !== null && (
          <span
            aria-hidden
            className="absolute inset-y-0 w-0.5 bg-muted"
            style={{ left: `${limitMark}%` }}
          />
        )}
      </span>

      <StatusBadge status={space.status} className="mt-auto w-full pt-2.5 text-xs text-muted" />
    </button>
  )
}
