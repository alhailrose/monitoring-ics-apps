'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
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
type EmailTemplateType = 'in_progress' | 'selesai'

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

function formatDate(v: string | null): string {
  if (!v) return '-'
  return new Date(v).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' })
}

const STATUS_OPTIONS: TicketStatus[] = ['open', 'in_progress', 'resolved', 'closed']
const STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  closed: 'Closed',
}

function statusBadgeClass(s: TicketStatus): string {
  if (s === 'resolved' || s === 'closed') return 'h-5 px-2 text-[10px] bg-green-500/10 text-green-400 border-green-500/20'
  if (s === 'in_progress') return 'h-5 px-2 text-[10px] bg-amber-500/10 text-amber-400 border-amber-500/20'
  return 'h-5 px-2 text-[10px] bg-sky-500/10 text-sky-400 border-sky-500/20'
}

const TEMPLATE_OPTIONS: { value: EmailTemplateType; label: string }[] = [
  { value: 'in_progress', label: 'In Progress (sedang dikerjakan)' },
  { value: 'selesai', label: 'Selesai (closing)' },
]

const MONTHS = [
  { value: '1', label: 'Januari' }, { value: '2', label: 'Februari' },
  { value: '3', label: 'Maret' }, { value: '4', label: 'April' },
  { value: '5', label: 'Mei' }, { value: '6', label: 'Juni' },
  { value: '7', label: 'Juli' }, { value: '8', label: 'Agustus' },
  { value: '9', label: 'September' }, { value: '10', label: 'Oktober' },
  { value: '11', label: 'November' }, { value: '12', label: 'Desember' },
]

const defaultForm = {
  customer_id: '',
  task: '',
  pic: '',
  status: 'open' as TicketStatus,
  description_solution: '',
}

// ─── Inline status cell ───────────────────────────────────────────────────────

