import { useState } from "react"
import { Copy, Check } from "lucide-react"

type Props = {
  title: string
  text: string
}

export function CopyableOutput({ title, text }: Props) {
  const [copied, setCopied] = useState(false)

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  // If there's no text, don't render the block to avoid empty boxes
  if (!text) return null

  return (
    <section className="copyable-output" aria-label={title}>
      <header className="copyable-output-header">
        <strong>{title}</strong>
        <button
          type="button"
          className="ops-button"
          onClick={onCopy}
          aria-label="Copy to clipboard"
          style={{ minHeight: "2rem", padding: "0 0.75rem", fontSize: "0.8rem", gap: "6px" }}
        >
          {copied ? (
            <>
              <Check size={14} /> Copied
            </>
          ) : (
            <>
              <Copy size={14} /> Copy
            </>
          )}
        </button>
      </header>
      <pre>{text}</pre>
    </section>
  )
}
