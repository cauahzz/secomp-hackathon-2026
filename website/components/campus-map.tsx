'use client'

import { useCallback, useMemo } from 'react'

import { totalPeople, worstStatus } from '@/lib/aggregate'
import { EMPTY_VALUE, formatRate } from '@/lib/format'
import { statusColor, statusLabel } from '@/lib/status'
import type { Space, StructureBuilding, StructureFloor } from '@/lib/types'
import { useAtlas } from './atlas-provider'
import { Breadcrumb, type BreadcrumbItem } from './breadcrumb'
import { SpaceCard } from './space-card'
import { StatusLegend } from './status-legend'
import { SvgMap } from './svg-map'

/** Área do desenho: o SVG define a altura, limitada em globals.css. */
const MAP_SURFACE = 'map-surface'

export function CampusMap() {
  const { structure, spaces, spaceById, location, openBuilding, openFloor, selectSpace, selectedSpaceId, isLoading } =
    useAtlas()

  const building = useMemo<StructureBuilding | null>(() => {
    if (!structure || !location.buildingId) return null
    return structure.buildings.find((item) => item.id === location.buildingId) ?? null
  }, [structure, location.buildingId])

  const floor = useMemo<StructureFloor | null>(() => {
    if (!building || !location.floorId) return null
    return building.floors.find((item) => item.id === location.floorId) ?? null
  }, [building, location.floorId])

  const spacesByBuilding = useMemo(() => {
    const groups = new Map<string, Space[]>()
    for (const space of spaces) {
      const group = groups.get(space.building.id)
      if (group) group.push(space)
      else groups.set(space.building.id, [space])
    }
    return groups
  }, [spaces])

  const spacesByFloor = useMemo(() => {
    const groups = new Map<string, Space[]>()
    for (const space of spaces) {
      const group = groups.get(space.floor.id)
      if (group) group.push(space)
      else groups.set(space.floor.id, [space])
    }
    return groups
  }, [spaces])

  const breadcrumbItems = useMemo<BreadcrumbItem[]>(() => {
    const items: BreadcrumbItem[] = [
      {
        label: structure?.campus.name ?? 'Campus',
        onSelect: () => {
          openBuilding(null)
          selectSpace(null)
        },
      },
    ]
    if (building) {
      items.push({ label: building.name, onSelect: () => openBuilding(building.id) })
    }
    if (floor) {
      items.push({ label: floor.name, onSelect: () => openFloor(building!.id, floor.id) })
    }
    const selected = selectedSpaceId ? spaceById.get(selectedSpaceId) : null
    if (selected && floor && selected.floor.id === floor.id) {
      items.push({ label: selected.name })
    }
    return items
  }, [structure, building, floor, selectedSpaceId, spaceById, openBuilding, openFloor, selectSpace])

  /* ---- nível campus: prédios ---- */

  const buildingIds = useMemo(
    () => structure?.buildings.map((item) => item.id) ?? [],
    [structure],
  )

  const buildingFill = useCallback(
    (id: string) => {
      const group = spacesByBuilding.get(id)
      if (!group || group.length === 0) return null
      const status = worstStatus(group)
      return status ? statusColor(status) : null
    },
    [spacesByBuilding],
  )

  const buildingLabel = useCallback(
    (id: string) => {
      const group = spacesByBuilding.get(id) ?? []
      const status = worstStatus(group)
      const name = structure?.buildings.find((item) => item.id === id)?.name ?? id
      if (!status) return name
      return `${name}: ${group.length} ambientes, ${totalPeople(group)} pessoas, situação mais crítica ${statusLabel(status)}`
    },
    [spacesByBuilding, structure],
  )

  const buildingTooltip = useCallback(
    (id: string) => {
      const group = spacesByBuilding.get(id) ?? []
      const status = worstStatus(group)
      const name = structure?.buildings.find((item) => item.id === id)?.name ?? id
      return (
        <>
          <p className="font-medium text-text">{name}</p>
          <p className="tabular mt-0.5 text-muted">
            {group.length} ambientes · {totalPeople(group)} pessoas
          </p>
          {status && (
            <p className="mt-1 flex items-center gap-1.5 text-muted">
              <span
                aria-hidden
                className="size-2 rounded-full"
                style={{ backgroundColor: statusColor(status) }}
              />
              {statusLabel(status)}
            </p>
          )}
        </>
      )
    },
    [spacesByBuilding, structure],
  )

  /* ---- nível andar: ambientes ---- */

  const floorSpaceIds = useMemo(() => floor?.spaces.map((space) => space.id) ?? [], [floor])

  const spaceFill = useCallback(
    (id: string) => {
      const space = spaceById.get(id)
      return space ? statusColor(space.status) : null
    },
    [spaceById],
  )

  const spaceLabel = useCallback(
    (id: string) => {
      const space = spaceById.get(id)
      if (!space) return id
      if (space.status === 'no_data') return `${space.name}: sem dados`
      return `${space.name}: ${space.person_count} de ${space.capacity} pessoas, ${statusLabel(space.status)}`
    },
    [spaceById],
  )

  const spaceTooltip = useCallback(
    (id: string) => {
      const space = spaceById.get(id)
      if (!space) return <p className="text-muted">Ambiente sem dados na API</p>
      const hasData = space.status !== 'no_data'
      return (
        <>
          <p className="font-medium text-text">{space.name}</p>
          <p className="tabular mt-0.5 text-muted">
            {hasData ? `${space.person_count} / ${space.capacity} pessoas` : EMPTY_VALUE}
            {hasData ? ` · ${formatRate(space.occupancy_rate)}` : ''}
          </p>
          <p className="mt-1 flex items-center gap-1.5 text-muted">
            <span
              aria-hidden
              className="size-2 rounded-full"
              style={{ backgroundColor: statusColor(space.status) }}
            />
            {statusLabel(space.status)}
          </p>
        </>
      )
    },
    [spaceById],
  )

  if (isLoading && !structure) {
    return (
      <div
        className="h-[clamp(18rem,52vh,38rem)] animate-pulse rounded-xl bg-surface-2"
        aria-busy="true"
      />
    )
  }

  if (!structure) {
    return (
      <p className="rounded-xl border border-border bg-surface p-8 text-center text-muted">
        Estrutura do campus indisponível. Tentando novamente...
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <Breadcrumb items={breadcrumbItems} />

      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <div className="p-3 sm:p-4">
          {!building && (
            <SvgMap
              src={`/maps/${structure.campus.id}.svg`}
              interactiveIds={buildingIds}
              fillFor={buildingFill}
              labelFor={buildingLabel}
              tooltipFor={buildingTooltip}
              className={MAP_SURFACE}
              onSelect={(id) => openBuilding(id)}
              fallback={
                <BuildingListFallback
                  buildings={structure.buildings}
                  spacesByBuilding={spacesByBuilding}
                  onSelect={openBuilding}
                />
              }
            />
          )}

          {building && !floor && (
            <FloorPicker
              building={building}
              spacesByFloor={spacesByFloor}
              onSelect={(floorId) => openFloor(building.id, floorId)}
            />
          )}

          {building && floor && (
            <SvgMap
              src={`/maps/${floor.id}.svg`}
              interactiveIds={floorSpaceIds}
              fillFor={spaceFill}
              labelFor={spaceLabel}
              tooltipFor={spaceTooltip}
              selectedId={selectedSpaceId}
              className={MAP_SURFACE}
              onSelect={(id) => selectSpace(id)}
              fallback={
                <SpaceListFallback
                  spaces={floorSpaceIds
                    .map((id) => spaceById.get(id))
                    .filter((space): space is Space => Boolean(space))}
                  onSelect={selectSpace}
                />
              }
            />
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-surface-2 px-4 py-3">
          <StatusLegend />
          {!building && (
            <p className="text-xs text-muted">
              Cada prédio recebe a cor do seu ambiente mais crítico.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

/* ---- fallbacks quando o SVG daquele nível ainda não existe ---- */

function BuildingListFallback({
  buildings,
  spacesByBuilding,
  onSelect,
}: {
  buildings: StructureBuilding[]
  spacesByBuilding: Map<string, Space[]>
  onSelect: (buildingId: string) => void
}) {
  return (
    <div>
      <p className="mb-3 text-sm text-muted">
        Mapa do campus ainda não desenhado. Escolha um prédio:
      </p>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {buildings.map((building) => {
          const group = spacesByBuilding.get(building.id) ?? []
          const status = worstStatus(group)
          return (
            <li key={building.id}>
              <button
                type="button"
                onClick={() => onSelect(building.id)}
                className="press w-full rounded-lg border border-border bg-surface-2 p-4 text-left transition-colors hover:border-brand"
                style={
                  status ? { borderLeft: `3px solid ${statusColor(status)}` } : undefined
                }
              >
                <p className="font-medium text-text">{building.name}</p>
                <p className="tabular mt-1 text-xs text-muted">
                  {group.length} ambientes · {totalPeople(group)} pessoas
                </p>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function FloorPicker({
  building,
  spacesByFloor,
  onSelect,
}: {
  building: StructureBuilding
  spacesByFloor: Map<string, Space[]>
  onSelect: (floorId: string) => void
}) {
  return (
    <div>
      <p className="mb-3 text-sm text-muted">Escolha um andar de {building.name}:</p>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {building.floors.map((floor) => {
          const group = spacesByFloor.get(floor.id) ?? []
          const status = worstStatus(group)
          return (
            <li key={floor.id}>
              <button
                type="button"
                onClick={() => onSelect(floor.id)}
                className="press w-full rounded-lg border border-border bg-surface-2 p-4 text-left transition-colors hover:border-brand"
                style={status ? { borderLeft: `3px solid ${statusColor(status)}` } : undefined}
              >
                <p className="font-medium text-text">{floor.name}</p>
                <p className="tabular mt-1 text-xs text-muted">
                  {group.length} ambientes · {totalPeople(group)} pessoas
                </p>
                {status && (
                  <p className="mt-2 text-xs text-muted">{statusLabel(status)} no mais crítico</p>
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function SpaceListFallback({
  spaces,
  onSelect,
}: {
  spaces: Space[]
  onSelect: (spaceId: string) => void
}) {
  return (
    <div>
      <p className="mb-3 text-sm text-muted">
        Planta deste andar ainda não desenhada. Ambientes:
      </p>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {spaces.map((space) => (
          <li key={space.id}>
            <SpaceCard space={space} onSelect={() => onSelect(space.id)} />
          </li>
        ))}
      </ul>
    </div>
  )
}
