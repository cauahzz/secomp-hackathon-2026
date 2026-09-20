'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { formatTimeWithSeconds } from '@/lib/format'
import { useAtlas } from './atlas-provider'
import { NAV_ITEMS } from './nav-items'
import { SpaceSearch } from './space-search'

export function AppHeader() {
  const pathname = usePathname()
  const { structure, summary, isOffline } = useAtlas()

  return (
    <header className="border-b border-border bg-surface">
      {/* Fio de gradiente: único enfeite com a cor da marca. */}
      <div
        aria-hidden
        className="h-0.5 w-full"
        style={{
          background: 'linear-gradient(90deg, var(--brand-strong), var(--brand-soft))',
        }}
      />
      <div className="mx-auto flex h-14 w-full max-w-[1600px] items-center gap-3 px-4 sm:h-16 sm:gap-6 sm:px-6">
        <Link
          href="/"
          className="flex shrink-0 items-center gap-3 rounded-md py-2"
          aria-label="ATLAS, ir para a visão geral"
        >
          <Image
            src="/brand/atlas-logo.png"
            alt="ATLAS"
            width={72}
            height={36}
            priority
            className="h-8 w-auto sm:h-9"
          />
          <span className="hidden text-xs text-muted lg:block">
            {structure?.campus.name ?? 'Campus'}
          </span>
        </Link>

        {/* No mobile a navegação mora na barra inferior, ao alcance do polegar. */}
        <nav className="hidden items-center gap-1 md:flex" aria-label="Navegação principal">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? 'page' : undefined}
                className={`rounded-md px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-brand/15 font-medium text-brand-soft'
                    : 'text-muted hover:bg-surface-2 hover:text-text'
                }`}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="ml-auto flex min-w-0 flex-1 items-center justify-end gap-3 sm:flex-none sm:gap-4">
          <SpaceSearch />
          <p
            className="flex shrink-0 items-center gap-2 text-xs text-muted"
            title={isOffline ? 'Sem resposta da API' : 'Dados atualizados'}
          >
            <span
              aria-hidden
              className="size-2 rounded-full"
              style={{
                backgroundColor: isOffline ? 'var(--status-over)' : 'var(--status-normal)',
              }}
            />
            <span className="tabular hidden lg:inline">
              {summary ? formatTimeWithSeconds(summary.generated_at) : '--:--:--'}
            </span>
            <span className="sr-only">
              {isOffline ? 'Sem resposta da API' : 'Dados atualizados'}
            </span>
          </p>
        </div>
      </div>
    </header>
  )
}
