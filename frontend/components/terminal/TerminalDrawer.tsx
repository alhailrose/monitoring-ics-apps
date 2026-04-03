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

function stripAnsi(value: string): string {
  return value
    // eslint-disable-next-line no-control-regex
    .replace(/\x1b\[[0-9;]*[A-Za-z]/g, '')
    // eslint-disable-next-line no-control-regex
    .replace(/\x1b\][^\x07]*\x07/g, '')
}

function CopyableCommand({ cmd, color = 'emerald' }: { cmd: string; color?: 'emerald' | 'violet' }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(cmd)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  const colorClass = color === 'violet'
    ? 'text-violet-300 bg-violet-950/30 border-violet-900/40'
    : 'text-emerald-300 bg-emerald-950/30 border-emerald-900/40'
  return (
    <div className="flex items-center gap-2 group">
      <code className={`flex-1 font-mono text-[11px] border px-2 py-1 rounded truncate ${colorClass}`}>
        {cmd}
      </code>
      <button
        onClick={copy}
        className="shrink-0 text-slate-500 hover:text-slate-200 transition-colors opacity-0 group-hover:opacity-100 p-0.5"
        aria-label="Copy command"
      >
        {copied
          ? <span className={`text-[10px] font-bold ${color === 'violet' ? 'text-violet-400' : 'text-emerald-400'}`}>✓</span>
          : <HugeiconsIcon icon={Copy01Icon} strokeWidth={2} className="size-3.5" />
        }
      </button>
    </div>
  )
}

function LoginHint({ autoExpand = false }: { autoExpand?: boolean }) {
  const [open, setOpen] = useState(autoExpand)
  const [ssoSessions, setSsoSessions] = useState<string[]>([])
  const [loginProfiles, setLoginProfiles] = useState<string[]>([])

  // Auto-expand when backend signals first session
  useEffect(() => { if (autoExpand) setOpen(true) }, [autoExpand])

  useEffect(() => {
    fetch('/api/terminal-token', { cache: 'no-store' })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(({ token }) => Promise.all([
        apiFetch<{ sso_sessions: string[] }>('/profiles/sso-sessions', { token }),
        apiFetch<{ login_session_profiles: string[] }>('/profiles/login-session-profiles', { token }),
      ]))
      .then(([sso, login]) => {
        setSsoSessions(sso.sso_sessions)
        setLoginProfiles(login.login_session_profiles)
      })
      .catch(() => {})
  }, [])

  const hasAny = ssoSessions.length > 0 || loginProfiles.length > 0

  return (
    <div className="border-b border-border/30 bg-[#0d1117] text-xs select-none">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 w-full px-3 py-1.5 text-slate-300 hover:text-white transition-colors"
      >
        <HugeiconsIcon icon={InformationCircleIcon} strokeWidth={2} className="size-3.5 shrink-0 text-sky-400" />
        <span className="font-semibold tracking-wide">AWS Login</span>
        {autoExpand && !open && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 font-medium">
            Setup diperlukan
          </span>
        )}
        <span className="ml-auto text-slate-500 text-[10px]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-3">
          {autoExpand && (
            <div className="rounded border border-sky-500/20 bg-sky-950/30 px-3 py-2">
              <p className="text-sky-300 font-semibold mb-0.5">Selamat datang! Setup AWS pertama kali:</p>
              <p className="text-slate-400">
                Jalankan salah satu perintah di bawah di terminal untuk login ke AWS.
                Buka URL yang muncul di browser, masukkan kode verifikasi, lalu kembali ke terminal.
              </p>
            </div>
          )}

          {!hasAny && (
            <p className="text-amber-400/80 italic">
              ~/.aws/config belum ada atau tidak ada sso-session / login_session profile.
              Hubungi admin untuk setup config.
            </p>
          )}

          {ssoSessions.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-slate-400">
                <span className="text-emerald-400 font-semibold">SSO session</span>
                {' '}— salin perintah, jalankan di terminal, buka URL di browser lalu masukkan kodenya.
              </p>
              {ssoSessions.map(s => (
                <CopyableCommand key={s} cmd={`aws sso login --sso-session ${s} --use-device-code`} color="emerald" />
              ))}
            </div>
          )}

          {loginProfiles.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-slate-400">
                <span className="text-violet-400 font-semibold">login_session profile</span>
                {' '}— jalankan di terminal, buka URL di browser, lalu paste kode balik ke terminal.
              </p>
              {loginProfiles.map(p => (
                <CopyableCommand key={p} cmd={`aws login --remote --profile ${p}`} color="violet" />
              ))}
            </div>
          )}

          <div className="space-y-1.5">
            <p className="text-slate-400">
              <span className="text-amber-300 font-semibold">Access key profile</span>
              {' '}— kalau tidak pakai SSO, buat profile dengan access key di terminal.
            </p>
            <CopyableCommand cmd="aws configure --profile monitoring" color="emerald" />
          </div>
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

