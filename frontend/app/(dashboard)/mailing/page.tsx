'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface MailingContact {
  id: string
  customer_id: string | null
  email: string
  name: string | null
  created_at: string
}

interface CustomerOption {
  id: string
  display_name: string
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) ?? {}),
  }
  const res = await fetch(path, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed (${res.status})`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export default function MailingPage() {
  const [contacts, setContacts] = useState<MailingContact[]>([])
  const [customers, setCustomers] = useState<CustomerOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterCustomer, setFilterCustomer] = useState('')

  // Add form
  const [formEmail, setFormEmail] = useState('')
  const [formName, setFormName] = useState('')
  const [formCustomer, setFormCustomer] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const loadContacts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const qs = filterCustomer ? `?customer_id=${filterCustomer}` : ''
      const rows = await apiFetch<MailingContact[]>(`/api/mailing${qs}`)
      setContacts(rows)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [filterCustomer])

  useEffect(() => {
    apiFetch<{ customers: Array<{ id: string; display_name: string }> }>('/api/customers')
      .then(data => setCustomers((data.customers || []).map(c => ({ id: c.id, display_name: c.display_name }))))
      .catch(() => setCustomers([]))
  }, [])

  useEffect(() => { loadContacts() }, [loadContacts])

  const addContact = async () => {
    if (!formEmail.trim()) return
    setSaving(true)
    setFormError(null)
    try {
      await apiFetch('/api/mailing', {
        method: 'POST',
        body: JSON.stringify({
          customer_id: formCustomer || null,
          email: formEmail.trim(),
          name: formName.trim() || null,
        }),
      })
      setFormEmail('')
      setFormName('')
      setFormCustomer('')
      await loadContacts()
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Gagal menyimpan')
    } finally {
      setSaving(false)
    }
  }

  const deleteContact = async (id: string) => {
    try {
      await apiFetch(`/api/mailing/${id}`, { method: 'DELETE' })
      await loadContacts()
    } catch {
      // ignore
    }
  }

  const customerName = (id: string | null) =>
    id ? (customers.find(c => c.id === id)?.display_name ?? id) : '-'

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Mailing List</h1>
        <p className="text-sm text-muted-foreground mt-1">Daftar email kontak per customer untuk pengiriman notifikasi.</p>
      </div>

      {/* Add form */}
      <div className="rounded-lg border p-4 space-y-3 bg-muted/20">
        <p className="text-sm font-medium">Tambah Kontak</p>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="space-y-1">
            <Label className="text-xs">Customer</Label>
            <Select value={formCustomer || '_none'} onValueChange={v => setFormCustomer(v === '_none' ? '' : v)}>
              <SelectTrigger className="h-8 w-44 text-xs"><SelectValue placeholder="Semua / Tanpa customer" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">Tanpa customer</SelectItem>
                {customers.map(c => <SelectItem key={c.id} value={c.id} className="text-xs">{c.display_name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Email <span className="text-destructive">*</span></Label>
            <Input
              className="h-8 text-xs w-56"
              placeholder="email@customer.com"
              value={formEmail}
              onChange={e => setFormEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addContact()}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Nama (opsional)</Label>
            <Input
              className="h-8 text-xs w-40"
              placeholder="Nama penerima"
              value={formName}
              onChange={e => setFormName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addContact()}
            />
          </div>
          <Button size="sm" onClick={addContact} disabled={saving || !formEmail.trim()}>
            {saving ? 'Menyimpan...' : 'Tambah'}
          </Button>
        </div>
        {formError && <p className="text-xs text-destructive">{formError}</p>}
      </div>

      {/* Filter */}
      <div className="flex gap-3 items-end">
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Filter Customer</Label>
          <Select value={filterCustomer || '_all'} onValueChange={v => setFilterCustomer(v === '_all' ? '' : v)}>
            <SelectTrigger className="h-8 w-44 text-xs"><SelectValue placeholder="Semua" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="_all">Semua</SelectItem>
              {customers.map(c => <SelectItem key={c.id} value={c.id} className="text-xs">{c.display_name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground pb-1">{contacts.length} kontak</p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Customer</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Nama</TableHead>
              <TableHead className="w-20" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-sm text-muted-foreground">Loading...</TableCell>
              </TableRow>
            ) : contacts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-sm text-muted-foreground">Belum ada kontak</TableCell>
              </TableRow>
            ) : (
              contacts.map(c => (
                <TableRow key={c.id}>
                  <TableCell>
                    <Badge variant="outline" className="text-xs font-normal">
                      {customerName(c.customer_id)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm font-mono">{c.email}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{c.name || '-'}</TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-xs px-2 text-destructive hover:text-destructive"
                      onClick={() => deleteContact(c.id)}
                    >
                      Hapus
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
