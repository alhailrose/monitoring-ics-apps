import { redirect } from 'next/navigation'

import { getSession } from '@/lib/auth'
import { LoginForm } from '@/components/auth/LoginForm'
import { LoginHero } from '@/components/auth/LoginHero'
import type { NextRequest } from 'next/server'

export default async function LoginPage({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const params = await searchParams
  const session = await getSession()
  // Don't redirect if there's an OAuth error to display
  if (session && !params.error) redirect('/dashboard')

  return (
    <div className="bg-[#020617]">
      <div className="flex min-h-svh flex-col lg:grid lg:grid-cols-[1.1fr_0.9fr]">
        <LoginHero />

        <section className="flex min-h-svh flex-col items-center justify-center bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 px-6 py-10 md:px-10 lg:bg-background lg:bg-none">
          {/* Mobile-only branding header */}
          <div className="mb-6 flex w-full max-w-md items-center gap-3 lg:hidden">
            <div className="rounded-lg bg-white px-2.5 py-1.5 shadow">
              <img src="/brand/ics-logo.png" alt="ICS" className="h-7 w-auto" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-white/60">ICS Monitoring Hub</p>
              <p className="text-sm font-semibold text-white">Infrastructure Command Suite</p>
            </div>
          </div>

          <div className="w-full max-w-md space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur lg:border-border/40 lg:bg-card/95 lg:shadow-black/5">
              <LoginForm />
            </div>
            <div className="rounded-xl border border-dashed border-white/20 bg-white/5 px-4 py-3 text-xs text-white/50 backdrop-blur lg:border-border/70 lg:bg-card/70 lg:text-muted-foreground">
              <p className="mb-1 font-semibold text-white/80 lg:text-foreground">Butuh akses tambahan?</p>
              <p>Hubungi ICS Operations Admin untuk aktivasi ruang kendali baru atau reset MFA agar tetap sinkron.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
