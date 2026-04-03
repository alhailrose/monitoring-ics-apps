'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { HugeiconsIcon } from '@hugeicons/react'
import { InformationCircleIcon, Copy01Icon } from '@hugeicons/core-free-icons'
import { Button } from '@/components/ui/button'

type UserRole = 'super_user' | 'user'

function CopyCommand({ cmd }: { cmd: string }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(cmd)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1400)
  }

  return (
    <div className="flex items-center gap-2 rounded border border-border/60 bg-background/90 px-2 py-1">
      <code className="flex-1 truncate font-mono text-[11px] text-sky-300">{cmd}</code>
      <button
        type="button"
        className="text-muted-foreground hover:text-foreground transition-colors"
        onClick={copy}
        aria-label="Copy setup command"
      >
        {copied ? <span className="text-[10px] text-emerald-400">Copied</span> : <HugeiconsIcon icon={Copy01Icon} strokeWidth={2} className="size-3.5" />}
      </button>
    </div>
  )
}

export function FirstRunGuide({ username, role }: { username: string; role: UserRole }) {
  const [visible, setVisible] = useState(false)
  const storageKey = useMemo(() => `onboarding.quickstart.${username}`, [username])

  useEffect(() => {
    try {
      const dismissed = window.localStorage.getItem(storageKey) === 'done'
      setVisible(!dismissed)
    } catch {
      setVisible(true)
    }
  }, [storageKey])

  const dismiss = () => {
    try {
      window.localStorage.setItem(storageKey, 'done')
    } catch {
      // ignore storage errors
    }
    setVisible(false)
  }

  if (!visible) return null

  return (
    <section className="rounded-xl border border-sky-500/30 bg-gradient-to-br from-sky-500/10 to-transparent p-4">
      <div className="mb-3 flex items-start gap-2">
        <HugeiconsIcon icon={InformationCircleIcon} strokeWidth={2} className="mt-0.5 size-4 shrink-0 text-sky-400" />
        <div>
          <h2 className="text-sm font-semibold">Quick Start Setup</h2>
          <p className="text-xs text-muted-foreground">
            Untuk mulai monitoring, setup kredensial AWS dulu. Kamu bisa pilih SSO atau access key.
          </p>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="space-y-2 rounded-lg border border-border/50 bg-card/80 p-3">
          <p className="text-xs font-medium">Opsi 1: AWS SSO</p>
          <ol className="space-y-1 text-[11px] text-muted-foreground">
            <li>1) Buka Terminal (ikon command line di kanan atas).</li>
            <li>2) Jalankan login command berikut:</li>
          </ol>
          <CopyCommand cmd="aws sso login --profile monitoring" />
          <p className="text-[11px] text-muted-foreground">Setelah login sukses, tambahkan account di halaman Customers dengan auth method Profile.</p>
        </div>

        <div className="space-y-2 rounded-lg border border-border/50 bg-card/80 p-3">
          <p className="text-xs font-medium">Opsi 2: Access Key</p>
          <ol className="space-y-1 text-[11px] text-muted-foreground">
            <li>1) Buka <span className="font-medium text-foreground">Customers</span> lalu Add/Edit Account.</li>
            <li>2) Pilih auth method <span className="font-medium text-foreground">Access Key</span>.</li>
            <li>3) Isi Access Key ID + Secret Access Key lalu klik Test Connection.</li>
          </ol>
          <p className="text-[11px] text-muted-foreground">
            Kalau perlu template config per-user, buka <span className="font-medium text-foreground">Settings → AWS Config</span>.
          </p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Link href="/customers">
          <Button size="sm" className="h-7 text-xs">Open Customers</Button>
        </Link>
        {role === 'super_user' && (
          <Link href="/settings/aws-config">
            <Button size="sm" variant="outline" className="h-7 text-xs">Open AWS Config</Button>
          </Link>
        )}
        <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={dismiss}>Saya paham</Button>
      </div>
    </section>
  )
}
