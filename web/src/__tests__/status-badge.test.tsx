import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { StatusBadge } from "../components/common/StatusBadge"

describe("StatusBadge", () => {
  test.each([
    ["OK", "ok"],
    ["WARN", "warn"],
    ["ERROR", "error"],
    ["ALARM", "alarm"],
    ["NO_DATA", "no_data"],
  ] as const)("renders %s with semantic status variant", (status, variant) => {
    render(<StatusBadge status={status} />)
    const badge = screen.getByText(status)
    expect(badge).toHaveAttribute("data-status", variant)
  })
})
