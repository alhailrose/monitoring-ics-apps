'use client'

import { useState, useTransition, useRef } from 'react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { addAccount, updateAccount } from '@/app/(dashboard)/customers/actions'
import { HugeiconsIcon } from '@hugeicons/react'
import { Add01Icon, Delete01Icon, Loading03Icon } from '@hugeicons/core-free-icons'
import type { Account } from '@/lib/types/api'

interface AccountSheetProps {
  customerId: string
  account?: Account
  open: boolean
  onClose: () => void
}

export function AccountSheet({ customerId, account, open, onClose }: AccountSheetProps) {
  const isEdit = !!account
  const [isPending, startTransition] = useTransition()

  // Alarm names state
  const [alarmNames, setAlarmNames] = useState<string[]>(account?.alarm_names ?? [])
  const [newAlarm, setNewAlarm] = useState('')
  const [isDiscovering, setIsDiscovering] = useState(false)
  const alarmInputRef = useRef<HTMLInputElement>(null)

  const addAlarm = () => {
    const name = newAlarm.trim()
    if (!name || alarmNames.includes(name)) return
    setAlarmNames((prev) => [...prev, name].sort())
    setNewAlarm('')
    alarmInputRef.current?.focus()
  }

  const removeAlarm = (name: string) => {
    setAlarmNames((prev) => prev.filter((a) => a !== name))
  }

  const discoverAlarms = async () => {
    if (!account?.id) return
    setIsDiscovering(true)
    try {
      const res = await fetch(`/api/discover-alarms/${account.id}`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        toast.error('Failed to discover alarms', { description: err.detail ?? err.error })
        return
      }
      const data = await res.json()
      const discovered: string[] = data.alarm_names ?? []
      setAlarmNames(discovered)
      toast.success(`Found ${discovered.length} alarm${discovered.length !== 1 ? 's' : ''}`)
    } catch {
      toast.error('Failed to discover alarms')
    } finally {
      setIsDiscovering(false)
    }
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    // Inject alarm_names as newline-joined string (actions.ts splits it back)
    formData.set('alarm_names', alarmNames.join('\n'))
    startTransition(async () => {
      const res = isEdit
        ? await updateAccount(customerId, account.id, formData)
        : await addAccount(customerId, formData)
      if (res.error) {
        toast.error(isEdit ? 'Failed to update account' : 'Failed to add account', {
          description: res.error,
        })
      } else {
        toast.success(isEdit ? 'Account updated' : 'Account added')
        onClose()
      }
    })
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Account' : 'Add Account'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-1">
          <div className="space-y-1.5">
            <Label htmlFor="profile_name">Profile name</Label>
            <Input
              id="profile_name"
              name="profile_name"
              required
              disabled={isEdit}
              defaultValue={account?.profile_name ?? ''}
              placeholder="e.g. prod-account"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="display_name">Display name</Label>
            <Input
              id="display_name"
              name="display_name"
              required
              defaultValue={account?.display_name ?? ''}
              placeholder="e.g. Production"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="region">
              Region <span className="text-muted-foreground text-xs">(optional)</span>
            </Label>
            <Input
              id="region"
              name="region"
              defaultValue={(account?.config_extra?.region as string) ?? ''}
              placeholder="e.g. ap-southeast-1"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="is_active"
              name="is_active"
              defaultChecked={account?.is_active ?? true}
              className="h-4 w-4 rounded border-border accent-primary"
            />
            <Label htmlFor="is_active">Active</Label>
          </div>

          <Separator />

          {/* Alarm names */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>
                Alarm Names
                <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                  (for CloudWatch alarm verification)
                </span>
              </Label>
              {isEdit && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-6 text-[11px] px-2 gap-1"
                  onClick={discoverAlarms}
                  disabled={isDiscovering}
                >
                  {isDiscovering ? (
                    <HugeiconsIcon icon={Loading03Icon} className="size-3 animate-spin" strokeWidth={2} />
                  ) : null}
                  {isDiscovering ? 'Discovering…' : 'Discover from CloudWatch'}
                </Button>
              )}
            </div>

            {/* Current alarm badges */}
            {alarmNames.length > 0 && (
              <div className="flex flex-wrap gap-1.5 p-2 rounded-md border border-border/60 bg-muted/20 max-h-36 overflow-y-auto">
                {alarmNames.map((name) => (
                  <Badge
                    key={name}
                    variant="outline"
                    className="text-[10px] font-mono px-1.5 py-px h-auto gap-1 cursor-pointer hover:border-destructive/50 hover:text-destructive group"
                    onClick={() => removeAlarm(name)}
                    title="Click to remove"
                  >
                    {name}
                    <HugeiconsIcon
                      icon={Delete01Icon}
                      strokeWidth={2}
                      className="size-2.5 opacity-0 group-hover:opacity-100 transition-opacity"
                    />
                  </Badge>
                ))}
              </div>
            )}

            {alarmNames.length === 0 && (
              <p className="text-xs text-muted-foreground px-1">
                No alarm names configured.{isEdit ? ' Use Discover or add manually.' : ' Add manually below.'}
              </p>
            )}

            {/* Add alarm input */}
            <div className="flex gap-2">
              <Input
                ref={alarmInputRef}
                value={newAlarm}
                onChange={(e) => setNewAlarm(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { e.preventDefault(); addAlarm() }
                }}
                placeholder="Alarm name (Enter to add)"
                className="h-8 text-xs font-mono"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 shrink-0"
                onClick={addAlarm}
                disabled={!newAlarm.trim()}
              >
                <HugeiconsIcon icon={Add01Icon} strokeWidth={2} className="size-3.5" />
              </Button>
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Add account'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
