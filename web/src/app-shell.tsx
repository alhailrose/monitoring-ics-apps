import { useEffect, useState } from "react"

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

const ROUTES: Array<{ path: string; key: PageKey; label: string }> = [
  { path: "/", key: "home", label: "Home" },
  { path: "/checks/single", key: "singleCheck", label: "Single Check" },
  { path: "/checks/all", key: "allCheck", label: "All Check" },
  { path: "/checks/arbel", key: "arbelCheck", label: "Arbel Check" },
  { path: "/customers", key: "customers", label: "Customers" },
  { path: "/profiles", key: "profiles", label: "Profiles" },
  { path: "/history", key: "history", label: "History" },
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
  }

  const currentRouteLabel = ROUTES.find((route) => route.key === page)?.label ?? "Home"

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
          {isNavOpen ? "Close" : "Menu"}
        </button>
        <div className="app-topbar-title">{currentRouteLabel}</div>
        <div className="app-topbar-brand">MON_HUB</div>
      </header>

      <button
        type="button"
        className="app-backdrop"
        data-open={isNavOpen}
        aria-hidden={!isNavOpen}
        tabIndex={isNavOpen ? 0 : -1}
        onClick={() => setIsNavOpen(false)}
      />

      <nav id="main-sidebar" className="app-sidebar" data-open={isNavOpen} aria-label="Main Navigation">
        <div className="app-sidebar-header">
          <span className="ops-cursor">_</span> MON_HUB
        </div>
        <div className="app-nav">
          {ROUTES.map((route, index) => (
            <button
              key={route.path}
              type="button"
              data-active={page === route.key}
              aria-current={page === route.key ? "page" : undefined}
              onClick={() => navigate(route.path, route.key)}
            >
              [{index + 1}] {route.label}
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
