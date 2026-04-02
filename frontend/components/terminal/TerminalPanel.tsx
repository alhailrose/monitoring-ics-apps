'use client'
// Client component — xterm.js requires browser APIs

import { useCallback, useEffect, useRef, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { HugeiconsIcon } from '@hugeicons/react'
import { RefreshIcon, Settings01Icon, Copy01Icon, CheckmarkCircle01Icon } from '@hugeicons/core-free-icons'
import type { Terminal } from '@xterm/xterm'
import type { FitAddon } from '@xterm/addon-fit'

type Status = 'connecting' | 'connected' | 'disconnected'

// ─── SSO login overlay ────────────────────────────────────────────────────────

interface SsoLoginInfo {
  url: string
  code: string
}

// Strip ANSI escape codes from terminal output
function stripAnsi(str: string): string {
  // eslint-disable-next-line no-control-regex
  return str.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '').replace(/\x1b\][^\x07]*\x07/g, '')
}

function SsoOverlay({
  info,
  onDismiss,
}: {
  info: SsoLoginInfo
  onDismiss: () => void
}) {
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [copiedCode, setCopiedCode] = useState(false)

  const copy = async (text: string, which: 'url' | 'code') => {
    await navigator.clipboard.writeText(text)
    if (which === 'url') {
      setCopiedUrl(true)
      setTimeout(() => setCopiedUrl(false), 2000)
    } else {
      setCopiedCode(true)
      setTimeout(() => setCopiedCode(false), 2000)
    }
  }

  return (
    <div className="absolute bottom-4 right-4 z-50 w-80 rounded-lg border border-yellow-500/30 bg-[#1a1a0a] shadow-xl p-4 space-y-3">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold text-yellow-400">AWS SSO Login</p>
        <button onClick={onDismiss} className="text-muted-foreground hover:text-foreground text-xs leading-none">✕</button>
      </div>
      <p className="text-[11px] text-muted-foreground">
        Buka URL di browser, lalu masukkan kode verifikasi:
      </p>

      {/* URL */}
      <div className="space-y-1">
        <p className="text-[10px] text-muted-foreground uppercase tracking-widest">URL</p>
        <div className="flex items-center gap-2">
          <a
            href={info.url}
            target="_blank"
            rel="noreferrer"
            className="flex-1 text-xs text-blue-400 underline truncate hover:text-blue-300"
          >
            {info.url}
          </a>
          <button
            onClick={() => copy(info.url, 'url')}
            className="shrink-0 text-muted-foreground hover:text-foreground"
            title="Copy URL"
          >
            <HugeiconsIcon
              icon={copiedUrl ? CheckmarkCircle01Icon : Copy01Icon}
              strokeWidth={2}
              className={`size-3.5 ${copiedUrl ? 'text-green-400' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Code */}
      <div className="space-y-1">
        <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Kode Verifikasi</p>
        <div className="flex items-center gap-2">
          <span className="flex-1 font-mono text-lg font-bold tracking-[0.2em] text-yellow-300">
            {info.code}
          </span>
          <button
            onClick={() => copy(info.code, 'code')}
            className="shrink-0 text-muted-foreground hover:text-foreground"
            title="Copy kode"
          >
            <HugeiconsIcon
              icon={copiedCode ? CheckmarkCircle01Icon : Copy01Icon}
              strokeWidth={2}
              className={`size-3.5 ${copiedCode ? 'text-green-400' : ''}`}
            />
          </button>
        </div>
      </div>

      <p className="text-[10px] text-muted-foreground">Kode berlaku ±5 menit</p>
    </div>
  )
}

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: Status }) {
  if (status === 'connected') {
    return (
      <Badge className="text-[10px] h-5 px-2 bg-green-500/10 text-green-400 border-green-500/20">
        Connected
      </Badge>
    )
  }
  if (status === 'connecting') {
    return (
      <Badge className="text-[10px] h-5 px-2 bg-yellow-500/10 text-yellow-400 border-yellow-500/20">
        Connecting…
      </Badge>
    )
  }
  return (
    <Badge className="text-[10px] h-5 px-2 bg-red-500/10 text-red-400 border-red-500/20">
      Disconnected
    </Badge>
  )
}

// ─── AWS Config dialog ────────────────────────────────────────────────────────

function AwsConfigDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setMessage(null)
    fetch('/api/settings/my-aws-config')
      .then(r => r.json())
      .then(data => setContent(data.content ?? ''))
      .catch(() => setMessage({ type: 'error', text: 'Gagal memuat config.' }))
      .finally(() => setLoading(false))
  }, [open])

  const save = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const res = await fetch('/api/settings/my-aws-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      if (res.ok) {
        setMessage({ type: 'success', text: 'Config berhasil disimpan. Buka terminal baru untuk menggunakan config terbaru.' })
      } else {
        const body = await res.json()
        setMessage({ type: 'error', text: body.detail ?? 'Gagal menyimpan.' })
      }
    } catch {
      setMessage({ type: 'error', text: 'Terjadi kesalahan.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm">~/.aws/config (milik kamu)</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Edit konfigurasi AWS milikmu. Setelah disimpan, jalankan{' '}
            <code className="bg-muted px-1 rounded">aws sso login --profile &lt;profile&gt;</code>{' '}
            di terminal untuk login SSO.
          </p>

          {message && (
            <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
              <AlertDescription className="text-xs">{message.text}</AlertDescription>
            </Alert>
          )}

          <textarea
            className="w-full font-mono text-xs bg-muted/40 border rounded-md resize-none outline-none focus:ring-1 focus:ring-ring px-3 py-2.5 min-h-[280px] leading-relaxed"
            value={loading ? 'Memuat...' : content}
            onChange={e => setContent(e.target.value)}
            disabled={loading}
            spellCheck={false}
          />
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Batal</Button>
          <Button size="sm" onClick={save} disabled={saving || loading}>
            {saving ? 'Menyimpan...' : 'Simpan Config'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Main terminal panel ──────────────────────────────────────────────────────

// Patterns to detect AWS SSO device auth output
const SSO_URL_RE = /https:\/\/device\.sso\.[a-z0-9-]+\.amazonaws\.com\/[^\s\r\n]*/
const SSO_CODE_RE = /[A-Z]{4}-[A-Z]{4}/

export function TerminalPanel() {
  const [status, setStatus] = useState<Status>('connecting')
  const [configOpen, setConfigOpen] = useState(false)
  const [ssoInfo, setSsoInfo] = useState<SsoLoginInfo | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  // Buffer to accumulate terminal output for SSO detection
  const outputBufRef = useRef('')

  const detectSso = useCallback((chunk: string) => {
    outputBufRef.current += chunk
    // Keep last 2KB to avoid unbounded growth
    if (outputBufRef.current.length > 2048) {
      outputBufRef.current = outputBufRef.current.slice(-2048)
    }
    const clean = stripAnsi(outputBufRef.current)
    const urlMatch = clean.match(SSO_URL_RE)
    const codeMatch = clean.match(SSO_CODE_RE)
    if (urlMatch && codeMatch) {
      setSsoInfo({ url: urlMatch[0], code: codeMatch[0] })
      // Clear buffer so we don't re-trigger
      outputBufRef.current = ''
    }
  }, [])

  const connect = async () => {
    setStatus('connecting')
    setSsoInfo(null)
    outputBufRef.current = ''

    const res = await fetch('/api/terminal-token')
    if (!res.ok) {
      setStatus('disconnected')
      return
    }
    const { token } = await res.json()

    const { Terminal } = await import('@xterm/xterm')
    const { FitAddon } = await import('@xterm/addon-fit')
    const { WebLinksAddon } = await import('@xterm/addon-web-links')

    if (termRef.current) {
      termRef.current.dispose()
      termRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const term = new Terminal({
      fontSize: 13,
      cursorBlink: true,
      copyOnSelect: true,           // auto-copy on mouse select
      theme: { background: '#0a0a0a' },
    })
    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()

    term.loadAddon(fitAddon)
    term.loadAddon(webLinksAddon)

    if (containerRef.current) {
      term.open(containerRef.current)
      fitAddon.fit()
    }

    termRef.current = term
    fitAddonRef.current = fitAddon

    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1'
    const wsUrl = apiUrl
      .replace(/^http/, 'ws')
      .replace(/\/api\/v1\/?$/, '')
    const ws = new WebSocket(`${wsUrl}/api/v1/terminal?token=${token}`)
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws

    ws.onopen = () => setStatus('connected')

    ws.onmessage = (e) => {
      if (e.data instanceof ArrayBuffer) {
        const bytes = new Uint8Array(e.data)
        term.write(bytes)
        detectSso(new TextDecoder().decode(bytes))
      } else {
        term.write(e.data as string)
        detectSso(e.data as string)
      }
    }

    ws.onclose = () => {
      setStatus('disconnected')
      term.write('\r\n\x1b[31m[Connection closed]\x1b[0m\r\n')
    }

    ws.onerror = () => {
      setStatus('disconnected')
      term.write('\r\n\x1b[31m[Connection error]\x1b[0m\r\n')
    }

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    })

    term.onResize(({ cols, rows }) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }))
      }
    })
  }

  useEffect(() => {
    connect()

    const el = containerRef.current
    const ro = el ? new ResizeObserver(() => fitAddonRef.current?.fit()) : null
    if (el && ro) ro.observe(el)

    return () => {
      ro?.disconnect()
      wsRef.current?.close()
      termRef.current?.dispose()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="relative flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-muted/20 shrink-0">
        <span className="text-xs font-mono text-muted-foreground">bash — server</span>
        <div className="flex items-center gap-2">
          <StatusBadge status={status} />
          <Button
            size="sm"
            variant="ghost"
            className="h-6 text-xs px-2 text-muted-foreground hover:text-foreground"
            onClick={() => setConfigOpen(true)}
            title="Configure AWS"
          >
            <HugeiconsIcon icon={Settings01Icon} strokeWidth={2} className="size-3 mr-1" />
            AWS Config
          </Button>
          {status === 'disconnected' && (
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-xs px-2"
              onClick={connect}
            >
              <HugeiconsIcon icon={RefreshIcon} strokeWidth={2} className="size-3 mr-1" />
              Reconnect
            </Button>
          )}
        </div>
      </div>

      {/* Terminal container */}
      <div
        ref={containerRef}
        className="flex-1 bg-[#0a0a0a] overflow-hidden"
      />

      {/* SSO login overlay */}
      {ssoInfo && (
        <SsoOverlay info={ssoInfo} onDismiss={() => setSsoInfo(null)} />
      )}

      <AwsConfigDialog open={configOpen} onClose={() => setConfigOpen(false)} />
    </div>
  )
}