function StatusCell({ ticket, onUpdated }: { ticket: Ticket; onUpdated: () => void }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const change = async (newStatus: TicketStatus) => {
    if (newStatus === ticket.status) return
    setSaving(true)
    setError(null)
    try {
      await apiFetch(`/api/tickets/${ticket.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      onUpdated()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Gagal update')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <Select value={ticket.status} onValueChange={v => change(v as TicketStatus)} disabled={saving}>
        <SelectTrigger className="h-7 w-32 text-[10px] px-2 border-transparent hover:border-border focus:ring-0">
          <Badge className={statusBadgeClass(ticket.status)}>{STATUS_LABELS[ticket.status]}</Badge>
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map(s => (
            <SelectItem key={s} value={s} className="text-xs">{STATUS_LABELS[s]}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      {error && <p className="text-[10px] text-destructive mt-0.5">{error}</p>}
    </div>
  )
}

// ─── Delete button ────────────────────────────────────────────────────────────

function DeleteButton({ ticket, onDeleted }: { ticket: Ticket; onDeleted: () => void }) {
  const [confirm, setConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const doDelete = async () => {
    setDeleting(true)
    try {
      await apiFetch(`/api/tickets/${ticket.id}`, { method: 'DELETE' })
      onDeleted()
    } catch {
      setDeleting(false)
      setConfirm(false)
    }
  }

  if (!confirm) {
    return (
      <Button size="sm" variant="ghost" className="h-7 text-xs px-2 text-destructive hover:text-destructive" onClick={() => setConfirm(true)}>
        Hapus
      </Button>
    )
  }

  return (
    <div className="flex gap-1 items-center">
      <span className="text-[10px] text-destructive">Yakin?</span>
      <Button size="sm" variant="destructive" className="h-6 text-[10px] px-2" onClick={doDelete} disabled={deleting}>
        {deleting ? '...' : 'Ya'}
      </Button>
      <Button size="sm" variant="ghost" className="h-6 text-[10px] px-2" onClick={() => setConfirm(false)}>
        Batal
      </Button>
    </div>
  )
}

// ─── Email template dialog ────────────────────────────────────────────────────

function EmailTemplateDialog({ ticket, customers, onClose }: {
  ticket: Ticket
  customers: CustomerOption[]
  onClose: () => void
}) {
  const [templateType, setTemplateType] = useState<EmailTemplateType>('in_progress')
  const [data, setData] = useState<{ subject: string; body: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState<'subject' | 'body' | null>(null)
  const loadedType = useRef<string | null>(null)

  useEffect(() => {
    if (loadedType.current === templateType) return
    loadedType.current = templateType
    setLoading(true)
    apiFetch<{ subject: string; body: string }>(
      `/api/tickets/${ticket.id}?template_type=${templateType}`
    )
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [templateType, ticket.id])

  const copy = async (text: string, type: 'subject' | 'body') => {
    await navigator.clipboard.writeText(text)
    setCopied(type)
    setTimeout(() => setCopied(null), 2000)
  }

  const customerName = customers.find(c => c.id === ticket.customer_id)?.display_name ?? '-'

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Generate Email</DialogTitle>
          <p className="text-xs text-muted-foreground mt-1">{customerName} · {ticket.task}</p>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>Fase</Label>
            <Select value={templateType} onValueChange={v => {
              loadedType.current = null
              setTemplateType(v as EmailTemplateType)
            }}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {TEMPLATE_OPTIONS.map(t => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading && <p className="text-xs text-muted-foreground">Memuat...</p>}

          {data && !loading && (
            <>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label>Subject</Label>
                  <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => copy(data.subject, 'subject')}>
                    {copied === 'subject' ? '✓ Copied' : 'Copy'}
                  </Button>
                </div>
                <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm font-mono">{data.subject}</div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label>Body</Label>
                  <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => copy(data.body, 'body')}>
                    {copied === 'body' ? '✓ Copied' : 'Copy'}
                  </Button>
                </div>
                <pre className="rounded-md border bg-muted/30 px-3 py-2 text-xs whitespace-pre-wrap font-sans max-h-64 overflow-y-auto">
                  {data.body}
                </pre>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Tutup</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function TicketingPage() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openCreate, setOpenCreate] = useState(false)
  const [editing, setEditing] = useState<Ticket | null>(null)
  const [emailTicket, setEmailTicket] = useState<Ticket | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(defaultForm)
  const [customers, setCustomers] = useState<CustomerOption[]>([])
  const [exporting, setExporting] = useState(false)

  // Filters
  const [filterCustomer, setFilterCustomer] = useState('')
  const [filterMonth, setFilterMonth] = useState('')
  const [filterYear, setFilterYear] = useState(String(new Date().getFullYear()))

  const buildQuery = useCallback(() => {
    const p = new URLSearchParams()
    if (filterCustomer) p.set('customer_id', filterCustomer)
    if (filterMonth) p.set('month', filterMonth)
    if (filterYear) p.set('year', filterYear)
    return p.toString() ? `?${p.toString()}` : ''
  }, [filterCustomer, filterMonth, filterYear])

  const loadTickets = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await apiFetch<Ticket[]>(`/api/tickets${buildQuery()}`)
      setTickets(rows)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load tickets')
    } finally {
      setLoading(false)
    }
  }, [buildQuery])

  useEffect(() => {
    apiFetch<{ customers: Array<{ id: string; display_name: string }> }>('/api/customers')
      .then(data => setCustomers((data.customers || []).map(c => ({ id: c.id, display_name: c.display_name }))))
      .catch(() => setCustomers([]))
  }, [])

  useEffect(() => { loadTickets() }, [loadTickets])

  const doExport = async () => {
    setExporting(true)
    try {
      const p = new URLSearchParams()
      if (filterMonth) p.set('month', filterMonth)
      if (filterYear) p.set('year', filterYear)
      const qs = p.toString() ? `?${p.toString()}` : ''
      const res = await fetch(`/api/tickets/export${qs}`)
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const cd = res.headers.get('Content-Disposition') ?? ''
      const match = cd.match(/filename="?([^"]+)"?/)
      a.download = match ? match[1] : 'tickets.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // silent fail
    } finally {
      setExporting(false)
    }
  }

  const openCreateDialog = () => { setForm(defaultForm); setOpenCreate(true) }
  const openEditDialog = (t: Ticket) => {
    setEditing(t)
    setForm({
      customer_id: t.customer_id ?? '',
      task: t.task,
      pic: t.pic,
      status: t.status,
      description_solution: t.description_solution ?? '',
    })
  }

  const createTicket = async () => {
    if (!form.customer_id || !form.task.trim() || !form.pic.trim()) return
    setSaving(true)
    setError(null)
    try {
      await apiFetch('/api/tickets', {
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
      await apiFetch(`/api/tickets/${editing.id}`, {
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

  const currentYear = new Date().getFullYear()
  const yearOptions = Array.from({ length: 4 }, (_, i) => String(currentYear - i))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Ticketing</h1>
          <p className="text-sm text-muted-foreground mt-1">Tracking task operasional dan solusi insiden.</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={doExport} disabled={exporting}>
            {exporting ? 'Exporting...' : 'Export Excel'}
          </Button>
          <Button size="sm" onClick={openCreateDialog}>Tambah Ticket</Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Customer</Label>
          <Select value={filterCustomer || '_all'} onValueChange={v => setFilterCustomer(v === '_all' ? '' : v)}>
            <SelectTrigger className="h-8 w-44 text-xs"><SelectValue placeholder="Semua Customer" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="_all">Semua Customer</SelectItem>
              {customers.map(c => <SelectItem key={c.id} value={c.id} className="text-xs">{c.display_name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Bulan</Label>
          <Select value={filterMonth || '_all'} onValueChange={v => setFilterMonth(v === '_all' ? '' : v)}>
            <SelectTrigger className="h-8 w-36 text-xs"><SelectValue placeholder="Semua Bulan" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="_all">Semua Bulan</SelectItem>
              {MONTHS.map(m => <SelectItem key={m.value} value={m.value} className="text-xs">{m.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Tahun</Label>
          <Select value={filterYear || '_all'} onValueChange={v => setFilterYear(v === '_all' ? '' : v)}>
            <SelectTrigger className="h-8 w-28 text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="_all">Semua</SelectItem>
              {yearOptions.map(y => <SelectItem key={y} value={y} className="text-xs">{y}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        {(filterCustomer || filterMonth) && (
          <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => { setFilterCustomer(''); setFilterMonth('') }}>
            Reset Filter
          </Button>
        )}
        <p className="text-xs text-muted-foreground self-end pb-1">{tickets.length} ticket</p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Customer</TableHead>
              <TableHead>Task</TableHead>
              <TableHead>PIC</TableHead>
              <TableHead>Dibuat</TableHead>
              <TableHead>Selesai</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Deskripsi/Solusi</TableHead>
              <TableHead className="w-32" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-sm text-muted-foreground">Loading...</TableCell>
              </TableRow>
            ) : tickets.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-sm text-muted-foreground">Belum ada ticket</TableCell>
              </TableRow>
            ) : (
              tickets.map(ticket => (
                <TableRow key={ticket.id}>
                  <TableCell className="text-sm whitespace-nowrap">
                    {customers.find(c => c.id === ticket.customer_id)?.display_name ?? '-'}
                  </TableCell>
                  <TableCell className="font-medium max-w-[220px] truncate" title={ticket.task}>
                    {ticket.task}
                  </TableCell>
                  <TableCell className="text-sm whitespace-nowrap">{ticket.pic}</TableCell>
                  <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{formatDate(ticket.created_at)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{formatDate(ticket.ended_at)}</TableCell>
                  <TableCell>
                    <StatusCell ticket={ticket} onUpdated={loadTickets} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground max-w-[180px] truncate" title={ticket.description_solution ?? ''}>
                    {ticket.description_solution || '-'}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      <Button size="sm" variant="ghost" className="h-7 text-xs px-2" onClick={() => setEmailTicket(ticket)}>
                        Email
                      </Button>
                      <Button size="sm" variant="outline" className="h-7 text-xs px-2" onClick={() => openEditDialog(ticket)}>
                        Edit
                      </Button>
                      <DeleteButton ticket={ticket} onDeleted={loadTickets} />
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create dialog */}
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

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={open => !open && setEditing(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>Edit Ticket</DialogTitle></DialogHeader>
          <TicketForm form={form} setForm={setForm} customers={customers} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={updateTicket} disabled={saving || !form.customer_id || !form.task.trim() || !form.pic.trim()}>
              {saving ? 'Menyimpan...' : 'Update'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Email template dialog */}
      {emailTicket && (
        <EmailTemplateDialog ticket={emailTicket} customers={customers} onClose={() => setEmailTicket(null)} />
      )}
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
        <Select value={form.customer_id} onValueChange={v => setForm(p => ({ ...p, customer_id: v }))}>
          <SelectTrigger><SelectValue placeholder="Pilih customer" /></SelectTrigger>
          <SelectContent>
            {customers.map(c => <SelectItem key={c.id} value={c.id}>{c.display_name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="task">Task</Label>
        <Input id="task" value={form.task} onChange={e => setForm(p => ({ ...p, task: e.target.value }))} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="pic">PIC</Label>
        <Input id="pic" value={form.pic} onChange={e => setForm(p => ({ ...p, pic: e.target.value }))} />
      </div>
      <div className="space-y-1.5">
        <Label>Status</Label>
        <Select value={form.status} onValueChange={v => setForm(p => ({ ...p, status: v as TicketStatus }))}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map(s => <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="desc">Deskripsi/Solusi</Label>
        <textarea
          id="desc"
          value={form.description_solution}
          onChange={e => setForm(p => ({ ...p, description_solution: e.target.value }))}
          className="min-h-[100px] w-full rounded-md border bg-background px-3 py-2 text-sm"
        />
      </div>
    </div>
  )
}
