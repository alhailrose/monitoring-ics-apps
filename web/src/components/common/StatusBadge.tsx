import type { CheckStatus } from "../../types/api"

type StatusVariant = "ok" | "warn" | "error" | "alarm" | "no_data"

type Props = {
  status: CheckStatus | string
}

const toVariant = (status: string): StatusVariant => {
  const normalized = status.trim().toUpperCase()

  if (normalized === "OK") return "ok"
  if (normalized === "WARN") return "warn"
  if (normalized === "ERROR") return "error"
  if (normalized === "ALARM") return "alarm"
  return "no_data"
}

export function StatusBadge({ status }: Props) {
  const label = status.trim().toUpperCase() || "NO_DATA"
  const variant = toVariant(label)

  return (
    <span className="status-badge" data-status={variant}>
      {label}
    </span>
  )
}
