import { CampusMap } from '@/components/campus-map'
import { PageHeader } from '@/components/page-header'

export const metadata = { title: 'Mapa — ATLAS' }

export default function MapPage() {
  return (
    <>
      <PageHeader
        title="Mapa"
        hint="Do campus ao ambiente: escolha um prédio, depois um andar, depois a sala."
      />
      <CampusMap />
    </>
  )
}
