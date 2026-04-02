'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface Invite {
  id: string
  email: string
  role: string
  accepted: boolean
  expires_at: string
  created_at: string
}

export default function InvitesPage() {
  const [invites, setInvites] = useState<Invite[]>([])
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('user')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const fetchInvites = async () => {
    const res = await fetch('/api/invites')
    if (res.ok) setInvites(await res.json())
  }

  useEffect(() => { fetchInvites() }, [])

  const sendInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage(null)
    try {
      const res = await fetch('/api/invites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role }),
      })
      if (res.ok) {
        setMessage({ type: 'success', text: `Undangan berhasil dikirim ke ${email}` })
        setEmail('')
        fetchInvites()
      } else {
        const body = await res.json()
        setMessage({ type: 'error', text: body.detail ?? 'Gagal mengirim undangan' })
      }
    } catch {
      setMessage({ type: 'error', text: 'Terjadi kesalahan. Coba lagi.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8 p-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">Undangan Pengguna</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Undang anggota tim menggunakan email @icscompute.com. Mereka akan login dengan Google.
        </p>
      </div>

      {/* Send invite form */}
      <div className="rounded-lg border bg-card p-5 space-y-4">
        <h2 className="font-medium">Kirim Undangan</h2>
        {message && (
          <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
            <AlertDescription>{message.text}</AlertDescription>
          </Alert>
        )}
        <form onSubmit={sendInvite} className="flex gap-3">
          <Input
            type="email"
            placeholder="nama@icscompute.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            className="flex-1"
          />
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="user">User</SelectItem>
              <SelectItem value="super_user">Super User</SelectItem>
            </SelectContent>
          </Select>
          <Button type="submit" disabled={loading}>
            {loading ? 'Mengirim...' : 'Kirim'}
          </Button>
        </form>
      </div>

      {/* Invite list */}
      <div className="rounded-lg border bg-card">
        <div className="px-5 py-3 border-b">
          <h2 className="font-medium text-sm">Riwayat Undangan</h2>
        </div>
        {invites.length === 0 ? (
          <p className="px-5 py-4 text-sm text-muted-foreground">Belum ada undangan.</p>
        ) : (
          <div className="divide-y">
            {invites.map(inv => (
              <div key={inv.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium">{inv.email}</p>
                  <p className="text-xs text-muted-foreground">
                    {inv.role} · {new Date(inv.created_at).toLocaleDateString('id-ID')}
                  </p>
                </div>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  inv.accepted
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : new Date(inv.expires_at) < new Date()
                    ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                }`}>
                  {inv.accepted ? 'Diterima' : new Date(inv.expires_at) < new Date() ? 'Expired' : 'Pending'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
