import Image from 'next/image'

export function LoginHero() {
  return (
    <aside className="relative flex min-h-svh flex-col overflow-hidden bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-32 top-24 h-96 w-96 rounded-full bg-indigo-500/30 blur-[160px]" />
        <div className="absolute -right-16 bottom-16 h-80 w-80 rounded-full bg-sky-400/30 blur-[140px]" />
      </div>
      <div className="relative z-10 flex flex-1 flex-col justify-between gap-8 p-8 xl:p-12">
        <div
          data-testid="login-hero-strip"
          className="flex items-center gap-6 rounded-full border border-white/15 bg-white/5 px-5 py-4 backdrop-blur"
        >
          <div className="rounded-xl bg-white px-3 py-2 shadow-lg">
            <Image
              src="/brand/ics-logo.png"
              alt="ICS logo"
              width={140}
              height={70}
              className="h-10 w-auto"
            />
          </div>
          <div className="flex-1">
            <p className="text-[11px] uppercase tracking-[0.55em] text-white/70">ICS Monitoring Hub</p>
            <h2 className="text-2xl font-semibold text-white">Infrastructure Command Suite</h2>
          </div>
        </div>
        <div className="space-y-4 text-sm text-slate-200/80">
          <p>Operational visibility for multi-region workloads. Realtime compliance alerts, twice-daily digests.</p>
          <div className="flex items-center justify-between rounded-2xl border border-white/15 bg-white/5 p-6 text-white">
            <div>
              <p className="text-xs uppercase tracking-[0.4em] text-white/60">Uptime Window</p>
              <p className="text-3xl font-semibold text-white">99.95% uptime</p>
            </div>
            <p className="max-w-[200px] text-xs text-white/70">
              Suites refresh twice per day across APAC + global regions.
            </p>
          </div>
        </div>
        <p className="text-[11px] text-white/60">Made by Bagus Ganteng 😎</p>
      </div>
    </aside>
  )
}
