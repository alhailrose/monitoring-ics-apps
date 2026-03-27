import { redirect } from 'next/navigation'

import { getSession } from '@/lib/auth'
import { LoginForm } from '@/components/auth/LoginForm'
import { LoginHero } from '@/components/auth/LoginHero'

export default async function LoginPage() {
  const session = await getSession()
  if (session) redirect('/dashboard')

  return (
    <div className="bg-[#020617]">
      <div className="flex min-h-svh flex-col lg:grid lg:grid-cols-[1.1fr_0.9fr]">
        <LoginHero />

        <section className="relative flex min-h-svh items-center justify-center bg-gradient-to-b from-background via-background to-background/70 px-6 py-10 md:px-10">
          <div className="absolute inset-0 bg-white/85 backdrop-blur-sm lg:bg-transparent" />
          <div className="relative z-10 w-full max-w-md space-y-8">
            <div className="rounded-2xl border border-border/40 bg-card/95 p-6 shadow-2xl shadow-black/5">
              <LoginForm />
            </div>
            <div className="rounded-xl border border-dashed border-border/70 bg-card/70 px-4 py-3 text-xs text-muted-foreground">
              <p className="mb-1 font-semibold text-foreground">Butuh akses tambahan?</p>
              <p>Hubungi ICS Operations Admin untuk aktivasi ruang kendali baru atau reset MFA agar tetap sinkron.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
