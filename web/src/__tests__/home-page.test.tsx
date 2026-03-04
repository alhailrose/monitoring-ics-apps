import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, test } from "vitest"

import HomePage from "../app/page"

afterEach(() => {
  cleanup()
})

describe("HomePage", () => {
  test("renders navigation cards for all main workflows", () => {
    render(<HomePage />)

    expect(screen.getByRole("main")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /aws monitoring hub/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /single check/i })).toHaveAttribute("href", "/checks/single")
    expect(screen.getByRole("link", { name: /all check/i })).toHaveAttribute("href", "/checks/all")
    expect(screen.getByRole("link", { name: /arbel check/i })).toHaveAttribute("href", "/checks/arbel")
    expect(screen.getByRole("link", { name: /customer management/i })).toHaveAttribute("href", "/customers")
    expect(screen.getByRole("link", { name: /profile detection/i })).toHaveAttribute("href", "/profiles")
    expect(screen.getByRole("link", { name: /history/i })).toHaveAttribute("href", "/history")
  })
})
