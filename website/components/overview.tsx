'use client'

import { formatRate, formatTime } from '@/lib/format'
import { STATUS_ORDER, statusColor, statusLabel } from '@/lib/status'
import type { Space, Summary } from '@/lib/types'
import { useAtlas } from './atlas-provider'
import { SpaceCard } from './space-card'

const BUSIEST_LIMIT = 4

export function Overview() {
  const { summary, spaces, isLoading, selectSpace } = useAtlas()

  if (isLoading && !summary) {
    return (
      <div className="space-y-7 sm:space-y-8" aria-busy="true">
        <div className="grid gap-3 sm:gap-4 lg:grid-cols-3">
          <div className="h-40 animate-pulse rounded-xl bg-surface-2 lg:col-span-2" />
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-1">
            <div className="h-24 animate-pulse rounded-xl bg-surface-2 lg:h-auto" />
            <div className="h-24 animate-pulse rounded-xl bg-surface-2 lg:h-auto" />
          </div>
        </div>
        <div className="h-44 animate-pulse rounded-xl bg-surface-2" />
      </div>
    )
  }

  if (!summary) {
    return (
      <p className="rounded-xl border border-border bg-surface p-8 text-center text-muted">
        Resumo indisponível. Tentando novamente…
      </p>
    )
  }

  // Soma de lugares, não de status: o número grande sozinho não diz se 312
  // pessoas é um campus vazio ou lotado.
  const seats = spaces.reduce((total, space) => total + space.capacity, 0)
  const campusRate = seats > 0 ? summary.total_people / seats : null

  const overLimit = spaces.filter((space) => space.status === 'over_limit')

  const busiest = [...spaces]
    .filter((space) => space.status !== 'no_data' && (space.person_count ?? 0) > 0)
    .sort((left, right) => (right.occupancy_rate ?? 0) - (left.occupancy_rate ?? 0))
    .slice(0, BUSIEST_LIMIT)

  const allCamerasOnline = summary.cameras_online === summary.cameras_total

  return (
    <div className="space-y-7 sm:space-y-8">
      {overLimit.length > 0 && <OverLimitAlert spaces={overLimit} onSelect={selectSpace} />}

      <section className="grid gap-3 sm:gap-4 lg:grid-cols-3">
        <article
          className="rounded-xl border border-border bg-surface p-4 sm:p-6 lg:col-span-2"
          style={{ borderLeft: '3px solid var(--brand)' }}
        >
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h2 className="text-sm text-muted">Pessoas no campus</h2>
            <p className="tabular text-xs text-muted">
              atualizado às {formatTime(summary.generated_at)}
            </p>
          </div>

          <p className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 sm:mt-3">
            <span
              className="tabular text-5xl leading-none font-bold sm:text-6xl"
              style={{ color: 'var(--brand)' }}
            >
              {summary.total_people}
            </span>
            <span className="tabular text-sm text-muted">de {seats} lugares</span>
          </p>

          {campusRate !== null && (
            <div className="mt-4 sm:mt-5">
              <div
                className="h-2 w-full overflow-hidden rounded-full bg-bg"
                role="img"
                aria-label={`${formatRate(campusRate)} dos lugares do campus ocupados`}
              >
                <div
                  className="bar-fill h-full rounded-full"
                  style={{
                    width: `${Math.min(100, Math.round(campusRate * 100))}%`,
                    backgroundColor: 'var(--brand)',
                  }}
                />
              </div>
              <p className="tabular mt-2 text-xs text-pretty text-muted">
                {formatRate(campusRate)} da capacidade · {summary.spaces_total} ambientes
                {summary.no_data > 0 ? ` · ${summary.no_data} sem leitura` : ''}
              </p>
            </div>
          )}
        </article>

        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-1">
          <StatCard
            label="Câmeras online"
            value={`${summary.cameras_online}/${summary.cameras_total}`}
            accent={allCamerasOnline ? 'var(--status-normal)' : 'var(--status-high)'}
            hint={
              allCamerasOnline
                ? 'Todas reportando'
                : `${summary.cameras_total - summary.cameras_online} sem sinal`
            }
          />
          <StatCard
            label="Ambientes"
            value={String(summary.spaces_total)}
            accent="var(--brand-soft)"
            hint="No campus"
          />
        </div>
      </section>

      <StatusDistribution summary={summary} />

      {busiest.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-muted uppercase">
            Mais cheios agora
          </h2>
          <ul className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            {busiest.map((space: Space) => (
              <li key={space.id}>
                <SpaceCard space={space} onSelect={() => selectSpace(space.id)} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

/**
 * O status mais crítico é a única coisa da tela que pede ação; enterrado como
 * o quarto número de uma fileira de cartões, ele não pedia nada.
 */
function OverLimitAlert({
  spaces,
  onSelect,
}: {
  spaces: Space[]
  onSelect: (spaceId: string) => void
}) {
  return (
    <section
      aria-live="polite"
      className="rounded-xl border border-border bg-surface p-4 sm:p-5"
      style={{ borderLeft: '3px solid var(--status-over)' }}
    >
      <h2 className="flex items-center gap-2 text-sm font-semibold text-text">
        <span
          aria-hidden
          className="size-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: 'var(--status-over)' }}
        />
        {spaces.length === 1
          ? '1 ambiente acima do limite'
          : `${spaces.length} ambientes acima do limite`}
      </h2>
      <ul className="mt-3 flex flex-wrap gap-2">
        {spaces.map((space) => (
          <li key={space.id}>
            <button
              type="button"
              onClick={() => onSelect(space.id)}
              className="press flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm transition-colors hover:border-brand hover:text-brand-soft"
            >
              <span className="truncate text-text">{space.name}</span>
              <span className="tabular shrink-0 text-muted">
                {space.person_count}/{space.capacity}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

/**
 * Uma barra proporcional no lugar de cinco cartões: a leitura "quase tudo
 * normal" ou "metade em alta" sai de um relance, e os números continuam
 * escritos na legenda.
 */
function StatusDistribution({ summary }: { summary: Summary }) {
  // No contrato cada contagem de /summary tem o nome do próprio status, então
  // a ordem oficial dos status também é a ordem da barra.
  const segments = STATUS_ORDER.filter((status) => summary[status] > 0)
  const description = segments
    .map((status) => `${summary[status]} ${statusLabel(status).toLowerCase()}`)
    .join(', ')

  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-muted uppercase">
        Ambientes por situação
      </h2>
      <div className="rounded-xl border border-border bg-surface p-4 sm:p-5">
        {segments.length > 0 && (
          <div
            className="flex h-3 w-full gap-1"
            role="img"
            aria-label={`${summary.spaces_total} ambientes: ${description}`}
          >
            {segments.map((status) => (
              <span
                key={status}
                className="h-full rounded-full"
                style={{
                  flex: `${summary[status]} 1 0%`,
                  minWidth: '0.75rem',
                  backgroundColor: statusColor(status),
                }}
              />
            ))}
          </div>
        )}

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 lg:grid-cols-5">
          {STATUS_ORDER.map((status) => (
            <div
              key={status}
              className={summary[status] === 0 ? 'opacity-45' : undefined}
            >
              <dt className="flex items-start gap-2 text-xs text-pretty text-muted">
                <span
                  aria-hidden
                  className="mt-1 size-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: statusColor(status) }}
                />
                <span className="min-w-0">{statusLabel(status)}</span>
              </dt>
              <dd className="tabular mt-1 ml-[1.125rem] text-2xl font-bold text-text">
                {summary[status]}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}

function StatCard({
  label,
  value,
  accent,
  hint,
}: {
  label: string
  value: string
  accent: string
  hint?: string
}) {
  return (
    <article
      className="flex h-full flex-col rounded-xl border border-border bg-surface p-4 sm:p-5"
      style={{ borderLeft: `3px solid ${accent}` }}
    >
      {/* O rótulo quebra em vez de cortar: em 320 px "Câmeras online" não cabe
          numa linha, e meia palavra informa menos que duas linhas. */}
      <h3 className="flex items-start gap-2 text-sm text-pretty text-muted">
        <span
          aria-hidden
          className="mt-1.5 size-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: accent }}
        />
        <span className="min-w-0">{label}</span>
      </h3>
      <p className="tabular mt-1.5 text-2xl font-bold text-text sm:mt-2 sm:text-3xl">{value}</p>
      {hint && <p className="mt-1 text-xs text-pretty text-muted">{hint}</p>}
    </article>
  )
}
