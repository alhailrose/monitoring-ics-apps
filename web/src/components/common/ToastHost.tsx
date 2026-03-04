import { useCallback, useMemo, useState } from "react"

export type ToastTone = "success" | "error" | "info"

export type ToastItem = {
  id: number
  tone: ToastTone
  message: string
}

export function ToastHost({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: number) => void }) {
  if (toasts.length === 0) {
    return null
  }

  return (
    <div className="toast-host" aria-live="polite" aria-label="Notifications">
      {toasts.map((toast) => (
        <div key={toast.id} className="toast-item" data-tone={toast.tone}>
          <p>{toast.message}</p>
          <button type="button" onClick={() => onDismiss(toast.id)}>
            Dismiss
          </button>
        </div>
      ))}
    </div>
  )
}

export function useToastQueue() {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const pushToast = useCallback((tone: ToastTone, message: string) => {
    const id = Date.now() + Math.floor(Math.random() * 1000)
    setToasts((current) => [...current, { id, tone, message }])
    setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id))
    }, 5000)
  }, [])

  return useMemo(
    () => ({ toasts, pushToast, dismissToast }),
    [dismissToast, pushToast, toasts],
  )
}
