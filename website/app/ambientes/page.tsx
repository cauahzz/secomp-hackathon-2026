import { PageHeader } from '@/components/page-header'
import { SpacesTable } from '@/components/spaces-table'

export const metadata = { title: 'Ambientes — ATLAS' }

export default function SpacesPage() {
  return (
    <>
      <PageHeader
        title="Ambientes"
        hint="Todos os ambientes monitorados. Selecione um para ver o detalhe e o histórico."
      />
      <SpacesTable />
    </>
  )
}
