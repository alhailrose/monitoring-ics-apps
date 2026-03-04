type Props = {
  title?: string
  detail?: string
}

export function LoadingState({
  title = "Executing checks...",
  detail = "This may take a few minutes. Please wait.",
}: Props) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <div className="loading-spinner" aria-hidden="true" />
      <p className="loading-title">{title}</p>
      <p className="loading-detail">{detail}</p>
    </div>
  )
}
