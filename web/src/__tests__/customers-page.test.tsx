import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, test, vi } from "vitest"

import CustomersPage from "../app/customers/page"

afterEach(() => {
  cleanup()
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

describe("CustomersPage", () => {
  test("creates customer and adds account", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ customers: [] }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => customerFixture,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ customers: [customerFixture] }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          id: "acc-1",
          profile_name: "aryanoble-prod",
          account_id: "123",
          display_name: "Prod",
          is_active: true,
          config_extra: null,
          created_at: "2026-03-03T00:00:00Z",
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
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
                  config_extra: null,
                  created_at: "2026-03-03T00:00:00Z",
                },
              ],
            },
          ],
        }),
      } as Response)

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

    expect(await screen.findByRole("heading", { name: /aryanoble \(aryanoble\)/i })).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/target customer/i), { target: { value: "cust-1" } })
    fireEvent.change(screen.getByLabelText(/profile name/i), { target: { value: "aryanoble-prod" } })
    fireEvent.change(screen.getByLabelText(/account display name/i), { target: { value: "Prod" } })
    fireEvent.click(screen.getByRole("button", { name: /add account/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/customers/cust-1/accounts",
        expect.objectContaining({ method: "POST" }),
      )
    })

    expect(await screen.findByText(/prod/i)).toBeInTheDocument()
  })

  test("updates bot mapping config for selected customer", async () => {
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
          ...customerFixture,
          slack_enabled: true,
          slack_webhook_url: "https://hooks.slack.com/services/T/B/X",
          slack_channel: "#monitoring",
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          customers: [
            {
              ...customerFixture,
              slack_enabled: true,
              slack_webhook_url: "https://hooks.slack.com/services/T/B/X",
              slack_channel: "#monitoring",
            },
          ],
        }),
      } as Response)

    render(<CustomersPage />)

    expect(await screen.findByRole("heading", { name: /aryanoble \(aryanoble\)/i })).toBeInTheDocument()

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
