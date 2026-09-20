'use client'

import { EMPTY_VALUE, formatRate } from '@/lib/format'
import { statusColor } from '@/lib/status'
import type { Space } from '@/lib/types'
import { useAtlas } from './atlas-provider'
import { StatusBadge } from './status-badge'

const COLUMNS = ['Ambiente', 'Prédio', 'Capacidade', 'Pessoas', 'Ocupação', 'Status'] as const

export function SpacesTable() {
  const { spaces, isLoading, selectSpace, selectedSpaceId } = useAtlas()

  if (isLoading && spaces.length === 0) {
    return (
      <div className="space-y-2" aria-busy="true">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-20 animate-pulse rounded-lg bg-surface-2 lg:h-12" />
        ))}
      </div>
    )
  }

  if (spaces.length === 0) {
    return (
      <p className="rounded-xl border border-border bg-surface p-8 text-center text-muted">
        Nenhum ambiente retornado pela API.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="tabular text-sm text-muted">
        {spaces.length} {spaces.length === 1 ? 'ambiente' : 'ambientes'}
      </p>

      {/* Até 1024 px a tabela vira lista: seis colunas em português só param
          de se espremer a partir daí. */}
      <ul className="grid gap-2 sm:grid-cols-2 lg:hidden">
        {spaces.map((space) => (
          <li key={space.id}>
            <SpaceListItem
              space={space}
              isSelected={space.id === selectedSpaceId}
              onSelect={() => selectSpace(space.id)}
            />
          </li>
        ))}
      </ul>

      <div className="hidden overflow-hidden rounded-xl border border-border lg:block">
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">
            Ambientes do campus com ocupação atual. Selecione uma linha para ver o detalhe.
          </caption>
          <thead>
            <tr className="bg-surface-2 text-left text-xs tracking-wide text-muted uppercase">
              {COLUMNS.map((column) => (
                <th key={column} scope="col" className="px-4 py-3 font-semibold">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {spaces.map((space) => (
              <SpaceRow
                key={space.id}
                space={space}
                isSelected={space.id === selectedSpaceId}
                onSelect={() => selectSpace(space.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SpaceRow({
  space,
  isSelected,
  onSelect,
}: {
  space: Space
  isSelected: boolean
  onSelect: () => void
}) {
  const hasData = space.status !== 'no_data'

  return (
    <tr
      onClick={onSelect}
      className={`cursor-pointer border-t border-border transition-colors hover:bg-surface-2 ${
        isSelected ? 'bg-surface-2' : 'bg-surface'
      }`}
    >
      {/* A linha inteira é clicável no mouse; o botão é o caminho do teclado. */}
      <th scope="row" className="px-4 py-3 text-left font-medium text-text">
        <button
          type="button"
          onClick={onSelect}
          className="rounded text-left hover:text-brand-soft"
        >
          {space.name}
        </button>
        <span className="ml-2 text-xs font-normal whitespace-nowrap text-muted">
          {space.floor.name}
        </span>
      </th>
      <td className="px-4 py-3 whitespace-nowrap text-muted">{space.building.name}</td>
      <td className="tabular px-4 py-3 text-muted">{space.capacity}</td>
      <td className="tabular px-4 py-3 font-semibold text-text">
        {hasData ? space.person_count : EMPTY_VALUE}
      </td>
      <td className="tabular px-4 py-3 text-text">
        {hasData ? formatRate(space.occupancy_rate) : EMPTY_VALUE}
      </td>
      <td className="px-4 py-3 text-muted">
        <StatusBadge status={space.status} />
      </td>
    </tr>
  )
}

function SpaceListItem({
  space,
  isSelected,
  onSelect,
}: {
  space: Space
  isSelected: boolean
  onSelect: () => void
}) {
  const hasData = space.status !== 'no_data'

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`press flex h-full w-full items-center gap-3 rounded-lg border border-border px-4 py-3 text-left transition-colors ${
        isSelected ? 'bg-surface-2' : 'bg-surface'
      }`}
      style={{ borderLeft: `3px solid ${statusColor(space.status)}` }}
    >
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium text-text">{space.name}</span>
        <span className="mt-0.5 block truncate text-xs text-muted">
          {space.building.name} · {space.floor.name}
        </span>
        <StatusBadge status={space.status} className="mt-1.5 text-xs text-muted" />
      </span>
      <span className="shrink-0 text-right">
        <span className="tabular block text-xl font-bold text-text">
          {hasData ? space.person_count : EMPTY_VALUE}
          <span className="text-sm font-normal text-muted">/{space.capacity}</span>
        </span>
        <span className="tabular mt-0.5 block text-xs text-muted">
          {hasData ? formatRate(space.occupancy_rate) : EMPTY_VALUE}
        </span>
      </span>
    </button>
  )
}
