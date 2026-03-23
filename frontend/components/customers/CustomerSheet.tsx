'use client'

import { useState, useTransition } from 'react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { createCustomer, updateCustomer } from '@/app/(dashboard)/customers/actions'
import type { Customer } from '@/lib/types/api'

const CHECK_OPTIONS = [
  { value: 'guardduty',          label: 'GuardDuty' },
  { value: 'cloudwatch',         label: 'CloudWatch' },
  { value: 'notifications',      label: 'Notifications' },
  { value: 'backup',             label: 'Backup' },
  { value: 'cost',               label: 'Cost' },
  { value: 'ec2_utilization',    label: 'EC2 Utilization' },
  { value: 'daily-arbel',        label: 'Daily Arbel (RDS + EC2 Arbel)' },
  { value: 'daily-arbel-rds',    label: 'Daily Arbel RDS' },
  { value: 'daily-arbel-ec2',    label: 'Daily Arbel EC2' },
  { value: 'ec2list',            label: 'EC2 List' },
  { value: 'alarm_verification', label: 'Alarm Verification' },
  { value: 'daily-budget',       label: 'Daily Budget' },
]

interface CustomerSheetProps {
  customer?: Customer
  open: boolean
  onClose: () => void
}

export function CustomerSheet({ customer, open, onClose }: CustomerSheetProps) {
  const isEdit = !!customer
  const [slackEnabled, setSlackEnabled] = useState(customer?.slack_enabled ?? false)
  const [isPending, startTransition] = useTransition()

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    startTransition(async () => {
      const res = isEdit
        ? await updateCustomer(customer.id, formData)
        : await createCustomer(formData)
      if (res.error) {
        const msg =
          res.error.includes('409') || res.error.toLowerCase().includes('already')
            ? 'Customer name already exists'
            : res.error
        toast.error(isEdit ? 'Failed to update customer' : 'Failed to create customer', {
          description: msg,
        })
      } else {
        toast.success(isEdit ? 'Customer updated' : 'Customer created')
        onClose()
      }
    })
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Customer' : 'New Customer'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-1">
          <div className="space-y-1.5">
            <Label htmlFor="name">Slug</Label>
            <Input
              id="name"
              name="name"
              required
              disabled={isEdit}
              defaultValue={customer?.name ?? ''}
              placeholder="e.g. acme-corp"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="display_name">Display name</Label>
            <Input
              id="display_name"
              name="display_name"
              required
              defaultValue={customer?.display_name ?? ''}
              placeholder="e.g. Acme Corp"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="sso_session">
              SSO session{' '}
              <span className="text-muted-foreground text-xs">(optional)</span>
            </Label>
            <Input
              id="sso_session"
              name="sso_session"
              defaultValue={(customer as unknown as Record<string, string>)?.sso_session ?? ''}
              placeholder="e.g. acme-sso"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="label">
              Label{' '}
              <span className="text-muted-foreground text-xs">(optional)</span>
            </Label>
            <Input
              id="label"
              name="label"
              defaultValue={customer?.label ?? ''}
              placeholder="e.g. Enterprise, Trial, Internal"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="report_mode">Report mode</Label>
            <Select name="report_mode" defaultValue={customer?.report_mode ?? 'summary'}>
              <SelectTrigger id="report_mode">
                <SelectValue placeholder="Select report mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="summary">Summary (condensed)</SelectItem>
                <SelectItem value="detailed">Detailed (full report)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Checks */}
          <div className="space-y-2">
            <Label>Checks</Label>
            <div className="rounded-lg border border-border divide-y divide-border">
              {CHECK_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-muted/30 transition-colors"
                >
                  <input
                    type="checkbox"
                    name="checks"
                    value={opt.value}
                    defaultChecked={customer?.checks.includes(opt.value) ?? false}
                    className="h-4 w-4 rounded border-border accent-primary"
                  />
                  <span className="text-sm">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Slack */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="slack_enabled"
                name="slack_enabled"
                checked={slackEnabled}
                onChange={(e) => setSlackEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-border accent-primary"
              />
              <Label htmlFor="slack_enabled">Enable Slack notifications</Label>
            </div>

            {slackEnabled && (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="slack_channel">Slack channel</Label>
                  <Input
                    id="slack_channel"
                    name="slack_channel"
                    defaultValue={customer?.slack_channel ?? ''}
                    placeholder="#monitoring"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="slack_webhook_url">Webhook URL</Label>
                  <Input
                    id="slack_webhook_url"
                    name="slack_webhook_url"
                    defaultValue={
                      (customer as unknown as Record<string, string>)?.slack_webhook_url ?? ''
                    }
                    placeholder="https://hooks.slack.com/…"
                  />
                </div>
              </>
            )}
          </div>

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Create customer'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
