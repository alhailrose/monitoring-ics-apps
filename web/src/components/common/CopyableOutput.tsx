import { useState } from "react"

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
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="copyable-output" aria-label={title}>
      <header className="copyable-output-header">
        <strong>{title}</strong>
        <button type="button" className="ops-button" onClick={onCopy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </header>
      <pre>{text}</pre>
    </section>
  )
}
