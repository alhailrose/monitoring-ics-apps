import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, test, vi } from "vitest"

import CustomersPage from "../app/customers/page"
import type { Customer } from "../types/api"

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

const customerFixture = {
  id: "cust-1",
  name: "aryanoble",
  display_name: "Aryanoble",
  checks: [],
  sso_session: null,
  slack_webhook_url: null,
  slack_channel: null,
  slack_enabled: false,
  created_at: "2026-03-03T00:00:00Z",
  updated_at: "2026-03-03T00:00:00Z",
  accounts: [],
}

const sessionFixture = {
  total_profiles: 1,
  ok: 1,
  expired: 0,
  error: 0,
  profiles: [
    {
      profile_name: "aryanoble-prod",
      account_id: "123",
      display_name: "Prod",
      status: "ok",
      error: "",
      sso_session: "",
      login_command: "aws sso login",
    },
  ],
  sso_sessions: {},
}

const jsonResponse = (payload: unknown): Response => {
  return {
    ok: true,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => payload,
  } as Response
}

describe("CustomersPage", () => {
  test("creates customer and adds account", async () => {
    let customersState: { customers: Customer[] } = { customers: [] }
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input)
      const method = init?.method ?? "GET"

      if (url === "/api/v1/sessions/health") {
        return jsonResponse(sessionFixture)
      }

      if (url === "/api/v1/customers" && method === "GET") {
        return jsonResponse(customersState)
      }

      if (url === "/api/v1/customers" && method === "POST") {
        customersState = { customers: [customerFixture] }
        return jsonResponse(customerFixture)
      }

      if (url === "/api/v1/customers/cust-1/accounts" && method === "POST") {
        customersState = {
          customers: [
            {
              ...customerFixture,
              accounts: [
                {
                  id: "acc-1",
                  profile_name: "aryanoble-prod",
                  account_id: "123",
                  display_name: "Prod",
                  is_active: true,
                  region: null,
                  alarm_names: null,
                  config_extra: null,
                  created_at: "2026-03-03T00:00:00Z",
                },
              ],
            },
          ],
        }

        return jsonResponse(customersState.customers[0].accounts[0])
      }

      throw new Error(`Unhandled fetch call: ${method} ${url}`)
    })

    render(<CustomersPage />)

    fireEvent.change(screen.getByLabelText(/^name$/i), { target: { value: "aryanoble" } })
    fireEvent.change(screen.getByLabelText(/^display name$/i), { target: { value: "Aryanoble" } })
    fireEvent.click(screen.getByRole("button", { name: /add customer/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/customers",
        expect.objectContaining({ method: "POST" }),
      )
    })

    expect(
      await screen.findByRole("heading", { name: /aryanoble \(aryanoble\)/i }),
    ).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/target customer/i), { target: { value: "cust-1" } })
    fireEvent.change(screen.getByLabelText(/profile name/i), {
      target: { value: "aryanoble-prod" },
    })
    fireEvent.change(screen.getByLabelText(/account display name/i), { target: { value: "Prod" } })
    fireEvent.click(screen.getByRole("button", { name: /add account/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/customers/cust-1/accounts",
        expect.objectContaining({ method: "POST" }),
      )
    })

    expect(await screen.findByText(/prod \(aryanoble-prod\)/i)).toBeInTheDocument()
  })

  test("updates bot mapping config for selected customer", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input)
      const method = init?.method ?? "GET"

      if (url === "/api/v1/sessions/health") {
        return jsonResponse(sessionFixture)
      }

      if (url === "/api/v1/customers" && method === "GET") {
        return jsonResponse({ customers: [customerFixture] })
      }

      if (url === "/api/v1/customers/cust-1" && method === "PATCH") {
        return jsonResponse({
          ...customerFixture,
          slack_enabled: true,
          slack_webhook_url: "https://hooks.slack.com/services/T/B/X",
          slack_channel: "#monitoring",
        })
      }

      throw new Error(`Unhandled fetch call: ${method} ${url}`)
    })

    render(<CustomersPage />)

    expect(
      await screen.findByRole("heading", { name: /aryanoble \(aryanoble\)/i }),
    ).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/bot customer/i), { target: { value: "cust-1" } })
    fireEvent.change(screen.getByLabelText(/bot webhook url/i), {
      target: { value: "https://hooks.slack.com/services/T/B/X" },
    })
    fireEvent.change(screen.getByLabelText(/bot channel/i), { target: { value: "#monitoring" } })
    fireEvent.click(screen.getByLabelText(/bot enabled/i))
    fireEvent.click(screen.getByRole("button", { name: /save bot mapping/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/customers/cust-1",
        expect.objectContaining({ method: "PATCH" }),
      )
    })
  })
})
