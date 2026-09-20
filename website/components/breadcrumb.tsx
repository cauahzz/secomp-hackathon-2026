'use client'

export interface BreadcrumbItem {
  label: string
  /** Ausente no item atual, que não é clicável. */
  onSelect?: () => void
}

export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Trilha de navegação">
      {/* Alvos de 44 px: a trilha é o botão "voltar" do mapa no celular. */}
      <ol className="flex flex-wrap items-center gap-y-1 text-sm">
        {items.map((item, index) => {
          const isLast = index === items.length - 1
          return (
            <li key={`${item.label}-${index}`} className="flex items-center">
              {index > 0 && (
                <span aria-hidden className="px-0.5 text-muted select-none">
                  ›
                </span>
              )}
              {item.onSelect && !isLast ? (
                <button
                  type="button"
                  onClick={item.onSelect}
                  className="press -mx-1 rounded-md px-2 py-2.5 text-muted transition-colors hover:bg-surface-2 hover:text-brand-soft"
                >
                  {item.label}
                </button>
              ) : (
                <span
                  aria-current={isLast ? 'page' : undefined}
                  className="px-1 py-2.5 font-medium text-brand-soft"
                >
                  {item.label}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
