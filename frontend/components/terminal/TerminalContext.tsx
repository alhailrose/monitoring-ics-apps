'use client'
// Context for toggling the floating terminal drawer from anywhere

import { createContext, useContext, useState } from 'react'

interface TerminalContextValue {
  open: boolean
  toggle: () => void
  show: () => void
  hide: () => void
}

const TerminalContext = createContext<TerminalContextValue | null>(null)

export { TerminalContext }

export function TerminalProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <TerminalContext.Provider
      value={{
        open,
        toggle: () => setOpen((v) => !v),
        show: () => setOpen(true),
        hide: () => setOpen(false),
      }}
    >
      {children}
    </TerminalContext.Provider>
  )
}

export function useTerminal() {
  const ctx = useContext(TerminalContext)
  if (!ctx) throw new Error('useTerminal must be used inside TerminalProvider')
  return ctx
}
