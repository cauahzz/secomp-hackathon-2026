'use client'

import { usePathname, useRouter } from 'next/navigation'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

import * as api from '@/lib/api'
import {
  effectiveLimit,
  EMPTY_VALUE,
  formatRate,
  formatTime,
  formatTimeWithSeconds,
} from '@/lib/format'
import { statusColor, statusLabel } from '@/lib/status'
import type { History, SpaceDetail } from '@/lib/types'
import { POLL_INTERVAL_MS, useAtlas } from './atlas-provider'
import { OccupancyChart } from './occupancy-chart'

const HISTORY_MINUTES = 30

/** Painel lateral compartilhado pelo mapa e pela tabela. */
export function SpaceDetailPanel() {
  const { selectedSpaceId, selectSpace } = useAtlas()
  // Estável entre ciclos de polling: um `onClose` novo a cada 2 s remontaria
  // os efeitos do diálogo e roubaria o foco de quem está lendo.
  const close = useCallback(() => selectSpace(null), [selectSpace])

  if (!selectedSpaceId) return null

  // A `key` remonta o painel a cada ambiente: nenhum dado do anterior sobra.
  return <DetailDialog key={selectedSpaceId} spaceId={selectedSpaceId} onClose={close} />
}

function DetailDialog({ spaceId, onClose }: { spaceId: string; onClose: () => void }) {
  const { openFloor } = useAtlas()
  const router = useRouter()
  const pathname = usePathname()
  const [detail, setDetail] = useState<SpaceDetail | null>(null)
  const [history, setHistory] = useState<History | null>(null)
  const [notFound, setNotFound] = useState(false)
  const panelRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const controller = new AbortController()
    let inFlight = false

    async function poll(id: string) {
      if (inFlight) return
      inFlight = true
      try {
        const [nextDetail, nextHistory] = await Promise.all([
          api.getSpace(id, controller.signal),
          api.getHistory(id, HISTORY_MINUTES, controller.signal),
        ])
        setDetail(nextDetail)
        setHistory(nextHistory)
        setNotFound(false)
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        if (error instanceof api.ApiError && error.status === 404) setNotFound(true)
        // Demais falhas mantêm a última leitura; o aviso global já está na tela.
      } finally {
        inFlight = false
      }
    }

    void poll(spaceId)
    const timer = setInterval(() => void poll(spaceId), POLL_INTERVAL_MS)

    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [spaceId])

  // Enquanto o painel está aberto ele é a tela: o fundo não rola e o foco
  // começa aqui dentro, voltando ao ponto de partida no fechamento.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    panelRef.current?.focus()

    return () => {
      document.body.style.overflow = previousOverflow
      opener?.focus()
    }
  }, [])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const hasData = detail !== null && detail.status !== 'no_data'
  const limit = detail ? effectiveLimit(detail.capacity, detail.operational_limit) : 0
  const fill = hasData ? Math.min(100, Math.round((detail.occupancy_rate ?? 0) * 100)) : 0

  // A marca só existe quando o limite operacional é mais apertado que a
  // capacidade — é ela que explica por que o status virou antes de lotar.
  const limitMark =
    detail && detail.operational_limit !== null && detail.operational_limit < detail.capacity
      ? (detail.operational_limit / detail.capacity) * 100
      : null

  // Na própria tela do mapa o botão levaria de volta para onde já se está.
  const showMapAction = detail !== null && pathname !== '/mapa'

  function goToMap() {
    if (!detail) return
    openFloor(detail.building.id, detail.floor.id)
    router.push('/mapa')
  }

  return (
    <>
      <div aria-hidden onClick={onClose} className="anim-overlay fixed inset-0 z-40 bg-black/60" />
      {/* Mobile: folha que sobe da borda inferior. Desktop: gaveta à direita. */}
      <aside
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="detalhe-titulo"
        className="anim-panel fixed inset-x-0 bottom-0 z-50 flex max-h-[88dvh] flex-col rounded-t-2xl border-t border-border bg-surface shadow-2xl outline-none sm:inset-y-0 sm:right-0 sm:left-auto sm:max-h-none sm:w-full sm:max-w-md sm:rounded-none sm:border-t-0 sm:border-l"
      >
        <header className="flex items-start gap-3 border-b border-border px-4 py-3 sm:px-5 sm:py-4">
          <div className="min-w-0 flex-1">
            <h2 id="detalhe-titulo" className="truncate text-lg font-semibold text-text">
              {detail?.name ?? (notFound ? 'Ambiente não encontrado' : 'Carregando…')}
            </h2>
            <p className="truncate text-sm text-muted">
              {detail
                ? `${detail.building.name} · ${detail.floor.name}${detail.code ? ` · ${detail.code}` : ''}`
                : spaceId}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar detalhe"
            className="press -mr-1 flex size-11 shrink-0 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface-2 hover:text-text"
          >
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              className="size-5"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div
          className="flex-1 overflow-y-auto overscroll-contain pb-4"
          style={
            showMapAction ? undefined : { paddingBottom: 'calc(env(safe-area-inset-bottom) + 1rem)' }
          }
        >
          {notFound && (
            <p className="px-5 py-6 text-sm text-muted">Este ambiente não existe na API.</p>
          )}

          {!detail && !notFound && (
            <div className="space-y-4 px-4 py-4 sm:px-5 sm:py-5" aria-busy="true">
              <div className="h-40 animate-pulse rounded-xl bg-surface-2" />
              <div className="h-44 animate-pulse rounded-xl bg-surface-2" />
              <div className="h-32 animate-pulse rounded-xl bg-surface-2" />
            </div>
          )}

          {detail && (
            <div className="space-y-6 px-4 py-4 sm:px-5 sm:py-5">
              <section className="rounded-xl border border-border bg-surface-2 p-4 sm:p-5">
                <span
                  className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold"
                  style={{
                    color: statusColor(detail.status),
                    backgroundColor: `color-mix(in srgb, ${statusColor(detail.status)} 15%, transparent)`,
                  }}
                >
                  <span
                    aria-hidden
                    className="size-2 shrink-0 rounded-full"
                    style={{ backgroundColor: statusColor(detail.status) }}
                  />
                  {statusLabel(detail.status)}
                </span>

                {hasData ? (
                  <>
                    <p className="mt-4 flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <span className="tabular text-5xl leading-none font-bold text-text">
                        {detail.person_count}
                      </span>
                      <span className="tabular text-sm text-muted">
                        de {detail.capacity} lugares
                      </span>
                      <span className="tabular ml-auto text-lg font-semibold text-text">
                        {formatRate(detail.occupancy_rate)}
                      </span>
                    </p>

                    <div
                      className="relative mt-4 h-2.5 w-full overflow-hidden rounded-full bg-bg"
                      role="img"
                      aria-label={`${formatRate(detail.occupancy_rate)} da capacidade`}
                    >
                      <div
                        className="bar-fill h-full rounded-full"
                        style={{ width: `${fill}%`, backgroundColor: statusColor(detail.status) }}
                      />
                      {limitMark !== null && (
                        <span
                          aria-hidden
                          className="absolute inset-y-0 w-0.5 bg-muted"
                          style={{ left: `${limitMark}%` }}
                        />
                      )}
                    </div>

                    {limitMark !== null && (
                      <p className="tabular mt-2 flex items-center gap-1.5 text-xs text-muted">
                        <span aria-hidden className="inline-block h-3 w-0.5 shrink-0 bg-muted" />
                        limite operacional {detail.operational_limit}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="mt-3 text-sm text-muted">
                    {detail.captured_at
                      ? `Última leitura às ${formatTime(detail.captured_at)}`
                      : 'Nenhuma leitura registrada.'}
                  </p>
                )}
              </section>

              <section>
                <h3 className="mb-2 text-xs font-semibold tracking-wide text-muted uppercase">
                  Últimos {HISTORY_MINUTES} minutos
                </h3>
                <OccupancyChart
                  points={history?.points ?? []}
                  limit={limit}
                  color={statusColor(detail.status)}
                />
              </section>

              <section>
                <h3 className="mb-2 text-xs font-semibold tracking-wide text-muted uppercase">
                  Detalhes
                </h3>
                <dl className="divide-y divide-border rounded-xl border border-border">
                  <DetailRow term="Capacidade" value={detail.capacity} />
                  <DetailRow
                    term="Limite operacional"
                    value={detail.operational_limit ?? EMPTY_VALUE}
                  />
                  <DetailRow
                    term="Última leitura"
                    value={formatTimeWithSeconds(detail.captured_at)}
                  />
                  <DetailRow
                    term="Câmera"
                    value={
                      <span className="flex items-center justify-end gap-2">
                        <span
                          aria-hidden
                          className="size-2 shrink-0 rounded-full"
                          style={{
                            backgroundColor: detail.source.online
                              ? 'var(--status-normal)'
                              : 'var(--status-nodata)',
                          }}
                        />
                        <span className="truncate">{detail.source.camera_name}</span>
                        <span className="shrink-0 font-normal text-muted">
                          {detail.source.online ? 'online' : 'offline'}
                        </span>
                      </span>
                    }
                  />
                  <DetailRow term="Último sinal" value={formatTime(detail.source.last_seen_at)} />
                </dl>
              </section>
            </div>
          )}
        </div>

        {showMapAction && (
          <footer
            className="border-t border-border px-4 py-3 sm:px-5"
            style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 0.75rem)' }}
          >
            <button
              type="button"
              onClick={goToMap}
              className="press flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand font-semibold text-bg transition-colors hover:bg-brand-strong"
            >
              <svg
                aria-hidden
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.75}
                strokeLinecap="round"
                strokeLinejoin="round"
                className="size-5"
              >
                <path d="m9 4-6 3v13l6-3 6 3 6-3V4l-6 3-6-3Z" />
                <path d="M9 4v13M15 7v13" />
              </svg>
              Ver no mapa
            </button>
          </footer>
        )}
      </aside>
    </>
  )
}

function DetailRow({ term, value }: { term: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-2.5 text-sm">
      <dt className="shrink-0 text-muted">{term}</dt>
      <dd className="tabular min-w-0 truncate font-medium text-text">{value}</dd>
    </div>
  )
}
