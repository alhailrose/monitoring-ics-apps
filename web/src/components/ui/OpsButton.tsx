import type { ButtonHTMLAttributes } from "react"

type OpsButtonProps = ButtonHTMLAttributes<HTMLButtonElement>

export function OpsButton({ className = "", type = "button", ...props }: OpsButtonProps) {
  const mergedClassName = ["ops-button", className].filter(Boolean).join(" ")
  return <button className={mergedClassName} type={type} {...props} />
}
