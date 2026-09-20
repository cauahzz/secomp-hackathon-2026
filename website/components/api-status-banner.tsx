'use client'

import { useAtlas } from './atlas-provider'

/**
 * Aviso fixo de API fora do ar. A tela anterior continua visível: o polling
 * segue tentando e o aviso some sozinho quando uma resposta chega.
 */
export function ApiStatusBanner() {
  const { isOffline, usingMock } = useAtlas()

  if (usingMock) {
    return (
      <div className="border-b border-border bg-surface-2 px-4 py-1.5 text-center text-xs text-muted">
        Modo mock — dados de demonstração.
      </div>
    )
  }

  if (!isOffline) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-wrap items-center justify-center gap-x-2 border-b border-over/40 bg-over/10 px-4 py-2 text-center text-sm font-medium text-text"
    >
      <span className="flex items-center gap-2">
        <span
          aria-hidden
          className="size-2 shrink-0 rounded-full"
          style={{ backgroundColor: 'var(--status-over)' }}
        />
        API indisponível — dados podem estar desatualizados
      </span>
      <span className="text-xs font-normal text-muted">Tentando reconectar…</span>
    </div>
  )
}
