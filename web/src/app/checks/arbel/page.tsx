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
  // Alarm menu: { accountId: Set<alarmName> } — empty = account not participating
  const [selectedAlarms, setSelectedAlarms] = useState<Record<string, Set<string>>>({})
  // Track which alarm accordion cards are expanded
  const [expandedAlarmAccounts, setExpandedAlarmAccounts] = useState<Set<string>>(new Set())

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
      if (key === "alarm") {
        setSelectedAlarms({})
        setExpandedAlarmAccounts(new Set())
      }
      return
    }
    setActiveMenu(key)
    setResult(null)
    setError("")
    setSendSlack(false)
    setSelectAll(true)
    setWindowHours(12)

    if (key === "alarm") {
      setSelectedAlarms({})
      setExpandedAlarmAccounts(new Set())
    } else {
      setSelectedAccountIds(accounts.map((a) => a.id))
    }
  }

  const onToggleSelectAll = (checked: boolean) => {
    setSelectAll(checked)
    if (checked) {
      setSelectedAccountIds(accounts.map((a) => a.id))
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

    setIsExecuting(true)
    setError("")
    setResult(null)

    let accountIds: string[] | null = null
    let checkParams: Record<string, unknown> | null = null

    if (menu.key === "alarm") {
      // Build per-account alarm map; skip accounts with no alarms selected
      const accountAlarmNames: Record<string, string[]> = {}
      for (const [accountId, alarms] of Object.entries(selectedAlarms)) {
        if (alarms.size > 0) {
          accountAlarmNames[accountId] = [...alarms]
        }
      }
      const participatingIds = Object.keys(accountAlarmNames)
      if (participatingIds.length === 0) {
        setError("Select at least one alarm.")
        setIsExecuting(false)
        return
      }
      accountIds = participatingIds
      checkParams = { account_alarm_names: accountAlarmNames }
    } else {
      if (selectedAccountIds.length === 0) {
        setError("Select at least one account.")
        setIsExecuting(false)
        return
      }
      accountIds = selectAll ? null : selectedAccountIds
      if (menu.key === "rds") {
        checkParams = { window_hours: windowHours }
      }
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

  const toggleAlarm = (accountId: string, alarmName: string) => {
    setSelectedAlarms((cur) => {
      const next = { ...cur }
      const set = new Set(cur[accountId] ?? [])
      if (set.has(alarmName)) {
        set.delete(alarmName)
      } else {
        set.add(alarmName)
      }
      next[accountId] = set
      return next
    })
  }

  const selectAllAlarmsForAccount = (accountId: string, alarmNames: string[]) => {
    setSelectedAlarms((cur) => ({ ...cur, [accountId]: new Set(alarmNames) }))
  }

  const clearAlarmsForAccount = (accountId: string) => {
    setSelectedAlarms((cur) => ({ ...cur, [accountId]: new Set() }))
  }

  const toggleAlarmAccountExpanded = (accountId: string) => {
    setExpandedAlarmAccounts((cur) => {
      const next = new Set(cur)
      if (next.has(accountId)) {
        next.delete(accountId)
      } else {
        next.add(accountId)
      }
      return next
    })
  }

  const renderAlarmSelector = () => {
    if (alarmAccounts.length === 0) {
      return (
        <p className="checks-help">
          No accounts have alarm_names configured. Run seed_alarms script first.
        </p>
      )
    }

    return (
      <div className="arbel-alarm-accordion">
        {alarmAccounts.map((account) => {
          const alarmNames = getAlarmNames(account)
          const selected = selectedAlarms[account.id] ?? new Set<string>()
          const isExpanded = expandedAlarmAccounts.has(account.id)
          const selectedCount = selected.size
          const allSelected = selectedCount === alarmNames.length && alarmNames.length > 0
          const someSelected = selectedCount > 0 && selectedCount < alarmNames.length

          return (
            <div key={account.id} className="arbel-alarm-account-card">
              <div className="arbel-alarm-account-header">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected
                  }}
                  onChange={() => {
                    if (allSelected || someSelected) {
                      clearAlarmsForAccount(account.id)
                    } else {
                      selectAllAlarmsForAccount(account.id, alarmNames)
                    }
                  }}
                  disabled={isExecuting}
                />
                <span
                  className="arbel-alarm-account-label"
                  onClick={() => toggleAlarmAccountExpanded(account.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && toggleAlarmAccountExpanded(account.id)}
                >
                  {account.display_name} ({account.profile_name})
                </span>
                <span className="arbel-alarm-count-badge">
                  {selectedCount}/{alarmNames.length} selected
                </span>
                <div className="arbel-alarm-account-actions">
                  <button
                    type="button"
                    className="arbel-alarm-action-btn"
                    onClick={() => selectAllAlarmsForAccount(account.id, alarmNames)}
                    disabled={isExecuting}
                  >
                    all
                  </button>
                  <button
                    type="button"
                    className="arbel-alarm-action-btn"
                    onClick={() => clearAlarmsForAccount(account.id)}
                    disabled={isExecuting}
                  >
                    none
                  </button>
                  <button
                    type="button"
                    className="arbel-alarm-action-btn"
                    onClick={() => toggleAlarmAccountExpanded(account.id)}
                  >
                    {isExpanded ? "▲" : "▼"}
                  </button>
                </div>
              </div>

              {isExpanded ? (
                <div className="arbel-alarm-list">
                  {alarmNames.map((name) => (
                    <label key={name} className="arbel-alarm-item">
                      <input
                        type="checkbox"
                        checked={selected.has(name)}
                        onChange={() => toggleAlarm(account.id, name)}
                        disabled={isExecuting}
                      />
                      {name}
                    </label>
                  ))}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    )
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
          </label>
        ))}
      </div>
    </div>
  )

  const renderSubMenu = (menu: MenuConfig) => {
    return (
      <div className="arbel-submenu">
        {menu.key === "alarm" ? renderAlarmSelector() : renderAccountSelector(accounts)}

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
            disabled={isExecuting || (
              menu.key === "alarm"
                ? Object.values(selectedAlarms).every((s) => s.size === 0)
                : selectedAccountIds.length === 0
            )}
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
