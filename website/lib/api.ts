import * as mock from './mock'
import type {
  Health,
  History,
  Occupancy,
  Space,
  SpaceDetail,
  Structure,
  Summary,
} from './types'

/**
 * Único ponto de contato com o backend.
 * Nenhum componente chama fetch direto: todos passam por aqui, e é aqui que se
 * decide entre a API real e o modo mock.
 */

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(
  /\/+$/,
  '',
)

export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true'

export class ApiError extends Error {
  /** null quando a requisição nem chegou ao servidor (rede fora, CORS). */
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { signal, cache: 'no-store' })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('API indisponível', null)
  }

  if (!response.ok) {
    // A API devolve { "detail": "..." } nos erros; texto livre é aceito como reserva.
    const detail = await response
      .json()
      .then((body: { detail?: string }) => body?.detail)
      .catch(() => undefined)
    throw new ApiError(detail ?? `Erro ${response.status}`, response.status)
  }

  return (await response.json()) as T
}

export function getHealth(signal?: AbortSignal): Promise<Health> {
  if (USE_MOCK) return Promise.resolve({ status: 'ok' })
  return request<Health>('/health', signal)
}

export function getStructure(signal?: AbortSignal): Promise<Structure> {
  if (USE_MOCK) return mock.getStructure()
  return request<Structure>('/structure', signal)
}

export function getSpaces(signal?: AbortSignal): Promise<Space[]> {
  if (USE_MOCK) return mock.getSpaces()
  return request<Space[]>('/spaces', signal)
}

export function getSpace(spaceId: string, signal?: AbortSignal): Promise<SpaceDetail> {
  if (USE_MOCK) return mock.getSpace(spaceId)
  return request<SpaceDetail>(`/spaces/${encodeURIComponent(spaceId)}`, signal)
}

export function getOccupancy(spaceId: string, signal?: AbortSignal): Promise<Occupancy> {
  if (USE_MOCK) return mock.getOccupancy(spaceId)
  return request<Occupancy>(`/spaces/${encodeURIComponent(spaceId)}/occupancy`, signal)
}

export function getHistory(
  spaceId: string,
  minutes = 30,
  signal?: AbortSignal,
): Promise<History> {
  if (USE_MOCK) return mock.getHistory(spaceId, minutes)
  return request<History>(
    `/spaces/${encodeURIComponent(spaceId)}/history?minutes=${minutes}`,
    signal,
  )
}

export function getSummary(signal?: AbortSignal): Promise<Summary> {
  if (USE_MOCK) return mock.getSummary()
  return request<Summary>('/summary', signal)
}
