import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'

import { AppHeader } from '@/components/app-header'
import { ApiStatusBanner } from '@/components/api-status-banner'
import { AtlasProvider } from '@/components/atlas-provider'
import { MobileNav } from '@/components/mobile-nav'
import { SpaceDetailPanel } from '@/components/space-detail-panel'
import './globals.css'

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'ATLAS — Ocupação do campus',
  description: 'Mapa interativo e ocupação em tempo real dos ambientes da UNIFEI Itabira.',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // A barra inferior encosta na borda: o conteúdo precisa das áreas seguras.
  viewportFit: 'cover',
  colorScheme: 'dark',
  // Espelha --bg; a meta tag não lê var().
  themeColor: '#05070A',
}

export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="pt-BR" className={`${inter.variable} h-full`}>
      <body className="flex min-h-full flex-col">
        <a href="#conteudo" className="skip-link">
          Pular para o conteúdo
        </a>
        <AtlasProvider>
          {/* Cabeçalho e aviso grudam juntos: o alerta de API fora do ar não
              some ao rolar a tabela. */}
          <div className="sticky top-0 z-40">
            <AppHeader />
            <ApiStatusBanner />
          </div>
          <main
            id="conteudo"
            className="page-main mx-auto w-full max-w-[1600px] flex-1 px-4 py-5 sm:px-6 sm:py-6"
          >
            {children}
          </main>
          <MobileNav />
          <SpaceDetailPanel />
        </AtlasProvider>
      </body>
    </html>
  )
}
