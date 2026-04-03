'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function MyConfigPage() {
  const [content, setContent] = useState('')
  const [username, setUsername] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    fetch('/api/settings/my-aws-config')
      .then((r) => r.json())
      .then((data) => {
        setContent(data.content ?? '')
        setUsername(data.username ?? '')
      })
      .finally(() => setLoading(false))
  }, [])

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
        setMessage({ type: 'success', text: 'Config berhasil disimpan.' })
      } else {
        const body = await res.json()
        setMessage({ type: 'error', text: body.detail ?? 'Gagal menyimpan config.' })
      }
    } catch {
      setMessage({ type: 'error', text: 'Terjadi kesalahan.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6 p-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">My AWS Config</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Konfigurasi AWS pribadi kamu yang digunakan di terminal.
          {username && (
            <span className="ml-1 font-mono text-foreground/70">({username})</span>
          )}
        </p>
      </div>

      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      <div className="rounded-lg border bg-card space-y-0">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h2 className="font-medium text-sm">~/.aws/config</h2>
          <Button size="sm" onClick={save} disabled={saving || loading}>
            {saving ? 'Menyimpan...' : 'Simpan'}
          </Button>
        </div>
        <textarea
          className="w-full font-mono text-sm bg-transparent resize-none outline-none px-5 py-4 min-h-[400px] leading-relaxed"
          value={loading ? 'Memuat...' : content}
          onChange={(e) => setContent(e.target.value)}
          disabled={loading}
          spellCheck={false}
        />
      </div>

      <div className="rounded-lg border border-dashed bg-muted/30 px-5 py-4 text-sm text-muted-foreground space-y-1">
        <p className="font-medium text-foreground text-xs uppercase tracking-widest mb-2">Cara kerja</p>
        <p>• Config ini disimpan di server dan digunakan saat kamu membuka terminal</p>
        <p>• Setelah disimpan, jalankan <code className="bg-muted px-1 rounded text-xs">aws sso login --sso-session &lt;session&gt;</code> di terminal untuk login</p>
        <p>• Jika tidak menggunakan SSO session, gunakan <code className="bg-muted px-1 rounded text-xs">aws sso login --profile &lt;profile&gt;</code></p>
        <p>• Perubahan berlaku saat kamu membuka sesi terminal baru</p>
      </div>
    </div>
  )
}
