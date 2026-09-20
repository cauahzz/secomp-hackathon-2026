'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import * as api from '@/lib/api'
import type { Space, Structure, Summary } from '@/lib/types'

/** Ciclo de atualização definido na spec. */
export const POLL_INTERVAL_MS = 2000

export interface MapLocation {
  buildingId: string | null
  floorId: string | null
}

interface AtlasContextValue {
  structure: Structure | null
  spaces: Space[]
  spaceById: Map<string, Space>
  summary: Summary | null
  /** true só até a primeira resposta chegar. */
  isLoading: boolean
  /** A última tela continua na tela; isto apenas avisa que os dados envelheceram. */
  isOffline: boolean
  usingMock: boolean
  selectedSpaceId: string | null
  selectSpace: (spaceId: string | null) => void
  location: MapLocation
  openBuilding: (buildingId: string | null) => void
  openFloor: (buildingId: string, floorId: string) => void
}

const AtlasContext = createContext<AtlasContextValue | null>(null)

export function useAtlas(): AtlasContextValue {
  const context = useContext(AtlasContext)
  if (!context) throw new Error('useAtlas precisa estar dentro de <AtlasProvider>')
  return context
}

export function AtlasProvider({ children }: { children: ReactNode }) {
  const [structure, setStructure] = useState<Structure | null>(null)
  const [spaces, setSpaces] = useState<Space[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isOffline, setIsOffline] = useState(false)
  const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(null)
  const [location, setLocation] = useState<MapLocation>({ buildingId: null, floorId: null })

  // Evita que um ciclo lento se sobreponha ao próximo.
  const inFlightRef = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    let structureLoaded = false

    // /structure é carregado uma vez; se falhar, o próximo ciclo tenta de novo.
    async function loadStructure() {
      try {
        setStructure(await api.getStructure(controller.signal))
        structureLoaded = true
      } catch {
        structureLoaded = false
      }
    }

    async function poll() {
      if (inFlightRef.current) return
      inFlightRef.current = true
      try {
        if (!structureLoaded) await loadStructure()
        const [nextSpaces, nextSummary] = await Promise.all([
          api.getSpaces(controller.signal),
          api.getSummary(controller.signal),
        ])
        setSpaces(nextSpaces)
        setSummary(nextSummary)
        setIsOffline(false)
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setIsOffline(true)
      } finally {
        setIsLoading(false)
        inFlightRef.current = false
      }
    }

    void poll()
    const timer = setInterval(() => void poll(), POLL_INTERVAL_MS)

    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [])

  const spaceById = useMemo(
    () => new Map(spaces.map((space) => [space.id, space])),
    [spaces],
  )

  const selectSpace = useCallback((spaceId: string | null) => {
    setSelectedSpaceId(spaceId)
  }, [])

  const openBuilding = useCallback((buildingId: string | null) => {
    setLocation({ buildingId, floorId: null })
  }, [])

  const openFloor = useCallback((buildingId: string, floorId: string) => {
    setLocation({ buildingId, floorId })
  }, [])

  const value = useMemo<AtlasContextValue>(
    () => ({
      structure,
      spaces,
      spaceById,
      summary,
      isLoading,
      isOffline,
      usingMock: api.USE_MOCK,
      selectedSpaceId,
      selectSpace,
      location,
      openBuilding,
      openFloor,
    }),
    [
      structure,
      spaces,
      spaceById,
      summary,
      isLoading,
      isOffline,
      selectedSpaceId,
      selectSpace,
      location,
      openBuilding,
      openFloor,
    ],
  )

  return <AtlasContext.Provider value={value}>{children}</AtlasContext.Provider>
}
