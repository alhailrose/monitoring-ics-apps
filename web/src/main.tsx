import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import AppShell from "./app-shell"
import "./styles/ops-theme.css"

const rootElement = document.getElementById("root")

if (!rootElement) {
  throw new Error("Missing root element")
}

createRoot(rootElement).render(
  <StrictMode>
    <AppShell />
  </StrictMode>
)
