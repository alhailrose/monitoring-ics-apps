'use client'
// Floating terminal drawer — GCP Cloud Shell style, fixed at bottom of viewport
// Always mounted (never unmounted) so xterm instance survives open/close/minimize

import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { HugeiconsIcon } from '@hugeicons/react'
import { RefreshIcon, Cancel01Icon, MinusSignIcon, ArrowUp01Icon, InformationCircleIcon, Copy01Icon } from '@hugeicons/core-free-icons'
import { cn } from '@/lib/utils'
import { useTerminal } from '@/components/terminal/TerminalContext'
import { apiFetch } from '@/lib/api/client'
import type { Terminal } from '@xterm/xterm'
import type { FitAddon } from '@xterm/addon-fit'

function LoginHint() {
  const [open, setOpen] = useState(false)
  const [sessions, setSessions] = useState<string[]>([])
  const [copied, setCopied] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/terminal-token')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(({ token }) => apiFetch<{ sso_sessions: string[] }>('/profiles/sso-sessions', { token }))
      .then(d => setSessions(d.sso_sessions))
      .catch(() => {})
  }, [])

  const copy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(text)
    setTimeout(() => setCopied(null), 1500)
  }

  return (
    <div className="border-b border-border/30 bg-[#0d1117] text-xs select-none">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 w-full px-3 py-1.5 text-slate-300 hover:text-white transition-colors"
      >
        <HugeiconsIcon icon={InformationCircleIcon} strokeWidth={2} className="size-3.5 shrink-0 text-sky-400" />
        <span className="font-semibold tracking-wide">AWS SSO Login</span>
        <span className="ml-auto text-slate-500 text-[10px]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2">
          <p className="text-slate-400 leading-relaxed">
            Gunakan{' '}
            <code className="text-sky-300 bg-sky-950/50 px-1 py-0.5 rounded">--use-device-code</code>
            {' '}— terminal akan tampilkan URL + kode, buka di browser lalu masukkan kodenya.
          </p>
          {sessions.length === 0 ? (
            <p className="text-amber-400/80 italic">
              ~/.aws/config belum ada atau tidak ada sso-session. Buat dulu via terminal di bawah.
            </p>
          ) : (
            <div className="space-y-1.5">
              {sessions.map(s => {
                const cmd = `aws sso login --sso-session ${s} --use-device-code`
                return (
                  <div key={s} className="flex items-center gap-2 group">
                    <code className="flex-1 font-mono text-[11px] text-emerald-300 bg-emerald-950/30 border border-emerald-900/40 px-2 py-1 rounded truncate">
                      {cmd}
                    </code>
                    <button
                      onClick={() => copy(cmd)}
                      className="shrink-0 text-slate-500 hover:text-slate-200 transition-colors opacity-0 group-hover:opacity-100 p-0.5"
                      aria-label="Copy command"
                    >
                      {copied === cmd
                        ? <span className="text-emerald-400 text-[10px] font-bold">✓</span>
                        : <HugeiconsIcon icon={Copy01Icon} strokeWidth={2} className="size-3.5" />
                      }
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

type Status = 'connecting' | 'connected' | 'disconnected'

function StatusDot({ status }: { status: Status }) {
  return (
    <span
      className={cn('inline-block size-2 rounded-full shrink-0', {
        'bg-yellow-400 animate-pulse': status === 'connecting',
        'bg-green-400': status === 'connected',
        'bg-red-400': status === 'disconnected',
      })}
    />
  )
}

const DEFAULT_HEIGHT = 320
const MIN_HEIGHT = 160
const MAX_HEIGHT = 700

export function TerminalDrawer() {
  const { open, hide } = useTerminal()
  const [status, setStatus] = useState<Status>('connecting')
  const [height, setHeight] = useState(DEFAULT_HEIGHT)
  const [minimized, setMinimized] = useState(false)
  const hasConnectedOnce = useRef(false)

  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)

  // ── Resize drag ────────────────────────────────────────────────────────────
  const dragStartY = useRef(0)
  const dragStartH = useRef(0)

  const onDragStart = useCallback((e: React.MouseEvent) => {
    dragStartY.current = e.clientY
    dragStartH.current = height
    const onMove = (ev: MouseEvent) => {
      const delta = dragStartY.current - ev.clientY
      const next = Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, dragStartH.current + delta))
      setHeight(next)
      fitAddonRef.current?.fit()
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      fitAddonRef.current?.fit()
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [height])

  // ── Connect ────────────────────────────────────────────────────────────────
  const connect = useCallback(async () => {
    setStatus('connecting')

    const res = await fetch('/api/terminal-token')
    if (!res.ok) { setStatus('disconnected'); return }
    const { token } = await res.json()

    const { Terminal } = await import('@xterm/xterm')
    const { FitAddon } = await import('@xterm/addon-fit')
    const { WebLinksAddon } = await import('@xterm/addon-web-links')

    // Dispose previous instances
    if (termRef.current) { termRef.current.dispose(); termRef.current = null }
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null }

    const term = new Terminal({ fontSize: 13, cursorBlink: true, theme: { background: '#0a0a0a' } })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.loadAddon(new WebLinksAddon())

    // containerRef is always mounted — safe to attach here
    if (containerRef.current) {
      term.open(containerRef.current)
      fitAddon.fit()
    }

    termRef.current = term
    fitAddonRef.current = fitAddon
    hasConnectedOnce.current = true

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsBase = `${protocol}//${window.location.host}`
    const ws = new WebSocket(`${wsBase}/api/v1/terminal?token=${token}`)
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws

    ws.onopen = () => setStatus('connected')
    ws.onmessage = (e) => {
      term.write(e.data instanceof ArrayBuffer ? new Uint8Array(e.data) : (e.data as string))
    }
    ws.onclose = () => {
      setStatus('disconnected')
      term.write('\r\n\x1b[31m[Connection closed]\x1b[0m\r\n')
    }
    ws.onerror = () => {
      setStatus('disconnected')
      term.write('\r\n\x1b[31m[Connection error]\x1b[0m\r\n')
    }

    term.onData((data) => { if (ws.readyState === WebSocket.OPEN) ws.send(data) })
    term.onResize(({ cols, rows }) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'resize', cols, rows }))
    })
  }, [])

  // ── Connect on first open ──────────────────────────────────────────────────
  useEffect(() => {
    if (open && !hasConnectedOnce.current) {
      connect()
    }
  }, [open, connect])

  // ── ResizeObserver — fit whenever container dimensions actually change ──────
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      if (fitAddonRef.current && !minimized) fitAddonRef.current.fit()
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [minimized])

  // ── Cleanup on unmount ─────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      wsRef.current?.close()
      termRef.current?.dispose()
    }
  }, [])

  // Always render — use CSS to show/hide so xterm DOM is never destroyed
  return (
    <div
      className={cn(
        'fixed bottom-0 left-0 right-0 z-50 flex flex-col shadow-2xl border-t border-border/60 bg-[#0a0a0a] transition-transform duration-200',
        !open && 'translate-y-full pointer-events-none',
      )}
      style={{ height: minimized ? 36 : height }}
      aria-hidden={!open}
    >
      {/* Drag handle — only when expanded */}
      {!minimized && (
        <div
          className="absolute top-0 left-0 right-0 h-1 cursor-ns-resize hover:bg-primary/40 transition-colors"
          onMouseDown={onDragStart}
        />
      )}

      {/* Title bar */}
      <div className="flex items-center gap-2 px-3 h-9 shrink-0 border-b border-border/30 bg-[#111111] select-none">
        <StatusDot status={status} />
        <span className="text-xs font-mono text-muted-foreground flex-1">bash — server</span>

        {status === 'disconnected' && !minimized && (
          <Button
            size="sm"
            variant="ghost"
            className="h-6 text-xs px-2 text-muted-foreground hover:text-foreground"
            onClick={connect}
          >
            <HugeiconsIcon icon={RefreshIcon} strokeWidth={2} className="size-3 mr-1" />
            Reconnect
          </Button>
        )}

        <button
          className="text-muted-foreground hover:text-foreground transition-colors p-1"
          onClick={() => setMinimized((v) => !v)}
          aria-label={minimized ? 'Expand terminal' : 'Minimize terminal'}
        >
          <HugeiconsIcon
            icon={minimized ? ArrowUp01Icon : MinusSignIcon}
            strokeWidth={2}
            className="size-3.5"
          />
        </button>
        <button
          className="text-muted-foreground hover:text-foreground transition-colors p-1"
          onClick={hide}
          aria-label="Close terminal"
        >
          <HugeiconsIcon icon={Cancel01Icon} strokeWidth={2} className="size-3.5" />
        </button>
      </div>

      {/* AWS SSO login hint — only when expanded */}
      {!minimized && <LoginHint />}

      {/* xterm container — always in DOM, hidden via CSS when minimized */}
      <div
        ref={containerRef}
        className={cn('flex-1 overflow-hidden', minimized && 'hidden')}
      />
    </div>
  )
}
