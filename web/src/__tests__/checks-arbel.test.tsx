import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import ArbelCheckPage from "../app/checks/arbel/page"

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

const makeExecuteResponse = (checkName: string) =>
  ({
    ok: true,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => ({
      check_run_id: `run-${checkName}`,
      execution_time_seconds: 1.5,
      consolidated_output: `${checkName} output`,
      slack_sent: false,
      results: [
        {
          account: { id: "acc-1", profile_name: "aryanoble-prod", display_name: "Prod" },
          check_name: checkName,
          status: "OK",
          summary: `${checkName} healthy`,
          output: `${checkName} result`,
        },
      ],
    }),
  }) as Response

const makeBackupExecuteResponse = (payload: {
  results: Array<{
    account: { id: string; profile_name: string; display_name: string }
    status: "OK" | "WARN" | "ERROR" | "ALARM" | "NO_DATA"
    summary: string
    output: string
  }>
  backup_overviews?: Record<
    string,
    {
      all_success?: boolean
      total_accounts?: number
      ok_accounts_count?: number
      problem_accounts_count?: number
      problem_accounts?: Array<{ display_name?: string; profile?: string }>
    }
  >
}) =>
  ({
    ok: true,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => ({
      check_run_id: "run-backup",
      execution_time_seconds: 1.2,
      consolidated_output: "backup whatsapp ready report",
      slack_sent: false,
      backup_overviews: payload.backup_overviews,
      results: payload.results.map((item) => ({ ...item, check_name: "backup" })),
    }),
  }) as Response

const aryanobleFixture = {
  id: "cust-ary",
  name: "aryanoble",
  display_name: "Aryanoble",
  checks: [],
  sso_session: null,
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
      region: null,
      alarm_names: ["Alarm1", "Alarm2"],
      config_extra: null,
      created_at: "2026-03-04T00:00:00Z",
    },
    {
      id: "acc-2",
      profile_name: "aryanoble-dev",
      account_id: "456",
      display_name: "Dev",
      is_active: true,
      region: null,
      alarm_names: null,
      config_extra: null,
      created_at: "2026-03-04T00:00:00Z",
    },
  ],
}

const mockListCustomers = () =>
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: true,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => ({ customers: [aryanobleFixture] }),
  } as Response)

const mockLocalStorage = () => {
  const store: Record<string, string> = {}
  vi.spyOn(window.localStorage, "getItem").mockImplementation((key: string) => store[key] ?? null)
  vi.spyOn(window.localStorage, "setItem").mockImplementation((key: string, value: string) => {
    store[key] = value
  })
  vi.spyOn(window.localStorage, "removeItem").mockImplementation((key: string) => {
    delete store[key]
  })
  vi.spyOn(window.localStorage, "clear").mockImplementation(() => {
    Object.keys(store).forEach((key) => delete store[key])
  })
  return store
}

