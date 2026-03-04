import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, test, vi } from "vitest"

import ArbelCheckPage from "../app/checks/arbel/page"

afterEach(() => {
  vi.restoreAllMocks()
})

const aryanobleFixture = {
  id: "cust-ary",
  name: "aryanoble",
  display_name: "Aryanoble",
  checks: ["cost", "guardduty", "cloudwatch"],
  slack_webhook_url: null,
  slack_channel: null,
  slack_enabled: false,
  created_at: "2026-03-04T00:00:00Z",
  updated_at: "2026-03-04T00:00:00Z",
  accounts: [
    {
      id: "acc-1",
      profile_name: "aryanoble-prod",
      account_id: "123",
      display_name: "Prod",
      is_active: true,
      config_extra: null,
      created_at: "2026-03-04T00:00:00Z",
    },
    {
      id: "acc-2",
      profile_name: "aryanoble-dev",
      account_id: "456",
      display_name: "Dev",
      is_active: true,
      config_extra: null,
      created_at: "2026-03-04T00:00:00Z",
    },
  ],
}

describe("ArbelCheckPage", () => {
  test("lets user choose arbel features and specific accounts before running", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ customers: [aryanobleFixture] }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          checks: [
            { name: "cost", class: "CostCheck" },
            { name: "guardduty", class: "GuardDutyCheck" },
            { name: "cloudwatch", class: "CloudWatchCheck" },
          ],
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          check_run_id: "run-cost",
          execution_time_seconds: 3.2,
          consolidated_output: "cost output",
          slack_sent: false,
          results: [
            {
              account: { id: "acc-1", profile_name: "aryanoble-prod", display_name: "Prod" },
              check_name: "cost",
              status: "OK",
              summary: "Cost healthy",
              output: "cost result",
            },
          ],
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          check_run_id: "run-guardduty",
          execution_time_seconds: 4.1,
          consolidated_output: "guardduty output",
          slack_sent: false,
          results: [
            {
              account: { id: "acc-1", profile_name: "aryanoble-prod", display_name: "Prod" },
              check_name: "guardduty",
              status: "WARN",
              summary: "Needs review",
              output: "guardduty result",
            },
          ],
        }),
      } as Response)

    render(<ArbelCheckPage />)

    expect(await screen.findByDisplayValue(/aryanoble/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/cost/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/guardduty/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/cloudwatch/i)).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText(/cloudwatch/i))
    fireEvent.click(screen.getByLabelText(/select all accounts/i))
    fireEvent.click(screen.getByLabelText(/prod \(aryanoble-prod\)/i))
    fireEvent.click(screen.getByRole("button", { name: /run selected arbel checks/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(4)
    })

    const executeCalls = fetchMock.mock.calls.slice(2)
    const payloads = executeCalls.map((call) => JSON.parse(String((call[1] as RequestInit).body)))

    expect(payloads).toHaveLength(2)
    expect(payloads.map((payload) => payload.check_name).sort()).toEqual(["cost", "guardduty"])
    expect(payloads.every((payload) => payload.mode === "single")).toBe(true)
    expect(payloads.every((payload) => JSON.stringify(payload.account_ids) === JSON.stringify(["acc-1"]))).toBe(true)

    expect(await screen.findByText(/runs:\s*2/i)).toBeInTheDocument()
    expect(screen.getByText(/guardduty result/i)).toBeInTheDocument()
  })
})
