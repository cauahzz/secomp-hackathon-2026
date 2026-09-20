/** Título da tela com uma linha de contexto; no mobile o par ocupa menos altura. */
export function PageHeader({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="mb-5 sm:mb-6">
      <h1 className="text-xl font-semibold text-balance text-text sm:text-2xl">{title}</h1>
      <p className="mt-1 text-sm text-pretty text-muted">{hint}</p>
    </div>
  )
}
