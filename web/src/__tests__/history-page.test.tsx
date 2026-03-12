import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, test, vi } from "vitest"

import HistoryPage from "../app/history/page"

afterEach(() => {
  vi.restoreAllMocks()
})

const customerFixture = {
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
}

describe("HistoryPage", () => {
  test("loads history with query filters and opens detail", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ customers: [customerFixture] }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          total: 1,
          items: [
            {
              check_run_id: "run-1",
              check_mode: "single",
              check_name: "guardduty",
              created_at: "2026-03-03T10:00:00Z",
              execution_time_seconds: 10.5,
              slack_sent: false,
              results_summary: { total: 1, ok: 1, warn: 0, error: 0 },
            },
          ],
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          check_run_id: "run-1",
          customer: {
            id: "cust-1",
            name: "aryanoble",
            display_name: "Aryanoble",
          },
          check_mode: "single",
          check_name: "guardduty",
          created_at: "2026-03-03T10:00:00Z",
          execution_time_seconds: 10.5,
          slack_sent: false,
          results: [
            {
              account: {
                id: "acc-1",
                profile_name: "aryanoble-prod",
                display_name: "Prod",
              },
              check_name: "guardduty",
              status: "OK",
              summary: "No findings",
              output: "detail output",
              details: null,
              created_at: "2026-03-03T10:00:00Z",
            },
          ],
        }),
      } as Response)

    render(<HistoryPage />)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/history?customer_id=cust-1"),
        undefined,
      )
    })

    fireEvent.click(screen.getByRole("button", { name: /view details/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/history/run-1", undefined)
    })

    expect(await screen.findByText("detail output")).toBeInTheDocument()
  })
})
