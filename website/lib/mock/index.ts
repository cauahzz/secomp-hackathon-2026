import type {
  History,
  HistoryPoint,
  Occupancy,
  Source,
  Space,
  SpaceDetail,
  Structure,
  Summary,
} from '../types'
import { computeStatus, lastSnapshotAt, simulateCount, SNAPSHOT_INTERVAL_MS } from './simulate'

import sourcesJson from './sources.json'
import spacesJson from './spaces.json'
import structureJson from './structure.json'

/**
 * Modo mock: substitui a API inteira, no formato exato do contrato.
 * Serve de esqueleto andante na FASE 0 e de plano B na demo.
 */

const MOCK_LATENCY_MS = 40
const MAX_HISTORY_POINTS = 500

const structure = structureJson as Structure
const baseSpaces = spacesJson as unknown as Space[]

interface MockCamera {
  name: string
  online: boolean
  regions: Record<string, string>
}

const cameras = sourcesJson as unknown as Record<string, MockCamera>

/** space_id -> câmera/ROI, espelhando o que a visão leria do seed. */
const sourceBySpace = new Map<string, Source>()
for (const [cameraId, camera] of Object.entries(cameras)) {
  for (const [spaceId, regionId] of Object.entries(camera.regions)) {
    sourceBySpace.set(spaceId, {
      camera_id: cameraId,
      camera_name: camera.name,
      region_id: regionId,
      online: camera.online,
      last_seen_at: null,
    })
  }
}

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), MOCK_LATENCY_MS))
}

function sourceOf(spaceId: string, atMs: number): Source {
  const source = sourceBySpace.get(spaceId)
  if (!source) {
    return {
      camera_id: '—',
      camera_name: 'Sem câmera',
      region_id: '—',
      online: false,
      last_seen_at: null,
    }
  }
  return {
    ...source,
    last_seen_at: source.online ? lastSnapshotAt(atMs) : null,
  }
}

/** Reconstrói um space com a leitura "atual" simulada. */
function readSpace(base: Space, atMs: number): Space {
  const source = sourceOf(base.id, atMs)
  const offline = !source.online

  if (offline) {
    return {
      ...base,
      person_count: null,
      occupancy_rate: null,
      status: 'no_data',
      captured_at: base.captured_at,
    }
  }

  const personCount = simulateCount(base.id, base.person_count ?? 0, base.capacity, atMs)
  return {
    ...base,
    person_count: personCount,
    occupancy_rate: personCount / base.capacity,
    status: computeStatus(personCount, base.capacity, base.operational_limit, true),
    captured_at: lastSnapshotAt(atMs),
  }
}

function findBase(spaceId: string): Space | undefined {
  return baseSpaces.find((space) => space.id === spaceId)
}

export function getStructure(): Promise<Structure> {
  return delay(structure)
}

export function getSpaces(): Promise<Space[]> {
  const now = Date.now()
  return delay(baseSpaces.map((base) => readSpace(base, now)))
}

export function getSpace(spaceId: string): Promise<SpaceDetail> {
  const base = findBase(spaceId)
  if (!base) return Promise.reject(new Error('space not found'))
  const now = Date.now()
  return delay({ ...readSpace(base, now), source: sourceOf(spaceId, now) })
}

export function getOccupancy(spaceId: string): Promise<Occupancy> {
  const base = findBase(spaceId)
  if (!base) return Promise.reject(new Error('space not found'))
  const now = Date.now()
  const space = readSpace(base, now)
  const source = sourceOf(spaceId, now)
  return delay({
    space_id: space.id,
    person_count: space.person_count,
    occupancy_rate: space.occupancy_rate,
    status: space.status,
    captured_at: space.captured_at,
    source: {
      camera_id: source.camera_id,
      online: source.online,
      last_seen_at: source.last_seen_at,
    },
  })
}

export function getHistory(spaceId: string, minutes = 30): Promise<History> {
  const base = findBase(spaceId)
  if (!base) return Promise.reject(new Error('space not found'))

  const source = sourceOf(spaceId, Date.now())
  if (!source.online) return delay({ space_id: spaceId, points: [] })

  const now = Date.now()
  const total = Math.floor((minutes * 60 * 1000) / SNAPSHOT_INTERVAL_MS)
  const count = Math.min(total, MAX_HISTORY_POINTS)
  const points: HistoryPoint[] = []

  for (let i = count - 1; i >= 0; i--) {
    const atMs = now - i * SNAPSHOT_INTERVAL_MS
    const personCount = simulateCount(base.id, base.person_count ?? 0, base.capacity, atMs)
    points.push({
      captured_at: lastSnapshotAt(atMs),
      person_count: personCount,
      occupancy_rate: personCount / base.capacity,
    })
  }

  return delay({ space_id: spaceId, points })
}

export function getSummary(): Promise<Summary> {
  const now = Date.now()
  const spaces = baseSpaces.map((base) => readSpace(base, now))
  const cameraList = Object.values(cameras)

  return delay({
    total_people: spaces.reduce((total, space) => total + (space.person_count ?? 0), 0),
    spaces_total: spaces.length,
    empty: spaces.filter((space) => space.status === 'empty').length,
    normal: spaces.filter((space) => space.status === 'normal').length,
    high: spaces.filter((space) => space.status === 'high').length,
    over_limit: spaces.filter((space) => space.status === 'over_limit').length,
    no_data: spaces.filter((space) => space.status === 'no_data').length,
    cameras_online: cameraList.filter((camera) => camera.online).length,
    cameras_total: cameraList.length,
    generated_at: new Date(now).toISOString().replace(/\.\d{3}Z$/, 'Z'),
  })
}
