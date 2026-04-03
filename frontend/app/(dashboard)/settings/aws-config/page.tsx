'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface UserRow {
  id: string
  username: string
  is_active: boolean
}

export default function AwsConfigPage() {
  const [content, setContent] = useState('')
  const [isDefault, setIsDefault] = useState(true)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [applying, setApplying] = useState(false)
  const [applyUsername, setApplyUsername] = useState('')
  const [usernames, setUsernames] = useState<string[]>([])
  const [usersLoading, setUsersLoading] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Per-user config viewer/editor
  const [selectedUser, setSelectedUser] = useState('')
  const [userConfig, setUserConfig] = useState('')
  const [userConfigLoading, setUserConfigLoading] = useState(false)
  const [userConfigSaving, setUserConfigSaving] = useState(false)
  const [userConfigMsg, setUserConfigMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const loadedUserRef = useRef('')

  useEffect(() => {
    fetch('/api/settings/aws-template')
      .then(r => r.json())
      .then(data => {
        setContent(data.content ?? '')
        setIsDefault(data.is_default ?? true)
      })
      .finally(() => setLoading(false))

    fetch('/api/users')
      .then(async (r) => {
        if (!r.ok) return [] as UserRow[]
        return r.json() as Promise<UserRow[]>
      })
      .then((rows) => {
        const activeUsernames = rows
          .filter((u) => u.is_active)
          .map((u) => u.username)
          .sort((a, b) => a.localeCompare(b))
        setUsernames(activeUsernames)
      })
      .finally(() => setUsersLoading(false))
  }, [])

  const save = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const res = await fetch('/api/settings/aws-template', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      if (res.ok) {
        setIsDefault(false)
        setMessage({ type: 'success', text: 'Template berhasil disimpan.' })
      } else {
        const body = await res.json()
        setMessage({ type: 'error', text: body.detail ?? 'Gagal menyimpan template.' })
      }
    } catch {
      setMessage({ type: 'error', text: 'Terjadi kesalahan.' })
    } finally {
      setSaving(false)
    }
  }

  const loadUserConfig = async (username: string) => {
    if (!username) return
    setUserConfigLoading(true)
    setUserConfigMsg(null)
    try {
      const res = await fetch(`/api/settings/user-aws-config/${encodeURIComponent(username)}`)
      const data = await res.json()
      if (res.ok) {
        setUserConfig(data.content ?? '')
        loadedUserRef.current = username
      } else {
        setUserConfigMsg({ type: 'error', text: data.detail ?? 'Gagal mengambil config.' })
      }
    } catch {
      setUserConfigMsg({ type: 'error', text: 'Terjadi kesalahan.' })
    } finally {
      setUserConfigLoading(false)
    }
  }

  const saveUserConfig = async () => {
    if (!selectedUser) return
    setUserConfigSaving(true)
    setUserConfigMsg(null)
    try {
      const res = await fetch(`/api/settings/user-aws-config/${encodeURIComponent(selectedUser)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: userConfig }),
      })
      const data = await res.json()
      if (res.ok) {
        setUserConfigMsg({ type: 'success', text: `Config ${selectedUser} berhasil disimpan.` })
      } else {
        setUserConfigMsg({ type: 'error', text: data.detail ?? 'Gagal menyimpan config.' })
      }
    } catch {
      setUserConfigMsg({ type: 'error', text: 'Terjadi kesalahan.' })
    } finally {
      setUserConfigSaving(false)
    }
  }

  const applyToUser = async () => {
    if (!applyUsername.trim()) return
    setApplying(true)
    setMessage(null)
    try {
      const res = await fetch('/api/settings/aws-template/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: applyUsername.trim() }),
      })
      const body = await res.json()
      if (res.ok) {
        setMessage({ type: 'success', text: body.message })
        setApplyUsername('')
      } else {
        setMessage({ type: 'error', text: body.detail ?? 'Gagal menerapkan template.' })
      }
    } catch {
      setMessage({ type: 'error', text: 'Terjadi kesalahan.' })
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="space-y-8 p-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">Template AWS Config</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Template ini digunakan sebagai konfigurasi AWS default untuk setiap user terminal.
          Saat user pertama kali membuka terminal, config ini otomatis diterapkan.
        </p>
      </div>

      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Template editor */}
      <div className="rounded-lg border bg-card space-y-0">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <div className="flex items-center gap-2">
            <h2 className="font-medium text-sm">~/.aws/aws-config.template</h2>
            {isDefault && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                default (belum disimpan)
              </span>
            )}
          </div>
          <Button size="sm" onClick={save} disabled={saving || loading}>
            {saving ? 'Menyimpan...' : 'Simpan Template'}
          </Button>
        </div>
        <textarea
          className="w-full font-mono text-sm bg-transparent resize-none outline-none px-5 py-4 min-h-[320px] leading-relaxed"
          value={loading ? 'Memuat...' : content}
          onChange={e => setContent(e.target.value)}
          disabled={loading}
          spellCheck={false}
        />
      </div>

      {/* Apply to user */}
      <div className="rounded-lg border bg-card p-5 space-y-4">
        <div>
          <h2 className="font-medium text-sm">Terapkan ke User</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Salin template ke direktori AWS config milik user tertentu. Cocok untuk onboarding atau
            reset config user. Template yang digunakan adalah yang sudah disimpan di atas.
          </p>
        </div>
        <div className="flex gap-3">
          {usernames.length > 0 ? (
            <Select value={applyUsername} onValueChange={setApplyUsername} disabled={usersLoading}>
              <SelectTrigger className="flex-1 font-mono text-sm">
                <SelectValue placeholder={usersLoading ? 'Memuat user...' : 'Pilih user'} />
              </SelectTrigger>
              <SelectContent>
                {usernames.map((username) => (
                  <SelectItem key={username} value={username}>
                    {username}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              placeholder="username (contoh: bagus_syafiq)"
              value={applyUsername}
              onChange={e => setApplyUsername(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applyToUser()}
              className="flex-1 font-mono text-sm"
            />
          )}
          <Button onClick={applyToUser} disabled={applying || !applyUsername.trim() || isDefault} variant="outline">
            {applying ? 'Menerapkan...' : 'Apply'}
          </Button>
        </div>
        {usernames.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Menampilkan user aktif. Jika user belum ada, tambahkan dulu di Settings → Users.
          </p>
        )}
        {isDefault && (
          <p className="text-xs text-muted-foreground">
            Simpan template terlebih dahulu sebelum menerapkan ke user.
          </p>
        )}
      </div>

      {/* Per-user config viewer/editor */}
      <div className="rounded-lg border bg-card space-y-0">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h2 className="font-medium text-sm">Config Per User</h2>
        </div>
        <div className="p-5 space-y-4">
          <p className="text-xs text-muted-foreground">
            Lihat dan edit config AWS milik user tertentu secara langsung tanpa perlu terminal.
          </p>

          {userConfigMsg && (
            <Alert variant={userConfigMsg.type === 'error' ? 'destructive' : 'default'}>
              <AlertDescription>{userConfigMsg.text}</AlertDescription>
            </Alert>
          )}

          <div className="flex gap-3">
            <Select
              value={selectedUser}
              onValueChange={(val) => {
                setSelectedUser(val)
                setUserConfig('')
                loadedUserRef.current = ''
                setUserConfigMsg(null)
              }}
              disabled={usersLoading}
            >
              <SelectTrigger className="flex-1 font-mono text-sm">
                <SelectValue placeholder={usersLoading ? 'Memuat user...' : 'Pilih user'} />
              </SelectTrigger>
              <SelectContent>
                {usernames.map((u) => (
                  <SelectItem key={u} value={u}>{u}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              disabled={!selectedUser || userConfigLoading}
              onClick={() => loadUserConfig(selectedUser)}
            >
              {userConfigLoading ? 'Memuat...' : 'Lihat Config'}
            </Button>
          </div>

          {loadedUserRef.current && (
            <>
              <textarea
                className="w-full font-mono text-sm bg-transparent resize-none outline-none border rounded-md px-4 py-3 min-h-[260px] leading-relaxed"
                value={userConfig}
                onChange={(e) => setUserConfig(e.target.value)}
                spellCheck={false}
              />
              <div className="flex justify-end">
                <Button
                  size="sm"
                  onClick={saveUserConfig}
                  disabled={userConfigSaving}
                >
                  {userConfigSaving ? 'Menyimpan...' : `Simpan Config ${selectedUser}`}
                </Button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Info box */}
      <div className="rounded-lg border border-dashed bg-muted/30 px-5 py-4 text-sm text-muted-foreground space-y-1">
        <p className="font-medium text-foreground text-xs uppercase tracking-widest mb-2">Cara kerja</p>
        <p>• Template disimpan di <code className="bg-muted px-1 rounded text-xs">~/.aws/aws-config.template</code> di server</p>
        <p>• Saat user buka terminal pertama kali dan belum punya config, template otomatis diterapkan</p>
        <p>• Gunakan tombol <strong>Apply</strong> untuk reset atau provision manual config user</p>
        <p>• Setelah config diterapkan, jalankan <code className="bg-muted px-1 rounded text-xs">aws sso login --sso-session &lt;session&gt;</code> di terminal untuk login</p>
        <p>• Jika tidak menggunakan SSO session, gunakan <code className="bg-muted px-1 rounded text-xs">aws sso login --profile &lt;profile&gt;</code></p>
        <p>• Status login tiap profile bisa dipantau di halaman <strong>Customers</strong> (kolom Session)</p>
      </div>
    </div>
  )
}
