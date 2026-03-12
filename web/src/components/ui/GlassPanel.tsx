import type { HTMLAttributes, ReactNode } from "react"

type GlassPanelProps = HTMLAttributes<HTMLElement> & {
  as?: "section" | "article" | "div"
  children: ReactNode
}

export function GlassPanel({
  as: Element = "section",
  className = "",
  children,
  ...props
}: GlassPanelProps) {
  const mergedClassName = ["ops-glass-panel", className].filter(Boolean).join(" ")
  return (
    <Element className={mergedClassName} {...props}>
      {children}
    </Element>
  )
}
