import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, test, vi } from "vitest"

import ProfilesPage from "../app/profiles/page"

afterEach(() => {
  vi.restoreAllMocks()
})

describe("ProfilesPage", () => {
  test("scans profiles and renders mapped/unmapped groups", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          customers: [
            {
              id: "cust-1",
              name: "aryanoble",
              display_name: "Aryanoble",
              checks: [],
              slack_webhook_url: null,
              slack_channel: null,
              slack_enabled: false,
              created_at: "2026-03-03T00:00:00Z",
              updated_at: "2026-03-03T00:00:00Z",
              accounts: [],
            },
          ],
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          all_profiles: ["aryanoble-prod", "aryanoble-dev"],
          mapped_profiles: ["aryanoble-prod"],
          unmapped_profiles: ["aryanoble-dev"],
        }),
      } as Response)

    render(<ProfilesPage />)

    fireEvent.click(screen.getByRole("button", { name: /scan aws profiles/i }))

    await waitFor(() => {
      expect(screen.getAllByText("aryanoble-prod").length).toBeGreaterThan(0)
    })

    expect(screen.getAllByText("aryanoble-dev").length).toBeGreaterThan(0)
    expect(screen.getByRole("heading", { name: /^mapped profiles$/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /^unmapped profiles$/i })).toBeInTheDocument()
  })
})
