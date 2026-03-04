const STATUS_VALUES = ["queued", "running", "completed", "failed", "warn"] as const

export type StatusValue = (typeof STATUS_VALUES)[number]
type StatusVariant = StatusValue | "unknown"

type Props = {
  status: string
}

function toStatusVariant(status: string): StatusVariant {
  if ((STATUS_VALUES as readonly string[]).includes(status)) {
    return status as StatusValue
  }

  return "unknown"
}

export function StatusPill({ status }: Props) {
  const statusVariant = toStatusVariant(status)

  return (
    <span className="ops-status-pill" data-status={statusVariant}>
      {statusVariant}
    </span>
  )
}
