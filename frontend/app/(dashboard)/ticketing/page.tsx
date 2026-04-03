'use client'

import { useEffect, useState } from 'react'
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

type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'

interface Ticket {
  id: string
  ticket_no: string
  customer_id: string | null
  task: string
  pic: string
  status: TicketStatus
  description_solution: string | null
  created_at: string
  ended_at: string | null
}

interface CustomerOption {
  id: string
  display_name: string
}

async function appApiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
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

function formatDate(v: string | null): string {
  if (!v) return '-'
  return new Date(v).toLocaleString('id-ID')
}

function statusBadgeClass(status: TicketStatus): string {
  if (status === 'resolved' || status === 'closed') {
    return 'h-5 px-2 text-[10px] bg-green-500/10 text-green-400 border-green-500/20'
  }
  if (status === 'in_progress') {
    return 'h-5 px-2 text-[10px] bg-amber-500/10 text-amber-400 border-amber-500/20'
  }
  return 'h-5 px-2 text-[10px] bg-sky-500/10 text-sky-400 border-sky-500/20'
}

const defaultForm = {
  customer_id: '',
  task: '',
  pic: '',
  status: 'open' as TicketStatus,
  description_solution: '',
}

export default function TicketingPage() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openCreate, setOpenCreate] = useState(false)
  const [editing, setEditing] = useState<Ticket | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(defaultForm)
  const [customers, setCustomers] = useState<CustomerOption[]>([])

  const loadTickets = async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await appApiFetch<Ticket[]>('/api/tickets')
      setTickets(rows)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load tickets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTickets()
    appApiFetch<{ customers: Array<{ id: string; display_name: string }> }>('/api/customers')
      .then((data) => {
        const items = (data.customers || []).map((c) => ({ id: c.id, display_name: c.display_name }))
        setCustomers(items)
      })
      .catch(() => {
        setCustomers([])
      })
  }, [])

  const openCreateDialog = () => {
    setForm(defaultForm)
    setOpenCreate(true)
  }

  const openEditDialog = (ticket: Ticket) => {
    setEditing(ticket)
    setForm({
      customer_id: ticket.customer_id ?? '',
      task: ticket.task,
      pic: ticket.pic,
      status: ticket.status,
      description_solution: ticket.description_solution ?? '',
    })
  }

  const createTicket = async () => {
    if (!form.customer_id || !form.task.trim() || !form.pic.trim()) return
    setSaving(true)
    setError(null)
    try {
      await appApiFetch('/api/tickets', {
        method: 'POST',
        body: JSON.stringify({
          customer_id: form.customer_id,
          task: form.task.trim(),
          pic: form.pic.trim(),
          status: form.status,
          description_solution: form.description_solution.trim() || null,
        }),
      })
      setOpenCreate(false)
      setForm(defaultForm)
      await loadTickets()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create ticket')
    } finally {
      setSaving(false)
    }
  }

  const updateTicket = async () => {
    if (!editing) return
    setSaving(true)
    setError(null)
    try {
      await appApiFetch(`/api/tickets/${editing.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          customer_id: form.customer_id,
          task: form.task.trim(),
          pic: form.pic.trim(),
          status: form.status,
          description_solution: form.description_solution.trim() || null,
        }),
      })
      setEditing(null)
      setForm(defaultForm)
      await loadTickets()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update ticket')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Ticketing</h1>
          <p className="text-sm text-muted-foreground mt-1">Tracking task operasional dan solusi insiden.</p>
        </div>
        <Button size="sm" onClick={openCreateDialog}>Tambah Ticket</Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Nomor Ticket</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Task</TableHead>
              <TableHead>PIC</TableHead>
              <TableHead>Created At</TableHead>
              <TableHead>Ended At</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Deskripsi/Solusi</TableHead>
              <TableHead className="w-16" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-sm text-muted-foreground">Loading...</TableCell>
              </TableRow>
            ) : tickets.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-sm text-muted-foreground">Belum ada ticket</TableCell>
              </TableRow>
            ) : (
              tickets.map((ticket) => (
                <TableRow key={ticket.id}>
                  <TableCell className="font-mono text-xs">{ticket.ticket_no}</TableCell>
                  <TableCell className="text-sm">
                    {customers.find((c) => c.id === ticket.customer_id)?.display_name ?? '-'}
                  </TableCell>
                  <TableCell className="font-medium">{ticket.task}</TableCell>
                  <TableCell>{ticket.pic}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatDate(ticket.created_at)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatDate(ticket.ended_at)}</TableCell>
                  <TableCell>
                    <Badge className={statusBadgeClass(ticket.status)}>{ticket.status}</Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground max-w-[320px] truncate">
                    {ticket.description_solution || '-'}
                  </TableCell>
                  <TableCell>
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => openEditDialog(ticket)}>
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>Tambah Ticket</DialogTitle></DialogHeader>
          <TicketForm form={form} setForm={setForm} customers={customers} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenCreate(false)}>Cancel</Button>
            <Button onClick={createTicket} disabled={saving || !form.customer_id || !form.task.trim() || !form.pic.trim()}>
              {saving ? 'Menyimpan...' : 'Simpan'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!editing} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>Edit Ticket {editing?.ticket_no}</DialogTitle></DialogHeader>
          <TicketForm form={form} setForm={setForm} customers={customers} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={updateTicket} disabled={saving || !form.customer_id || !form.task.trim() || !form.pic.trim()}>
              {saving ? 'Menyimpan...' : 'Update'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function TicketForm({
  form,
  setForm,
  customers,
}: {
  form: typeof defaultForm
  setForm: React.Dispatch<React.SetStateAction<typeof defaultForm>>
  customers: CustomerOption[]
}) {
  return (
    <div className="space-y-4 py-2">
      <div className="space-y-1.5">
        <Label>Customer</Label>
        <Select value={form.customer_id} onValueChange={(v) => setForm((p) => ({ ...p, customer_id: v }))}>
          <SelectTrigger><SelectValue placeholder="Pilih customer" /></SelectTrigger>
          <SelectContent>
            {customers.map((customer) => (
              <SelectItem key={customer.id} value={customer.id}>{customer.display_name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="task">Task</Label>
        <Input id="task" value={form.task} onChange={(e) => setForm((p) => ({ ...p, task: e.target.value }))} />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="pic">PIC</Label>
        <Input id="pic" value={form.pic} onChange={(e) => setForm((p) => ({ ...p, pic: e.target.value }))} />
      </div>

      <div className="space-y-1.5">
        <Label>Status</Label>
        <Select value={form.status} onValueChange={(v: TicketStatus) => setForm((p) => ({ ...p, status: v }))}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="open">open</SelectItem>
            <SelectItem value="in_progress">in_progress</SelectItem>
            <SelectItem value="resolved">resolved</SelectItem>
            <SelectItem value="closed">closed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="desc">Deskripsi/Solusi</Label>
        <textarea
          id="desc"
          value={form.description_solution}
          onChange={(e) => setForm((p) => ({ ...p, description_solution: e.target.value }))}
          className="min-h-[120px] w-full rounded-md border bg-background px-3 py-2 text-sm"
        />
      </div>
    </div>
  )
}
