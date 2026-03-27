'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { HugeiconsIcon } from '@hugeicons/react'
import { UserAdd01Icon, Delete01Icon } from '@hugeicons/core-free-icons'

async function appApiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) ?? {}),
  }

  const res = await fetch(path, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    let detail = `Request failed (${res.status})`
    if (body && typeof body === 'object' && 'detail' in body) {
      const rawDetail = (body as { detail: unknown }).detail
      if (Array.isArray(rawDetail)) {
        const first = rawDetail[0] as { msg?: unknown } | undefined
        if (first?.msg) {
          detail = String(first.msg)
        }
      } else if (rawDetail) {
        detail = String(rawDetail)
      }
    }
    throw new Error(detail)
  }

  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

interface User {
  id: string
  username: string
  role: 'user' | 'super_user'
  is_active: boolean
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState({ username: '', password: '', role: 'user' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await appApiFetch<User[]>('/api/users')
      setUsers(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!form.username || !form.password) return
    if (form.password.length < 8) {
      setError('Password minimal 8 karakter')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await appApiFetch('/api/users', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      setAddOpen(false)
      setForm({ username: '', password: '', role: 'user' })
      load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create user')
    } finally {
      setSaving(false)
    }
  }

  const handleRoleChange = async (userId: string, role: string) => {
    await appApiFetch(`/api/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    })
    load()
  }

  const handleDeactivate = async (userId: string) => {
    if (!confirm('Deactivate this user?')) return
    await appApiFetch(`/api/users/${userId}`, { method: 'DELETE' })
    load()
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">User Management</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage dashboard access</p>
        </div>
        <Button size="sm" className="gap-1.5" onClick={() => setAddOpen(true)}>
          <HugeiconsIcon icon={UserAdd01Icon} strokeWidth={2} className="size-4" />
          Add User
        </Button>
      </div>

      <div className="rounded-lg border border-border/50 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Username</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-sm text-muted-foreground py-8">
                  Loading…
                </TableCell>
              </TableRow>
            ) : users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-sm text-muted-foreground py-8">
                  No users found
                </TableCell>
              </TableRow>
            ) : (
              users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-mono text-sm">{u.username}</TableCell>
                  <TableCell>
                    <Select
                      value={u.role}
                      onValueChange={(v) => handleRoleChange(u.id, v)}
                    >
                      <SelectTrigger className="h-7 w-32 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="user">User</SelectItem>
                        <SelectItem value="super_user">Super User</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Badge
                      className={
                        u.is_active
                          ? 'h-5 px-2 text-[10px] bg-green-500/10 text-green-400 border-green-500/20'
                          : 'h-5 px-2 text-[10px] bg-red-500/10 text-red-400 border-red-500/20'
                      }
                    >
                      {u.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {u.is_active && (
                      <button
                        className="text-muted-foreground hover:text-destructive transition-colors"
                        onClick={() => handleDeactivate(u.id)}
                        aria-label="Deactivate user"
                      >
                        <HugeiconsIcon icon={Delete01Icon} strokeWidth={2} className="size-4" />
                      </button>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Add user dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Add User</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                placeholder="e.g. john"
                autoComplete="off"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                placeholder="Min 8 characters"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Role</Label>
              <Select value={form.role} onValueChange={(v) => setForm((f) => ({ ...f, role: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="super_user">Super User</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving ? 'Creating…' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
