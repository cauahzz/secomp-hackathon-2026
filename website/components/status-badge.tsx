import { statusColor, statusLabel } from '@/lib/status'
import type { Status } from '@/lib/types'

/** Cor nunca vem sozinha: o rótulo em texto acompanha sempre o indicador. */
export function StatusBadge({ status, className = '' }: { status: Status; className?: string }) {
  return (
    <span className={`inline-flex min-w-0 items-center gap-2 ${className}`}>
      <span
        aria-hidden
        className="size-2.5 shrink-0 rounded-full"
        style={{ backgroundColor: statusColor(status) }}
      />
      <span className="truncate">{statusLabel(status)}</span>
    </span>
  )
}
