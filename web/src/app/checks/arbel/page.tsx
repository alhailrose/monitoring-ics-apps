import { useEffect, useMemo, useState } from "react"

import { executeChecks } from "../../../api/checks"
import { toUserMessage } from "../../../api/client"
import { listCustomers } from "../../../api/customers"
import { CopyableOutput } from "../../../components/common/CopyableOutput"
import { LoadingState } from "../../../components/common/LoadingState"
import { StatusBadge } from "../../../components/common/StatusBadge"
import type { Account, Customer, ExecuteCheckResponse } from "../../../types/api"

type ArbelMenu = "backup" | "rds" | "alarm" | "budget"

type MenuConfig = {
  key: ArbelMenu
  label: string
  description: string
  checkName: string
}

const MENUS: MenuConfig[] = [
  {
    key: "backup",
    label: "Backup Status",
    description: "Check AWS Backup job status across accounts",
    checkName: "backup",
  },
  {
    key: "rds",
    label: "RDS / EC2 Metrics",
    description: "Daily RDS & EC2 metric monitoring with threshold alerts",
    checkName: "daily-arbel",
  },
  {
    key: "alarm",
    label: "Alarm Verification",
    description: "Verify CloudWatch alarm states and breach history",
    checkName: "alarm_verification",
  },
  {
    key: "budget",
    label: "Daily Budget",
    description: "Check AWS Budgets threshold and over-budget alerts",
    checkName: "daily-budget",
  },
]

const WINDOW_OPTIONS = [
  { value: 6, label: "6 jam" },
  { value: 12, label: "12 jam" },
  { value: 24, label: "24 jam" },
]

const getAlarmNames = (account: Account): string[] => {
  // Prefer top-level typed field (populated by reimport_yaml_configs)
  if (account.alarm_names && account.alarm_names.length > 0) {
    return account.alarm_names
  }
  // Fallback: legacy config_extra path (for accounts not yet re-imported)
  const extra = account.config_extra as Record<string, unknown> | null
  if (!extra) return []
  const av = extra.alarm_verification as Record<string, unknown> | undefined
  if (!av) return []
  const names = av.alarm_names
  return Array.isArray(names) ? (names as string[]) : []
}

const hasAlarms = (account: Account): boolean => getAlarmNames(account).length > 0

