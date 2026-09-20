import { STATUS_ORDER, statusColor, statusLabel } from '@/lib/status'

export function StatusLegend({ className = '' }: { className?: string }) {
  return (
    <ul
      aria-label="Legenda de situação"
      className={`flex flex-wrap items-center gap-x-4 gap-y-2 text-xs sm:gap-x-5 ${className}`}
    >
      {STATUS_ORDER.map((status) => (
        <li key={status} className="flex items-center gap-2 text-muted">
          <span
            aria-hidden
            className="size-3 rounded-sm"
            style={{ backgroundColor: statusColor(status) }}
          />
          {statusLabel(status)}
        </li>
      ))}
    </ul>
  )
}