describe("ArbelCheckPage", () => {
  beforeEach(() => {
    mockLocalStorage()
  })

  test("renders the page with menu cards after loading", async () => {
    mockListCustomers()

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /backup status/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /rds metrics/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /ec2 metrics/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /alarm verification/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /daily budget/i })).toBeInTheDocument()
  })

  test("ec2 metrics sends daily-arbel with ec2 section scope", async () => {
    const fetchMock = mockListCustomers()
    fetchMock.mockResolvedValueOnce(makeExecuteResponse("daily-arbel"))

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /ec2 metrics/i }))

    const selectAllCheckbox = screen.getByRole("checkbox", { name: /select all/i })
    fireEvent.click(selectAllCheckbox)
    const prodLabel = screen.getAllByText(/aryanoble-prod/i).find((node) => node.closest("label"))?.closest("label")
    expect(prodLabel).toBeTruthy()
    fireEvent.click(prodLabel as HTMLElement)

    fireEvent.click(screen.getByRole("button", { name: /run ec2 metrics/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    const executeCall = fetchMock.mock.calls[1]
    const payload = JSON.parse(String((executeCall[1] as RequestInit).body))
    expect(payload.check_name).toBe("daily-arbel")
    expect(payload.check_params).toEqual({ window_hours: 12, section_scope: "ec2" })
    expect(payload.account_ids).toEqual(["acc-1"])
  })

  test("opens Backup menu and shows account list, runs check with specific accounts", async () => {
    const fetchMock = mockListCustomers()
    fetchMock.mockResolvedValueOnce(makeExecuteResponse("backup"))

    render(<ArbelCheckPage />)

    // Wait for load and open the Backup menu
    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /backup status/i }))

    // Account selector should appear with both accounts
    expect(await screen.findByText(/aryanoble-prod/)).toBeInTheDocument()
    expect(screen.getByText(/aryanoble-dev/)).toBeInTheDocument()

    // Uncheck "Select All" to enable individual selection, then pick only Prod
    const selectAllCheckbox = screen.getByRole("checkbox", { name: /select all/i })
    fireEvent.click(selectAllCheckbox) // deselect all
    const prodLabel = screen.getByText(/aryanoble-prod/i).closest("label")
    expect(prodLabel).toBeTruthy()
    fireEvent.click(prodLabel as HTMLElement)

    // Click Run
    fireEvent.click(screen.getByRole("button", { name: /run backup status/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    const executeCall = fetchMock.mock.calls[1]
    const payload = JSON.parse(String((executeCall[1] as RequestInit).body))
    expect(payload.check_name).toBe("backup")
    expect(payload.account_ids).toEqual(["acc-1"])
    expect(payload.mode).toBe("single")
  })

  test("alarm verification accordion shows only accounts with alarm_names", async () => {
    mockListCustomers()

    render(<ArbelCheckPage />)

    // Wait for load and open the Alarm Verification menu
    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /alarm verification/i }))

    // The accordion card for Prod (has alarms) should appear
    expect(await screen.findByText(/aryanoble-prod/)).toBeInTheDocument()

    // Dev has null alarm_names — it should NOT appear in the alarm accordion
    expect(screen.queryByText(/aryanoble-dev/)).not.toBeInTheDocument()

    // Prod shows 0/2 selected initially
    expect(screen.getByText(/0\/2 selected/)).toBeInTheDocument()
  })

  test("alarm verification: selecting an alarm and running includes account_alarm_names in payload", async () => {
    const fetchMock = mockListCustomers()
    fetchMock.mockResolvedValueOnce(makeExecuteResponse("alarm_verification"))

    render(<ArbelCheckPage />)

    // Wait for load and open the Alarm Verification menu
    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /alarm verification/i }))

    // Expand the Prod account accordion to see individual alarms
    const prodCard = await screen.findByText(/aryanoble-prod/)
    const accountCard = prodCard.closest(".arbel-alarm-account-card")!
    const expandButton = within(accountCard as HTMLElement).getByRole("button", { name: /▼/ })
    fireEvent.click(expandButton)

    // Individual alarm checkboxes should now be visible
    expect(await screen.findByText("Alarm1")).toBeInTheDocument()
    expect(screen.getByText("Alarm2")).toBeInTheDocument()

    // Select Alarm1
    const alarm1Checkbox = screen.getByRole("checkbox", { name: /alarm1/i })
    fireEvent.click(alarm1Checkbox)

    // Badge should update to 1/2
    expect(screen.getByText(/1\/2 selected/)).toBeInTheDocument()

    // Run button should be enabled; click it
    const runButton = screen.getByRole("button", { name: /run alarm verification/i })
    expect(runButton).not.toBeDisabled()
    fireEvent.click(runButton)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    const executeCall = fetchMock.mock.calls[1]
    const payload = JSON.parse(String((executeCall[1] as RequestInit).body))
    expect(payload.check_name).toBe("alarm_verification")
    expect(payload.check_params.account_alarm_names).toEqual({ "acc-1": ["Alarm1"] })
    expect(payload.account_ids).toEqual(["acc-1"])
  })

  test("alarm verification: master checkbox in indeterminate state clears all on click", async () => {
    mockListCustomers()

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /alarm verification/i }))

    // Expand the Prod account accordion
    const prodCard = await screen.findByText(/aryanoble-prod/)
    const accountCard = prodCard.closest(".arbel-alarm-account-card")!
    const expandButton = within(accountCard as HTMLElement).getByRole("button", { name: /▼/ })
    fireEvent.click(expandButton)

    // Select only Alarm1 — puts master checkbox into indeterminate state (1/2 selected)
    const alarm1Checkbox = await screen.findByRole("checkbox", { name: /alarm1/i })
    fireEvent.click(alarm1Checkbox)
    expect(screen.getByText(/1\/2 selected/)).toBeInTheDocument()

    // The master checkbox for the account card (first checkbox in the header)
    const masterCheckbox = within(accountCard as HTMLElement).getAllByRole("checkbox")[0]

    // Click master checkbox — should clear all (indeterminate → clear, not select all)
    fireEvent.click(masterCheckbox)

    // Badge should go back to 0/2 selected
    expect(screen.getByText(/0\/2 selected/)).toBeInTheDocument()
  })

  test("alarm verification: Run button is disabled when no alarms are selected", async () => {
    mockListCustomers()

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /alarm verification/i }))

    await screen.findByText(/aryanoble-prod/)

    // No alarms selected — Run button should be disabled
    const runButton = screen.getByRole("button", { name: /run alarm verification/i })
    expect(runButton).toBeDisabled()
  })

  test("profile manager add/remove/reset updates and persists", async () => {
    mockListCustomers()

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /rds metrics/i }))

    const countBadge = await screen.findByTestId("profile-count-rds")
    expect(countBadge).toHaveTextContent("Ditampilkan 2/2")

    const removeButtons = await screen.findAllByRole("button", { name: /hapus dari daftar/i })
    fireEvent.click(removeButtons[0])
    await waitFor(() => {
      expect(screen.getByTestId("profile-count-rds")).toHaveTextContent("Ditampilkan 1/2")
    })

    const select = screen.getByLabelText(/tambah profil/i)
    fireEvent.change(select, { target: { value: "acc-1" } })
    fireEvent.click(screen.getByRole("button", { name: /tambah ke daftar/i }))
    await waitFor(() => {
      expect(screen.getByTestId("profile-count-rds")).toHaveTextContent("Ditampilkan 2/2")
    })

    fireEvent.click(screen.getByRole("button", { name: /reset ke default/i }))
    await waitFor(() => {
      expect(screen.getByTestId("profile-count-rds")).toHaveTextContent("Ditampilkan 2/2")
    })
  })

  test("visible profiles persist per mode across reloads", async () => {
    window.localStorage.setItem(
      "arbel_visible_profiles",
      JSON.stringify({ rds: ["acc-1"], ec2: ["acc-2"] })
    )
    mockListCustomers()

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /ec2 metrics/i }))
    await waitFor(() => {
      expect(screen.getByTestId("profile-count-ec2")).toHaveTextContent("Ditampilkan 1/2")
    })

    const chips = screen.getAllByLabelText(/profil-active-chip/i)
    expect(chips).toHaveLength(1)
    expect(chips[0]).toHaveTextContent(/aryanoble-dev/)
  })

  test("run button disabled when no visible accounts and select all", async () => {
    mockListCustomers()

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /ec2 metrics/i }))

    const removeButtons = await screen.findAllByRole("button", { name: /hapus dari daftar/i })
    removeButtons.forEach((btn) => fireEvent.click(btn))

    const runButton = screen.getByRole("button", { name: /run ec2 metrics/i })
    expect(runButton).toBeDisabled()
  })

  test("backup renders structured summary from backup_overviews and keeps account details", async () => {
    const fetchMock = mockListCustomers()
    fetchMock.mockResolvedValueOnce(
      makeBackupExecuteResponse({
        backup_overviews: {
          "cust-ary": {
            all_success: false,
            total_accounts: 2,
            ok_accounts_count: 1,
            problem_accounts_count: 1,
            problem_accounts: [{ display_name: "Dev", profile: "aryanoble-dev" }],
          },
        },
        results: [
          {
            account: { id: "acc-1", profile_name: "aryanoble-prod", display_name: "Prod" },
            status: "OK",
            summary: "backup healthy",
            output: "prod backup ok",
          },
          {
            account: { id: "acc-2", profile_name: "aryanoble-dev", display_name: "Dev" },
            status: "ERROR",
            summary: "backup failed",
            output: "dev backup failed",
          },
        ],
      })
    )

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /backup status/i }))
    fireEvent.click(screen.getByRole("button", { name: /run backup status/i }))

    expect(await screen.findByText("Ada gagal")).toBeInTheDocument()
    expect(screen.getByText("Total: 2")).toBeInTheDocument()
    expect(screen.getByText("Sukses: 1")).toBeInTheDocument()
    expect(screen.getByText("Gagal: 1")).toBeInTheDocument()
    const summarySection = screen.getByLabelText(/backup summary/i)
    expect(within(summarySection).getByText("Akun gagal:")).toBeInTheDocument()
    expect(within(summarySection).getByText(/Dev \(aryanoble-dev\)/)).toBeInTheDocument()

    expect(screen.getByRole("heading", { name: /Prod \(aryanoble-prod\)/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /Dev \(aryanoble-dev\)/i })).toBeInTheDocument()
  })

  test("backup summary falls back to derive from results when backup_overviews is missing", async () => {
    const fetchMock = mockListCustomers()
    fetchMock.mockResolvedValueOnce(
      makeBackupExecuteResponse({
        results: [
          {
            account: { id: "acc-1", profile_name: "aryanoble-prod", display_name: "Prod" },
            status: "OK",
            summary: "backup healthy",
            output: "prod backup ok",
          },
          {
            account: { id: "acc-2", profile_name: "aryanoble-dev", display_name: "Dev" },
            status: "WARN",
            summary: "backup warning",
            output: "dev backup warning",
          },
        ],
      })
    )

    render(<ArbelCheckPage />)

    expect(await screen.findByText(/Aryanoble — 2 active accounts/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /backup status/i }))
    fireEvent.click(screen.getByRole("button", { name: /run backup status/i }))

    expect(await screen.findByText("Ada gagal")).toBeInTheDocument()
    expect(screen.getByText("Total: 2")).toBeInTheDocument()
    expect(screen.getByText("Sukses: 1")).toBeInTheDocument()
    expect(screen.getByText("Gagal: 1")).toBeInTheDocument()
    const summarySection = screen.getByLabelText(/backup summary/i)
    expect(within(summarySection).getByText(/Dev \(aryanoble-dev\)/)).toBeInTheDocument()
  })
})
