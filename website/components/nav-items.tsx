import type { ComponentType, SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

/** Traço comum a todos os ícones: nunca são a única pista, sempre têm rótulo. */
function Icon({ children, ...props }: IconProps) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {children}
    </svg>
  )
}

function OverviewIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </Icon>
  )
}

function MapIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 3.2 3.6 5.6A1 1 0 0 0 3 6.5v13a1 1 0 0 0 1.4.9L9 18.4l6 2.4 5.4-2.4a1 1 0 0 0 .6-.9v-13a1 1 0 0 0-1.4-.9L15 5.6z" />
      <path d="M9 3.2v15.2" />
      <path d="M15 5.6v15.2" />
    </Icon>
  )
}

function TableIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M8 6h13M8 12h13M8 18h13" />
      <path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01" />
    </Icon>
  )
}

export interface NavItem {
  href: '/' | '/mapa' | '/ambientes'
  label: string
  /** Rótulo curto da barra inferior, onde a largura é do polegar. */
  shortLabel: string
  Icon: ComponentType<IconProps>
}

export const NAV_ITEMS: NavItem[] = [
  { href: '/', label: 'Visão Geral', shortLabel: 'Geral', Icon: OverviewIcon },
  { href: '/mapa', label: 'Mapa', shortLabel: 'Mapa', Icon: MapIcon },
  { href: '/ambientes', label: 'Ambientes', shortLabel: 'Ambientes', Icon: TableIcon },
]
