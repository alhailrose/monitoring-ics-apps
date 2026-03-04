import type { InputHTMLAttributes } from "react"

type OpsInputProps = InputHTMLAttributes<HTMLInputElement>

export function OpsInput({ className = "", ...props }: OpsInputProps) {
  const mergedClassName = ["ops-input", className].filter(Boolean).join(" ")
  return <input className={mergedClassName} {...props} />
}
