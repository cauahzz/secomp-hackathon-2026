import { Overview } from '@/components/overview'
import { PageHeader } from '@/components/page-header'

export default function OverviewPage() {
  return (
    <>
      <PageHeader
        title="Visão Geral"
        hint="Quantas pessoas estão no campus agora e como os ambientes estão distribuídos."
      />
      <Overview />
    </>
  )
}
