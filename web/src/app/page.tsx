import type { MouseEvent } from "react"
import {
  Activity,
  TerminalSquare,
  Layers,
  Database,
  Users,
  ShieldCheck,
  History,
} from "lucide-react"

const DASHBOARD_METRICS = [
  { label: "ACCOUNTS_ACTIVE", value: "32", unit: "UNIT" },
  { label: "CHECKS_AVAILABLE", value: "10", unit: "MOD" },
  { label: "SYSTEM_HEALTH", value: "99.9", unit: "%" },
]

const NAV_ITEMS = [
  {
    title: "Single Check",
    description: "Run one monitoring check for selected customer accounts.",
    href: "/checks/single",
    icon: (
      <TerminalSquare size={20} className="home-card-icon" color="var(--ops-color-text-accent)" />
    ),
  },
  {
    title: "All Check",
    description: "Run the customer check template in synchronous mode.",
    href: "/checks/all",
    icon: <Layers size={20} className="home-card-icon" color="var(--ops-color-text-accent)" />,
  },
  {
    title: "Arbel Check",
    description: "Run Aryanoble full monitoring suite.",
    href: "/checks/arbel",
    icon: <Database size={20} className="home-card-icon" color="var(--ops-color-text-accent)" />,
  },
  {
    title: "Customer Management",
    description: "Create and maintain customers with mapped AWS accounts.",
    href: "/customers",
    icon: <Users size={20} className="home-card-icon" color="var(--ops-color-text-accent)" />,
  },
  {
    title: "Profile Detection",
    description: "Scan local AWS profiles and review mapped or unmapped status.",
    href: "/profiles",
    icon: <ShieldCheck size={20} className="home-card-icon" color="var(--ops-color-text-accent)" />,
  },
  {
    title: "History",
    description: "Filter and inspect historical check runs.",
    href: "/history",
    icon: <History size={20} className="home-card-icon" color="var(--ops-color-text-accent)" />,
  },
]

export default function HomePage() {
  const onNavigate = (event: MouseEvent<HTMLAnchorElement>, href: string) => {
    event.preventDefault()
    if (window.location.pathname === href) {
      return
    }
    window.history.pushState({}, "", href)
    window.dispatchEvent(new PopStateEvent("popstate"))
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  return (
    <main className="home-page" aria-labelledby="home-title">
      <section
        className="ops-glass-panel home-hero-panel"
        style={{
          borderRadius: "8px",
          border: "1px solid var(--ops-color-border-strong)",
          background: "rgba(18, 28, 40, 0.6)",
          padding: "2rem",
        }}
      >
        <p className="home-eyebrow" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Activity size={16} /> SYSTEM_COMMAND_CENTER
        </p>
        <h1 id="home-title" className="home-title">
          Monitoring Hub
        </h1>
        <p className="home-description">
          Unified AWS Monitoring Platform. Perform health checks, manage multi-tenant accounts, and
          analyze infrastructure costs through an industrial-grade interface.
        </p>
      </section>

      <section className="home-metrics-section" style={{ marginTop: "1rem" }}>
        <h2 className="home-metrics-heading">LIVE_METRICS</h2>
        <div className="home-metrics-grid" style={{ marginTop: "0.5rem" }}>
          {DASHBOARD_METRICS.map((metric) => (
            <div
              key={metric.label}
              className="home-kpi-card ops-glass-panel"
              style={{
                background: "rgba(18, 28, 40, 0.4)",
                borderRadius: "8px",
                border: "1px solid var(--ops-color-border-strong)",
              }}
            >
              <p className="home-kpi-term">{metric.label}</p>
              <div className="home-kpi-value">
                {metric.value}
                <span style={{ fontSize: "1rem", color: "var(--ops-color-text-muted)" }}>
                  {" "}
                  {metric.unit}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="home-actions" style={{ marginTop: "1rem" }}>
        <h2 className="home-metrics-heading">QUICK_ACTIONS</h2>
        <div
          className="home-nav-grid"
          aria-label="Navigation cards"
          style={{ marginTop: "0.5rem" }}
        >
          {NAV_ITEMS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="home-nav-card"
              onClick={(event) => onNavigate(event, item.href)}
            >
              <h2>
                {item.icon} {item.title}
              </h2>
              <p>{item.description}</p>
            </a>
          ))}
        </div>
      </section>
    </main>
  )
}
