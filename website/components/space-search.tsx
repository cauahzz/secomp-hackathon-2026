'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import { statusColor, statusLabel } from '@/lib/status'
import { useAtlas } from './atlas-provider'

interface SearchHit {
  spaceId: string
  spaceName: string
  buildingId: string
  buildingName: string
  floorId: string
  floorName: string
}

const MAX_HITS = 6
const LISTBOX_ID = 'busca-ambientes'

/** Busca simples por nome ou código, sobre os dados de /structure. */
export function SpaceSearch() {
  const { structure, spaceById, openFloor, selectSpace } = useAtlas()
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const catalog = useMemo<SearchHit[]>(() => {
    if (!structure) return []
    return structure.buildings.flatMap((building) =>
      building.floors.flatMap((floor) =>
        floor.spaces.map((space) => ({
          spaceId: space.id,
          spaceName: `${space.name}${space.code ? ` (${space.code})` : ''}`,
          buildingId: building.id,
          buildingName: building.name,
          floorId: floor.id,
          floorName: floor.name,
        })),
      ),
    )
  }, [structure])

  const hits = useMemo(() => {
    const term = query.trim().toLowerCase()
    if (!term) return []
    return catalog
      .filter(
        (hit) =>
          hit.spaceName.toLowerCase().includes(term) ||
          hit.buildingName.toLowerCase().includes(term),
      )
      .slice(0, MAX_HITS)
  }, [catalog, query])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const showList = isOpen && hits.length > 0
  const hasQuery = query.trim().length > 0

  function goTo(hit: SearchHit) {
    openFloor(hit.buildingId, hit.floorId)
    selectSpace(hit.spaceId)
    setQuery('')
    setIsOpen(false)
    inputRef.current?.blur()
    router.push('/mapa')
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      setIsOpen(false)
      return
    }
    if (event.key === 'Enter') {
      const hit = hits[activeIndex] ?? hits[0]
      if (hit) goTo(hit)
      return
    }
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return
    if (hits.length === 0) return
    event.preventDefault()
    setIsOpen(true)
    const step = event.key === 'ArrowDown' ? 1 : -1
    setActiveIndex((current) => (current + step + hits.length) % hits.length)
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-64">
      <svg
        aria-hidden
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinecap="round"
        className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>

      <input
        ref={inputRef}
        type="search"
        name="ambiente"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setActiveIndex(0)
          setIsOpen(true)
        }}
        onFocus={() => setIsOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="Buscar ambiente…"
        aria-label="Buscar ambiente"
        role="combobox"
        aria-expanded={showList}
        aria-controls={LISTBOX_ID}
        aria-autocomplete="list"
        aria-activedescendant={showList ? `${LISTBOX_ID}-${activeIndex}` : undefined}
        autoComplete="off"
        spellCheck={false}
        /* 16 px no celular: abaixo disso o iOS dá zoom ao focar o campo. */
        className="h-10 w-full rounded-md border border-border bg-surface pr-9 pl-8 text-base text-text placeholder:text-muted focus:border-brand focus:outline-none sm:h-9 sm:text-sm [&::-webkit-search-cancel-button]:hidden"
      />

      {hasQuery && (
        <button
          type="button"
          onClick={() => {
            setQuery('')
            setIsOpen(false)
            inputRef.current?.focus()
          }}
          aria-label="Limpar busca"
          className="absolute top-1/2 right-0.5 flex size-9 -translate-y-1/2 items-center justify-center rounded-md text-muted transition-colors hover:text-text"
        >
          <svg
            aria-hidden
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.75}
            strokeLinecap="round"
            className="size-4"
          >
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      )}

      <ul
        id={LISTBOX_ID}
        role="listbox"
        aria-label="Ambientes encontrados"
        hidden={!showList}
        className="absolute right-0 z-50 mt-1 w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-md border border-border bg-surface py-1 shadow-xl"
      >
        {hits.map((hit, index) => {
          const space = spaceById.get(hit.spaceId)
          return (
            <li
              key={hit.spaceId}
              id={`${LISTBOX_ID}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              onClick={() => goTo(hit)}
              onPointerEnter={() => setActiveIndex(index)}
              className={`flex cursor-pointer items-center gap-2 px-3 py-2.5 ${
                index === activeIndex ? 'bg-surface-2' : ''
              }`}
            >
              {space && (
                <span
                  aria-hidden
                  className="size-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: statusColor(space.status) }}
                />
              )}
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm text-text">{hit.spaceName}</span>
                <span className="block truncate text-xs text-muted">
                  {hit.buildingName} · {hit.floorName}
                  {space ? ` · ${statusLabel(space.status)}` : ''}
                </span>
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