export default function ArbelCheckPage() {
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")

  const [activeMenu, setActiveMenu] = useState<ArbelMenu | null>(null)

  // Per-menu state
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([])
  const [selectAll, setSelectAll] = useState(true)
  const [windowHours, setWindowHours] = useState(12)
  const [sendSlack, setSendSlack] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [result, setResult] = useState<ExecuteCheckResponse | null>(null)

  const accounts = useMemo(() => {
    if (!customer) return []
    return customer.accounts.filter((a) => a.is_active)
  }, [customer])

  // For alarm verification, only show accounts that have alarm_names
  const alarmAccounts = useMemo(() => accounts.filter(hasAlarms), [accounts])

  useEffect(() => {
    let mounted = true
    const load = async () => {
      setIsLoading(true)
      setError("")
      try {
        const rows = await listCustomers()
        if (!mounted) return
        const arbel =
          rows.find((c) => c.name.toLowerCase() === "aryanoble") ||
          rows.find((c) => c.display_name.toLowerCase().includes("aryanoble")) ||
          null
        if (!arbel) {
          setError("Aryanoble customer not found.")
          return
        }
        setCustomer(arbel)
      } catch (e) {
        if (mounted) setError(toUserMessage(e, "Failed to load."))
      } finally {
        if (mounted) setIsLoading(false)
      }
    }
    void load()
    return () => { mounted = false }
  }, [])

  const onToggleMenu = (key: ArbelMenu) => {
    if (activeMenu === key) {
      setActiveMenu(null)
      return
    }
    setActiveMenu(key)
    setResult(null)
    setError("")
    setSendSlack(false)
    setSelectAll(true)
    setWindowHours(12)

    // Pre-select accounts based on menu
    if (key === "alarm") {
      setSelectedAccountIds(alarmAccounts.map((a) => a.id))
    } else {
      setSelectedAccountIds(accounts.map((a) => a.id))
    }
  }

  const onToggleSelectAll = (checked: boolean) => {
    setSelectAll(checked)
    if (checked) {
      const pool = activeMenu === "alarm" ? alarmAccounts : accounts
      setSelectedAccountIds(pool.map((a) => a.id))
    } else {
      setSelectedAccountIds([])
    }
  }

  const toggleAccount = (id: string) => {
    setSelectedAccountIds((cur) =>
      cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]
    )
  }

  const onRun = async (menu: MenuConfig) => {
    if (!customer) return
    if (selectedAccountIds.length === 0) {
      setError("Select at least one account.")
      return
    }

    setIsExecuting(true)
    setError("")
    setResult(null)

    const accountIds = selectAll ? null : selectedAccountIds

    // Build check_params based on menu
    let checkParams: Record<string, unknown> | null = null
    if (menu.key === "rds") {
      checkParams = { window_hours: windowHours }
    }

    try {
      const run = await executeChecks({
        customer_id: customer.id,
        mode: "single",
        check_name: menu.checkName,
        account_ids: accountIds,
        send_slack: sendSlack,
        check_params: checkParams,
      })
      setResult(run)
    } catch (e) {
      setError(toUserMessage(e, `Failed to execute ${menu.label}.`))
    } finally {
      setIsExecuting(false)
    }
  }

  const renderAccountSelector = (pool: Account[]) => (
    <div className="arbel-accounts">
      <label className="checks-inline-checkbox">
        <input
          type="checkbox"
          checked={selectAll}
          onChange={(e) => onToggleSelectAll(e.target.checked)}
          disabled={isExecuting}
        />
        Select All ({pool.length})
      </label>
      <div className="checks-account-list">
        {pool.length === 0 ? (
          <p className="checks-help">No accounts available.</p>
        ) : null}
        {pool.map((account) => (
          <label key={account.id} className="checks-inline-checkbox">
            <input
              type="checkbox"
              checked={selectedAccountIds.includes(account.id)}
              onChange={() => toggleAccount(account.id)}
              disabled={selectAll || isExecuting}
            />
            {account.display_name} ({account.profile_name})
            {activeMenu === "alarm" ? (
              <span className="arbel-alarm-count">
                {getAlarmNames(account).length} alarms
              </span>
            ) : null}
          </label>
        ))}
      </div>
    </div>
  )

  const renderSubMenu = (menu: MenuConfig) => {
    const pool = menu.key === "alarm" ? alarmAccounts : accounts

    return (
      <div className="arbel-submenu">
        {renderAccountSelector(pool)}

        {menu.key === "rds" ? (
          <div className="arbel-option-row">
            <label htmlFor="arbel-window">Monitoring Window</label>
            <select
              id="arbel-window"
              className="ops-input"
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
              disabled={isExecuting}
            >
              {WINDOW_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        ) : null}

        {menu.key === "alarm" && alarmAccounts.length === 0 ? (
          <p className="checks-help">
            No accounts have alarm_names configured. Run seed_alarms script first.
          </p>
        ) : null}

        <div className="arbel-run-row">
          <label className="checks-inline-checkbox">
            <input
              type="checkbox"
              checked={sendSlack}
              onChange={(e) => setSendSlack(e.target.checked)}
              disabled={isExecuting}
            />
            Send to Slack
          </label>
          <button
            className="ops-button"
            type="button"
            onClick={() => onRun(menu)}
            disabled={isExecuting || selectedAccountIds.length === 0}
          >
            {isExecuting ? "Running..." : `Run ${menu.label}`}
          </button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <main className="ops-page checks-page" aria-labelledby="arbel-title">
        <section className="ops-glass-panel checks-header">
          <h1 id="arbel-title">Arbel Check</h1>
          <p>Aryanoble monitoring suite</p>
        </section>
        <section className="ops-glass-panel checks-form-panel">
          <LoadingState title="Loading Aryanoble configuration..." />
        </section>
      </main>
    )
  }

  return (
    <main className="ops-page checks-page" aria-labelledby="arbel-title">
      <section className="ops-glass-panel checks-header">
        <h1 id="arbel-title">Arbel Check</h1>
        <p>
          {customer
            ? `${customer.display_name} — ${accounts.length} active accounts`
            : "Aryanoble monitoring suite"}
        </p>
      </section>

      <div className="arbel-menu-grid">
        {MENUS.map((menu) => {
          const isOpen = activeMenu === menu.key
          return (
            <section
              key={menu.key}
              className={`ops-glass-panel arbel-menu-card${isOpen ? " arbel-menu-open" : ""}`}
            >
              <button
                type="button"
                className="arbel-menu-header"
                onClick={() => onToggleMenu(menu.key)}
                aria-expanded={isOpen}
              >
                <div>
                  <h2>{menu.label}</h2>
                  <p>{menu.description}</p>
                </div>
                <span className="arbel-chevron">{isOpen ? "\u25B2" : "\u25BC"}</span>
              </button>

              {isOpen ? renderSubMenu(menu) : null}
            </section>
          )
        })}
      </div>

      {error ? (
        <section className="ops-glass-panel">
          <p className="form-error" role="alert">{error}</p>
        </section>
      ) : null}

      {isExecuting ? (
        <section className="ops-glass-panel">
          <LoadingState />
        </section>
      ) : null}

      {result ? (
        <section className="ops-glass-panel checks-result" aria-label="Check output">
          <p className="checks-meta">
            Execution time: {result.execution_time_seconds}s
          </p>
          <CopyableOutput title="Output" text={result.consolidated_output} />

          {result.results.map((item, index) => (
            <article
              key={`${item.account.id}-${item.check_name}-${index}`}
              className="checks-result-row"
            >
              <header>
                <h2>
                  {item.account.display_name} ({item.account.profile_name})
                </h2>
                <StatusBadge status={item.status} />
              </header>
              <p>{item.summary}</p>
              <CopyableOutput
                title={`${item.check_name} Output`}
                text={item.output || item.summary}
              />
            </article>
          ))}
        </section>
      ) : null}
    </main>
  )
}
