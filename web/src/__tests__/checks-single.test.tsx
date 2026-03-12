import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, test, vi } from "vitest"

import SingleCheckPage from "../app/checks/single/page"

afterEach(() => {
  vi.restoreAllMocks()
})

const customerFixture = {
  id: "cust-1",
  name: "aryanoble",
  display_name: "Aryanoble",
  checks: ["cost", "guardduty"],
  slack_webhook_url: null,
  slack_channel: null,
  slack_enabled: false,
  created_at: "2026-03-03T00:00:00Z",
  updated_at: "2026-03-03T00:00:00Z",
  accounts: [
    {
      id: "acc-1",
      profile_name: "aryanoble-prod",
      account_id: "123",
      display_name: "Prod",
      is_active: true,
      config_extra: null,
      created_at: "2026-03-03T00:00:00Z",
    },
  ],
}

describe("SingleCheckPage", () => {
  test("submits synchronous execute payload and renders copyable output", async () => {
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
        json: async () => ({ checks: [{ name: "guardduty", class: "GuardDutyCheck" }] }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          check_runs: [{ customer_id: "cust-1", check_run_id: "run-1", slack_sent: false }],
          execution_time_seconds: 12.4,
          consolidated_output: "=== report ===",
          results: [
            {
              customer_id: "cust-1",
              account: {
                id: "acc-1",
                profile_name: "aryanoble-prod",
                display_name: "Prod",
              },
              check_name: "guardduty",
              status: "OK",
              summary: "No findings",
              output: "guardduty output",
            },
          ],
        }),
      } as Response)

    render(<SingleCheckPage />)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/customers", undefined)
    })

    fireEvent.change(screen.getByLabelText(/^check type$/i), { target: { value: "guardduty" } })
    const selectAllCheckbox = screen.getByLabelText(/select all accounts/i) as HTMLInputElement
    expect(selectAllCheckbox.checked).toBe(false)
    const prodLabel = screen.getByText(/aryanoble-prod/i).closest("label")
    expect(prodLabel).toBeTruthy()
    fireEvent.click(prodLabel as HTMLElement)
    fireEvent.click(screen.getByRole("button", { name: /run single check/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/checks/execute",
        expect.objectContaining({
          method: "POST",
        }),
      )
    })

    const submitCall = fetchMock.mock.calls[2]
    expect(submitCall).toBeTruthy()
    const init = submitCall[1] as RequestInit
    expect(init.body).toBe(
      JSON.stringify({
        customer_ids: ["cust-1"],
        mode: "single",
        check_name: "guardduty",
        account_ids: ["acc-1"],
        send_slack: false,
      }),
    )

    expect(await screen.findByText(/execution time: 12.4s/i)).toBeInTheDocument()
    expect(screen.getByText("=== report ===")).toBeInTheDocument()
    expect(screen.getByText("guardduty output")).toBeInTheDocument()
  })
})
