import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import AppShell from "./app-shell"
import "./styles/ops-theme.css"
import "./styles/pages/arbel.css"
import "./styles/pages/customers.css"

const rootElement = document.getElementById("root")

if (!rootElement) {
  throw new Error("Missing root element")
}

createRoot(rootElement).render(
  <StrictMode>
    <AppShell />
  </StrictMode>,
)
