import { forwardRef, type SelectHTMLAttributes } from "react"

export interface OpsSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: { label: string; value: string }[]
}

export const OpsSelect = forwardRef<HTMLSelectElement, OpsSelectProps>(
  ({ className, options, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={`ops-select ${className ?? ""}`}
        {...props}
      >
        <option value="" disabled hidden>
          {props.placeholder || "Select an option..."}
        </option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    )
  }
)
OpsSelect.displayName = "OpsSelect"