const DEFAULT_HEIGHT = 460
const MIN_HEIGHT = 200
const MAX_HEIGHT = 800

export function TerminalDrawer() {
  const { open, hide } = useTerminal()
  const [status, setStatus] = useState<Status>('connecting')
  const [height, setHeight] = useState(DEFAULT_HEIGHT)
  const [minimized, setMinimized] = useState(false)
  const [firstSession, setFirstSession] = useState(false)
  const [autoFollow, setAutoFollow] = useState(true)
  const [copyNotice, setCopyNotice] = useState('')
  const hasConnectedOnce = useRef(false)
  const autoFollowRef = useRef(true)

  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const activeTokenRef = useRef<string | null>(null)
  const outputBufferRef = useRef('')
  const viewportCleanupRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    autoFollowRef.current = autoFollow
  }, [autoFollow])

  const flashCopyNotice = useCallback((message: string) => {
    setCopyNotice(message)
    window.setTimeout(() => setCopyNotice(''), 1400)
  }, [])

  const copySelection = useCallback(async () => {
    const selected = termRef.current?.getSelection() ?? ''
    if (!selected.trim()) {
      flashCopyNotice('No selection')
      return
    }
    await navigator.clipboard.writeText(selected)
    flashCopyNotice('Selection copied')
  }, [flashCopyNotice])

  const copyOutput = useCallback(async () => {
    const payload = outputBufferRef.current.trim()
    if (!payload) {
      flashCopyNotice('No output yet')
      return
    }
    await navigator.clipboard.writeText(payload)
    flashCopyNotice('Output copied')
  }, [flashCopyNotice])

  const resumeFollow = useCallback(() => {
    setAutoFollow(true)
    termRef.current?.scrollToBottom()
  }, [])

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

  const fetchTerminalToken = useCallback(async (): Promise<string | null> => {
    const res = await fetch('/api/terminal-token', { cache: 'no-store' })
    if (!res.ok) return null
    const payload = await res.json() as { token?: string }
    return payload.token ?? null
  }, [])

  // ── Connect ────────────────────────────────────────────────────────────────
  const connect = useCallback(async () => {
    setStatus('connecting')

    const token = await fetchTerminalToken()
    if (!token) { setStatus('disconnected'); return }
    activeTokenRef.current = token

    const { Terminal } = await import('@xterm/xterm')
    const { FitAddon } = await import('@xterm/addon-fit')
    const { WebLinksAddon } = await import('@xterm/addon-web-links')

    // Dispose previous instances
    if (termRef.current) { termRef.current.dispose(); termRef.current = null }
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null }
    if (viewportCleanupRef.current) { viewportCleanupRef.current(); viewportCleanupRef.current = null }
    outputBufferRef.current = ''
    setAutoFollow(true)
    setFirstSession(false)

    const term = new Terminal({
      fontSize: 13,
      cursorBlink: true,
      scrollOnUserInput: true,     // scroll to bottom whenever user types
      scrollback: 5000,            // keep more history
      rightClickSelectsWord: true,
      theme: {
        background: '#0a0a0a',
        foreground: '#e2e8f0',
        cursor: '#7dd3fc',
        selectionBackground: '#3b82f680',
        black: '#0a0a0a', brightBlack: '#475569',
        red: '#f87171', brightRed: '#fca5a5',
        green: '#4ade80', brightGreen: '#86efac',
        yellow: '#fbbf24', brightYellow: '#fde68a',
        blue: '#60a5fa', brightBlue: '#93c5fd',
        magenta: '#c084fc', brightMagenta: '#d8b4fe',
        cyan: '#22d3ee', brightCyan: '#67e8f9',
        white: '#e2e8f0', brightWhite: '#f8fafc',
      },
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.loadAddon(new WebLinksAddon())

    // containerRef is always mounted — safe to attach here
    if (containerRef.current) {
      term.open(containerRef.current)
      fitAddon.fit()

      const viewport = containerRef.current.querySelector('.xterm-viewport') as HTMLElement | null
      if (viewport) {
        const onScroll = () => {
          const atBottom = viewport.scrollTop + viewport.clientHeight >= viewport.scrollHeight - 4
          if (!atBottom && autoFollowRef.current) {
            setAutoFollow(false)
            return
          }
          if (atBottom && !autoFollowRef.current) {
            setAutoFollow(true)
          }
        }
        viewport.addEventListener('scroll', onScroll)
        viewportCleanupRef.current = () => viewport.removeEventListener('scroll', onScroll)
      }
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
      // Check for JSON control messages from backend
      if (typeof e.data === 'string') {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'first_session') {
            setFirstSession(true)
            return
          }
        } catch {
          // Not JSON — fall through to terminal write
        }
      }
      const data = e.data instanceof ArrayBuffer ? new Uint8Array(e.data) : (e.data as string)
      const textChunk = typeof data === 'string' ? data : new TextDecoder().decode(data)
      outputBufferRef.current += stripAnsi(textChunk)
      if (outputBufferRef.current.length > 250_000) {
        outputBufferRef.current = outputBufferRef.current.slice(-250_000)
      }

      term.write(data, () => {
        if (autoFollowRef.current) {
          term.scrollToBottom()
        }
      })
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
  }, [fetchTerminalToken])

  // ── Connect on first open ──────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return

    let cancelled = false
    const ensureConnection = async () => {
      const latestToken = await fetchTerminalToken()
      if (cancelled) return

      const tokenChanged = Boolean(
        latestToken &&
        activeTokenRef.current &&
        latestToken !== activeTokenRef.current,
      )
      const wsConnected = wsRef.current?.readyState === WebSocket.OPEN

      if (!hasConnectedOnce.current || tokenChanged || !wsConnected) {
        await connect()
      }
    }

    void ensureConnection()
    return () => { cancelled = true }
  }, [open, connect, fetchTerminalToken])

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
      viewportCleanupRef.current?.()
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
          className="absolute top-0 left-0 right-0 h-2 cursor-ns-resize group flex items-center justify-center"
          onMouseDown={onDragStart}
        >
          <div className="w-10 h-0.5 rounded-full bg-border/50 group-hover:bg-primary/60 transition-colors" />
        </div>
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

        {!minimized && (
          <button
            className="text-[11px] text-muted-foreground hover:text-foreground transition-colors px-1.5 py-0.5"
            onClick={copySelection}
            aria-label="Copy selected terminal text"
          >
            Copy selected
          </button>
        )}

        {!minimized && (
          <button
            className="text-[11px] text-muted-foreground hover:text-foreground transition-colors px-1.5 py-0.5"
            onClick={copyOutput}
            aria-label="Copy terminal output"
          >
            Copy output
          </button>
        )}

        {!minimized && !autoFollow && (
          <button
            className="text-[11px] text-sky-300 hover:text-sky-200 transition-colors px-1.5 py-0.5"
            onClick={resumeFollow}
            aria-label="Resume follow output"
          >
            Follow output
          </button>
        )}

        {!minimized && copyNotice && (
          <span className="text-[11px] text-emerald-300">{copyNotice}</span>
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
      {!minimized && <LoginHint autoExpand={firstSession} />}

      {/* xterm container — always in DOM, hidden via CSS when minimized */}
      <div
        ref={containerRef}
        className={cn('flex-1 overflow-hidden', minimized && 'hidden')}
      />
    </div>
  )
}
