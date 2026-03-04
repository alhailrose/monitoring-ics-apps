import { describe, expect, test, vi } from "vitest"

import { apiRequest } from "../api/client"
import { deleteAccount, updateAccount } from "../api/customers"
import { buildHistoryQuery } from "../api/history"

describe("apiRequest", () => {
  test("uses backend detail field for user-facing errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Validation failed" }),
    } as Response)

    await expect(apiRequest("/customers")).rejects.toMatchObject({
      message: "Validation failed",
      status: 400,
    })
  })

  test("returns actionable message on backend server errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ error: "internal" }),
    } as Response)

    await expect(apiRequest("/customers")).rejects.toMatchObject({
      message: expect.stringContaining("Backend server error (500)"),
      status: 500,
    })
  })

  test("returns connection hint when backend is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("Failed to fetch"))

    await expect(apiRequest("/customers")).rejects.toMatchObject({
      message: expect.stringContaining("Cannot connect to backend"),
      status: 0,
    })
  })
})

describe("buildHistoryQuery", () => {
  test("builds stable query string with optional filters", () => {
    const query = buildHistoryQuery({
      customerId: "cust-1",
      startDate: "2026-03-01",
      endDate: "2026-03-03",
      checkMode: "all",
      checkName: "guardduty",
      limit: 25,
      offset: 50,
    })

    expect(query).toContain("customer_id=cust-1")
    expect(query).toContain("start_date=2026-03-01T00%3A00%3A00.000Z")
    expect(query).toContain("end_date=2026-03-03T23%3A59%3A59.999Z")
    expect(query).toContain("check_mode=all")
    expect(query).toContain("check_name=guardduty")
    expect(query).toContain("limit=25")
    expect(query).toContain("offset=50")
  })
})

describe("customers api", () => {
  test("updates and deletes account via /accounts/{id}", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          id: "acc-1",
          profile_name: "aryanoble-prod",
          account_id: "123",
          display_name: "Production",
          is_active: true,
          config_extra: null,
          created_at: "2026-03-03T00:00:00Z",
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
      } as Response)

    await updateAccount("acc-1", { display_name: "Production" })
    await deleteAccount("acc-1")

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/accounts/acc-1",
      expect.objectContaining({ method: "PATCH" }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/accounts/acc-1",
      expect.objectContaining({ method: "DELETE" }),
    )
  })
})
