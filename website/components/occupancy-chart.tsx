import { formatTime } from '@/lib/format'
import type { HistoryPoint } from '@/lib/types'

const VIEW_WIDTH = 300
const VIEW_HEIGHT = 90
const GRADIENT_ID = 'atlas-chart-fill'

interface OccupancyChartProps {
  points: HistoryPoint[]
  /** Linha tracejada de referência (effective_limit). */
  limit: number
  color: string
}

/** Gráfico de linha deliberadamente simples: pessoas ao longo dos últimos minutos. */
export function OccupancyChart({ points, limit, color }: OccupancyChartProps) {
  if (points.length < 2) {
    return (
      <p className="rounded-lg border border-dashed border-border py-8 text-center text-sm text-muted">
        Sem histórico para exibir.
      </p>
    )
  }

  const counts = points.map((point) => point.person_count)
  const peak = Math.max(...counts)
  const scaleMax = Math.max(peak * 1.15, limit * 1.05, 1)

  const toX = (index: number) => (index / (points.length - 1)) * VIEW_WIDTH
  const toY = (count: number) => VIEW_HEIGHT - (count / scaleMax) * VIEW_HEIGHT

  const line = points.map((point, index) => `${toX(index)},${toY(point.person_count)}`).join(' ')
  const area = `${line} ${VIEW_WIDTH},${VIEW_HEIGHT} 0,${VIEW_HEIGHT}`
  const limitY = toY(limit)

  return (
    <figure className="m-0">
      <div className="flex items-baseline justify-between gap-2 text-xs text-muted">
        <span className="tabular">
          pico {peak} · limite {limit}
        </span>
        <span className="tabular font-semibold text-text">
          agora {counts[counts.length - 1]}
        </span>
      </div>

      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        preserveAspectRatio="none"
        className="mt-1.5 h-36 w-full sm:h-32"
        role="img"
        aria-label={`Histórico de ocupação: de ${counts[0]} a ${counts[counts.length - 1]} pessoas, pico de ${peak}.`}
      >
        <defs>
          {/* O degradê dá volume à série sem competir com a linha. */}
          <linearGradient id={GRADIENT_ID} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.32} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>

        <polygon points={area} fill={`url(#${GRADIENT_ID})`} />
        {limit <= scaleMax && (
          <line
            x1={0}
            x2={VIEW_WIDTH}
            y1={limitY}
            y2={limitY}
            stroke="var(--text-muted)"
            strokeDasharray="4 4"
            strokeWidth={1}
            vectorEffect="non-scaling-stroke"
          />
        )}
        <polyline
          points={line}
          fill="none"
          stroke={color}
          strokeWidth={2.5}
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
        {/* Marca do "agora": com preserveAspectRatio="none" um círculo viraria
            elipse, então a leitura mais recente é uma linha vertical. */}
        <line
          x1={VIEW_WIDTH}
          x2={VIEW_WIDTH}
          y1={toY(counts[counts.length - 1])}
          y2={VIEW_HEIGHT}
          stroke={color}
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
          opacity={0.5}
        />
      </svg>

      <figcaption className="tabular mt-1 flex justify-between text-xs text-muted">
        <span>{formatTime(points[0].captured_at)}</span>
        <span>{formatTime(points[points.length - 1].captured_at)}</span>
      </figcaption>
    </figure>
  )
}
