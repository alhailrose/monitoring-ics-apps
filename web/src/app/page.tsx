import type { MouseEvent } from "react"

const NAV_ITEMS = [
  {
    title: "Single Check",
    description: "Run one monitoring check for selected customer accounts.",
    href: "/checks/single",
  },
  {
    title: "All Check",
    description: "Run the customer check template in synchronous mode.",
    href: "/checks/all",
  },
  {
    title: "Arbel Check",
    description: "Run Aryanoble full monitoring suite.",
    href: "/checks/arbel",
  },
  {
    title: "Customer Management",
    description: "Create and maintain customers with mapped AWS accounts.",
    href: "/customers",
  },
  {
    title: "Profile Detection",
    description: "Scan local AWS profiles and review mapped or unmapped status.",
    href: "/profiles",
  },
  {
    title: "History",
    description: "Filter and inspect historical check runs.",
    href: "/history",
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
  }

  return (
    <main className="home-page" aria-labelledby="home-title">
      <section className="ops-glass-panel home-hero-panel">
        <p className="home-eyebrow">AWS Monitoring Platform</p>
        <h1 id="home-title" className="home-title">
          AWS Monitoring Hub
        </h1>
        <p className="home-description">Choose a workflow to run checks, manage tenants, and review monitoring history.</p>
      </section>

      <section className="home-nav-grid" aria-label="Navigation cards">
        {NAV_ITEMS.map((item) => (
          <a key={item.href} href={item.href} className="home-nav-card" onClick={(event) => onNavigate(event, item.href)}>
            <h2>{item.title}</h2>
            <p>{item.description}</p>
          </a>
        ))}
      </section>
    </main>
  )
}
