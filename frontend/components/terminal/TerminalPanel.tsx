'use client'
// Client component — xterm.js requires browser APIs

import { useEffect, useRef, useState } from 'react'
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
import { RefreshIcon, Settings01Icon } from '@hugeicons/core-free-icons'
import type { Terminal } from '@xterm/xterm'
import type { FitAddon } from '@xterm/addon-fit'

type Status = 'connecting' | 'connected' | 'disconnected'

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
            <code className="bg-muted px-1 rounded">aws login --remote --profile &lt;profile&gt;</code>{' '}
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

export function TerminalPanel() {
  const [status, setStatus] = useState<Status>('connecting')
  const [configOpen, setConfigOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)

  const connect = async () => {
    setStatus('connecting')

    // Get token from server-side route (httpOnly cookie → token)
    const res = await fetch('/api/terminal-token')
    if (!res.ok) {
      setStatus('disconnected')
      return
    }
    const { token } = await res.json()

    // Dynamically import xterm to avoid SSR issues
    const { Terminal } = await import('@xterm/xterm')
    const { FitAddon } = await import('@xterm/addon-fit')
    const { WebLinksAddon } = await import('@xterm/addon-web-links')

    // Dispose existing terminal
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

    // Build WebSocket URL from NEXT_PUBLIC_API_URL
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
        term.write(new Uint8Array(e.data))
      } else {
        term.write(e.data as string)
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
    <div className="flex flex-col h-full">
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

      <AwsConfigDialog open={configOpen} onClose={() => setConfigOpen(false)} />
    </div>
  )
}
