import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, test } from "vitest"

import AppShell, { resolvePagePath } from "../app-shell"

beforeEach(() => {
  window.history.replaceState({}, "", "/")
})

describe("resolvePagePath", () => {
  test("maps known routes to pages", () => {
    expect(resolvePagePath("/")).toBe("home")
    expect(resolvePagePath("/checks/single")).toBe("singleCheck")
    expect(resolvePagePath("/checks/all")).toBe("allCheck")
    expect(resolvePagePath("/checks/arbel")).toBe("arbelCheck")
    expect(resolvePagePath("/customers")).toBe("customers")
    expect(resolvePagePath("/profiles")).toBe("profiles")
    expect(resolvePagePath("/history")).toBe("history")
  })

  test("falls back unknown routes to home", () => {
    expect(resolvePagePath("/does-not-exist")).toBe("home")
  })

  test("toggles mobile navigation drawer and closes on navigation", () => {
    render(<AppShell />)

    const nav = screen.getByRole("navigation", { name: /main navigation/i })
    expect(nav).toHaveAttribute("data-open", "false")

    fireEvent.click(screen.getByRole("button", { name: /open navigation/i }))
    expect(nav).toHaveAttribute("data-open", "true")

    fireEvent.click(screen.getByRole("button", { name: /^single check$/i }))
    expect(nav).toHaveAttribute("data-open", "false")
  })
})
