import { useEffect, useState } from "react"
import {
  Activity,
  TerminalSquare,
  Layers,
  Database,
  Users,
  ShieldCheck,
  History,
  Menu,
  X,
  RadioTower,
} from "lucide-react"

import ArbelCheckPage from "./app/checks/arbel/page"
import AllCheckPage from "./app/checks/all/page"
import SingleCheckPage from "./app/checks/single/page"
import CustomersPage from "./app/customers/page"
import HistoryPage from "./app/history/page"
import HomePage from "./app/page"
import ProfilesPage from "./app/profiles/page"

type PageKey =
  | "home"
  | "singleCheck"
  | "allCheck"
  | "arbelCheck"
  | "customers"
  | "profiles"
  | "history"

interface RouteConfig {
  path: string
  key: PageKey
  label: string
  icon: React.ReactNode
}

const ROUTES: RouteConfig[] = [
  { path: "/", key: "home", label: "Dashboard", icon: <Activity size={18} /> },
  {
    path: "/checks/single",
    key: "singleCheck",
    label: "Single Check",
    icon: <TerminalSquare size={18} />,
  },
  { path: "/checks/all", key: "allCheck", label: "All Checks", icon: <Layers size={18} /> },
  { path: "/checks/arbel", key: "arbelCheck", label: "Arbel Check", icon: <Database size={18} /> },
  { path: "/customers", key: "customers", label: "Customers", icon: <Users size={18} /> },
  { path: "/profiles", key: "profiles", label: "Profile Configs", icon: <ShieldCheck size={18} /> },
  { path: "/history", key: "history", label: "History", icon: <History size={18} /> },
]

const routeByPath = new Map(ROUTES.map((route) => [route.path, route.key]))

export const resolvePagePath = (pathname: string): PageKey => {
  const normalized = pathname.replace(/\/+$/, "") || "/"
  return routeByPath.get(normalized) ?? "home"
}

export default function AppShell() {
  const [page, setPage] = useState<PageKey>("home")
  const [isNavOpen, setIsNavOpen] = useState(false)

  useEffect(() => {
    setPage(resolvePagePath(window.location.pathname))

    const onPopState = () => {
      setPage(resolvePagePath(window.location.pathname))
      setIsNavOpen(false)
    }

    window.addEventListener("popstate", onPopState)
    return () => window.removeEventListener("popstate", onPopState)
  }, [])

  const navigate = (path: string, key: PageKey) => {
    setIsNavOpen(false)

    if (window.location.pathname === path) {
      return
    }

    window.history.pushState({}, "", path)
    setPage(key)
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  const currentRouteLabel = ROUTES.find((route) => route.key === page)?.label ?? "Dashboard"

  return (
    <div className="app-layout">
      <header className="app-topbar">
        <button
          type="button"
          className="app-mobile-menu-button"
          onClick={() => setIsNavOpen((current) => !current)}
          aria-label={isNavOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={isNavOpen}
          aria-controls="main-sidebar"
        >
          {isNavOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className="app-topbar-title">{currentRouteLabel}</div>
        <div className="app-topbar-brand">
          <RadioTower size={16} /> HUB
        </div>
      </header>

      <button
        type="button"
        className="app-backdrop"
        data-open={isNavOpen}
        aria-hidden={!isNavOpen}
        tabIndex={isNavOpen ? 0 : -1}
        onClick={() => setIsNavOpen(false)}
      />

      <nav
        id="main-sidebar"
        className="app-sidebar"
        data-open={isNavOpen}
        aria-label="Main Navigation"
      >
        <div className="app-sidebar-header">
          <RadioTower size={24} className="sidebar-brand-icon" />
          <span style={{ fontWeight: 800, letterSpacing: "1px" }}>MON_HUB</span>
        </div>

        <div className="app-nav">
          <div
            className="app-nav-group-label"
            style={{
              fontSize: "0.75rem",
              color: "var(--ops-color-text-muted)",
              padding: "0.75rem 1rem 0.25rem",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              fontWeight: 600,
            }}
          >
            Monitoring
          </div>
          {ROUTES.map((route) => (
            <button
              key={route.path}
              type="button"
              data-active={page === route.key}
              aria-current={page === route.key ? "page" : undefined}
              onClick={() => navigate(route.path, route.key)}
              className="app-nav-button"
            >
              <span className="app-nav-icon">{route.icon}</span>
              <span className="app-nav-label">{route.label}</span>
            </button>
          ))}
        </div>
      </nav>

      <div className="app-main">
        {page === "home" && <HomePage />}
        {page === "singleCheck" && <SingleCheckPage />}
        {page === "allCheck" && <AllCheckPage />}
        {page === "arbelCheck" && <ArbelCheckPage />}
        {page === "customers" && <CustomersPage />}
        {page === "profiles" && <ProfilesPage />}
        {page === "history" && <HistoryPage />}
      </div>
    </div>
  )
}
