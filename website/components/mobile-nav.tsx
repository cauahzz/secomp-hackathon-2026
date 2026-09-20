'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { NAV_ITEMS } from './nav-items'

/**
 * Barra inferior do mobile: três destinos, altura de polegar e área segura do
 * aparelho respeitada. No desktop a mesma navegação vive no cabeçalho.
 */
export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav
      aria-label="Navegação principal"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface/95 backdrop-blur md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <ul className="mx-auto flex max-w-lg">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href
          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                aria-current={isActive ? 'page' : undefined}
                className={`press relative flex h-16 flex-col items-center justify-center gap-1 text-[0.6875rem] transition-colors ${
                  isActive ? 'text-brand-soft' : 'text-muted'
                }`}
              >
                {/* A cor do item ativo nunca vem sozinha: há o traço e o rótulo. */}
                <span
                  aria-hidden
                  className={`absolute inset-x-5 top-0 h-0.5 rounded-b-full transition-opacity ${
                    isActive ? 'opacity-100' : 'opacity-0'
                  }`}
                  style={{ backgroundColor: 'var(--brand)' }}
                />
                <item.Icon className="size-6" />
                {item.shortLabel}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
